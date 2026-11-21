
"""Testes de persistência do backend no esquema real do Alembic."""

import importlib
import os
import re
import uuid

import psycopg2
import pytest
from sqlalchemy.engine import make_url

from backend.lib.salvar_ocorrencia import salvar_ocorrencia
from backend.lib.registrar_decisao import registrar_decisao
from backend.lib.concluir_ocorrencia import concluir_ocorrencia


modulo_salvar = importlib.import_module(
    "backend.lib.salvar_ocorrencia"
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
def condominio(conexao):
    with conexao.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sindicos (nome)
            VALUES ('Síndico de teste')
            RETURNING id
            """
        )
        sindico_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO condominios
                (identificador, nome, sindico_id)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (
                f"teste-{uuid.uuid4().hex[:8]}",
                "Condomínio de teste",
                sindico_id,
            ),
        )

        return cur.fetchone()[0]


def criar_ocorrencia(conexao, condominio):
    resultado = salvar_ocorrencia(
        {
            "condominioId": condominio,
            "origem": "morador",
            "nome": "Morador de teste",
            "apartamento": "101",
            "celular": "11999990000",
            "descricao": "Lâmpada do hall queimada",
        },
        conexao=conexao,
    )

    assert resultado["ok"] is True
    return resultado


def test_registro_e_protocolo(conexao, condominio):
    resultado = criar_ocorrencia(conexao, condominio)
    ocorrencia_id = resultado["ocorrenciaId"]

    assert resultado["protocolo"] == (
        f"TS-{ocorrencia_id:06d}"
    )

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT condominio_id, protocolo, status,
                   prioridade, celular
            FROM ocorrencias
            WHERE id = %s
            """,
            (ocorrencia_id,),
        )

        vinculo, protocolo, status, prioridade, celular = (
            cur.fetchone()
        )

        assert vinculo == condominio
        assert protocolo == resultado["protocolo"]
        assert status == "nova"
        assert prioridade in (
            "urgente", "alta", "normal", "baixa"
        )
        assert celular == "11999990000"


def test_registro_whatsapp(conexao, condominio):
    resultado = salvar_ocorrencia(
        {
            "condominioId": condominio,
            "origem": "whatsapp_sindico",
            "descricao": "Portão da garagem travado",
        },
        conexao=conexao,
    )

    assert resultado["ok"] is True

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT origem, nome, celular
            FROM ocorrencias
            WHERE id = %s
            """,
            (resultado["ocorrenciaId"],),
        )

        assert cur.fetchone() == (
            "whatsapp_sindico", None, None
        )


def test_falha_classificacao_preserva_ocorrencia(
    conexao, condominio, monkeypatch
):
    def classificacao_com_falha(texto):
        raise RuntimeError("Falha simulada")

    monkeypatch.setattr(
        modulo_salvar,
        "classificar",
        classificacao_com_falha,
    )

    resultado = criar_ocorrencia(conexao, condominio)
    ocorrencia_id = resultado["ocorrenciaId"]

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT status, prioridade, motivo
            FROM ocorrencias
            WHERE id = %s
            """,
            (ocorrencia_id,),
        )

        assert cur.fetchone() == (
            "nova",
            None,
            "não classificada, revisar",
        )

        cur.execute(
            """
            SELECT tipo, prioridade_sugerida
            FROM registros_decisao
            WHERE ocorrencia_id = %s
            """,
            (ocorrencia_id,),
        )

        assert cur.fetchall() == [
            ("entrada", None)
        ]


def test_registro_de_decisao(conexao, condominio):
    resultado = criar_ocorrencia(conexao, condominio)
    ocorrencia_id = resultado["ocorrenciaId"]

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT prioridade
            FROM ocorrencias
            WHERE id = %s
            """,
            (ocorrencia_id,),
        )
        prioridade = cur.fetchone()[0]

    resultado = registrar_decisao(
        {
            "ocorrenciaId": ocorrencia_id,
            "tipo": "prioridade_confirmada",
            "quemDecidiu": "sindico",
            "prioridadeSugerida": prioridade,
            "prioridadeFinal": prioridade,
        },
        conexao=conexao,
    )

    assert resultado["ok"] is True

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT tipo, quem_decidiu, prioridade_final
            FROM registros_decisao
            WHERE id = %s
            """,
            (resultado["registroId"],),
        )

        assert cur.fetchone() == (
            "prioridade_confirmada",
            "sindico",
            prioridade,
        )


def test_conclusao_e_historico(conexao, condominio):
    resultado = criar_ocorrencia(conexao, condominio)
    ocorrencia_id = resultado["ocorrenciaId"]

    # Uma ocorrência nova não pode ser concluída.
    assert concluir_ocorrencia(
        ocorrencia_id,
        conexao=conexao,
    )["ok"] is False

    acao = registrar_decisao(
        {
            "ocorrenciaId": ocorrencia_id,
            "tipo": "acao",
            "quemDecidiu": "sindico",
            "acao": "eu_mesmo",
        },
        conexao=conexao,
    )

    assert acao["ok"] is True

    # Prepara o estado exigido pela H13.
    # A transição real da H11 pertence ao fluxo da aplicação.
    with conexao.cursor() as cur:
        cur.execute(
            """
            UPDATE ocorrencias
            SET status = 'em_andamento'
            WHERE id = %s
            """,
            (ocorrencia_id,),
        )

    resultado = concluir_ocorrencia(
        ocorrencia_id,
        conexao=conexao,
    )

    assert resultado["ok"] is True

    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT status, concluida_em
            FROM ocorrencias
            WHERE id = %s
            """,
            (ocorrencia_id,),
        )

        status, concluida_em = cur.fetchone()

        assert status == "concluida"
        assert concluida_em is not None

        cur.execute(
            """
            SELECT tipo
            FROM registros_decisao
            WHERE ocorrencia_id = %s
            ORDER BY id
            """,
            (ocorrencia_id,),
        )

        assert cur.fetchall() == [
            ("entrada",),
            ("acao",),
            ("conclusao",),
        ]


def test_fk_invalida_rejeitada(conexao):
    with conexao.cursor() as cur:
        with pytest.raises(
            psycopg2.errors.ForeignKeyViolation
        ):
            cur.execute(
                """
                INSERT INTO ocorrencias
                    (protocolo, condominio_id,
                     origem, descricao)
                VALUES (%s, -1, 'morador', 'Teste')
                """,
                (f"TEST-{uuid.uuid4().hex[:12]}",),
            )


def test_identificador_duplicado_rejeitado(
    conexao, condominio
):
    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT identificador
            FROM condominios
            WHERE id = %s
            """,
            (condominio,),
        )

        identificador = cur.fetchone()[0]

        with pytest.raises(
            psycopg2.errors.UniqueViolation
        ):
            cur.execute(
                """
                INSERT INTO condominios
                    (identificador, nome)
                VALUES (%s, 'Duplicado')
                """,
                (identificador,),
            )
