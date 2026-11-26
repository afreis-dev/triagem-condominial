import os
import uuid
import psycopg2
import pytest
from fastapi.testclient import TestClient

from main import app
from lib.auth import criar_token

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def conn_public():
    # usa o banco public, igual a API — não o schema teste_xxx
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    c = psycopg2.connect(url)
    yield c
    c.rollback()
    c.close()

def _token(sindico_id):
    return criar_token(sindico_id)

def _criar(conn_public, condominio_id, prioridade="normal", travada=False, status="nova"):
    protocolo = f"TEST-{uuid.uuid4().hex[:8].upper()}"
    with conn_public.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ocorrencias
                (condominio_id, protocolo, origem, descricao, prioridade, travada, status)
            VALUES (%s, %s, 'morador', %s, %s, %s, %s)
            RETURNING id
            """,
            (condominio_id, protocolo, "teste lote", prioridade, travada, status),
        )
        oid = cur.fetchone()[0]
    conn_public.commit()
    return oid

def _limpar(conn_public, ids):
    with conn_public.cursor() as cur:
        # desliga a trigger que proíbe apagar histórico, só pra limpar o teste
        cur.execute("SET LOCAL session_replication_role = replica")
        cur.execute("DELETE FROM registros_decisao WHERE ocorrencia_id = ANY(%s)", (ids,))
        cur.execute("DELETE FROM ocorrencias WHERE id = ANY(%s)", (ids,))
    conn_public.commit()

SINDICO = 2
CONDOMINIO = 7
OUTRO_SINDICO = 3

def test_aprova_varias_de_uma_vez(conn_public, client):
    ids = [_criar(conn_public, CONDOMINIO) for _ in range(3)]
    try:
        r = client.post(
            "/ocorrencias/aprovar-lote",
            json={"ids": ids},
            headers={"Authorization": f"Bearer {_token(SINDICO)}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["aprovadas"] == 3
    finally:
        _limpar(conn_public, ids)

def test_recusa_urgente_e_travada(conn_public, client):
    id_urg = _criar(conn_public, CONDOMINIO, prioridade="urgente")
    id_trav = _criar(conn_public, CONDOMINIO, travada=True)
    try:
        r = client.post(
            "/ocorrencias/aprovar-lote",
            json={"ids": [id_urg, id_trav]},
            headers={"Authorization": f"Bearer {_token(SINDICO)}"},
        )
        assert r.status_code in (409, 422), r.text
    finally:
        _limpar(conn_public, [id_urg, id_trav])

def test_recusa_outro_sindico(conn_public, client):
    oid = _criar(conn_public, CONDOMINIO)
    try:
        r = client.post(
            "/ocorrencias/aprovar-lote",
            json={"ids": [oid]},
            headers={"Authorization": f"Bearer {_token(OUTRO_SINDICO)}"},
        )
        assert r.status_code in (403, 409, 422), r.text
    finally:
        _limpar(conn_public, [oid])

def test_nao_grava_nada_se_um_id_invalido(conn_public, client):
    id_ok = _criar(conn_public, CONDOMINIO)
    try:
        r = client.post(
            "/ocorrencias/aprovar-lote",
            json={"ids": [id_ok, 999999]},
            headers={"Authorization": f"Bearer {_token(SINDICO)}"},
        )
        assert r.status_code in (404, 409, 422), r.text
        with conn_public.cursor() as cur:
            cur.execute("SELECT status FROM ocorrencias WHERE id = %s", (id_ok,))
            assert cur.fetchone()[0] == "nova"
    finally:
        _limpar(conn_public, [id_ok])

def test_exige_token(conn_public, client):
    oid = _criar(conn_public, CONDOMINIO)
    try:
        r = client.post("/ocorrencias/aprovar-lote", json={"ids": [oid]})
        assert r.status_code == 401
    finally:
        _limpar(conn_public, [oid])

def test_registro_aparece_no_historico(conn_public, client):
    from lib.registrar_decisao import buscar_decisoes

    oid = _criar(conn_public, CONDOMINIO)
    try:
        r = client.post(
            "/ocorrencias/aprovar-lote",
            json={"ids": [oid]},
            headers={"Authorization": f"Bearer {_token(SINDICO)}"},
        )
        assert r.status_code == 200, r.text
        decisoes = buscar_decisoes(oid, conn_public)
        assert any(d.get("tipo") == "aprovacao_lote" for d in decisoes)
    finally:
        _limpar(conn_public, [oid])