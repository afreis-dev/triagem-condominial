import psycopg2

try:
    from backend.config import obter_database_url
except ModuleNotFoundError as erro:
    if erro.name != "backend":
        raise
    from config import obter_database_url


def conectar():
    """Abre uma conexão com o PostgreSQL conforme o APP_ENV."""
    url = obter_database_url()
    return psycopg2.connect(url, connect_timeout=5)
