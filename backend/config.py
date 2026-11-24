import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


def obter_database_url():
    ambiente = os.getenv("APP_ENV")

    variaveis = {
        "development": "DATABASE_URL_DEV",
        "production": "DATABASE_URL_PROD",
    }

    if ambiente not in variaveis:
        raise RuntimeError(f"APP_ENV inválido: {ambiente}")

    nome = variaveis[ambiente]
    url = os.getenv(nome)

    if not url:
        raise RuntimeError(f"{nome} não configurada")

    return url
