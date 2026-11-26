import os
import sys
import uuid
import psycopg2
import pytest
from fastapi.testclient import TestClient

from main import app
from lib.auth import criar_token, gerar_hash
from lib import conexao as conexao_mod

def _patch_conectar(nova_fn):
    """Patcha conectar em todos os módulos que já importaram por valor."""
    for mod in list(sys.modules.values()):
        try:
            if mod is not None and hasattr(mod, "conectar"):
                mod.conectar = nova_fn
        except Exception:
            pass

@pytest.fixture
def ambiente():
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    schema = f"teste_{uuid.uuid4().hex[:8]}"

    # 1. Cria schema isolado copiando a estrutura do public
    admin = psycopg2.connect(url)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(f'CREATE SCHEMA "{schema}"')
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            AND table_name NOT IN ('alembic_version')
        """)
        for (t,) in cur.fetchall():
            cur.execute(f'CREATE TABLE "{schema}"."{t}" (LIKE public."{t}" INCLUDING ALL)')
    admin.close()

    # 2. Conexão de teste com search_path fixo no schema
    conectar_original = conexao_mod.conectar

    def conectar_teste():
        return psycopg2.connect(url, options=f"-c search_path={schema},public")

    _patch_conectar(conectar_teste)
    conn = conectar_teste()

    try:
        sufixo = uuid.uuid4().hex[:8]
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sindicos (nome, email, senha_hash) VALUES (%s, %s, %s) RETURNING id",
                (f"Síndico Teste {sufixo}", f"sindico-{sufixo}@teste.com", gerar_hash("1234")),
            )
            sindico_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO condominios (identificador, nome, bairro, sindico_id) VALUES (%s, %s, %s, %s) RETURNING id",
                (f"cond-{sufixo}", f"Cond {sufixo}", "Centro", sindico_id),
            )
            condominio_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO sindicos (nome, email, senha_hash) VALUES (%s, %s, %s) RETURNING id",
                (f"Outro {sufixo}", f"outro-{sufixo}@teste.com", gerar_hash("1234")),
            )
            outro_sindico_id = cur.fetchone()[0]
        conn.commit()

        yield {
            "conn": conn, "schema": schema, "url": url,
            "sindico": sindico_id, "condominio": condominio_id,
            "outro_sindico": outro_sindico_id,
        }
    finally:
        _patch_conectar(conectar_original)
        conn.close()
        admin = psycopg2.connect(url)
        admin.autocommit = True
        with admin.cursor() as cur:
            cur.execute(f'DROP SCHEMA "{schema}" CASCADE')
        admin.close()

@pytest.fixture
def client():
    return TestClient(app)

def _token(sindico_id):
    return criar_token(sindico_id)

def _criar_ocorrencia(amb, prioridade="normal", travada=False, status="nova"):
    protocolo = f"TEST-{uuid.uuid4().hex[:8].upper()}"
    with amb["conn"].cursor() as cur:
        cur.execute(
            """
            INSERT INTO ocorrencias
                (condominio_id, protocolo, origem, descricao, prioridade, travada, status)
            VALUES (%s, %s, 'morador', %s, %s, %s, %s)
            RETURNING id
            """,
            (amb["condominio"], protocolo, "teste lote", prioridade, travada, status),
        )
        oid = cur.fetchone()[0]
    amb["conn"].commit()
    return oid

def _acao_individual(amb, oid):
    from lib.registrar_decisao import registrar_decisao
    r = registrar_decisao(
        {"tipo": "acao", "ocorrenciaId": oid, "quemDecidiu": "sindico",
         "acao": "delegar", "responsavel": "zelador", "nota": "individual"},
        conexao=amb["conn"],
    )
    assert r.get("ok"), r
    with amb["conn"].cursor() as cur:
        cur.execute("UPDATE ocorrencias SET status='em_andamento' WHERE id=%s", (oid,))
    amb["conn"].commit()

def test_aprova_varias_de_uma_vez(ambiente, client):
    ids = [_criar_ocorrencia(ambiente) for _ in range(3)]
    r = client.post(
        "/ocorrencias/aprovar-lote", json={"ids": ids},
        headers={"Authorization": f"Bearer {_token(ambiente['sindico'])}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["aprovadas"] == 3

def test_recusa_urgente_e_travada(ambiente, client):
    id_urg = _criar_ocorrencia(ambiente, prioridade="urgente")
    id_trav = _criar_ocorrencia(ambiente, travada=True)
    r = client.post(
        "/ocorrencias/aprovar-lote", json={"ids": [id_urg, id_trav]},
        headers={"Authorization": f"Bearer {_token(ambiente['sindico'])}"},
    )
    assert r.status_code in (409, 422), r.text

def test_recusa_outro_sindico(ambiente, client):
    oid = _criar_ocorrencia(ambiente)
    r = client.post(
        "/ocorrencias/aprovar-lote", json={"ids": [oid]},
        headers={"Authorization": f"Bearer {_token(ambiente['outro_sindico'])}"},
    )
    assert r.status_code in (403, 409, 422), r.text

def test_nao_grava_nada_se_um_id_invalido(ambiente, client):
    id_ok = _criar_ocorrencia(ambiente)
    r = client.post(
        "/ocorrencias/aprovar-lote", json={"ids": [id_ok, 999999]},
        headers={"Authorization": f"Bearer {_token(ambiente['sindico'])}"},
    )
    assert r.status_code in (404, 409, 422), r.text
    with ambiente["conn"].cursor() as cur:
        cur.execute("SELECT status FROM ocorrencias WHERE id = %s", (id_ok,))
        assert cur.fetchone()[0] == "nova"

def test_exige_token(ambiente, client):
    oid = _criar_ocorrencia(ambiente)
    r = client.post("/ocorrencias/aprovar-lote", json={"ids": [oid]})
    assert r.status_code == 401

def test_registro_aparece_no_historico(ambiente, client):
    from lib.registrar_decisao import buscar_decisoes
    oid = _criar_ocorrencia(ambiente)
    r = client.post(
        "/ocorrencias/aprovar-lote", json={"ids": [oid]},
        headers={"Authorization": f"Bearer {_token(ambiente['sindico'])}"},
    )
    assert r.status_code == 200, r.text
    decisoes = buscar_decisoes(oid, ambiente["conn"])
    assert any(d.get("tipo") == "aprovacao_lote" for d in decisoes)

def test_desfazer_lote_valido(ambiente, client):
    from lib.registrar_decisao import buscar_decisoes
    ids = [_criar_ocorrencia(ambiente) for _ in range(2)]
    token = {"Authorization": f"Bearer {_token(ambiente['sindico'])}"}
    assert client.post("/ocorrencias/aprovar-lote", json={"ids": ids}, headers=token).status_code == 200
    r = client.post("/ocorrencias/desfazer-lote", json={"ids": ids}, headers=token)
    assert r.status_code == 200, r.text
    assert r.json()["desfeitos"] == ids
    for oid in ids:
        decisoes = buscar_decisoes(oid, ambiente["conn"])
        assert decisoes[-1]["tipo"] == "desfazer_aprovacao_lote"

def test_desfazer_rejeita_acao_individual(ambiente, client):
    oid = _criar_ocorrencia(ambiente)
    _acao_individual(ambiente, oid)
    r = client.post(
        "/ocorrencias/desfazer-lote", json={"ids": [oid]},
        headers={"Authorization": f"Bearer {_token(ambiente['sindico'])}"},
    )
    assert r.status_code == 409, r.text
    with ambiente["conn"].cursor() as cur:
        cur.execute("SELECT status FROM ocorrencias WHERE id = %s", (oid,))
        assert cur.fetchone()[0] == "em_andamento"

def test_preserva_prioridade_alta_e_baixa_no_historico(ambiente, client):
    from lib.registrar_decisao import buscar_decisoes
    id_alta = _criar_ocorrencia(ambiente, prioridade="alta")
    id_baixa = _criar_ocorrencia(ambiente, prioridade="baixa")
    token = {"Authorization": f"Bearer {_token(ambiente['sindico'])}"}
    r = client.post(
        "/ocorrencias/aprovar-lote", json={"ids": [id_alta, id_baixa]}, headers=token,
    )
    assert r.status_code == 200, r.text
    assert buscar_decisoes(id_alta, ambiente["conn"])[-1]["prioridadeFinal"] == "alta"
    assert buscar_decisoes(id_baixa, ambiente["conn"])[-1]["prioridadeFinal"] == "baixa"
    r2 = client.post(
        "/ocorrencias/desfazer-lote", json={"ids": [id_alta, id_baixa]}, headers=token,
    )
    assert r2.status_code == 200, r2.text
    assert buscar_decisoes(id_alta, ambiente["conn"])[-1]["prioridadeFinal"] == "alta"
    assert buscar_decisoes(id_baixa, ambiente["conn"])[-1]["prioridadeFinal"] == "baixa"