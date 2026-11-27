
"""Executa testes de banco em um PostgreSQL temporário e isolado."""

import os
import re
import subprocess
import sys
import time
import uuid

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from sqlalchemy.engine import make_url


def executar(*comando, ambiente=None):
    print(f"\n> {' '.join(comando)}", flush=True)
    subprocess.run(comando, check=True, env=ambiente)


def conectar_admin(url):
    return psycopg2.connect(
        host=url.host,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        dbname="postgres",
        connect_timeout=3,
    )


def aguardar_postgres(url):
    for _ in range(20):
        try:
            conexao = conectar_admin(url)
            conexao.close()
            return
        except psycopg2.OperationalError:
            time.sleep(1)
    raise RuntimeError("PostgreSQL não respondeu após 20 segundos")


def main():
    load_dotenv()

    if os.getenv("APP_ENV") != "development":
        raise RuntimeError("db-test exige APP_ENV=development")

    database_url = os.getenv("DATABASE_URL_DEV")
    if not database_url:
        raise RuntimeError("DATABASE_URL_DEV não foi configurada")

    url = make_url(database_url)

    # Proteção contra execução em servidores remotos.
    if url.host not in ("localhost", "127.0.0.1"):
        raise RuntimeError("db-test permite apenas PostgreSQL local")

    if url.database != "triagem_db_dev":
        raise RuntimeError(
            "DATABASE_URL_DEV deve apontar para triagem_db_dev"
        )

    nome_teste = f"triagem_test_{uuid.uuid4().hex[:12]}"
    url_teste = url.set(database=nome_teste)
    conexao_teste = url_teste.render_as_string(
        hide_password=False
    )

    ambiente = os.environ.copy()
    ambiente["DATABASE_URL_DEV"] = conexao_teste
    ambiente["DATABASE_URL"] = conexao_teste
    ambiente["TEST_DATABASE_URL"] = conexao_teste

    print("Iniciando PostgreSQL...", flush=True)
    executar("docker", "compose", "up", "-d", "postgres")
    aguardar_postgres(url)

    admin = conectar_admin(url)
    admin.autocommit = True
    criado = False

    try:
        with admin.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(nome_teste)
                )
            )
        criado = True
        print(f"Banco temporário criado: {nome_teste}", flush=True)

        executar(
            sys.executable, "-m", "alembic",
            "upgrade", "head",
            ambiente=ambiente,
        )

        executar(
            sys.executable, "-m", "pytest",
            "-v", "tests/",
            ambiente=ambiente,
        )

        executar(
            sys.executable, "-m", "alembic",
            "downgrade", "base",
            ambiente=ambiente,
        )

        print("\nTodos os testes passaram!", flush=True)

    finally:
        if criado:
            if not re.fullmatch(r"triagem_test_[0-9a-f]{12}", nome_teste):
                raise RuntimeError("Nome de banco temporário inválido")

            print("\nLimpando banco temporário...", flush=True)

            with admin.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s
                      AND pid <> pg_backend_pid()
                    """,
                    (nome_teste,),
                )
                cursor.execute(
                    sql.SQL("DROP DATABASE {}").format(
                        sql.Identifier(nome_teste)
                    )
                )

            print("Banco temporário removido.", flush=True)

        admin.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print(f"\nFalha no db-test: {erro}", file=sys.stderr)
        sys.exit(1)
