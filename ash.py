#!/usr/bin/env python3
"""ASH · comando único, multiplataforma (Windows, macOS, Linux). Só biblioteca padrão.

Uso: python ash.py <comando> [opções]

Livres (squad-lead; agentes de papel só os que a permissão de cada um libera):
  status                 ambiente, perfil de stack, lentes, repositório e portões
  configurar             grava PO, FDE, Dev revisor, remoto e e-mail do git em .ash/config.env
  setup [--remote URL]   ferramentas do harness, dependências do perfil, git, hooks, remoto e commit inicial
  perfil [NOME]          mostra o perfil de stack ativo; com NOME, ativa perfis/NOME.json (mudança de harness)
  testar                 testes rápidos do projeto, pelo comando do perfil
  testar-harness [--integracao]   testes do próprio harness (tests_harness/), com o pytest da .venv-tools, em qualquer
                         stack; com --integracao, roda tests_harness_integracao/ contra o AWS Emulator; com --auditoria,
                         audita o requirements-tools.txt contra os aceites de risco (as duas variantes ficam fora do CI)
  etapa NOME             uma etapa do CI do perfil, isolada (ex.: testes, sast, dependencias, integracao-aws)
  emulador iniciar|parar|status|reset   AWS Emulator local (modos linux, wsl, container); só sobe por este
                         comando, encerra sozinho por inatividade e nunca toca conta AWS real
  validar ID | relatorio validação de uma spec | linha do tempo das specs, sem AWS
  nova-spec ID SLUG      branch feat/<id> a partir da main e story do PO
  nova-descoberta ID SLUG  story a partir do PRD aprovado + branch feat/<id>
  ci                     spec-gate (núcleo), etapas do perfil de stack, rastreio (núcleo)
  pendencias             o que espera decisão humana
  metricas | backup      envio de eventos e git bundle para o S3
  restaurar BUCKET DEST  restaura o repositório a partir do S3
  portao abrir|status    abre o portão de uma decisão humana / mostra o estado
  sync                   envia a branch feat/<id> atual ao GitHub (nunca a main)

Atos humanos (só executam com portão aberto e a frase literal do humano no chat em --mensagem):
  aprovar ID --papel po|design|dev|homologacao --nome NOME   (homologacao: --branch e --evidencia)
  aprovar-prd ID --nome NOME    aprova o PRFAQ/PRD da fase de descoberta
  publicar-proto ID             publica o protótipo da iniciativa em S3+CloudFront
  merge BRANCH ID [--fde NOME]
  bootstrap | teardown
  publicar-harness       commit e push na main de mudanças do próprio harness

Fluxo de um ato humano no Kiro:
  1. squad-lead: python ash.py portao abrir --acao aprovar-po --spec INS-016 --resumo "..."
  2. squad-lead mostra a decisão no chat e pede: responda APROVO
  3. humano responde APROVO no chat
  4. squad-lead: python ash.py aprovar INS-016 --papel po --nome "..." --mensagem "APROVO"
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
os.chdir(RAIZ)
sys.path.insert(0, str(RAIZ / "scripts"))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WIN = platform.system() == "Windows"
CFG = RAIZ / ".ash" / "config.env"

# Variáveis de certificado TLS que pip, pip-audit, AWS CLI, Node e curl leem do ambiente.
VARS_CERTIFICADO = ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "AWS_CA_BUNDLE", "NODE_EXTRA_CA_CERTS",
                    "CURL_CA_BUNDLE", "PIP_CERT")
CERTIFICADOS_IGNORADOS: list[str] = []
COMANDOS_DE_REDE = {"setup", "sync", "ci", "merge", "publicar-harness", "publicar-proto", "metricas",
                    "backup", "restaurar", "bootstrap", "teardown"}


def limpar_certificados_invalidos(ambiente: dict | None = None) -> list[str]:
    """Tira do ambiente as variáveis de certificado que apontam para caminho inexistente.

    Notebooks corporativos podem trazer essas variáveis no escopo de máquina apontando para um .pem
    que ainda não foi instalado; aí pip, pip-audit, AWS CLI e Node falham por TLS. Variável que aponta
    para arquivo ou pasta existente é certificado corporativo legítimo e fica intacta. Nada é gravado
    no registro do sistema: a limpeza vale só para este processo e para os comandos que ele chama.
    """
    amb = os.environ if ambiente is None else ambiente
    ignoradas = []
    for nome in VARS_CERTIFICADO:
        valor = (amb.get(nome) or "").strip().strip('"')
        if valor and not Path(os.path.expandvars(os.path.expanduser(valor))).exists():
            amb.pop(nome, None)
            ignoradas.append(nome)
    return ignoradas


# ---------------------------------------------------------------- perfil de stack
# O núcleo do ASH (spec, faixas, portões, evidência) não depende de linguagem. O que muda por stack
# fica no perfil ativo, ash-perfil.json: setup do projeto, comando de teste, etapas do CI e onde
# ficam os testes. Sem o arquivo, vale o perfil Python abaixo (comportamento original do ASH).
PERFIL_ARQ = RAIZ / "ash-perfil.json"
PASTA_PERFIS = RAIZ / "perfis"
PERFIL_PADRAO = {
    "nome": "python",
    "descricao": "Python 3.12 com pytest e cobertura, Semgrep com as regras de .semgrep/ e pip-audit",
    "testado": True,
    "pasta_codigo": "src",
    "pasta_testes": "tests",
    "arquivos_teste": ["tests/**/test_*.py"],
    "cobertura_minima": 80,
    "setup": [
        {"comando": ["{python}", "-m", "venv", ".venv"], "se_nao_existe": ".venv"},
        ["{py}", "-m", "pip", "install", "-q", "--upgrade", "pip"],
        ["{py}", "-m", "pip", "install", "-q", "-r", "requirements.txt", "-r", "requirements-dev.txt"],
    ],
    "testar": ["{py}", "-m", "pytest", "-q"],
    "etapas": [
        {"nome": "testes", "comando": ["{py}", "-m", "pytest", "-q", "--cov={codigo}", "--cov-report=term-missing",
                                       "--cov-fail-under={cobertura}"]},
        {"nome": "sast", "comando": ["{semgrep}", "scan", "--config", ".semgrep/", "--metrics=off", "--error",
                                     "--quiet", "{codigo}/"]},
        {"nome": "dependencias", "comando": ["{pip-audit}", "-r", "requirements.txt", "--progress-spinner", "off"]},
    ],
}
ETAPAS_NUCLEO = ("spec-gate", "rastreio")


def validar_perfil(dados: dict, origem: str) -> dict:
    """Confere os campos mínimos de um perfil de stack e devolve o próprio perfil."""
    if dados.get("modelo"):
        raise SystemExit(f"[ERRO] {origem} é o modelo de perfil, não um perfil pronto. Copie para "
                         "perfis/<stack>.json, preencha os campos entre < > e apague a chave modelo.")
    faltando = [k for k in ("nome", "testar", "etapas") if not dados.get(k)]
    if faltando:
        raise SystemExit(f"[ERRO] perfil {origem} sem o(s) campo(s): {', '.join(faltando)}")
    for etapa in dados["etapas"]:
        if not etapa.get("nome") or not etapa.get("comando"):
            raise SystemExit(f"[ERRO] perfil {origem}: toda etapa precisa de nome e comando")
        if etapa["nome"] in ETAPAS_NUCLEO:
            raise SystemExit(f"[ERRO] perfil {origem}: a etapa {etapa['nome']} é do núcleo e não pode ser redefinida")
        if etapa.get("requer") not in (None, "emulador_aws"):
            raise SystemExit(f"[ERRO] perfil {origem}: etapa {etapa['nome']} com requer '{etapa['requer']}' inválido; "
                             "o único valor aceito é emulador_aws")
        if etapa.get("requer") == "emulador_aws" and not dados.get("emulador_aws"):
            raise SystemExit(f"[ERRO] perfil {origem}: a etapa {etapa['nome']} requer emulador_aws, "
                             "mas o perfil não tem o bloco emulador_aws")
    if "emulador_aws" in dados:
        import emulador
        erros = emulador.validar_bloco(dados["emulador_aws"])
        if erros:
            raise SystemExit(f"[ERRO] perfil {origem}: " + "; ".join(erros))
    return dados


def perfil() -> dict:
    """Perfil de stack ativo: ash-perfil.json, ou o perfil Python padrão se o arquivo não existir."""
    if not PERFIL_ARQ.exists():
        return PERFIL_PADRAO
    try:
        dados = json.loads(PERFIL_ARQ.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"[ERRO] ash-perfil.json não é JSON válido: {e}")
    return validar_perfil(dados, "ash-perfil.json")


def cobertura_minima(pf: dict) -> str:
    return os.environ.get("ASH_COBERTURA_MIN") or str(pf.get("cobertura_minima", 80))


def expandir(cmd: list[str], pf: dict) -> list[str]:
    """Troca os marcadores do perfil pelos valores desta máquina e resolve o programa no PATH."""
    trocas = {"{python}": sys.executable, "{py}": py_projeto(), "{cobertura}": cobertura_minima(pf),
              "{codigo}": pf.get("pasta_codigo", "src"), "{testes}": pf.get("pasta_testes", "tests")}
    saida_cmd = []
    for parte in cmd:
        if parte in ("{semgrep}", "{pip-audit}"):
            parte = ferramenta(parte[1:-1])
        for marcador, valor in trocas.items():
            parte = parte.replace(marcador, valor)
        saida_cmd.append(parte)
    if saida_cmd and not any(s in saida_cmd[0] for s in ("/", "\\")):
        saida_cmd[0] = shutil.which(saida_cmd[0]) or saida_cmd[0]
    return saida_cmd


def lentes_ativas() -> list[str]:
    return sorted(p.stem for p in (RAIZ / ".kiro" / "steering").glob("*lente*.md"))


def aviso_certificados() -> str:
    """Linha de status sobre as variáveis de certificado ignoradas neste processo."""
    if not CERTIFICADOS_IGNORADOS:
        return "Certificados: nenhuma variável ignorada"
    return (f"Certificados: ignoradas {len(CERTIFICADOS_IGNORADOS)} variável(is) que apontam para arquivo "
            f"inexistente ({', '.join(CERTIFICADOS_IGNORADOS)}). Vale só para este comando; o sistema não muda")


# ---------------------------------------------------------------- utilidades
def venv_bin(nome: str) -> Path:
    return RAIZ / nome / ("Scripts" if WIN else "bin")


def venv_py(nome: str) -> Path:
    return venv_bin(nome) / ("python.exe" if WIN else "python")


def py_projeto() -> str:
    p = venv_py(".venv")
    return str(p) if p.exists() else sys.executable


def ferramenta(nome: str) -> str:
    for c in (venv_bin(".venv-tools") / f"{nome}.exe", venv_bin(".venv-tools") / nome):
        if c.exists():
            return str(c)
    achado = shutil.which(nome)
    if not achado:
        raise SystemExit(f"[ERRO] '{nome}' não encontrado. Rode: python ash.py setup")
    return achado


def exe(nome: str) -> str:
    achado = shutil.which(nome)
    if not achado:
        raise SystemExit(f"[ERRO] '{nome}' não está instalado ou não está no PATH")
    return achado


def rodar(cmd: list[str], env: dict | None = None, checar: bool = True) -> int:
    print("$ " + " ".join(cmd))
    r = subprocess.run(cmd, env={**os.environ, **(env or {})})
    if checar and r.returncode != 0:
        raise SystemExit(f"[ERRO] comando falhou (código {r.returncode})")
    return r.returncode


def saida(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def config() -> dict:
    dados = {}
    if CFG.exists():
        for linha in CFG.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                dados[k.strip()] = v.strip().strip('"')
    return dados


def gravar_config(chave: str, valor: str) -> None:
    texto = CFG.read_text(encoding="utf-8") if CFG.exists() else ""
    if re.search(rf"^{chave}=", texto, re.M):
        texto = re.sub(rf"^{chave}=.*$", f"{chave}={valor}", texto, flags=re.M)
    else:
        texto += f"\n{chave}={valor}\n"
    CFG.write_text(texto, encoding="utf-8")


def aws_base(cfg: dict) -> list[str]:
    base = [exe("aws"), "--region", cfg.get("AWS_REGION") or "us-east-1"]
    if cfg.get("AWS_PROFILE"):
        base += ["--profile", cfg["AWS_PROFILE"]]
    return base


def portao_consumir(acao: str, spec: str, mensagem: str | None) -> dict:
    import portao
    conf = portao.consumir(acao, spec, mensagem)
    print(f"[PORTÃO] confirmação humana válida ({conf['canal']}): \"{conf['texto_humano'][:80]}\"")
    return conf


def branch_atual() -> str:
    return saida(["git", "branch", "--show-current"])


def _agora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- comandos
def remoto() -> str:
    return saida(["git", "remote", "get-url", "origin"])


def push(ref: str, upstream: bool = False) -> bool:
    if not remoto():
        print("[AVISO] sem remoto 'origin'; nada foi enviado ao GitHub")
        return False
    cmd = ["git", "push", "-q"] + (["-u"] if upstream else []) + ["origin", ref]
    print("$ " + " ".join(cmd))
    r = subprocess.run(cmd, env={**os.environ, "ASH_PUSH": "1"})
    if r.returncode != 0:
        print(f"[AVISO] push de {ref} falhou (código {r.returncode}). Verifique o login do Git no GitHub.")
        return False
    return True


def _arquivos_de_hooks(pasta: Path | None = None) -> list[Path]:
    """Arquivos de .githooks/ da pasta dada (padrão: a raiz do projeto)."""
    dir_hooks = (pasta or RAIZ) / ".githooks"
    return sorted(p for p in dir_hooks.iterdir() if p.is_file()) if dir_hooks.is_dir() else []


def garantir_hooks_executaveis(pasta: Path | None = None) -> list[str]:
    """Soma os bits de execução aos de cada arquivo de .githooks/ e devolve os nomes alterados (Windows: nada muda)."""
    if platform.system() == "Windows":
        return []
    alterados = []
    for p in _arquivos_de_hooks(pasta):
        modo = p.stat().st_mode
        if modo & 0o111 != 0o111:
            os.chmod(p, modo | 0o111)
            alterados.append(p.name)
    return alterados


def hooks_sem_execucao(pasta: Path | None = None) -> list[str]:
    """Nomes dos arquivos de .githooks/ sem permissão de execução (Windows: sempre vazio, o Git não depende do bit)."""
    if platform.system() == "Windows":
        return []
    return [p.name for p in _arquivos_de_hooks(pasta) if not os.access(p, os.X_OK)]


def linha_hooks(pasta: Path | None = None) -> str:
    """Linha do status sobre a permissão dos hooks; vazia no Windows ou sem pasta .githooks."""
    if platform.system() == "Windows" or not _arquivos_de_hooks(pasta):
        return ""
    sem_exec = hooks_sem_execucao(pasta)
    if not sem_exec:
        return "Hooks: executáveis"
    return (f"[AVISO] hooks sem permissão de execução ({', '.join(sem_exec)}): o Git os ignora e a main fica "
            "sem proteção. Corrija com python ash.py setup (ou chmod +x .githooks/*).")


def marcar_hooks_no_indice(pasta: Path | None = None) -> None:
    """Registra o modo 100755 dos hooks no índice do Git, para o modo valer também em clones feitos em macOS e Linux."""
    pasta = pasta or RAIZ
    arqs = [f".githooks/{p.name}" for p in _arquivos_de_hooks(pasta)]
    if arqs:
        subprocess.run(["git", "-C", str(pasta), "update-index", "--chmod=+x", *arqs], capture_output=True)


def cmd_setup(a) -> int:
    if sys.version_info < (3, 11):
        raise SystemExit(f"[ERRO] Python {platform.python_version()}; use 3.11 ou maior (recomendado 3.12)")
    print(f"== Python {platform.python_version()} em {sys.executable}")
    # Ferramentas do harness (Semgrep e pip-audit), em ambiente próprio, valem para qualquer stack.
    if not venv_py(".venv-tools").exists():
        rodar([sys.executable, "-m", "venv", ".venv-tools"])
    rodar([str(venv_py(".venv-tools")), "-m", "pip", "install", "-q", "--upgrade", "pip"])
    rodar([str(venv_py(".venv-tools")), "-m", "pip", "install", "-q", "-r", "requirements-tools.txt"])
    # Dependências do projeto, conforme o perfil de stack ativo.
    pf = perfil()
    print(f"== perfil de stack: {pf['nome']}")
    for passo in pf.get("setup", []):
        if isinstance(passo, dict):
            alvo = passo.get("se_nao_existe")
            if alvo and (RAIZ / alvo).exists():
                continue
            passo = passo["comando"]
        rodar(expandir(passo, pf))
    if not CFG.exists():
        shutil.copy(RAIZ / ".ash" / "config.env.example", CFG)
    cfg = config()
    novo_repo = not (RAIZ / ".git").exists()
    if novo_repo:
        rodar(["git", "init", "-q", "-b", "main"])
    rodar(["git", "config", "core.hooksPath", ".githooks"])
    corrigidos = garantir_hooks_executaveis()
    if corrigidos:
        print(f"[OK] permissão de execução aplicada aos hooks: {', '.join(corrigidos)}")
    rodar(["git", "config", "core.autocrlf", "false"])
    if cfg.get("ASH_GIT_NOME"):
        rodar(["git", "config", "user.name", cfg["ASH_GIT_NOME"]])
    if cfg.get("ASH_GIT_EMAIL"):
        rodar(["git", "config", "user.email", cfg["ASH_GIT_EMAIL"]])
    if not saida(["git", "config", "user.name"]) or not saida(["git", "config", "user.email"]):
        print("[AVISO] git sem user.name ou user.email. Preencha ASH_GIT_NOME e ASH_GIT_EMAIL em .ash/config.env "
              "e rode python ash.py setup de novo.")
    url = a.remote or cfg.get("ASH_GIT_REMOTE", "")
    if url:
        if remoto():
            rodar(["git", "remote", "set-url", "origin", url])
        else:
            rodar(["git", "remote", "add", "origin", url])
        gravar_config("ASH_GIT_REMOTE", url)
        rodar(["git", "fetch", "-q", "origin"], checar=False)
    sem_head = subprocess.run(["git", "rev-parse", "--verify", "-q", "HEAD"], capture_output=True).returncode != 0
    remoto_main = subprocess.run(["git", "rev-parse", "--verify", "-q", "origin/main"],
                                 capture_output=True).returncode == 0
    if sem_head and remoto_main:
        # repositório remoto já tem histórico: adota o histórico e mantém os arquivos desta pasta
        rodar(["git", "reset", "-q", "--mixed", "origin/main"])
        rodar(["git", "branch", "-q", "--set-upstream-to=origin/main", "main"], checar=False)
        print("[OK] histórico do GitHub adotado. As diferenças desta pasta aparecem como mudanças no harness: "
              "publique com o portão publicar-harness.")
    elif sem_head:
        rodar(["git", "add", "-A"])
        marcar_hooks_no_indice()
        rodar(["git", "commit", "-q", "-m", "ASH: estrutura inicial"], env={"ASH_MERGE": "1"})
        if remoto():
            push("main", upstream=True)
    print("[OK] setup concluído")
    return 0


def cmd_sync(_a) -> int:
    """Envia a branch de trabalho atual ao GitHub. Nunca envia a main."""
    b = branch_atual()
    if not b.startswith("feat/"):
        raise SystemExit(f"[ERRO] sync só envia branches feat/<id>; branch atual: {b or '(nenhuma)'}")
    return 0 if push(b, upstream=True) else 1


TRABALHO = (".kiro/specs/", "stories/", "src/", "tests/", "reviews/", "portfolio/iniciativas/")
HARNESS = (".kiro/steering/", ".kiro/agents/", ".kiro/hooks/", ".githooks/", ".semgrep/", "scripts/", "docs/",
           "templates/", "infra/", "perfis/", "tests_harness/", "tests_harness_integracao/", ".ash/config.env.example")
# Arquivos de scaffold do harness fora das pastas acima (tratados como harness, um a um).
HARNESS_ARQUIVOS = {"portfolio/backlog.md"}
HARNESS_RAIZ = {"ash.py", "ash-perfil.json", "README.md", "AGENTS.md", "pytest.ini", ".gitignore", ".gitattributes",
                "requirements.txt", "requirements-dev.txt", "requirements-tools.txt"}
NUNCA = (".venv", ".ash/", "__pycache__", ".pytest_cache", "infra/cdk.out")
# Arquivos que versões antigas deixaram na raiz. O publicar-harness apaga e publica a remoção.
OBSOLETOS = {"spec-kiro-v1.md"}


def _eh_harness(caminho: str) -> bool:
    if any(caminho.startswith(n) or f"/{n}" in "/" + caminho for n in NUNCA) and \
            caminho != ".ash/config.env.example":
        return False
    if caminho.endswith((".zip", ".bundle", ".pyc")):
        return False
    return (caminho in HARNESS_RAIZ or caminho in OBSOLETOS or caminho in HARNESS_ARQUIVOS
            or caminho.startswith(HARNESS))


def _mudancas_harness() -> list[str]:
    """Arquivos alterados que pertencem ao harness (fora das pastas de trabalho das specs)."""
    caminhos = []
    bruto = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], capture_output=True,
                           text=True, encoding="utf-8").stdout
    for linha in bruto.splitlines():
        caminho = linha[3:].strip().strip('"')
        if " -> " in caminho:
            caminho = caminho.split(" -> ", 1)[1]
        caminho = caminho.replace("\\", "/")
        if caminho and not caminho.startswith(TRABALHO) and _eh_harness(caminho):
            caminhos.append(caminho)
    return caminhos


# Arquivos cuja mudança pode alterar o que os testes de integração do harness cobrem (emulador, Lambdas, backup).
GATILHOS_INTEGRACAO_HARNESS = ("ash.py", "scripts/emulador.py", "infra/lambdas/", "infra/emulador/",
                               "tests_harness_integracao/")


def aviso_integracao_harness(arquivos: list[str]) -> str:
    """Aviso (não bloqueante) do publicar-harness quando a mudança toca o que a integração do harness cobre."""
    tocados = [f for f in arquivos if f.startswith(GATILHOS_INTEGRACAO_HARNESS)]
    if not tocados:
        return ""
    return ("[AVISO] a publicação toca arquivos que os testes de integração do harness cobrem ("
            + ", ".join(tocados[:5]) + (", ..." if len(tocados) > 5 else "") + "). Se a mudança é no emulador, no CI por "
            "etapas, no backup, nas Lambdas ou na versão do emulador, rode antes: python ash.py testar-harness --integracao "
            "(precisa de um modo do emulador disponível). Isto não bloqueia a publicação.")


ARQUIVOS_DE_AUDITORIA = ("requirements-tools.txt", "tests_harness/auditoria_ferramentas.json")


def aviso_auditoria_harness(arquivos: list[str], hoje=None, caminho=None) -> str:
    """Aviso (não bloqueante) do publicar-harness: mudança nas ferramentas ou nos aceites de risco, ou aceite vencido."""
    import auditoria_ferramentas as aud
    motivos = []
    tocados = [f for f in arquivos if f in ARQUIVOS_DE_AUDITORIA]
    if tocados:
        motivos.append("a publicação muda " + ", ".join(tocados))
    try:
        dados = aud.carregar(caminho or aud.ARQ_ACEITES)
        expirados = aud.vencidos(dados, hoje or aud.hoje_utc())
    except aud.ErroAuditoria:
        expirados = []
        motivos.append("não consegui ler o arquivo de aceites de risco")
    if expirados:
        motivos.append("há " + str(len(expirados)) + " aceite(s) de risco vencido(s): "
                       + ", ".join(a.get("id", "?") for a in expirados[:4]) + (", ..." if len(expirados) > 4 else ""))
    if not motivos:
        return ""
    return ("[AVISO] " + "; ".join(motivos) + ". Rode antes: python ash.py testar-harness --auditoria (precisa de rede; "
            "CVE novo ou aceite vencido exige decisão do autor do harness, nunca de um agente). Isto não bloqueia a publicação.")


def aviso_boto3_do_projeto(pf: dict) -> str:
    """Aviso quando o perfil declara emulador_aws e o requirements.txt do projeto não fixa o boto3."""
    if not pf.get("emulador_aws"):
        return ""
    import emulador
    arq = RAIZ / "requirements.txt"
    texto = arq.read_text(encoding="utf-8") if arq.exists() else ""
    problema = emulador.aviso_boto3(pf["emulador_aws"], texto)
    return f"[AVISO] {problema}" if problema else ""


def cmd_publicar_harness(a) -> int:
    """Commita na main as mudanças do próprio harness (steering, agentes, scripts, ash.py, docs) e envia ao
    GitHub. Pode rodar de qualquer branch: leva só os arquivos do harness para a main e, se estiver numa
    feat/<id>, traz a main atualizada de volta para essa branch."""
    origem = branch_atual()
    for nome in OBSOLETOS:
        if (RAIZ / nome).exists() and saida(["git", "ls-files", nome]):
            (RAIZ / nome).unlink()
            print(f"[INFO] {nome} é de uma versão antiga e será removido")
    arquivos = _mudancas_harness()
    if not arquivos:
        print("[OK] nada do harness a publicar")
        return 0
    print("Arquivos do harness a publicar:\n  " + "\n  ".join(arquivos))
    for aviso in (aviso_integracao_harness(arquivos), aviso_auditoria_harness(arquivos)):
        if aviso:
            print(aviso)
    conf = portao_consumir("publicar-harness", "HARNESS", a.mensagem)
    env = {"ASH_MERGE": "1"}
    if origem != "main":
        rodar(["git", "stash", "push", "-q", "--include-untracked", "-m", "ash-harness", "--"] + arquivos)
        rodar(["git", "switch", "-q", "main"])
        rodar(["git", "stash", "pop", "-q"])
    rodar(["git", "add", "-A", "--"] + arquivos, env=env)
    rodar(["git", "commit", "-q", "-m",
           f"ASH: atualização do harness (aprovada no chat: {conf['texto_humano'][:40]})"], env=env)
    push("main", upstream=True)
    if origem and origem != "main":
        rodar(["git", "switch", "-q", origem])
        rodar(["git", "merge", "-q", "--no-edit", "main"])
        push(origem)
        print(f"[OK] harness publicado na main e trazido para {origem}")
    else:
        print("[OK] harness publicado na main")
    return 0


def ator_do_ci() -> str:
    """Ator do evento ci_executado: 'agente' por padrão (o squad-lead roda o CI); ASH_ATOR=humano para execução manual."""
    ator = (os.environ.get("ASH_ATOR") or "agente").strip().lower()
    if ator not in ("agente", "humano"):
        raise SystemExit(f"[ERRO] ASH_ATOR deve ser 'agente' ou 'humano', recebi '{ator}'")
    return ator


def cmd_ci(a) -> int:
    pular = set(filter(None, (os.environ.get("ASH_PULAR", "")).split(",")))
    if pular & set(ETAPAS_NUCLEO):
        raise SystemExit(f"[ERRO] ASH_PULAR não pode pular etapas do núcleo: {', '.join(sorted(pular & set(ETAPAS_NUCLEO)))}")
    pf = perfil()
    print(f"== perfil de stack: {pf['nome']}{'' if pf.get('testado') else ' (NÃO TESTADO)'}")
    aviso = aviso_boto3_do_projeto(pf)
    if aviso:
        print(aviso)
    etapas = [("spec-gate", [sys.executable, "scripts/validar_spec.py", "--todas"], None)]
    for etapa in pf["etapas"]:
        etapas.append((etapa["nome"], None if etapa["nome"] in pular else expandir(etapa["comando"], pf),
                       etapa.get("requer")))
    etapas.append(("rastreio", [sys.executable, "scripts/rastrear_aceite.py"], None))
    resultado = []
    env_semgrep = {"PYTHONUTF8": "1"}
    import emulador
    pilha = contextlib.ExitStack()  # guarda o emulador que o próprio ci subir, para parar ao final
    emulador_estado = None
    try:
        for nome, cmd, requer in etapas:
            if nome in pular:
                print(f"== {nome}: PULADA (ASH_PULAR)")
                resultado.append((nome, "PULADA"))
                continue
            print(f"== {nome}")
            env = {**os.environ, **env_semgrep}
            if requer == "emulador_aws":
                try:
                    if emulador_estado is None:
                        emulador_estado = pilha.enter_context(emulador.emulador_para_ci(config(), pf.get("emulador_aws")))
                    env = emulador.ambiente_do_estado(emulador_estado, os.environ)
                except emulador.ErroEmulador as e:
                    print(f"[ERRO] {e}")
                    resultado.append((nome, "FALHOU"))
                    continue
            rc = subprocess.run(cmd, env=env).returncode
            resultado.append((nome, "OK" if rc == 0 else "FALHOU"))
    finally:
        pilha.close()
    print(f"\nResumo do CI local ({branch_atual() or 'sem-git'}):")
    for nome, st in resultado:
        print(f"  {nome:<14} {st}")
    falhou = any(st == "FALHOU" for _, st in resultado)
    pulou = any(st == "PULADA" for _, st in resultado)
    status = ("falhou" if falhou else "ok") + ("_parcial" if pulou else "")
    import registrar_evento as ev
    nomes_emulador = {e["nome"] for e in pf["etapas"] if e.get("requer") == "emulador_aws"}
    detalhe = {"status": status, "commit": saida(["git", "rev-parse", "--short", "HEAD"]) or "sem-commit"}
    detalhe.update(emulador.evidencia(pf.get("emulador_aws"), [(n, st) for n, st in resultado if n in nomes_emulador]))
    ev.gravar("ci_executado", getattr(a, "spec", None) or os.environ.get("ASH_SPEC", "NA"), ator_do_ci(), "", detalhe)
    if falhou:
        print("CI LOCAL: FALHOU")
        return 1
    if pulou:
        print("CI LOCAL: OK COM ETAPAS PULADAS (não serve para merge)")
        return 3
    print("CI LOCAL: OK")
    return 0


def cmd_nova_spec(a) -> int:
    low = a.id.lower()
    rodar(["git", "switch", "-q", "main"])
    rodar(["git", "switch", "-c", f"feat/{low}"])
    story = RAIZ / "stories" / f"{a.id}-{a.slug}.md"
    story.parent.mkdir(exist_ok=True)
    if story.exists():
        print(f"== {story.name} já existe; mantido")
    else:
        texto = (RAIZ / "templates" / "story-po.md").read_text(encoding="utf-8")
        story.write_text(re.sub(r"^id: .*$", f"id: {a.id}", texto, count=1, flags=re.M), encoding="utf-8")
    print(f"[OK] branch feat/{low} criada; story em stories/{story.name}")
    if remoto():
        print("[INFO] a branch vai para o GitHub no primeiro python ash.py sync, depois do primeiro commit")
    return 0


def _slug_iniciativa(spec_id: str) -> Path | None:
    """Acha a pasta da iniciativa de descoberta cujo prd.md tem o id informado."""
    base = RAIZ / "portfolio" / "iniciativas"
    if not base.exists():
        return None
    for prd in base.glob("*/prd.md"):
        texto = prd.read_text(encoding="utf-8")
        if re.search(rf"^id:\s*{re.escape(spec_id)}\s*$", texto, re.M):
            return prd.parent
    return None


def cmd_aprovar_prd(a) -> int:
    """Portão aprovar-prd: registra a aprovação humana do PRFAQ/PRD da fase de descoberta."""
    import aprovar
    import registrar_evento as ev
    pasta = _slug_iniciativa(a.id)
    if pasta is None:
        raise SystemExit(f"[ERRO] não achei portfolio/iniciativas/*/prd.md com id {a.id}. "
                         "Gere o PRD com o product-lead antes.")
    for nome in ("prfaq.md", "prd.md"):
        if not (pasta / nome).exists():
            raise SystemExit(f"[ERRO] falta {nome} em {pasta.relative_to(RAIZ)}")
    conf = portao_consumir("aprovar-prd", a.id, a.mensagem)
    prd = pasta / "prd.md"
    texto = re.sub(r"^status:.*$", "status: aprovado", prd.read_text(encoding="utf-8"), count=1, flags=re.M)
    prd.write_text(texto, encoding="utf-8")
    arq = RAIZ / ".ash" / "approvals" / f"{a.id}-prd.json"
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps({"spec_id": a.id, "papel": "prd", "nome": a.nome, "ts": _agora_iso(),
                               "canal": conf["canal"], "texto_humano": conf["texto_humano"],
                               "portao": conf.get("id", "")}, ensure_ascii=False, indent=2), encoding="utf-8")
    ev.gravar("prd_aprovado", a.id, "humano", "descoberta", {"nome": a.nome, "canal": conf["canal"]})
    print(f"[OK] PRD de {a.id} aprovado por {a.nome}. "
          f"Gere a story com: python ash.py nova-descoberta {a.id} <slug>")
    return 0


def cmd_nova_descoberta(a) -> int:
    """Materializa a story a partir do PRD aprovado e cria a branch feat/<id>, como o nova-spec."""
    pasta = _slug_iniciativa(a.id)
    if pasta is None:
        raise SystemExit(f"[ERRO] não achei o PRD da iniciativa {a.id} em portfolio/iniciativas/.")
    prd = (pasta / "prd.md").read_text(encoding="utf-8")
    if not re.search(r"^status:\s*aprovado\s*$", prd, re.M):
        raise SystemExit(f"[ERRO] o PRD de {a.id} não está aprovado. Passe pelo portão aprovar-prd antes.")
    low = a.id.lower()
    rodar(["git", "switch", "-q", "main"])
    rodar(["git", "switch", "-c", f"feat/{low}"])
    story = RAIZ / "stories" / f"{a.id}-{a.slug}.md"
    story.parent.mkdir(exist_ok=True)
    if story.exists():
        print(f"== {story.name} já existe; mantido")
    else:
        modelo = (RAIZ / "templates" / "story-po.md").read_text(encoding="utf-8")
        modelo = re.sub(r"^id: .*$", f"id: {a.id}", modelo, count=1, flags=re.M)
        corpo = (modelo
                 + "\n\n## Origem\n"
                 + f"Esta story foi gerada a partir do PRD aprovado em "
                 + f"portfolio/iniciativas/{pasta.name}/prd.md (fase de descoberta).\n"
                 + "Preencha os campos acima a partir do PRD antes do intake, ou peça ao product-lead.\n")
        story.write_text(corpo, encoding="utf-8")
    print(f"[OK] branch feat/{low} criada; story em stories/{story.name} (origem: PRD {pasta.name})")
    if remoto():
        print("[INFO] a branch vai para o GitHub no primeiro python ash.py sync, depois do primeiro commit")
    return 0


def cmd_publicar_proto(a) -> int:
    """Portão publicar-proto: publica o protótipo da iniciativa em S3 privado + CloudFront (ato humano, toca AWS)."""
    cfg = config()
    pasta = _slug_iniciativa(a.id)
    if pasta is None:
        raise SystemExit(f"[ERRO] não achei a iniciativa {a.id} em portfolio/iniciativas/.")
    proto = pasta / "prototipo"
    if not proto.exists() or not any(proto.iterdir()):
        raise SystemExit(f"[ERRO] não há protótipo em {proto.relative_to(RAIZ)} (peça ao designer-proto).")
    bucket = cfg.get("ASH_PROTO_BUCKET")
    dist = cfg.get("ASH_PROTO_DISTRIBUTION")
    if not bucket or not dist:
        raise SystemExit("[ERRO] ASH_PROTO_BUCKET/ASH_PROTO_DISTRIBUTION vazios em .ash/config.env. "
                         "Rode o portão bootstrap com a stack de protótipo antes (python ash.py bootstrap).")
    import registrar_evento as ev
    conf = portao_consumir("publicar-proto", a.id, a.mensagem)
    prefixo = f"{pasta.name}/"
    rodar(aws_base(cfg) + ["s3", "sync", str(proto), f"s3://{bucket}/{prefixo}", "--delete",
                           "--sse", "AES256", "--only-show-errors"])
    rodar(aws_base(cfg) + ["cloudfront", "create-invalidation", "--distribution-id", dist,
                           "--paths", f"/{prefixo}*"])
    ev.gravar("proto_publicado", a.id, "humano", "descoberta", {"iniciativa": pasta.name, "canal": conf["canal"]})
    print(f"[OK] protótipo de {a.id} publicado em s3://{bucket}/{prefixo} e invalidado no CloudFront {dist}.")
    return 0


def cmd_aprovar(a) -> int:
    import aprovar
    import ash_spec
    import registrar_evento as ev
    caminho = aprovar.achar_spec(a.id)
    acao = {"po": "aprovar-po", "design": "aprovar-design", "dev": "aprovar-dev",
            "homologacao": "aprovar-homologacao"}[a.papel]
    if a.papel == "homologacao":
        if not a.branch or not a.evidencia:
            raise SystemExit("[ERRO] o papel homologacao exige --branch e --evidencia (onde está o registro da execução "
                             "em conta real de homologação, por exemplo um link ou o id da execução)")
        spec = ash_spec.ler(caminho)
        if spec.meta.get("status") != "aprovada":
            raise SystemExit("[ERRO] a spec precisa estar aprovada pelo PO antes da homologação")
        commit = aprovar.commit_da_branch(a.branch)
        conf = portao_consumir(acao, a.id, a.mensagem)
        aprovar.registrar_aprovacao(spec.id, "homologacao", a.nome, a.branch, commit,
                                    {**conf, "evidencia": a.evidencia.strip()[:300]})
        ev.gravar("aprovacao_merge", spec.id, "humano", spec.meta["faixa"],
                  {"papel": "homologacao", "commit": commit[:12], "canal": conf["canal"]})
        print(f"[OK] homologação em conta real de {spec.id} registrada no commit {commit[:8]} "
              f"(evidência declarada por {a.nome})")
        return 0
    if a.papel == "design":
        spec = ash_spec.ler(caminho)
        if spec.meta.get("status") != "aprovada":
            raise SystemExit("[ERRO] a spec precisa estar aprovada pelo PO antes do design")
        faltando = [n for n in ("design.md", "tasks.md") if not (caminho.parent / n).exists()]
        if faltando:
            raise SystemExit(f"[ERRO] faltam {faltando} em {caminho.parent}")
        conf = portao_consumir(acao, a.id, a.mensagem)
        aprovar.registrar_aprovacao(spec.id, "design", a.nome, branch_atual(), saida(["git", "rev-parse", "HEAD"]),
                                    conf)
        ev.gravar("design_aprovado", spec.id, "humano", spec.meta["faixa"],
                  {"nome": a.nome, "canal": conf["canal"]})
        print(f"[OK] design e tasks de {spec.id} aprovados por {a.nome}")
        return 0
    if a.papel == "po":
        aprovar.checar_spec_aprovavel(caminho)
        conf = portao_consumir(acao, a.id, a.mensagem)
        aprovar.aprovar_spec(caminho, a.nome, conf)
        return 0
    if not a.branch:
        raise SystemExit("[ERRO] --branch é obrigatório para o papel dev")
    aprovar.checar_merge_aprovavel(caminho, "dev", a.nome)
    conf = portao_consumir(acao, a.id, a.mensagem)
    aprovar.aprovar_dev(caminho, a.nome, a.branch, conf)
    return 0


def homologacao_pendente(aprov: dict, head: str) -> str:
    """Texto do problema se falta a aprovação 'homologacao' para o commit atual; vazio se está tudo certo."""
    h = aprov.get("homologacao")
    if not h:
        return ("falta a execução em conta real de homologação com evidência registrada "
                "(python ash.py aprovar ID --papel homologacao --nome NOME --branch feat/<id> --evidencia \"...\")")
    if h.get("commit") != head:
        return (f"a homologação foi registrada no commit {str(h.get('commit'))[:8]}, mas a branch está em {head[:8]}; "
                "registre de novo para o commit atual")
    return ""


def cmd_merge(a) -> int:
    import ash_spec
    import registrar_evento as ev
    if subprocess.run(["git", "diff", "--quiet"]).returncode != 0 or \
            subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode != 0:
        sujos = [x for x in _mudancas_harness()]
        if sujos:
            raise SystemExit("[ERRO] há mudanças do harness não publicadas: " + ", ".join(sujos) +
                             ". Abra antes o portão publicar-harness e depois volte ao merge.")
        raise SystemExit("[ERRO] há alterações não commitadas na branch. Faça commit na feat/<id> antes.")
    if subprocess.run(["git", "rev-parse", "--verify", "-q", a.branch], capture_output=True).returncode != 0:
        raise SystemExit(f"[ERRO] branch {a.branch} não existe")

    import portao
    portao.verificar("merge", a.id, a.mensagem)
    print(f"== 1/6 CI local na branch {a.branch}")
    rodar(["git", "switch", "-q", a.branch])
    os.environ["ASH_SPEC"] = a.id
    rc = cmd_ci(a)
    if rc != 0:
        raise SystemExit(f"[ERRO] CI local não passou (código {rc}). Merge cancelado; a branch {a.branch} "
                         "continua ativa para correção.")

    print("== 2/6 Aprovações")
    head = saida(["git", "rev-parse", a.branch])
    spec = next((ash_spec.ler(c) for c in ash_spec.todas() if ash_spec.ler(c).id == a.id), None)
    if spec is None:
        raise SystemExit(f"[ERRO] spec {a.id} não encontrada")
    if spec.meta.get("status") != "aprovada":
        raise SystemExit(f"[ERRO] spec {a.id} não está aprovada pelo PO")
    arq = RAIZ / ".ash" / "approvals" / f"{a.id}.json"
    aprov = {x["papel"]: x for x in json.loads(arq.read_text(encoding="utf-8"))["aprovacoes"]} if arq.exists() else {}
    faixa = spec.meta["faixa"]
    if "design" not in aprov:
        raise SystemExit("[ERRO] design.md e tasks.md ainda não foram aprovados (python ash.py aprovar ID --papel design)")
    fde = a.fde or config().get("ASH_FDE") or ""
    if not fde:
        raise SystemExit("[ERRO] informe --fde NOME ou ASH_FDE em .ash/config.env")
    if faixa == "critica" and "dev" in aprov and aprov["dev"]["nome"].lower() == fde.lower():
        raise SystemExit("[ERRO] separação de funções: FDE e dev_revisor são a mesma pessoa")
    exigidos = ["dev"] if faixa == "critica" else []
    for papel in exigidos:
        if papel not in aprov:
            raise SystemExit(f"[ERRO] falta aprovação do papel '{papel}' (faixa {faixa})")
        if aprov[papel]["commit"] != head:
            raise SystemExit(f"[ERRO] aprovação de '{papel}' foi dada no commit {aprov[papel]['commit'][:8]}, "
                             f"mas a branch está em {head[:8]}. Peça nova aprovação.")
    import emulador
    bloco_emulador = perfil().get("emulador_aws")
    if emulador.exige_homologacao(bloco_emulador, faixa):
        problema = homologacao_pendente(aprov, head)
        if problema:
            abaixo = ", ".join(emulador.servicos_abaixo_do_corte(bloco_emulador)) or "nenhum, mas a faixa crítica sempre exige"
            raise SystemExit(f"[ERRO] {problema} (faixa {faixa}; serviços do perfil abaixo do corte de fidelidade do "
                             f"emulador: {abaixo})")
    print(f"[OK] pré-condições válidas para {head[:8]} (faixa {faixa}); design aprovado"
          + (", dev_revisor aprovou" if exigidos else ""))

    conf = portao_consumir("merge", a.id, a.mensagem)
    import aprovar
    aprovar.registrar_aprovacao(a.id, "fde", fde, a.branch, head, conf)
    ev.gravar("aprovacao_merge", a.id, "humano", faixa, {"papel": "fde", "commit": head[:12], "canal": conf["canal"]})
    for _ in range(max(0, a.reescritas)):
        ev.gravar("reescrita_humana", a.id, "humano", faixa, {"papel": "fde"})
    canal = conf["canal"]

    print("== 3/6 Merge")
    rodar(["git", "switch", "-q", "main"])
    env = {"ASH_MERGE": "1"}
    rodar(["git", "merge", "--no-ff", "--no-commit", a.branch], env=env)
    rodar(["git", "add", "-f", str(arq.relative_to(RAIZ))], env=env)
    rodar(["git", "commit", "-q", "-m",
           f"merge: {a.id} ({a.branch}) com CI local verde e aprovações registradas"], env=env)
    ev.gravar("merge", a.id, "humano", faixa, {"branch": a.branch, "canal": canal,
                                                "commit": saida(["git", "rev-parse", "--short", "HEAD"])})
    print("== 4/6 GitHub")
    push("main")
    push(a.branch)
    print("== 5/6 Métricas para o S3")
    if config().get("ASH_EVENTS_BUCKET"):
        try:
            cmd_metricas(a)
        except SystemExit as e:
            print(f"[AVISO] métricas não enviadas: {e}")
    else:
        print("[INFO] coletor de métricas ainda não criado (portão bootstrap); eventos ficam em .ash/events/")
    print("== 6/6 Backup no S3 (opcional)")
    if config().get("ASH_CODE_BUCKET"):
        try:
            cmd_backup(a)
        except SystemExit as e:
            print(f"[AVISO] backup não feito: {e}")
    else:
        print("[INFO] backup em S3 não configurado; o GitHub é o repositório principal")
    print(f"[OK] {a.id} na main.")
    return 0


def cmd_metricas(_a) -> int:
    cfg = config()
    bucket = cfg.get("ASH_EVENTS_BUCKET")
    if not bucket:
        raise SystemExit("ASH_EVENTS_BUCKET vazio em .ash/config.env (rode python ash.py bootstrap)")
    squad = cfg.get("ASH_SQUAD", "minha-squad")
    pasta = RAIZ / ".ash" / "events"
    enviados = pasta / "enviados"
    enviados.mkdir(parents=True, exist_ok=True)
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    maquina = re.sub(r"[^A-Za-z0-9-]", "-", socket.gethostname().split(".")[0]) or "maquina"
    n = 0
    for f in sorted(pasta.glob("*.jsonl")):
        rodar(aws_base(cfg) + ["s3", "cp", str(f), f"s3://{bucket}/raw/squad={squad}/{maquina}-{f.name}",
                               "--sse", "AES256", "--only-show-errors"])
        n += 1
        if f.stem != hoje:
            shutil.move(str(f), str(enviados / f.name))
    print(f"[OK] {n} arquivo(s) de eventos enviados")
    return 0


def cmd_backup(_a) -> int:
    cfg = config()
    bucket = cfg.get("ASH_CODE_BUCKET")
    if not bucket:
        raise SystemExit("ASH_CODE_BUCKET vazio em .ash/config.env (rode python ash.py bootstrap)")
    repo = RAIZ.name
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with tempfile.TemporaryDirectory() as tmp:
        arq = Path(tmp) / f"{repo}-{ts}.bundle"
        rodar(["git", "bundle", "create", str(arq), "--all"])
        rodar(["git", "bundle", "verify", "-q", str(arq)])
        for chave in (f"bundles/{repo}/{repo}-{ts}.bundle", f"bundles/{repo}/latest.bundle"):
            rodar(aws_base(cfg) + ["s3", "cp", str(arq), f"s3://{bucket}/{chave}", "--sse", "AES256",
                                   "--only-show-errors"])
    print(f"[OK] backup em s3://{bucket}/bundles/{repo}/{repo}-{ts}.bundle e latest.bundle")
    return 0


def cmd_restaurar(a) -> int:
    destino = Path(a.destino).resolve()
    if destino.exists():
        raise SystemExit(f"[ERRO] {destino} já existe")
    cfg = config()
    with tempfile.TemporaryDirectory() as tmp:
        arq = Path(tmp) / "repo.bundle"
        rodar(aws_base(cfg) + ["s3", "cp", f"s3://{a.bucket}/bundles/{a.repo}/{a.bundle}", str(arq),
                               "--only-show-errors"])
        rodar(["git", "bundle", "verify", "-q", str(arq)])
        rodar(["git", "clone", "-q", str(arq), str(destino)])
    remotos = saida(["git", "-C", str(destino), "branch", "-r"]).splitlines()
    for r in remotos:
        r = r.strip()
        if "->" in r or not r.startswith("origin/"):
            continue
        b = r.split("/", 1)[1]
        if subprocess.run(["git", "-C", str(destino), "show-ref", "--verify", "-q", f"refs/heads/{b}"]).returncode:
            rodar(["git", "-C", str(destino), "branch", "-q", "--track", b, r])
    rodar(["git", "-C", str(destino), "remote", "remove", "origin"])
    rodar(["git", "-C", str(destino), "config", "core.hooksPath", ".githooks"])
    print(f"[OK] restaurado em {destino}. Rode python ash.py setup dentro dele.")
    return 0


def _cdk_env() -> dict:
    return {"PATH": str(venv_bin(".venv")) + os.pathsep + os.environ.get("PATH", "")}


def cmd_bootstrap(a) -> int:
    cfg = config() if CFG.exists() else {}
    if not CFG.exists():
        shutil.copy(RAIZ / ".ash" / "config.env.example", CFG)
        cfg = config()
    if not venv_py(".venv").exists():
        raise SystemExit("[ERRO] rode antes: python ash.py setup")
    conta = saida(aws_base(cfg) + ["sts", "get-caller-identity", "--query", "Account", "--output", "text"])
    if not conta:
        raise SystemExit("[ERRO] AWS CLI sem credenciais válidas")
    esperado = cfg.get("ASH_CONTA_ESPERADA")
    if esperado and conta != esperado:
        raise SystemExit(f"[ERRO] credenciais apontam para {conta}, esperado {esperado}")
    print(f"== conta {conta}")
    rodar([str(venv_py(".venv")), "-m", "pip", "install", "-q", "-r", "infra/requirements.txt"])
    cdk = exe("cdk")
    regiao = cfg.get("AWS_REGION") or "us-east-1"
    env = {**_cdk_env(), "AWS_REGION": regiao, "AWS_DEFAULT_REGION": regiao}
    if cfg.get("AWS_PROFILE"):
        env["AWS_PROFILE"] = cfg["AWS_PROFILE"]
    contexto = []
    for k, c in (("owner", "ASH_TAG_OWNER"), ("costCenter", "ASH_TAG_COST_CENTER"), ("env", "ASH_TAG_ENV"),
                 ("squad", "ASH_SQUAD")):
        if cfg.get(c):
            contexto += ["-c", f"{k}={cfg[c]}"]
    print("== cdk diff (o que será criado, inclusive IAM)")
    stacks = ["AshCodeStack", "AshMetricsStack", "AshProtoStack"]
    if a.so_diff:
        subprocess.run([cdk, "diff"] + stacks + contexto, cwd=RAIZ / "infra",
                       env={**os.environ, **env})
        print("[OK] diff mostrado. Abra o portão bootstrap e, com o APROVO do humano, rode sem --so-diff.")
        return 0
    portao_consumir("bootstrap", "AWS", a.mensagem)
    aprovacao = "never"
    r = subprocess.run([cdk, "deploy"] + stacks + ["--require-approval", aprovacao] + contexto,
                       cwd=RAIZ / "infra", env={**os.environ, **env})
    if r.returncode != 0:
        raise SystemExit("[ERRO] cdk deploy falhou")

    def out(stack: str, chave: str) -> str:
        return saida(aws_base(cfg) + ["cloudformation", "describe-stacks", "--stack-name", stack, "--query",
                                      f"Stacks[0].Outputs[?OutputKey=='{chave}'].OutputValue", "--output", "text"])

    for chave, (stack, saida_cfn) in {"ASH_CODE_BUCKET": ("AshCodeStack", "CodeBucketName"),
                                      "ASH_EVENTS_BUCKET": ("AshMetricsStack", "EventsBucketName"),
                                      "ASH_REPORTS_BUCKET": ("AshMetricsStack", "ReportsBucketName"),
                                      "ASH_PROTO_BUCKET": ("AshProtoStack", "ProtoBucketName"),
                                      "ASH_PROTO_DISTRIBUTION": ("AshProtoStack", "ProtoDistributionId")}.items():
        valor = out(stack, saida_cfn)
        gravar_config(chave, valor)
        print(f"  {chave}={valor}")
    print("[OK] bootstrap concluído")
    return 0


def cmd_teardown(a) -> int:
    cfg = config()
    portao_consumir("teardown", "AWS", a.mensagem)
    regiao = cfg.get("AWS_REGION") or "us-east-1"
    env = {**os.environ, **_cdk_env(), "AWS_REGION": regiao, "AWS_DEFAULT_REGION": regiao}
    if cfg.get("AWS_PROFILE"):
        env["AWS_PROFILE"] = cfg["AWS_PROFILE"]
    r = subprocess.run([exe("cdk"), "destroy", "AshMetricsStack", "AshProtoStack", "--force"], cwd=RAIZ / "infra", env=env)
    if r.returncode != 0:
        raise SystemExit("[ERRO] cdk destroy falhou")
    print(f"[OK] coletor e protótipo removidos (CloudFront e WAF). Buckets mantidos: código {cfg.get('ASH_CODE_BUCKET', '(não configurado)')}, "
          f"protótipo {cfg.get('ASH_PROTO_BUCKET', '(não configurado)')}")
    return 0


def cmd_pendencias(_a) -> int:
    import pendencias
    return pendencias.main()


def cmd_status(_a) -> int:
    print(f"Sistema: {platform.system()} · Python {platform.python_version()} ({sys.executable})")
    print(f".venv: {'ok' if venv_py('.venv').exists() else 'não criada'} · "
          f".venv-tools: {'ok' if venv_py('.venv-tools').exists() else 'não criada'}")
    for f in ("git", "aws", "node", "cdk"):
        print(f"{f}: {shutil.which(f) or 'NÃO ENCONTRADO'}")
    print(aviso_certificados())
    try:
        import emulador
        usa_emulador = bool(perfil().get("emulador_aws"))
        print(emulador.linha_status(config()) + ("" if usa_emulador else " · perfil ativo: não usa o emulador"))
    except Exception as e:  # o status nunca falha por causa do emulador
        print(f"Emulador AWS: não foi possível consultar ({type(e).__name__})")
    try:
        pf = perfil()
        origem = "ash-perfil.json" if PERFIL_ARQ.exists() else "padrão interno"
        print(f"Perfil de stack: {pf['nome']} ({'testado' if pf.get('testado') else 'NÃO TESTADO'}, {origem}) · "
              f"etapas do CI: {', '.join(['spec-gate'] + [e['nome'] for e in pf['etapas']] + ['rastreio'])}")
    except SystemExit as e:
        print(f"Perfil de stack: {e}")
    print(f"Lentes de vertical: {', '.join(lentes_ativas()) or 'nenhuma'}")
    print(f"Branch: {branch_atual() or '(sem git)'}")
    print(f"hooksPath: {saida(['git', 'config', 'core.hooksPath']) or '(não configurado)'}")
    linha = linha_hooks()
    if linha:
        print(linha)
    cfg = config()
    print(f"Squad: {cfg.get('ASH_SQUAD') or '(vazio)'} · PO: {cfg.get('ASH_PO') or '(vazio)'} · "
          f"FDE: {cfg.get('ASH_FDE') or '(vazio)'} · Dev revisor: {cfg.get('ASH_DEV_REVISOR') or '(nenhum)'}")
    print(f"Repositório remoto: {cfg.get('ASH_GIT_REMOTE') or '(vazio)'}")
    if not (cfg.get("ASH_PO") and cfg.get("ASH_FDE")):
        print("[CONFIGURAR] faltam nomes da squad: pergunte ao humano e rode python ash.py configurar")
    for k in ("ASH_CODE_BUCKET", "ASH_EVENTS_BUCKET", "ASH_REPORTS_BUCKET",
              "ASH_PROTO_BUCKET", "ASH_PROTO_DISTRIBUTION"):
        print(f"{k}: {cfg.get(k) or '(vazio)'}")
    import portao
    print(portao.status())
    return 0


def cmd_portao(a) -> int:
    import portao
    if a.operacao == "status":
        print(portao.status())
        return 0
    if not (a.acao and a.spec and a.resumo):
        raise SystemExit("[ERRO] use: portao abrir --acao ACAO --spec ID --resumo \"...\"")
    if a.acao == "aprovar-po":
        import aprovar
        aprovar.checar_spec_aprovavel(aprovar.achar_spec(a.spec))
    p = portao.abrir(a.acao, a.spec, a.resumo)
    print(f"[PORTÃO ABERTO] {p['acao']} {p['spec']} (id {p['id']}). "
          "Mostre a decisão ao humano e peça que responda APROVO no chat.")
    return 0


def cmd_testar(_a) -> int:
    """Roda os testes do projeto com o comando rápido do perfil de stack (sem cobertura)."""
    pf = perfil()
    return subprocess.run(expandir(pf["testar"], pf)).returncode


def cmd_testar_harness(a) -> int:
    """Roda tests_harness/ com o pytest da .venv-tools; com --integracao, roda tests_harness_integracao/ contra o emulador."""
    py = venv_py(".venv-tools")
    if not py.exists():
        raise SystemExit("[ERRO] .venv-tools não existe. Rode: python ash.py setup")
    if getattr(a, "auditoria", False):
        return subprocess.run([str(py), "scripts/auditoria_ferramentas.py"],
                              env={**os.environ, "PYTHONUTF8": "1"}).returncode
    if not getattr(a, "integracao", False):
        return subprocess.run([str(py), "-m", "pytest", "tests_harness", "-q"],
                              env={**os.environ, "PYTHONUTF8": "1"}).returncode
    import emulador
    try:
        bloco = emulador.bloco_do_harness()
        with emulador.emulador_para_ci(config(), bloco) as estado:
            env = emulador.ambiente_do_estado(estado, os.environ)
            return subprocess.run([str(py), "-m", "pytest", "tests_harness_integracao", "-q"], env=env).returncode
    except emulador.ErroEmulador as e:
        print(f"[ERRO] {e}")
        return 1


def cmd_etapa(a) -> int:
    """Roda uma etapa do CI do perfil isolada (ex.: testes, sast, dependencias). Não registra evento."""
    pf = perfil()
    nomes = [e["nome"] for e in pf["etapas"]]
    if a.nome not in nomes:
        raise SystemExit(f"[ERRO] etapa '{a.nome}' não existe no perfil {pf['nome']}. Etapas: {', '.join(nomes)}")
    etapa = next(e for e in pf["etapas"] if e["nome"] == a.nome)
    env = {**os.environ, "PYTHONUTF8": "1"}
    if etapa.get("requer") == "emulador_aws":
        import emulador
        try:
            with emulador.emulador_para_ci(config(), pf.get("emulador_aws")) as estado:
                env = emulador.ambiente_do_estado(estado, os.environ)
                return subprocess.run(expandir(etapa["comando"], pf), env=env).returncode
        except emulador.ErroEmulador as e:
            print(f"[ERRO] {e}")
            return 1
    return subprocess.run(expandir(etapa["comando"], pf), env=env).returncode


def cmd_emulador(a) -> int:
    """Sobe, para, mostra ou reinicia o AWS Emulator local (modos linux, wsl e container). Nunca toca conta real."""
    import emulador
    cfg = config()
    pf = perfil()
    bloco = pf.get("emulador_aws")
    try:
        if bloco is None and a.operacao in ("iniciar", "reset"):
            bloco = emulador.bloco_do_harness()
            print("[INFO] o perfil ativo não declara emulador_aws; usando a versão fixada dos testes de integração do "
                  "harness (tests_harness_integracao/emulador.json)")
        if a.operacao == "status":
            deteccao = emulador.detectar_modos(cfg)
            print(emulador.linha_status(cfg, deteccao=deteccao))
            print("Modos:")
            print("\n".join(emulador.detalhe_modos(deteccao)))
            return 0
        if a.operacao in ("parar", "reset"):
            estado = emulador.ler_estado()
            if emulador.parar(estado):
                print("[OK] emulador parado; estado local apagado")
            else:
                print("[OK] o emulador já estava parado")
            if a.operacao == "parar":
                return 0
        estado = emulador.iniciar(cfg, bloco)
        situacao = "já estava de pé" if estado.get("ja_estava") else "iniciado"
        print(f"[OK] emulador {situacao}: modo {estado['modo']}, {estado['endpoint']}, "
              f"encerra sozinho após {emulador.formatar_duracao(int(estado['idle']))} sem chamadas de API")
        print("[INFO] as chaves do emulador mudam a cada início e ficam só em .ash/emulador/ (fora do git)")
        return 0
    except emulador.ErroEmulador as e:
        print(f"[ERRO] {e}")
        return 1


def cmd_perfil(a) -> int:
    """Mostra o perfil de stack ativo ou ativa um perfil de perfis/ (mudança de harness)."""
    if not a.nome:
        pf = perfil()
        print(f"Perfil ativo: {pf['nome']} · {pf.get('descricao', '')}")
        print(f"Testado: {'sim' if pf.get('testado') else 'NÃO'} · código em {pf.get('pasta_codigo', 'src')}/ · "
              f"testes: {', '.join(pf.get('arquivos_teste', []))}")
        print(f"Etapas do CI: spec-gate, {', '.join(e['nome'] for e in pf['etapas'])}, rastreio")
        disponiveis = sorted(p.stem for p in PASTA_PERFIS.glob("*.json") if p.stem != "modelo")
        print(f"Perfis disponíveis em perfis/: {', '.join(disponiveis) or 'nenhum'} (modelo.json é o ponto de partida)")
        return 0
    origem = PASTA_PERFIS / f"{a.nome}.json"
    if not origem.exists():
        raise SystemExit(f"[ERRO] perfis/{a.nome}.json não existe")
    try:
        dados = json.loads(origem.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"[ERRO] perfis/{a.nome}.json não é JSON válido: {e}")
    validar_perfil(dados, f"perfis/{a.nome}.json")
    faltam = {"testes", "sast", "dependencias"} - {e["nome"] for e in dados["etapas"]}
    if faltam:
        print(f"[AVISO] os revisores de cobertura e de vulnerabilidade usam as etapas testes, sast e dependencias; "
              f"este perfil não tem: {', '.join(sorted(faltam))}. Ajuste os prompts desses revisores ou os nomes das etapas.")
    if "harness" not in {e["nome"] for e in dados["etapas"]}:
        print("[AVISO] todo perfil leva a etapa harness (comando: {python} ash.py testar-harness), que roda os testes do "
              "próprio ASH; este perfil não a tem.")
    aviso = aviso_boto3_do_projeto(dados)
    if aviso:
        print(aviso)
    PERFIL_ARQ.write_bytes(origem.read_bytes())  # cópia byte a byte: write_text trocaria LF por CRLF no Windows
    print(f"[OK] perfil ativo: {dados['nome']}. Rode python ash.py setup para instalar as dependências da stack "
          "e publique a mudança pelo portão publicar-harness.")
    if not dados.get("testado"):
        print("[AVISO] perfil marcado como não testado: rode python ash.py ci e confira cada etapa antes da primeira story.")
    return 0


def cmd_configurar(a) -> int:
    """Grava os dados da squad em .ash/config.env (arquivo local, fora do git)."""
    if not CFG.exists():
        CFG.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(RAIZ / ".ash" / "config.env.example", CFG)
    pares = {"ASH_PO": a.po, "ASH_FDE": a.fde, "ASH_DEV_REVISOR": a.dev, "ASH_GIT_REMOTE": a.remote,
             "ASH_SQUAD": a.squad, "ASH_GIT_NOME": a.git_nome or a.fde, "ASH_GIT_EMAIL": a.git_email}
    for chave, valor in pares.items():
        if valor:
            gravar_config(chave, f'"{valor}"' if " " in valor else valor)
    cfg = config()
    print(f"[OK] squad {cfg.get('ASH_SQUAD')}: PO {cfg.get('ASH_PO') or '(vazio)'}, FDE {cfg.get('ASH_FDE') or '(vazio)'}, "
          f"Dev revisor {cfg.get('ASH_DEV_REVISOR') or '(nenhum)'}, remoto {cfg.get('ASH_GIT_REMOTE') or '(vazio)'}")
    if cfg.get("ASH_DEV_REVISOR") and cfg.get("ASH_DEV_REVISOR", "").lower() == cfg.get("ASH_FDE", "").lower():
        print("[AVISO] Dev revisor e FDE são a mesma pessoa: a faixa critica não vai conseguir fazer merge")
    return 0


def cmd_relatorio(a) -> int:
    """Linha do tempo e métricas de cada spec a partir dos eventos locais (.ash/events), sem AWS."""
    import relatorio_local
    return relatorio_local.main(a.spec)


def cmd_validar(a) -> int:
    """Checagem completa de uma spec: dez blocos, critérios e perguntas em aberto (a mesma do aprovar-po)."""
    import aprovar
    import ash_spec
    caminho = aprovar.achar_spec(a.id)
    aprovar.checar_spec_aprovavel(caminho)
    spec = ash_spec.ler(caminho)
    print(f"[OK] {spec.id} pronta para o portão aprovar-po (faixa {spec.meta.get('faixa')}, "
          f"status {spec.meta.get('status')})")
    return 0


GITIGNORE_PADRAO = """.venv
.venv-tools
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
.ash/config.env
.ash/events/
.ash/approvals/
.ash/gate/
.ash/hook-debug/
.ash/emulador/
.ash/relatorio.md
infra/cdk.out/
infra/.cdk.staging/
*.bundle
.DS_Store
"""


def garantir_gitignore() -> None:
    """Recria o .gitignore se ele sumir (já aconteceu na extração do pacote no Windows)."""
    arq = RAIZ / ".gitignore"
    if not arq.exists():
        arq.write_text(GITIGNORE_PADRAO, encoding="utf-8")
        print("[INFO] .gitignore recriado")


def main(argv=None) -> int:
    garantir_gitignore()
    CERTIFICADOS_IGNORADOS[:] = limpar_certificados_invalidos()
    p = argparse.ArgumentParser(prog="ash", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="comando", required=True)

    def novo(nome, func, humano=False):
        s = sub.add_parser(nome)
        s.set_defaults(func=func)
        if humano:
            s.add_argument("--mensagem", help="texto literal da mensagem do humano no chat (modo oficial do portão)")
        return s

    novo("setup", cmd_setup).add_argument("--remote", help="URL do repositório no GitHub")
    novo("sync", cmd_sync)
    novo("publicar-harness", cmd_publicar_harness, humano=True)
    novo("ci", cmd_ci).add_argument("--spec")
    s = novo("nova-spec", cmd_nova_spec); s.add_argument("id"); s.add_argument("slug")
    s = novo("nova-descoberta", cmd_nova_descoberta); s.add_argument("id"); s.add_argument("slug")
    s = novo("aprovar-prd", cmd_aprovar_prd, humano=True); s.add_argument("id"); s.add_argument("--nome", required=True)
    s = novo("publicar-proto", cmd_publicar_proto, humano=True); s.add_argument("id")
    s = novo("aprovar", cmd_aprovar, humano=True)
    s.add_argument("id"); s.add_argument("--papel", required=True, choices=["po", "design", "dev", "homologacao"])
    s.add_argument("--nome", required=True); s.add_argument("--branch"); s.add_argument("--reescritas", type=int, default=0)
    s.add_argument("--evidencia", help="papel homologacao: onde está o registro da execução em conta real")
    s = novo("merge", cmd_merge, humano=True); s.add_argument("branch"); s.add_argument("id")
    s.add_argument("--fde"); s.add_argument("--reescritas", type=int, default=0)
    novo("metricas", cmd_metricas)
    novo("backup", cmd_backup)
    s = novo("restaurar", cmd_restaurar)
    s.add_argument("bucket"); s.add_argument("destino")
    s.add_argument("--bundle", default="latest.bundle"); s.add_argument("--repo", default=RAIZ.name)
    novo("bootstrap", cmd_bootstrap, humano=True).add_argument("--so-diff", action="store_true")
    novo("teardown", cmd_teardown, humano=True)
    novo("pendencias", cmd_pendencias)
    novo("testar", cmd_testar)
    s = novo("testar-harness", cmd_testar_harness)
    grupo = s.add_mutually_exclusive_group()
    grupo.add_argument("--integracao", action="store_true",
                       help="roda tests_harness_integracao/ contra o AWS Emulator (uso do autor do harness; não faz parte do CI)")
    grupo.add_argument("--auditoria", action="store_true",
                       help="audita o requirements-tools.txt com o pip-audit e os aceites de tests_harness/auditoria_ferramentas.json "
                            "(uso do autor do harness; precisa de rede; não faz parte do CI)")
    novo("emulador", cmd_emulador).add_argument("operacao", choices=["iniciar", "parar", "status", "reset"])
    novo("etapa", cmd_etapa).add_argument("nome")
    novo("perfil", cmd_perfil).add_argument("nome", nargs="?")
    novo("status", cmd_status)
    novo("validar", cmd_validar).add_argument("id")
    novo("relatorio", cmd_relatorio).add_argument("--spec")
    s = novo("configurar", cmd_configurar)
    s.add_argument("--po"); s.add_argument("--fde"); s.add_argument("--dev"); s.add_argument("--remote")
    s.add_argument("--squad"); s.add_argument("--git-nome", dest="git_nome"); s.add_argument("--git-email", dest="git_email")
    s = novo("portao", cmd_portao)
    s.add_argument("operacao", choices=["abrir", "status"])
    s.add_argument("--acao"); s.add_argument("--spec"); s.add_argument("--resumo")
    a = p.parse_args(argv)
    if CERTIFICADOS_IGNORADOS and a.comando in COMANDOS_DE_REDE:
        print(f"[INFO] {aviso_certificados()}")
    return a.func(a) or 0


if __name__ == "__main__":
    sys.exit(main())
