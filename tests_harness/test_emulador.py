"""Testes de scripts/emulador.py com dublês: nenhum emulador, WSL ou contêiner precisa estar de pé."""
import json
from types import SimpleNamespace

import pytest

import emulador
from emulador import ErroEmulador

CHAVE_FALSA = "EMULATOR_ID_FALSO_DE_TESTE"  # só o prefixo importa; não imita o formato real das chaves


@pytest.fixture(autouse=True)
def sem_variaveis_do_emulador(monkeypatch):
    """Garante que o ambiente real do desenvolvedor não influencia os testes."""
    for nome in ("ASH_EMULADOR_MODO", "ASH_EMULADOR_PORTA", "ASH_EMULADOR_IDLE", "ASH_EMULADOR_AUTO",
                 "ASH_EMULADOR_WSL_DISTRO", "ASH_CONTAINER_CLI"):
        monkeypatch.delenv(nome, raising=False)


@pytest.fixture()
def pasta_estado(monkeypatch, tmp_path):
    """Redireciona o estado do emulador para uma pasta temporária."""
    monkeypatch.setattr(emulador, "DIR", tmp_path / "emulador")
    monkeypatch.setattr(emulador, "ESTADO", tmp_path / "emulador" / "estado.json")
    monkeypatch.setattr(emulador, "LOG", tmp_path / "emulador" / "emulador.log")
    monkeypatch.setattr(emulador, "HOME_LOCAL", tmp_path / "emulador" / "home")
    return tmp_path / "emulador"


# ---------------------------------------------------------------- configuração
def test_porta_idle_e_auto_leem_cfg_com_padroes_e_limites():
    assert emulador.porta({}) == 9297 and emulador.idle({}) == 1800 and emulador.auto_ci({}) is False
    assert emulador.porta({"ASH_EMULADOR_PORTA": "9300"}) == 9300
    assert emulador.porta({"ASH_EMULADOR_PORTA": "0"}) == 9297 and emulador.porta({"ASH_EMULADOR_PORTA": "abc"}) == 9297
    assert emulador.idle({"ASH_EMULADOR_IDLE": "60"}) == 60 and emulador.idle({"ASH_EMULADOR_IDLE": "-5"}) == 1800
    assert emulador.auto_ci({"ASH_EMULADOR_AUTO": "SIM"}) is True


def test_variavel_de_ambiente_tem_precedencia_sobre_o_config(monkeypatch):
    monkeypatch.setenv("ASH_EMULADOR_IDLE", "120")
    assert emulador.idle({"ASH_EMULADOR_IDLE": "900"}) == 120


# ---------------------------------------------------------------- ambiente isolado e provas
def test_ambiente_isolado_remove_credenciais_reais_e_aponta_para_o_emulador(tmp_path):
    base = {"AWS_ACCESS_KEY_ID": "real", "AWS_SECRET_ACCESS_KEY": "real", "AWS_SESSION_TOKEN": "real",
            "AWS_PROFILE": "prod", "aws_default_profile": "prod", "AWS_WEB_IDENTITY_TOKEN_FILE": "x",
            "AWS_CONTAINER_CREDENTIALS_FULL_URI": "http://x", "AWS_ENDPOINT_URL_S3": "https://s3.real",
            "AWS_SSO_SESSION": "s", "OUTRA": "fica", "NO_PROXY": "interno.local"}
    env = emulador.ambiente_isolado(base, "https://127.0.0.1:9297", tmp_path)
    for removida in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE",
                     "aws_default_profile", "AWS_WEB_IDENTITY_TOKEN_FILE", "AWS_CONTAINER_CREDENTIALS_FULL_URI",
                     "AWS_ENDPOINT_URL_S3", "AWS_SSO_SESSION"):
        assert removida not in env
    assert env["AWS_ENDPOINT_URL"] == "https://127.0.0.1:9297"
    assert env["AWS_SHARED_CREDENTIALS_FILE"] == str(tmp_path / "emulator_credentials")
    assert env["AWS_CONFIG_FILE"] == str(tmp_path / "config") and env["AWS_CA_BUNDLE"] == str(tmp_path / "ca.pem")
    assert env["AWS_EC2_METADATA_DISABLED"] == "true" and env["AWS_DISABLE_HOST_PREFIX_INJECTION"] == "true"
    assert env["AWS_REGION"] == "us-east-1" and env["AWS_DEFAULT_REGION"] == "us-east-1"
    assert env["OUTRA"] == "fica" and env["NO_PROXY"] == "interno.local,127.0.0.1"
    assert "AWS_PROFILE" in base  # a cópia não altera o original


@pytest.mark.parametrize("endpoint", ["https://127.0.0.1:9297"])
def test_endpoint_local_e_aceito(endpoint):
    emulador.verificar_endpoint_local(endpoint, 9297)


@pytest.mark.parametrize("endpoint", ["http://127.0.0.1:9297", "https://localhost:9297", "https://10.0.0.5:9297",
                                      "https://127.0.0.1:9300", "https://s3.us-east-1.amazonaws.com"])
def test_endpoint_nao_local_e_recusado(endpoint):
    with pytest.raises(ErroEmulador, match="Endpoint recusado"):
        emulador.verificar_endpoint_local(endpoint, 9297)


def test_credenciais_do_emulador_passam_e_a_chave_nunca_aparece_no_erro(tmp_path):
    arq = tmp_path / "emulator_credentials"
    arq.write_text(f"[default]\naws_access_key_id = {CHAVE_FALSA}\naws_secret_access_key = SEGREDO\n", encoding="utf-8")
    emulador.verificar_credenciais(arq)
    arq.write_text("[default]\naws_access_key_id = AKIAREALREALREAL1234\naws_secret_access_key = SEGREDO\n", encoding="utf-8")
    with pytest.raises(ErroEmulador) as e:
        emulador.verificar_credenciais(arq)
    assert "AKIA" not in str(e.value) and "SEGREDO" not in str(e.value)
    with pytest.raises(ErroEmulador, match="não encontrado"):
        emulador.verificar_credenciais(tmp_path / "nao-existe")


def test_ambiente_do_estado_exige_todas_as_provas(tmp_path):
    estado = {"endpoint": "https://127.0.0.1:9297", "porta": 9297, "pasta_arquivos": str(tmp_path)}
    with pytest.raises(ErroEmulador):  # sem credenciais
        emulador.ambiente_do_estado(estado, {})
    (tmp_path / "emulator_credentials").write_text(f"aws_access_key_id = {CHAVE_FALSA}\n", encoding="utf-8")
    with pytest.raises(ErroEmulador, match="ca.pem"):  # sem certificado
        emulador.ambiente_do_estado(estado, {})
    (tmp_path / "ca.pem").write_text("x", encoding="utf-8")
    assert emulador.ambiente_do_estado(estado, {"AWS_PROFILE": "prod"})["AWS_ENDPOINT_URL"] == estado["endpoint"]
    with pytest.raises(ErroEmulador, match="Endpoint recusado"):
        emulador.ambiente_do_estado({**estado, "endpoint": "https://example.com:9297"}, {})


# ---------------------------------------------------------------- comandos puros
def test_container_publica_so_em_loopback_com_telemetria_e_idle():
    cmd = emulador.comando_container_run("podman", "ash-emulador-9297", 9297, 1800, "/pasta", "img:1", usuario="1000:1000")
    assert cmd[:3] == ["podman", "run", "-d"] and "--rm" in cmd
    assert "127.0.0.1:9297:9297" in cmd and "9297:9297" not in [c for c in cmd if c != "127.0.0.1:9297:9297"]
    assert "--memory=2g" in cmd and "--memory-swap=2g" in cmd
    assert cmd[cmd.index("img:1"):] == ["img:1", "-p", "9297", "--telemetry", "off", "--idle-timeout", "1800"]
    assert cmd[cmd.index("--user") + 1] == "1000:1000"


def test_container_sem_usuario_nao_passa_user():
    assert "--user" not in emulador.comando_container_run("docker", "n", 9297, 60, "/p", "i")


def test_comandos_linux_e_wsl_sempre_com_idle_e_sem_telemetria():
    assert emulador.comando_linux("/usr/bin/aws-emulator", 9300, 120) == [
        "/usr/bin/aws-emulator", "-p", "9300", "--telemetry", "off", "--idle-timeout", "120"]
    assert emulador.comando_wsl("wsl.exe", "Distro", 9297, 1800) == [
        "wsl.exe", "-d", "Distro", "--", "aws-emulator", "-p", "9297", "--telemetry", "off", "--idle-timeout", "1800"]
    assert emulador.comando_parar_wsl("wsl.exe", "Distro", 9297)[-3:] == ["-TERM", "-f", "aws-emulator -p 9297 "]


def test_build_do_container_usa_o_dockerfile_do_repositorio_e_a_url_do_pacote():
    cmd = emulador.comando_container_build("docker", "img:1", "https://exemplo/pacote.rpm")
    assert cmd[:2] == ["docker", "build"] and "EMULATOR_RPM_URL=https://exemplo/pacote.rpm" in cmd
    assert cmd[cmd.index("-f") + 1].replace("\\", "/").endswith("infra/emulador/Dockerfile")


def test_unc_wsl_monta_o_caminho_do_windows():
    assert emulador.unc_wsl("Ubuntu", "/home/dev\n", 9297) == "\\\\wsl$\\Ubuntu\\home\\dev\\.aws\\emulator\\9297"


def test_url_do_pacote_com_e_sem_versao_fixada():
    bloco = {"versao": "1.0.343", "pacote_url_base": "https://base/LTS/"}
    assert emulador.url_pacote(bloco, "x86_64") == "https://base/LTS/aws-emulator-1.0.343-1-x86_64.rpm"
    assert emulador.url_pacote({}, "aarch64") == emulador.BASE_PACOTES + "latest/aws-emulator-aarch64.rpm"


def test_arquitetura():
    assert emulador.arquitetura("AMD64") == "x86_64" and emulador.arquitetura("arm64") == "aarch64"
    with pytest.raises(ErroEmulador):
        emulador.arquitetura("riscv64")


def test_dockerfile_segue_o_da_documentacao():
    texto = (emulador.RAIZ / "infra" / "emulador" / "Dockerfile").read_text(encoding="utf-8")
    assert "amazonlinux:2023-minimal" in texto and "ARG EMULATOR_RPM_URL" in texto
    assert 'ENTRYPOINT ["aws-emulator", "-b", "0.0.0.0"]' in texto and "EXPOSE 9297" in texto


# ---------------------------------------------------------------- detecção de modos
SAIDA_WSL_SO_DOCKER = "  NAME              STATE           VERSION\n* docker-desktop    Stopped         2\n"
SAIDA_WSL_UBUNTU = SAIDA_WSL_SO_DOCKER + "  Ubuntu            Stopped         2\n  Velha             Stopped         1\n"


def _detectar(cfg=None, sistema="Windows", presentes=(), respostas=None):
    respostas = respostas or {}

    def which(nome):
        return f"/bin/{nome}" if nome in presentes else None

    def executar(cmd, timeout=20):
        for prefixo, resposta in respostas.items():
            if " ".join(cmd).startswith(prefixo):
                return resposta
        return 1, ""

    return emulador.detectar_modos(cfg or {}, sistema, which, executar)


def test_windows_so_com_distro_interna_do_docker_nao_tem_modo_wsl():
    det = _detectar(presentes=("wsl.exe",), respostas={"/bin/wsl.exe --list": (0, SAIDA_WSL_SO_DOCKER)})
    assert det["wsl"]["ok"] is False and "própria" in det["wsl"]["motivo"]
    assert det["linux"]["ok"] is False and "só roda em Linux" in det["linux"]["motivo"]


def test_windows_com_distro_wsl2_propria_tem_modo_wsl_e_ignora_wsl1():
    det = _detectar(presentes=("wsl.exe",), respostas={"/bin/wsl.exe --list": (0, SAIDA_WSL_UBUNTU)})
    assert det["wsl"]["ok"] is True and det["wsl"]["detalhe"]["distro"] == "Ubuntu"
    det = _detectar({"ASH_EMULADOR_WSL_DISTRO": "Velha"}, presentes=("wsl.exe",),
                    respostas={"/bin/wsl.exe --list": (0, SAIDA_WSL_UBUNTU)})
    assert det["wsl"]["ok"] is False


def test_container_exige_runtime_com_daemon_respondendo():
    assert _detectar(presentes=())["container"]["ok"] is False
    parado = _detectar(presentes=("docker",), respostas={"docker info": (1, "")})["container"]
    assert parado["ok"] is False and "daemon" in parado["motivo"]
    vivo = _detectar(presentes=("docker",), respostas={"docker info": (0, "ok")})["container"]
    assert vivo["ok"] is True and vivo["detalhe"]["cli"] == "docker"
    podman = _detectar({"ASH_CONTAINER_CLI": "podman"}, presentes=("docker", "podman"),
                       respostas={"podman info": (0, "ok")})["container"]
    assert podman["detalhe"]["cli"] == "podman"
    so_docker = _detectar({"ASH_CONTAINER_CLI": "podman"}, presentes=("docker",), respostas={"docker info": (0, "")})
    assert so_docker["container"]["ok"] is False


def test_linux_precisa_do_comando_aws_emulator():
    assert _detectar(sistema="Linux", presentes=("aws-emulator",))["linux"]["ok"] is True
    assert _detectar(sistema="Linux")["linux"]["ok"] is False
    assert _detectar(sistema="Linux", presentes=("aws-emulator",))["wsl"]["ok"] is False


def test_escolher_modo_pedido_automatico_e_nenhum():
    det = {"linux": {"ok": False, "motivo": "a"}, "wsl": {"ok": True, "motivo": "b"}, "container": {"ok": True, "motivo": "c"}}
    assert emulador.escolher_modo({}, det) == "wsl"  # automático: wsl antes de container
    assert emulador.escolher_modo({"ASH_EMULADOR_MODO": "container"}, det) == "container"
    with pytest.raises(ErroEmulador, match="indisponível"):
        emulador.escolher_modo({"ASH_EMULADOR_MODO": "linux"}, det)
    with pytest.raises(ErroEmulador, match="inválido"):
        emulador.escolher_modo({"ASH_EMULADOR_MODO": "vm"}, det)
    nenhum = {m: {"ok": False, "motivo": f"motivo-{m}"} for m in emulador.MODOS}
    with pytest.raises(ErroEmulador) as e:
        emulador.escolher_modo({}, nenhum)
    assert all(f"motivo-{m}" in str(e.value) for m in emulador.MODOS)


def test_decodificar_saida_utf16_do_wsl():
    assert "Ubuntu" in emulador.decodificar("\ufeffUbuntu\r\n".encode("utf-16-le"))
    assert emulador.decodificar("acentuação".encode("utf-8")) == "acentuação"


# ---------------------------------------------------------------- bloco do perfil e regra de fidelidade
BLOCO = {"versao": "1.0.343", "fidelidade_minima": 80,
         "servicos": [{"nome": "s3", "fidelidade": 95}, {"nome": "sts", "fidelidade": 60}, {"nome": "logs", "fidelidade": None}]}


def test_validar_bloco():
    assert emulador.validar_bloco(BLOCO) == []
    assert emulador.validar_bloco("x") and emulador.validar_bloco({"servicos": []})
    assert emulador.validar_bloco({"servicos": [{"nome": "s3", "fidelidade": 120}]})
    assert emulador.validar_bloco({"servicos": [{"nome": "s3"}], "fidelidade_minima": "alto"})
    assert emulador.validar_bloco({"servicos": [{"fidelidade": 1}]})


def test_servicos_abaixo_do_corte_contam_null_como_abaixo():
    assert emulador.servicos_abaixo_do_corte(BLOCO) == ["sts", "logs"]
    assert emulador.servicos_abaixo_do_corte(None) == []
    assert emulador.servicos_abaixo_do_corte({"servicos": [{"nome": "s3", "fidelidade": 95}]}) == []


def test_regra_de_fidelidade_por_faixa():
    acima = {"servicos": [{"nome": "s3", "fidelidade": 95}], "fidelidade_minima": 80}
    assert emulador.exige_homologacao(BLOCO, "autonoma") is False
    assert emulador.exige_homologacao(BLOCO, "semiautonoma") is True
    assert emulador.exige_homologacao(acima, "semiautonoma") is False
    assert emulador.exige_homologacao(acima, "critica") is True
    assert emulador.exige_homologacao(None, "critica") is False


def test_evidencia_do_emulador_no_ci():
    assert emulador.evidencia(None, []) == {"emulador": "nao_aplicavel"}
    ok = emulador.evidencia(BLOCO, [("integracao-aws", "OK")])
    assert ok == {"emulador": "ok", "emulador_versao": "1.0.343", "servicos_abaixo_do_corte": "sts,logs"}
    assert emulador.evidencia(BLOCO, [("x", "FALHOU")])["emulador"] == "falhou"
    assert emulador.evidencia(BLOCO, [("x", "PULADA")])["emulador"] == "pulado"
    assert emulador.evidencia(BLOCO, [])["emulador"] == "nao_aplicavel"


# ---------------------------------------------------------------- estado, status e ciclo de vida
def test_estado_grava_le_e_apaga_sem_chaves(pasta_estado):
    estado = {"modo": "container", "porta": 9297, "endpoint": "https://127.0.0.1:9297", "pasta_arquivos": "x"}
    emulador.gravar_estado(estado)
    assert emulador.ler_estado() == estado
    assert "EMULATOR" not in emulador.ESTADO.read_text(encoding="utf-8")
    emulador.limpar_estado()
    assert emulador.ler_estado() is None


def test_formatar_duracao():
    assert [emulador.formatar_duracao(s) for s in (45, 720, 7500)] == ["45 s", "12 min", "2 h 05 min"]


def test_linha_status_de_pe_e_parado(monkeypatch):
    estado = {"modo": "wsl", "endpoint": "https://127.0.0.1:9297", "idle": 1800, "iniciado_em": "2026-01-01T00:00:00Z"}
    monkeypatch.setattr(emulador, "de_pe", lambda e: True)
    monkeypatch.setattr(emulador, "agora", lambda: emulador.datetime(2026, 1, 1, 0, 12, 0, tzinfo=emulador.timezone.utc))
    linha = emulador.linha_status({}, estado)
    assert linha.startswith("Emulador AWS: de pé · modo wsl") and "há 12 min" in linha and "30 min" in linha
    monkeypatch.setattr(emulador, "de_pe", lambda e: False)
    nenhum = {m: {"ok": False, "motivo": "x", "detalhe": {}} for m in emulador.MODOS}
    assert "nenhum modo utilizável" in emulador.linha_status({}, {"modo": "wsl"}, nenhum)
    com_container = dict(nenhum, container={"ok": True, "motivo": "ok", "detalhe": {"cli": "docker"}})
    assert emulador.linha_status({}, None, com_container).endswith("modo que seria usado: container")


def test_iniciar_sem_nenhum_modo_explica_o_que_falta(monkeypatch, pasta_estado):
    nenhum = {m: {"ok": False, "motivo": f"falta-{m}", "detalhe": {}} for m in emulador.MODOS}
    monkeypatch.setattr(emulador, "detectar_modos", lambda cfg: nenhum)
    with pytest.raises(ErroEmulador, match="falta-linux"):
        emulador.iniciar({})
    assert emulador.ler_estado() is None


def test_iniciar_recusa_porta_em_uso(monkeypatch, pasta_estado):
    ok = {m: {"ok": True, "motivo": "", "detalhe": {}} for m in emulador.MODOS}
    monkeypatch.setattr(emulador, "detectar_modos", lambda cfg: ok)
    monkeypatch.setattr(emulador, "porta_em_uso", lambda p: True)
    with pytest.raises(ErroEmulador, match="ASH_EMULADOR_PORTA"):
        emulador.iniciar({"ASH_EMULADOR_MODO": "linux"})


def test_iniciar_sobe_prova_e_grava_estado_e_ja_estava_nao_reinicia(monkeypatch, pasta_estado):
    ok = {m: {"ok": True, "motivo": "", "detalhe": {}} for m in emulador.MODOS}
    monkeypatch.setattr(emulador, "detectar_modos", lambda cfg: ok)
    monkeypatch.setattr(emulador, "porta_em_uso", lambda p: False)
    chamadas = []

    def subir(estado, det, cfg):
        estado["pid"], estado["pasta_arquivos"] = 123, str(pasta_estado)
        chamadas.append("subiu")

    monkeypatch.setattr(emulador, "_subir_linux", subir)
    monkeypatch.setattr(emulador, "esperar_pronto", lambda e, *a, **k: chamadas.append("pronto"))
    monkeypatch.setattr(emulador, "ambiente_do_estado", lambda e, base: chamadas.append("provas"))
    estado = emulador.iniciar({"ASH_EMULADOR_MODO": "linux", "ASH_EMULADOR_IDLE": "600"}, {"versao": "1.0.343"})
    assert chamadas == ["subiu", "pronto", "provas"]
    assert estado["modo"] == "linux" and estado["idle"] == 600 and estado["versao"] == "1.0.343"
    assert emulador.ler_estado()["endpoint"] == "https://127.0.0.1:9297"
    monkeypatch.setattr(emulador, "de_pe", lambda e: True)
    assert emulador.iniciar({})["ja_estava"] is True and chamadas == ["subiu", "pronto", "provas"]


def test_iniciar_que_nao_fica_pronto_para_o_que_subiu_e_falha(monkeypatch, pasta_estado):
    ok = {m: {"ok": True, "motivo": "", "detalhe": {}} for m in emulador.MODOS}
    monkeypatch.setattr(emulador, "detectar_modos", lambda cfg: ok)
    monkeypatch.setattr(emulador, "porta_em_uso", lambda p: False)
    monkeypatch.setattr(emulador, "_subir_linux", lambda e, d, c: e.update(pid=1, pasta_arquivos=str(pasta_estado)))
    paradas = []

    def nao_fica_pronto(estado, *a, **k):
        raise ErroEmulador("não respondeu")

    monkeypatch.setattr(emulador, "esperar_pronto", nao_fica_pronto)
    monkeypatch.setattr(emulador, "parar", lambda estado=None, avisar=print, dormir=None: paradas.append(estado["modo"]))
    with pytest.raises(ErroEmulador, match="não respondeu"):
        emulador.iniciar({"ASH_EMULADOR_MODO": "linux"})
    assert paradas == ["linux"]


def test_parar_container_e_wsl_enviam_o_comando_certo_e_confirmam_que_nao_sobrou(monkeypatch, pasta_estado):
    comandos = []
    monkeypatch.setattr(emulador, "rodar_captura", lambda cmd, timeout=20: comandos.append(cmd) or (0, ""))
    monkeypatch.setattr(emulador, "restos", lambda estado: [])
    emulador.gravar_estado({"modo": "container"})
    assert emulador.parar({"modo": "container", "cli": "docker", "container": "ash-emulador-9297"}) is True
    assert comandos[-1] == ["docker", "stop", "ash-emulador-9297"] and emulador.ler_estado() is None
    emulador.parar({"modo": "wsl", "wsl": "wsl.exe", "distro": "D", "porta": 9297})
    assert comandos[-1][:4] == ["wsl.exe", "-d", "D", "--"] and "pkill" in comandos[-1]
    assert emulador.parar(None) is False


def test_parar_avisa_quando_sobra_processo(monkeypatch, pasta_estado):
    monkeypatch.setattr(emulador, "rodar_captura", lambda cmd, timeout=20: (0, ""))
    monkeypatch.setattr(emulador, "restos", lambda estado: ["contêiner x"])
    avisos = []
    emulador.parar({"modo": "container", "cli": "docker", "container": "x"}, avisos.append, dormir=lambda s: None)
    assert avisos and "contêiner x" in avisos[0]


def test_restos_do_container_usa_ps_e_o_do_wsl_usa_pgrep(monkeypatch):
    monkeypatch.setattr(emulador, "rodar_captura", lambda cmd, timeout=20: (0, "abc123\n"))
    assert emulador.restos({"modo": "container", "cli": "docker", "container": "n"}) == ["contêiner n"]
    assert emulador.restos({"modo": "wsl", "wsl": "w", "distro": "D", "porta": 1})
    monkeypatch.setattr(emulador, "rodar_captura", lambda cmd, timeout=20: (1, ""))
    assert emulador.restos({"modo": "wsl", "wsl": "w", "distro": "D", "porta": 1}) == []


# ---------------------------------------------------------------- contexto do ci
def test_emulador_para_ci_falha_com_mensagem_clara_sem_auto(monkeypatch):
    monkeypatch.setattr(emulador, "ler_estado", lambda: None)
    with pytest.raises(ErroEmulador, match="python ash.py emulador iniciar"):
        with emulador.emulador_para_ci({}, None):
            pass


def test_emulador_para_ci_com_auto_sobe_e_para_ao_final_mesmo_com_falha(monkeypatch):
    eventos = []
    monkeypatch.setattr(emulador, "ler_estado", lambda: None)
    monkeypatch.setattr(emulador, "iniciar", lambda cfg, bloco, avisar=print: eventos.append("iniciar") or {"modo": "linux"})
    monkeypatch.setattr(emulador, "parar", lambda estado=None, avisar=print, dormir=None: eventos.append("parar"))
    with emulador.emulador_para_ci({"ASH_EMULADOR_AUTO": "sim"}, None) as estado:
        assert estado == {"modo": "linux"}
    with pytest.raises(RuntimeError):
        with emulador.emulador_para_ci({"ASH_EMULADOR_AUTO": "sim"}, None):
            raise RuntimeError("falha na etapa")
    assert eventos == ["iniciar", "parar", "iniciar", "parar"]


def test_emulador_para_ci_deixa_como_estava_se_ja_estava_de_pe(monkeypatch):
    eventos = []
    monkeypatch.setattr(emulador, "ler_estado", lambda: {"modo": "wsl"})
    monkeypatch.setattr(emulador, "de_pe", lambda e: True)
    monkeypatch.setattr(emulador, "iniciar", lambda *a, **k: eventos.append("iniciar"))
    monkeypatch.setattr(emulador, "parar", lambda *a, **k: eventos.append("parar"))
    with emulador.emulador_para_ci({"ASH_EMULADOR_AUTO": "sim"}, None) as estado:
        assert estado == {"modo": "wsl"}
    assert eventos == []


def test_saude_devolve_falso_sem_certificado_ou_sem_servidor(tmp_path):
    assert emulador.saude("https://127.0.0.1:1", tmp_path / "nao-existe.pem") is False
    assert emulador.porta_em_uso(1) is False
