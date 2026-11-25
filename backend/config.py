import os
from pathlib import Path

from dotenv import load_dotenv

# backend/config.py -> RAIZ = triagem-condominial/
RAIZ = Path(__file__).resolve().parent.parent

load_dotenv(RAIZ / ".env", override=False)
load_dotenv(RAIZ / "backend" / ".env", override=False)

def obter_database_url():
    ambiente = (os.getenv("APP_ENV") or "development").strip().lower()

    apelidos = {
        "dev": "development",
        "local": "development",
        "development": "development",
        "prod": "production",
        "production": "production",
    }

    if ambiente not in apelidos:
        raise RuntimeError(f"APP_ENV inválido: {ambiente}")

    ambiente = apelidos[ambiente]

    variaveis = {
        "development": "DATABASE_URL_DEV",
        "production": "DATABASE_URL_PROD",
    }

    nome = variaveis[ambiente]
    url = os.getenv(nome)

    if not url:
        url = os.getenv("DATABASE_URL")

    if not url:
        raise RuntimeError(
            f"{nome} não configurada."
            f"Coloque {nome} ou DATABASE_URL no .env da raiz ou em backend/.env"
        )

    return url