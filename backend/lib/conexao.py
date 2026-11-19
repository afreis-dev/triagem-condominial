import os

import psycopg2
from dotenv import load_dotenv


def conectar():
    """Abre uma conexão com o PostgreSQL usando a DATABASE_URL do .env."""
    load_dotenv()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL não definida")
    return psycopg2.connect(url, connect_timeout=5)
