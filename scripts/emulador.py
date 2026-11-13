#!/usr/bin/env python3
"""Ciclo de vida do AWS Emulator para os testes de integração do ASH. Só biblioteca padrão.

O emulador só sobe por `python ash.py emulador iniciar` (ou pelo `ci`, quando ASH_EMULADOR_AUTO=sim).
Nada é instalado como serviço, tarefa agendada ou início automático, e o .wslconfig nunca é alterado.
Todo início usa --idle-timeout, então um emulador esquecido se encerra sozinho.

Três modos, escolhidos por ASH_EMULADOR_MODO (vazio: detecção automática, nesta ordem):
  linux      pacote nativo (RPM ou DEB) instalado em Linux
  wsl        no Windows, o pacote nativo instalado dentro de uma distribuição WSL2 própria, sem Docker
  container  imagem construída com o Dockerfile da AWS, no CLI de ASH_CONTAINER_CLI (docker ou podman)

As chaves que o emulador gera nunca são impressas nem copiadas: este módulo só confere o prefixo do ID
da chave, em memória, e passa o CAMINHO dos arquivos para o processo filho.
Fontes das afirmações sobre o emulador, o WSL e o Docker: docs/spec-ash-v4.md, seção 5.4.
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import socket
import ssl
import subprocess
import time
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent.parent
DIR = RAIZ / ".ash" / "emulador"
ESTADO = DIR / "estado.json"
LOG = DIR / "emulador.log"
HOME_LOCAL = DIR / "home"
PORTA_PADRAO = 9297
IDLE_PADRAO = 1800
ESPERA_PRONTO = 30
CONTA_EMULADOR = "000000000000"
IMAGEM = "ash-aws-emulator"
MODOS = ("linux", "wsl", "container")
# Distribuições internas de runtimes de contêiner não servem para hospedar o emulador.
DISTROS_IGNORADAS = {"docker-desktop", "docker-desktop-data", "rancher-desktop", "rancher-desktop-data",
                     "podman-machine-default"}
BASE_PACOTES = "https://downloads.aws.com/aws-emulator/packages/aws-emulator/LTS/"
REMOVER_EXATAS = {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_SECURITY_TOKEN",
                  "AWS_PROFILE", "AWS_DEFAULT_PROFILE", "AWS_WEB_IDENTITY_TOKEN_FILE", "AWS_ROLE_ARN",
                  "AWS_ROLE_SESSION_NAME", "AWS_USE_FIPS_ENDPOINT", "AWS_USE_DUALSTACK_ENDPOINT"}
REMOVER_PREFIXOS = ("AWS_CONTAINER_CREDENTIALS_", "AWS_CONTAINER_AUTHORIZATION_TOKEN", "AWS_ENDPOINT_URL_",
                    "AWS_SSO")
SERVICOS_PROVA = ("sts",)


class ErroEmulador(Exception):
    """Falha esperada do ciclo de vida do emulador, com mensagem pronta para o usuário."""


def agora() -> datetime:
    """Instante atual em UTC."""
    return datetime.now(timezone.utc)


def valor(cfg: dict, chave: str, padrao: str = "") -> str:
    """Valor de uma variável ASH_EMULADOR_*: ambiente do processo primeiro, depois o config.env."""
    return (os.environ.get(chave) or (cfg or {}).get(chave) or padrao).strip()


def _inteiro(texto: str, padrao: int, minimo: int, maximo: int) -> int:
    try:
        n = int(texto)
    except (TypeError, ValueError):
        return padrao
    return n if minimo <= n <= maximo else padrao


def porta(cfg: dict) -> int:
    """Porta HTTPS do emulador (ASH_EMULADOR_PORTA, padrão 9297)."""
    return _inteiro(valor(cfg, "ASH_EMULADOR_PORTA"), PORTA_PADRAO, 1, 65535)


def idle(cfg: dict) -> int:
    """Segundos sem chamadas de API até o emulador se encerrar (ASH_EMULADOR_IDLE, padrão 1800)."""
    return _inteiro(valor(cfg, "ASH_EMULADOR_IDLE"), IDLE_PADRAO, 1, 31536000)


def auto_ci(cfg: dict) -> bool:
    """Se o ci pode subir e parar o emulador sozinho (ASH_EMULADOR_AUTO=sim)."""
    return valor(cfg, "ASH_EMULADOR_AUTO").lower() in ("sim", "on", "true", "1")


# ---------------------------------------------------------------- perfil: bloco emulador_aws
def validar_bloco(bloco) -> list[str]:
    """Confere o bloco emulador_aws do perfil de stack e devolve a lista de erros."""
    if not isinstance(bloco, dict):
        return ["emulador_aws deve ser um objeto"]
    erros = []
    corte = bloco.get("fidelidade_minima", 80)
    if isinstance(corte, bool) or not isinstance(corte, (int, float)) or not 0 <= corte <= 100:
        erros.append("emulador_aws.fidelidade_minima deve ser um número de 0 a 100")
    servicos = bloco.get("servicos")
    if not isinstance(servicos, list) or not servicos:
        erros.append("emulador_aws.servicos deve ser uma lista com ao menos um serviço")
        servicos = []
    for s in servicos:
        if not isinstance(s, dict) or not s.get("nome"):
            erros.append("cada serviço de emulador_aws.servicos precisa de nome")
            continue
        f = s.get("fidelidade")
        if f is not None and (isinstance(f, bool) or not isinstance(f, (int, float)) or not 0 <= f <= 100):
            erros.append(f"fidelidade de {s['nome']} deve ser null ou um número de 0 a 100")
    if "versao" in bloco and not isinstance(bloco["versao"], str):
        erros.append("emulador_aws.versao deve ser texto, por exemplo 1.0.343")
    return erros


ARQ_BLOCO_HARNESS = RAIZ / "tests_harness_integracao" / "emulador.json"
RE_BOTO3_EXATO = re.compile(r"^\s*boto3\s*==\s*\S+", re.I | re.M)
RE_BOTO3_QUALQUER = re.compile(r"^\s*boto3\b", re.I | re.M)


def bloco_do_harness() -> dict:
    """Bloco emulador_aws dos testes de integração do próprio harness (tests_harness_integracao/emulador.json)."""
    nome = "tests_harness_integracao/emulador.json"
    try:
        dados = json.loads(ARQ_BLOCO_HARNESS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ErroEmulador(f"Não consegui ler {nome}: {e}")
    erros = validar_bloco(dados)
    if erros:
        raise ErroEmulador(f"{nome} inválido: " + "; ".join(erros))
    return dados


def aviso_boto3(bloco: dict | None, requirements: str) -> str:
    """Aviso se o perfil declara emulador_aws e o requirements.txt do projeto não fixa o boto3 com versão exata.

    O boto3 do projeto precisa estar no requirements.txt para a etapa dependencias (pip-audit) auditá-lo."""
    if not bloco:
        return ""
    if RE_BOTO3_EXATO.search(requirements or ""):
        return ""
    if RE_BOTO3_QUALQUER.search(requirements or ""):
        return ("o perfil declara emulador_aws, mas o boto3 do requirements.txt não tem versão exata (use boto3==X.Y.Z); "
                "sem versão exata o pip-audit e o emulador não testam sempre a mesma coisa")
    return ("o perfil declara emulador_aws, mas o requirements.txt não declara o boto3. Declare boto3 com versão exata "
            "(boto3==X.Y.Z) no requirements.txt do projeto: a etapa dependencias só audita esse arquivo")


def servicos_abaixo_do_corte(bloco: dict | None) -> list[str]:
    """Serviços do perfil com fidelidade abaixo do corte; fidelidade null conta como abaixo."""
    if not bloco:
        return []
    corte = bloco.get("fidelidade_minima", 80)
    return [s["nome"] for s in bloco.get("servicos", [])
            if s.get("fidelidade") is None or s["fidelidade"] < corte]


def exige_homologacao(bloco: dict | None, faixa: str) -> bool:
    """Regra de fidelidade por faixa: crítica sempre; semiautônoma só se há serviço abaixo do corte."""
    if not bloco:
        return False
    if faixa == "critica":
        return True
    return faixa == "semiautonoma" and bool(servicos_abaixo_do_corte(bloco))


def evidencia(bloco: dict | None, resultados: list[tuple[str, str]]) -> dict:
    """Campos de evidência do emulador para o detalhe do evento ci_executado."""
    if not bloco:
        return {"emulador": "nao_aplicavel"}
    estados = [st for _, st in resultados]
    if "FALHOU" in estados:
        situacao = "falhou"
    elif "PULADA" in estados:
        situacao = "pulado"
    elif "OK" in estados:
        situacao = "ok"
    else:
        situacao = "nao_aplicavel"
    return {"emulador": situacao, "emulador_versao": str(bloco.get("versao", "")),
            "servicos_abaixo_do_corte": ",".join(servicos_abaixo_do_corte(bloco))}


# ---------------------------------------------------------------- pacote e arquitetura
def arquitetura(maquina: str | None = None) -> str:
    """Arquitetura do pacote da AWS para esta máquina: x86_64 ou aarch64."""
    m = (maquina or platform.machine()).lower()
    if m in ("amd64", "x86_64", "x64"):
        return "x86_64"
    if m in ("arm64", "aarch64"):
        return "aarch64"
    raise ErroEmulador(f"Arquitetura {m} sem pacote do AWS Emulator (há x86_64 e aarch64)")


def url_pacote(bloco: dict | None, arq: str) -> str:
    """URL do RPM: versão fixada do perfil (aws-emulator-<versao>-1-<arq>.rpm) ou, sem versão, o latest."""
    bloco = bloco or {}
    base = bloco.get("pacote_url_base") or BASE_PACOTES
    versao = bloco.get("versao")
    if versao:
        return f"{base}aws-emulator-{versao}-1-{arq}.rpm"
    return f"{base}latest/aws-emulator-{arq}.rpm"


# ---------------------------------------------------------------- execução e detecção
def decodificar(dados: bytes) -> str:
    """Decodifica a saída de um comando; o wsl.exe escreve em UTF-16."""
    if b"\x00" in dados:
        return dados.decode("utf-16-le", errors="replace").replace("\ufeff", "")
    return dados.decode("utf-8", errors="replace")


def rodar_captura(cmd: list[str], timeout: int = 20) -> tuple[int, str]:
    """Roda um comando, sem shell, e devolve (código de saída, saída). Falha de execução vira 127."""
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""
    return r.returncode, decodificar(r.stdout) + decodificar(r.stderr)


def distros_wsl(executar=rodar_captura, which=shutil.which) -> list[dict]:
    """Distribuições WSL instaladas (nome, estado, versão), lidas de `wsl --list --verbose` sem iniciar nenhuma."""
    wsl = which("wsl.exe") or which("wsl")
    if not wsl:
        return []
    rc, saida = executar([wsl, "--list", "--verbose"])
    if rc != 0:
        return []
    achadas = []
    for linha in saida.splitlines():
        partes = linha.replace("*", " ").split()
        if len(partes) >= 3 and partes[-1] in ("1", "2") and partes[0].upper() != "NAME":
            achadas.append({"nome": partes[0], "estado": partes[1], "versao": int(partes[-1])})
    return achadas


def detectar_modos(cfg: dict, sistema: str | None = None, which=shutil.which, executar=rodar_captura) -> dict:
    """Diz, para cada modo, se está disponível e por quê. Não instala nem inicia nada."""
    sistema = sistema or platform.system()
    res: dict = {}
    if sistema != "Linux":
        res["linux"] = {"ok": False, "motivo": "o pacote nativo só roda em Linux", "detalhe": {}}
    elif which("aws-emulator"):
        res["linux"] = {"ok": True, "motivo": "comando aws-emulator encontrado", "detalhe": {}}
    else:
        res["linux"] = {"ok": False, "detalhe": {},
                        "motivo": "comando aws-emulator ausente; instale o pacote RPM ou DEB (README, seção Testes contra o AWS Emulator)"}
    if sistema != "Windows":
        res["wsl"] = {"ok": False, "motivo": "o modo wsl existe só no Windows", "detalhe": {}}
    else:
        pedida = valor(cfg, "ASH_EMULADOR_WSL_DISTRO")
        distros = [d for d in distros_wsl(executar, which)
                   if d["nome"].lower() not in DISTROS_IGNORADAS and d["versao"] == 2]
        if pedida:
            distros = [d for d in distros if d["nome"] == pedida]
        if distros:
            res["wsl"] = {"ok": True, "motivo": f"distribuição WSL2 {distros[0]['nome']} encontrada",
                          "detalhe": {"distro": distros[0]["nome"], "wsl": which("wsl.exe") or which("wsl")}}
        else:
            res["wsl"] = {"ok": False, "detalhe": {},
                          "motivo": "nenhuma distribuição WSL2 própria (as internas de runtimes de contêiner não valem); "
                                    "instale uma e o pacote aws-emulator dentro dela"}
    cli_pedido = valor(cfg, "ASH_CONTAINER_CLI")
    candidatos = [cli_pedido] if cli_pedido else ["docker", "podman"]
    motivo = "nenhum runtime de contêiner (docker ou podman) encontrado"
    res["container"] = {"ok": False, "motivo": motivo, "detalhe": {}}
    for cli in candidatos:
        if not which(cli):
            continue
        rc, _ = executar([cli, "info"])
        if rc == 0:
            res["container"] = {"ok": True, "motivo": f"{cli} ativo", "detalhe": {"cli": cli}}
            break
        res["container"] = {"ok": False, "detalhe": {},
                            "motivo": f"{cli} instalado, mas o daemon ou a máquina virtual não responde; inicie-o antes"}
    return res


def escolher_modo(cfg: dict, deteccao: dict) -> str:
    """Modo pedido em ASH_EMULADOR_MODO ou, se vazio, o primeiro disponível (linux, wsl, container)."""
    pedido = valor(cfg, "ASH_EMULADOR_MODO").lower()
    if pedido:
        if pedido not in MODOS:
            raise ErroEmulador(f"ASH_EMULADOR_MODO={pedido} inválido; use linux, wsl ou container")
        if not deteccao[pedido]["ok"]:
            raise ErroEmulador(f"Modo {pedido} indisponível: {deteccao[pedido]['motivo']}")
        return pedido
    for modo in MODOS:
        if deteccao[modo]["ok"]:
            return modo
    linhas = "\n".join(f"  - {m}: {deteccao[m]['motivo']}" for m in MODOS)
    raise ErroEmulador("Nenhum modo do emulador está disponível:\n" + linhas)


# ---------------------------------------------------------------- comandos (puros, testáveis)
def comando_linux(binario: str, porta_: int, idle_: int) -> list[str]:
    """Comando do emulador nativo: telemetria desligada e encerramento por inatividade."""
    return [binario, "-p", str(porta_), "--telemetry", "off", "--idle-timeout", str(idle_)]


def comando_wsl(wsl: str, distro: str, porta_: int, idle_: int) -> list[str]:
    """Comando que, no Windows, inicia o emulador dentro da distribuição WSL2."""
    return [wsl, "-d", distro, "--"] + comando_linux("aws-emulator", porta_, idle_)


def comando_parar_wsl(wsl: str, distro: str, porta_: int) -> list[str]:
    """Comando que envia SIGTERM ao emulador daquela porta dentro da distribuição WSL2."""
    return [wsl, "-d", distro, "--", "pkill", "-TERM", "-f", f"aws-emulator -p {porta_} "]


def comando_container_run(cli: str, nome: str, porta_: int, idle_: int, pasta_host: str, imagem: str,
                          usuario: str | None = None) -> list[str]:
    """docker run (ou podman run) publicando só em 127.0.0.1, com 2 GiB de memória e sem swap."""
    cmd = [cli, "run", "-d", "--rm", "--name", nome, "--memory=2g", "--memory-swap=2g",
           "-p", f"127.0.0.1:{porta_}:{porta_}", "-v", f"{pasta_host}:/home/emulator/.aws/emulator"]
    if usuario:
        cmd += ["--user", usuario]
    return cmd + [imagem, "-p", str(porta_), "--telemetry", "off", "--idle-timeout", str(idle_)]


def comando_container_build(cli: str, imagem: str, url_rpm: str) -> list[str]:
    """Comando que constrói a imagem com o Dockerfile da documentação da AWS (infra/emulador/Dockerfile)."""
    pasta = RAIZ / "infra" / "emulador"
    return [cli, "build", "-t", imagem, "--build-arg", f"EMULATOR_RPM_URL={url_rpm}",
            "-f", str(pasta / "Dockerfile"), str(pasta)]


def unc_wsl(distro: str, home_linux: str, porta_: int) -> str:
    """Caminho no Windows (\\\\wsl$) da pasta que o emulador usa dentro do WSL para aquela porta."""
    home = home_linux.strip().replace("/", "\\")
    return f"\\\\wsl$\\{distro}{home}\\.aws\\emulator\\{porta_}"


# ---------------------------------------------------------------- ambiente isolado e provas
def _removivel(nome: str) -> bool:
    n = nome.upper()
    return n in REMOVER_EXATAS or any(n.startswith(p) for p in REMOVER_PREFIXOS)


def ambiente_isolado(base: dict, endpoint: str, pasta: Path) -> dict:
    """Cópia do ambiente para o processo filho: sem credenciais reais, apontando só para o emulador.

    Vale só para o filho: nunca vai para o os.environ do ash.py nem para ~/.aws/config."""
    env = {k: v for k, v in base.items() if not _removivel(k)}
    env.update({
        "AWS_ENDPOINT_URL": endpoint,
        "AWS_SHARED_CREDENTIALS_FILE": str(Path(pasta) / "emulator_credentials"),
        "AWS_CONFIG_FILE": str(Path(pasta) / "config"),
        "AWS_CA_BUNDLE": str(Path(pasta) / "ca.pem"),
        "AWS_EC2_METADATA_DISABLED": "true",
        "AWS_DISABLE_HOST_PREFIX_INJECTION": "true",
        "AWS_REGION": "us-east-1",
        "AWS_DEFAULT_REGION": "us-east-1",
        "PYTHONUTF8": "1",
    })
    for chave in ("NO_PROXY", "no_proxy"):
        atual = env.get(chave, "")
        if "127.0.0.1" not in atual:
            env[chave] = (atual + "," if atual else "") + "127.0.0.1"
    return env


def verificar_endpoint_local(endpoint: str, porta_: int) -> None:
    """Recusa qualquer endpoint que não seja https://127.0.0.1:<porta>."""
    p = urlparse(endpoint)
    if p.scheme != "https" or p.hostname != "127.0.0.1" or p.port != porta_:
        raise ErroEmulador(f"Endpoint recusado: só https://127.0.0.1:{porta_} é aceito (host recebido: {p.hostname})")


def verificar_credenciais(arquivo: Path) -> None:
    """Confere, em memória, que o ID da chave começa com EMULATOR; nunca devolve nem imprime a chave."""
    try:
        texto = Path(arquivo).read_text(encoding="utf-8")
    except OSError:
        raise ErroEmulador("Arquivo de credenciais do emulador não encontrado: o emulador está de pé?")
    achado = re.search(r"^\s*aws_access_key_id\s*=\s*(\S+)", texto, re.M | re.I)
    if not achado or not achado.group(1).startswith("EMULATOR"):
        raise ErroEmulador("As credenciais não são as geradas pelo emulador (o ID da chave deve começar com EMULATOR). "
                           "Nada foi enviado.")


def saude(endpoint: str, ca: Path, timeout: float = 3) -> bool:
    """GET /__admin/health com o certificado do emulador; True se responder 200 com o corpo ok."""
    try:
        ctx = ssl.create_default_context(cafile=str(ca))
        abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ctx))
        with abridor.open(endpoint + "/__admin/health", timeout=timeout) as r:
            return r.status == 200 and r.read().strip() == b"ok"
    except (OSError, ssl.SSLError, ValueError):
        return False


def porta_em_uso(porta_: int) -> bool:
    """True se algo já escuta em 127.0.0.1:<porta>."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", porta_)) == 0


# ---------------------------------------------------------------- estado local (sem chaves)
def ler_estado() -> dict | None:
    """Estado gravado pelo `emulador iniciar` (modo, porta, caminhos), ou None."""
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def gravar_estado(estado: dict) -> None:
    """Grava o estado em .ash/emulador/estado.json (pasta fora do git; sem chaves)."""
    DIR.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def limpar_estado() -> None:
    """Apaga o estado local."""
    try:
        ESTADO.unlink()
    except OSError:
        pass


def pasta_arquivos(estado: dict) -> Path:
    """Pasta com emulator_credentials, config e ca.pem do emulador em execução."""
    return Path(estado["pasta_arquivos"])


def de_pe(estado: dict | None) -> bool:
    """True se há estado gravado e o emulador responde ao health check."""
    if not estado:
        return False
    return saude(estado["endpoint"], pasta_arquivos(estado) / "ca.pem")


def ambiente_do_estado(estado: dict, base: dict) -> dict:
    """Ambiente do processo filho para o emulador em execução, depois de todas as provas de que é local."""
    verificar_endpoint_local(estado["endpoint"], estado["porta"])
    pasta = pasta_arquivos(estado)
    verificar_credenciais(pasta / "emulator_credentials")
    if not (pasta / "ca.pem").exists():
        raise ErroEmulador("Certificado do emulador (ca.pem) não encontrado: o emulador está de pé?")
    return ambiente_isolado(base, estado["endpoint"], pasta)


# ---------------------------------------------------------------- iniciar, parar, status
def _log():
    DIR.mkdir(parents=True, exist_ok=True)
    return open(LOG, "ab")


def _sinalizadores_destacado() -> dict:
    if os.name == "nt":
        return {"creationflags": 0x00000008 | 0x00000200 | 0x08000000}  # DETACHED | NEW_PROCESS_GROUP | NO_WINDOW
    return {"start_new_session": True}


def _subir_linux(estado: dict, det: dict, cfg: dict) -> None:
    binario = shutil.which("aws-emulator") or "aws-emulator"
    pasta_home = HOME_LOCAL
    (pasta_home / ".aws" / "emulator").mkdir(parents=True, exist_ok=True)
    with _log() as log:
        proc = subprocess.Popen(comando_linux(binario, estado["porta"], estado["idle"]), stdout=log, stderr=log,
                                env={**os.environ, "HOME": str(pasta_home)}, **_sinalizadores_destacado())
    estado["pid"] = proc.pid
    estado["pasta_arquivos"] = str(pasta_home / ".aws" / "emulator" / str(estado["porta"]))


def _subir_wsl(estado: dict, det: dict, cfg: dict) -> None:
    wsl, distro = det["wsl"], det["distro"]
    rc, _ = rodar_captura([wsl, "-d", distro, "--", "sh", "-c", "command -v aws-emulator"])
    if rc != 0:
        raise ErroEmulador(f"O comando aws-emulator não está instalado na distribuição WSL {distro}. "
                           "Instale o pacote RPM ou DEB dentro dela (README, seção Testes contra o AWS Emulator).")
    rc, home = rodar_captura([wsl, "-d", distro, "--", "sh", "-c", 'printf %s "$HOME"'])
    if rc != 0 or not home.strip().startswith("/"):
        raise ErroEmulador(f"Não consegui descobrir o diretório home dentro da distribuição WSL {distro}.")
    with _log() as log:
        subprocess.Popen(comando_wsl(wsl, distro, estado["porta"], estado["idle"]), stdout=log, stderr=log,
                         **_sinalizadores_destacado())
    estado["distro"], estado["wsl"] = distro, wsl
    estado["pasta_arquivos"] = unc_wsl(distro, home.strip(), estado["porta"])


def _subir_container(estado: dict, det: dict, cfg: dict, bloco: dict | None, avisar) -> None:
    cli = det["cli"]
    imagem = f"{IMAGEM}:{(bloco or {}).get('versao') or 'latest'}"
    rc, _ = rodar_captura([cli, "image", "inspect", imagem])
    if rc != 0:
        url = url_pacote(bloco, arquitetura())
        avisar(f"[INFO] construindo a imagem {imagem} com o Dockerfile da documentação da AWS (pacote: {url})")
        r = subprocess.run(comando_container_build(cli, imagem, url))
        if r.returncode != 0:
            raise ErroEmulador(f"{cli} build falhou (código {r.returncode}); veja a saída acima.")
    pasta_host = HOME_LOCAL / ".aws" / "emulator"
    pasta_host.mkdir(parents=True, exist_ok=True)
    usuario = f"{os.getuid()}:{os.getgid()}" if hasattr(os, "getuid") else None
    nome = f"ash-emulador-{estado['porta']}"
    rc, saida = rodar_captura(comando_container_run(cli, nome, estado["porta"], estado["idle"], str(pasta_host),
                                                    imagem, usuario), timeout=120)
    if rc != 0:
        raise ErroEmulador(f"{cli} run falhou: {saida.strip()[:300]}")
    estado["cli"], estado["container"], estado["imagem"] = cli, nome, imagem
    estado["pasta_arquivos"] = str(pasta_host / str(estado["porta"]))


def esperar_pronto(estado: dict, segundos: int = ESPERA_PRONTO, dormir=time.sleep) -> None:
    """Espera o health check responder, uma tentativa por segundo."""
    ca = pasta_arquivos(estado) / "ca.pem"
    for _ in range(segundos):
        if saude(estado["endpoint"], ca):
            return
        dormir(1)
    raise ErroEmulador(f"O emulador não respondeu em {segundos} s em {estado['endpoint']}. Veja {LOG.relative_to(RAIZ)}.")


def iniciar(cfg: dict, bloco: dict | None = None, avisar=print) -> dict:
    """Sobe o emulador (um por vez), espera ficar pronto e prova que é local. Devolve o estado."""
    atual = ler_estado()
    if atual and de_pe(atual):
        return {**atual, "ja_estava": True}
    if atual:
        limpar_estado()
    det = detectar_modos(cfg)
    modo = escolher_modo(cfg, det)
    p = porta(cfg)
    if porta_em_uso(p):
        raise ErroEmulador(f"A porta {p} já está em uso. Defina outra em ASH_EMULADOR_PORTA (.ash/config.env).")
    estado = {"modo": modo, "porta": p, "endpoint": f"https://127.0.0.1:{p}", "iniciado_em": agora().strftime("%Y-%m-%dT%H:%M:%SZ"),
              "idle": idle(cfg), "versao": str((bloco or {}).get("versao", ""))}
    detalhe = det[modo]["detalhe"]
    if modo == "linux":
        _subir_linux(estado, detalhe, cfg)
    elif modo == "wsl":
        _subir_wsl(estado, detalhe, cfg)
    else:
        _subir_container(estado, detalhe, cfg, bloco, avisar)
    gravar_estado(estado)
    try:
        esperar_pronto(estado)
        ambiente_do_estado(estado, {})  # provas: endpoint local, ID de chave EMULATOR, certificado presente
    except ErroEmulador:
        parar(estado, avisar)
        raise
    return estado


def restos(estado: dict) -> list[str]:
    """Indícios de que o emulador daquele estado ainda existe (vazio quando nada sobrou)."""
    modo = estado.get("modo")
    achados = []
    if modo == "linux":
        try:
            os.kill(int(estado["pid"]), 0)
            achados.append(f"processo {estado['pid']}")
        except (OSError, KeyError, ValueError):
            pass
    elif modo == "wsl":
        rc, _ = rodar_captura([estado["wsl"], "-d", estado["distro"], "--", "pgrep", "-f",
                               f"aws-emulator -p {estado['porta']} "])
        if rc == 0:
            achados.append("processo aws-emulator na distribuição WSL")
    elif modo == "container":
        rc, saida = rodar_captura([estado["cli"], "ps", "-q", "--filter", f"name={estado['container']}"])
        if rc == 0 and saida.strip():
            achados.append(f"contêiner {estado['container']}")
    return achados


def parar(estado: dict | None = None, avisar=print, dormir=time.sleep) -> bool:
    """Para o emulador do estado (parada limpa por SIGTERM) e confirma que não sobrou processo."""
    estado = estado or ler_estado()
    if not estado:
        return False
    modo = estado["modo"]
    if modo == "linux":
        try:
            os.kill(int(estado["pid"]), 15)
        except (OSError, KeyError, ValueError):
            pass
    elif modo == "wsl":
        rodar_captura(comando_parar_wsl(estado["wsl"], estado["distro"], estado["porta"]))
    elif modo == "container":
        rodar_captura([estado["cli"], "stop", estado["container"]], timeout=60)
    sobrou = restos(estado)
    for _ in range(20):
        if not sobrou:
            break
        dormir(1)
        sobrou = restos(estado)
    limpar_estado()
    if sobrou:
        avisar("[AVISO] ainda existe: " + ", ".join(sobrou) + ". Confira com o passo a passo do README (seção Testes contra o AWS Emulator).")
    return True


def formatar_duracao(segundos: int) -> str:
    """Duração curta: 45 s, 12 min ou 2 h 05 min."""
    if segundos < 60:
        return f"{segundos} s"
    if segundos < 3600:
        return f"{segundos // 60} min"
    return f"{segundos // 3600} h {segundos % 3600 // 60:02d} min"


def linha_status(cfg: dict, estado: dict | None = None, deteccao: dict | None = None) -> str:
    """Linha 'Emulador AWS' do status: de pé ou parado, modo, tempo de vida e prazo de inatividade."""
    estado = estado if estado is not None else ler_estado()
    if estado and de_pe(estado):
        desde = datetime.strptime(estado["iniciado_em"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        vivo = formatar_duracao(max(0, int((agora() - desde).total_seconds())))
        return (f"Emulador AWS: de pé · modo {estado['modo']} · {estado['endpoint']} · há {vivo} · "
                f"encerra sozinho após {formatar_duracao(int(estado['idle']))} sem chamadas de API")
    deteccao = deteccao or detectar_modos(cfg)
    try:
        return f"Emulador AWS: parado · modo que seria usado: {escolher_modo(cfg, deteccao)}"
    except ErroEmulador:
        return "Emulador AWS: parado · nenhum modo utilizável; o que falta em cada um: python ash.py emulador status"


def detalhe_modos(deteccao: dict) -> list[str]:
    """Linhas legíveis com a disponibilidade de cada modo."""
    return [f"  {m:<10} {'disponível' if deteccao[m]['ok'] else 'indisponível'}: {deteccao[m]['motivo']}" for m in MODOS]


@contextmanager
def emulador_para_ci(cfg: dict, bloco: dict | None, avisar=print):
    """Entrega o estado de um emulador de pé. Se o ci o subiu (ASH_EMULADOR_AUTO=sim), para ao final, mesmo com falha."""
    estado = ler_estado()
    subiu = False
    if not de_pe(estado):
        if not auto_ci(cfg):
            raise ErroEmulador("Emulador AWS não está de pé. Rode: python ash.py emulador iniciar "
                               "(ou defina ASH_EMULADOR_AUTO=sim em .ash/config.env para o ci subir e parar o emulador sozinho).")
        estado = iniciar(cfg, bloco, avisar)
        subiu = not estado.get("ja_estava")
    try:
        yield estado
    finally:
        if subiu:
            parar(estado, avisar)
