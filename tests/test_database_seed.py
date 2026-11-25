
"""Testes de integração do seed da Sprint 1."""

import json
import os
import re

import psycopg2
import pytest
from sqlalchemy.engine import make_url

from scripts.db_seed import (
    DATA_FILE,
    DEMO_NAME,
    carregar_referencias,
    carregar_demonstracao,
    resumo,
)


@pytest.fixture
def conexao():
    url = os.environ.get("TEST_DATABASE_URL")

    if not url:
        pytest.fail("Execute usando: task db-test")

    banco = make_url(url)

    assert banco.host in ("localhost", "127.0.0.1")
    assert re.fullmatch(
        r"triagem_test_[0-9a-f]{12}",
        banco.database or "",
    ), "Banco de teste inválido"

    conn = psycopg2.connect(url)

    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.fixture
def dados():
    return json.loads(
        DATA_FILE.read_text(encoding="utf-8")
    )


def test_seed_dados_oficiais(conexao, dados):
    with conexao.cursor() as cur:
        carregar_referencias(cur, dados)

        for sindico in dados["sindicos"]:
            cur.execute(
                """
                SELECT nome, celular, email
                FROM sindicos
                WHERE email = %s
                """,
                (sindico["email"],),
            )

            assert cur.fetchall() == [
                (
                    sindico["nome"],
                    sindico["celular"],
                    sindico["email"],
                )
            ]

        for condominio in dados["condominios"]:
            cur.execute(
                """
                SELECT nome, bairro
                FROM condominios
                WHERE identificador = %s
                """,
                (condominio["identificador"],),
            )

            assert cur.fetchone() == (
                condominio["nome"],
                condominio["bairro"],
            )


def test_carteira_do_sindico(conexao, dados):
    with conexao.cursor() as cur:
        carregar_referencias(cur, dados)

        cur.execute(
            """
            SELECT c.identificador
            FROM condominios c
            JOIN sindicos s ON s.id = c.sindico_id
            WHERE s.email = %s
            """,
            (dados["sindicos"][0]["email"],),
        )

        identificadores = {
            linha[0] for linha in cur.fetchall()
        }

        assert identificadores == {
            c["identificador"]
            for c in dados["condominios"]
        }


def test_responsaveis_por_condominio(conexao, dados):
    with conexao.cursor() as cur:
        carregar_referencias(cur, dados)

        for responsavel in dados["responsaveis"]:
            cur.execute(
                """
                SELECT r.nome, r.celular
                FROM responsaveis r
                JOIN condominios c
                    ON c.id = r.condominio_id
                WHERE c.identificador = %s
                  AND r.papel = %s
                """,
                (
                    responsavel["condominio"],
                    responsavel["papel"],
                ),
            )

            assert cur.fetchall() == [
                (
                    responsavel["nome"],
                    responsavel["celular"],
                )
            ]


def test_palavras_de_risco(conexao, dados):
    with conexao.cursor() as cur:
        carregar_referencias(cur, dados)

        cur.execute(
            """
            SELECT palavra, categoria, prioridade,
                   responsavel_sugerido, motivo
            FROM palavras_risco
            ORDER BY ordem
            """
        )

        assert cur.fetchall() == [
            (
                p["palavra"],
                p["categoria"],
                p["prioridade"],
                p["responsavel_sugerido"],
                p["motivo"],
            )
            for p in dados["palavras_risco"]
        ]


def test_seed_referencia_idempotente(conexao, dados):
    with conexao.cursor() as cur:
        carregar_referencias(cur, dados)
        primeira_carga = resumo(cur)

        carregar_referencias(cur, dados)
        segunda_carga = resumo(cur)

        assert primeira_carga == segunda_carga


def test_seed_demonstrativo_idempotente(conexao, dados):
    with conexao.cursor() as cur:
        carregar_referencias(cur, dados)
        carregar_demonstracao(cur)

        primeira_carga = resumo(cur)

        cur.execute(
            """
            SELECT COUNT(*)
            FROM ocorrencias
            WHERE nome = %s
            """,
            (DEMO_NAME,),
        )
        assert cur.fetchone()[0] == 5

        cur.execute(
            """
            SELECT COUNT(*)
            FROM registros_decisao r
            JOIN ocorrencias o
                ON o.id = r.ocorrencia_id
            WHERE o.nome = %s
            """,
            (DEMO_NAME,),
        )
        assert cur.fetchone()[0] == 12

        carregar_demonstracao(cur)

        assert resumo(cur) == primeira_carga
