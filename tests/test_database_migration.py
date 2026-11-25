
"""Testes da migration inicial — SQU-72 / SQU-74."""

import os
import uuid
from pathlib import Path

import psycopg2
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text


TABELAS = {
    "sindicos",
    "condominios",
    "responsaveis",
    "palavras_risco",
    "ocorrencias",
    "registros_decisao",
}


@pytest.fixture
def conexao():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("Execute os testes usando: task db-test")

    banco = psycopg2.connect(url)
    banco.autocommit = True

    try:
        yield banco
    finally:
        banco.close()


def test_migration_aplicada(conexao):
    config = Config(Path(__file__).resolve().parents[1] / "alembic.ini")
    revisoes_esperadas = set(ScriptDirectory.from_config(config).get_heads())
    with conexao.cursor() as cursor:
        cursor.execute("SELECT version_num FROM alembic_version")
        revisoes_aplicadas = {versao for (versao,) in cursor.fetchall()}

    assert revisoes_aplicadas == revisoes_esperadas


def test_todas_as_tabelas_existem():
    url = os.environ.get("TEST_DATABASE_URL")
    assert url, "Execute usando: task db-test"

    engine = create_engine(url)
    try:
        tabelas = set(inspect(engine).get_table_names())
        assert TABELAS.issubset(tabelas)
    finally:
        engine.dispose()


def test_chaves_estrangeiras():
    url = os.environ["TEST_DATABASE_URL"]
    engine = create_engine(url)

    esperadas = {
        "condominios": ("sindico_id", "sindicos"),
        "responsaveis": ("condominio_id", "condominios"),
        "ocorrencias": ("condominio_id", "condominios"),
        "registros_decisao": ("ocorrencia_id", "ocorrencias"),
    }

    try:
        inspector = inspect(engine)

        for tabela, (coluna, destino) in esperadas.items():
            chaves = inspector.get_foreign_keys(tabela)

            assert any(
                coluna in chave["constrained_columns"]
                and chave["referred_table"] == destino
                for chave in chaves
            ), f"FK ausente: {tabela}.{coluna} -> {destino}"
    finally:
        engine.dispose()


def test_sindico_temporariamente_opcional(conexao):
    identificador = f"teste-{uuid.uuid4().hex[:8]}"

    with conexao.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO condominios (identificador, nome)
            VALUES (%s, %s)
            RETURNING sindico_id
            """,
            (identificador, "Condomínio de Teste"),
        )

        assert cursor.fetchone()[0] is None


def test_status_invalido_e_rejeitado(conexao):
    identificador = f"teste-{uuid.uuid4().hex[:8]}"

    with conexao.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO condominios (identificador, nome)
            VALUES (%s, %s)
            RETURNING id
            """,
            (identificador, "Condomínio de Teste"),
        )
        condominio_id = cursor.fetchone()[0]

        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                """
                INSERT INTO ocorrencias
                    (protocolo, condominio_id, origem, descricao, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    f"TEST-{uuid.uuid4().hex[:12]}",
                    condominio_id,
                    "morador",
                    "Ocorrência de teste",
                    "status_invalido",
                ),
            )


@pytest.mark.parametrize("operacao", ["UPDATE", "DELETE"])
def test_historico_nao_pode_ser_modificado(conexao, operacao):
    identificador = f"teste-{uuid.uuid4().hex[:8]}"

    with conexao.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO condominios (identificador, nome)
            VALUES (%s, %s)
            RETURNING id
            """,
            (identificador, "Condomínio de Teste"),
        )
        condominio_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO ocorrencias
                (protocolo, condominio_id, origem, descricao)
            VALUES (%s, %s, 'morador', 'Teste do histórico')
            RETURNING id
            """,
            (
                f"TEST-{uuid.uuid4().hex[:12]}",
                condominio_id,
            ),
        )
        ocorrencia_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO registros_decisao
                (ocorrencia_id, tipo, quem_decidiu, origem)
            VALUES (%s, 'entrada', 'sistema', 'morador')
            RETURNING id
            """,
            (ocorrencia_id,),
        )
        registro_id = cursor.fetchone()[0]

        if operacao == "UPDATE":
            comando = "UPDATE registros_decisao SET nota = 'alterado' WHERE id = %s"
        else:
            comando = "DELETE FROM registros_decisao WHERE id = %s"

        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(comando, (registro_id,))
