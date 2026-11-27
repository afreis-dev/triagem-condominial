import os
import sys
import uuid
from pathlib import Path

import psycopg2
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

SCHEMA = Path(__file__).with_name("schema_teste.sql")


@pytest.fixture(autouse=True)
def ia_desligada(monkeypatch):
    """Nenhum teste chama a IA de verdade, mesmo que IA_ATIVA esteja no ambiente."""
    monkeypatch.delenv("IA_ATIVA", raising=False)


@pytest.fixture
def conexao():
    """Conexão com um schema novo e descartável, criado a partir de schema_teste.sql."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("defina TEST_DATABASE_URL para rodar os testes com banco")
    conn = psycopg2.connect(url)
    nome = f"teste_{uuid.uuid4().hex[:10]}"
    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA {nome}")
        cur.execute(f"SET search_path TO {nome}")
        cur.execute(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()
    yield conn
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA {nome} CASCADE")
    conn.commit()
    conn.close()


@pytest.fixture
def sindico(conexao):
    with conexao.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sindicos (nome, email)
            VALUES (%s, %s)
            RETURNING id
            """,
            ("Síndico Teste", "sindico@teste.com"),
        )
        sindico_id = cur.fetchone()[0]

    conexao.commit()
    return sindico_id


@pytest.fixture
def condominio(conexao, sindico):
    with conexao.cursor() as cur:
        cur.execute(
            """
            INSERT INTO condominios (identificador, nome, bairro, sindico_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            ("aurora", "Residencial Aurora", "Boa Viagem", sindico),
        )
        condominio_id = cur.fetchone()[0]
    conexao.commit()
    return condominio_id


@pytest.fixture
def contar_confirmadas(conexao):
    """Conta as ocorrências por outra conexão, que só enxerga o que já foi confirmado no banco."""
    with conexao.cursor() as cur:
        cur.execute("SELECT current_schema()")
        esquema = cur.fetchone()[0]
    conexao.commit()
    outra = psycopg2.connect(os.environ["TEST_DATABASE_URL"])
    outra.autocommit = True

    def contar():
        with outra.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {esquema}.ocorrencias")
            return cur.fetchone()[0]

    yield contar
    outra.close()


@pytest.fixture
def criar_ocorrencia(conexao, condominio):
    def criar(status="nova", travada=False):
        with conexao.cursor() as cur:
            cur.execute("SELECT nextval(pg_get_serial_sequence('ocorrencias', 'id'))")
            ocorrencia_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO ocorrencias (id, protocolo, condominio_id, origem, descricao, status, travada) "
                "VALUES (%s, %s, %s, 'morador', 'teste', %s, %s)",
                (ocorrencia_id, f"TS-{ocorrencia_id:06d}", condominio, status, travada),
            )
        conexao.commit()
        return ocorrencia_id

    return criar
