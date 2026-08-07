"""Carrega config/perfis.json e as variaveis do .env."""

import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_CONFIG = RAIZ / "config" / "perfis.json"
CAMINHO_ENV = RAIZ / ".env"
DIR_DADOS = RAIZ / "dados"
DIR_RELATORIOS = RAIZ / "relatorios"


def carregar_env():
    """Le o .env sem dependencia externa. Nao sobrescreve o ambiente real."""
    if not CAMINHO_ENV.exists():
        return
    for linha in CAMINHO_ENV.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        chave = chave.strip()
        valor = valor.strip().strip('"').strip("'")
        if chave and chave not in os.environ:
            os.environ[chave] = valor


def carregar():
    carregar_env()
    dados = json.loads(CAMINHO_CONFIG.read_text(encoding="utf-8"))
    for perfil in dados["perfis"]:
        # O .env tem prioridade sobre o id gravado no json.
        chave = "IG_USER_ID_" + perfil["username"].upper()
        do_env = os.environ.get(chave, "").strip()
        if do_env:
            perfil["ig_user_id"] = do_env
    DIR_DADOS.mkdir(exist_ok=True)
    DIR_RELATORIOS.mkdir(exist_ok=True)
    return dados


def salvar(dados):
    """Regrava o json preservando o campo _leia_me."""
    CAMINHO_CONFIG.write_text(
        json.dumps(dados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def perfil_por_username(dados, username):
    for perfil in dados["perfis"]:
        if perfil["username"] == username:
            return perfil
    raise KeyError("perfil nao encontrado em config/perfis.json: " + username)


def token():
    carregar_env()
    return os.environ.get("IG_ACCESS_TOKEN", "").strip()


def versao_api():
    carregar_env()
    return os.environ.get("IG_API_VERSION", "v23.0").strip() or "v23.0"
