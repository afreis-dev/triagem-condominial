import os
import uuid

import psycopg2
import pytest
from fastapi.testclient import TestClient

import main
from lib import auth_deps
from lib.auth import criar_token
from lib.registrar_decisao import buscar_decisoes, registrar_decisao


@pytest.fixture
def ambiente(conexao, sindico, condominio):
    with conexao.cursor() as cur:
        cur.execute(
            "INSERT INTO sindicos (nome, email) VALUES (%s, %s) RETURNING id",
            ("Outro s?ndico", "outro@teste.com"),
        )
        outro_sindico = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO condominios (identificador, nome, sindico_id) "
            "VALUES (%s, %s, %s) RETURNING id",
            ("outro", "Outro condom?nio", outro_sindico),
        )
        outro_condominio = cur.fetchone()[0]
    conexao.commit()
    return {
        "conn": conexao,
        "sindico": sindico,
        "condominio": condominio,
        "outro_sindico": outro_sindico,
        "outro_condominio": outro_condominio,
    }


@pytest.fixture
def client(conexao, monkeypatch):
    with conexao.cursor() as cur:
        cur.execute("SELECT current_schema()")
        schema = cur.fetchone()[0]
    url = os.environ["TEST_DATABASE_URL"]

    def conectar_teste():
        return psycopg2.connect(url, options=f"-c search_path={schema}")

    monkeypatch.setenv("JWT_SECRET", "segredo-exclusivo-de-testes-da-h15")
    monkeypatch.setattr(main, "conectar", conectar_teste)
    monkeypatch.setattr(auth_deps, "conectar", conectar_teste)
    with TestClient(main.app) as cliente:
        yield cliente


def _token(sindico_id):
    return criar_token(sindico_id)

def _criar_ocorrencia(amb, prioridade="normal", travada=False, status="nova",
                      responsavel=None, motivo=None, condominio_id=None):
    protocolo = f"TEST-{uuid.uuid4().hex[:8].upper()}"
    with amb["conn"].cursor() as cur:
        cur.execute(
            """
            INSERT INTO ocorrencias
                (condominio_id, protocolo, origem, descricao, prioridade, travada, status,
                 responsavel_sugerido, motivo)
            VALUES (%s, %s, 'morador', %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (condominio_id or amb["condominio"], protocolo, "teste lote", prioridade,
             travada, status, responsavel, motivo),
        )
        oid = cur.fetchone()[0]
    amb["conn"].commit()
    return oid

def _acao_individual(amb, oid):
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

@pytest.mark.parametrize("prioridade, travada", [("urgente", False), ("normal", True)])
def test_recusa_urgente_ou_travada(ambiente, client, prioridade, travada):
    oid = _criar_ocorrencia(ambiente, prioridade=prioridade, travada=travada)
    r = client.post(
        "/ocorrencias/aprovar-lote", json={"ids": [oid]},
        headers={"Authorization": f"Bearer {_token(ambiente['sindico'])}"},
    )
    assert r.status_code == 409, r.text


def test_recusa_outro_sindico(ambiente, client):
    oid = _criar_ocorrencia(ambiente)
    r = client.post(
        "/ocorrencias/aprovar-lote", json={"ids": [oid]},
        headers={"Authorization": f"Bearer {_token(ambiente['outro_sindico'])}"},
    )
    assert r.status_code == 409, r.text

def test_nao_grava_nada_se_um_id_invalido(ambiente, client):
    id_ok = _criar_ocorrencia(ambiente)
    r = client.post(
        "/ocorrencias/aprovar-lote", json={"ids": [id_ok, 999999]},
        headers={"Authorization": f"Bearer {_token(ambiente['sindico'])}"},
    )
    assert r.status_code == 409, r.text
    with ambiente["conn"].cursor() as cur:
        cur.execute("SELECT status FROM ocorrencias WHERE id = %s", (id_ok,))
        assert cur.fetchone()[0] == "nova"
    assert buscar_decisoes(id_ok, ambiente["conn"]) == []

def test_exige_token(ambiente, client):
    oid = _criar_ocorrencia(ambiente)
    r = client.post("/ocorrencias/aprovar-lote", json={"ids": [oid]})
    assert r.status_code == 401

def test_registro_aparece_no_historico(ambiente, client):
    oid = _criar_ocorrencia(ambiente)
    r = client.post(
        "/ocorrencias/aprovar-lote", json={"ids": [oid]},
        headers={"Authorization": f"Bearer {_token(ambiente['sindico'])}"},
    )
    assert r.status_code == 200, r.text
    decisoes = buscar_decisoes(oid, ambiente["conn"])
    assert any(d.get("tipo") == "aprovacao_lote" for d in decisoes)

def test_desfazer_lote_valido(ambiente, client):
    ids = [_criar_ocorrencia(ambiente) for _ in range(2)]
    token = {"Authorization": f"Bearer {_token(ambiente['sindico'])}"}
    assert client.post("/ocorrencias/aprovar-lote", json={"ids": ids}, headers=token).status_code == 200
    r = client.post("/ocorrencias/desfazer-lote", json={"ids": ids}, headers=token)
    assert r.status_code == 200, r.text
    assert sorted(r.json()["desfeitos"]) == sorted(ids)
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

@pytest.mark.parametrize("ids", [[], [0], [True], ["abc"], [1, 1]])
@pytest.mark.parametrize("rota", ["aprovar-lote", "desfazer-lote"])
def test_rejeita_ids_invalidos(ambiente, client, rota, ids):
    r = client.post(
        f"/ocorrencias/{rota}", json={"ids": ids},
        headers={"Authorization": f"Bearer {_token(ambiente['sindico'])}"},
    )
    assert r.status_code == 422, r.text


def test_lista_apenas_elegiveis_com_responsavel_e_motivo(ambiente, client):
    oid = _criar_ocorrencia(
        ambiente, prioridade="alta", responsavel="zelador", motivo="Vazamento",
    )
    _criar_ocorrencia(ambiente, prioridade="urgente")
    _criar_ocorrencia(ambiente, travada=True)
    _criar_ocorrencia(ambiente, status="em_andamento")
    _criar_ocorrencia(ambiente, condominio_id=ambiente["outro_condominio"])

    r = client.get(
        "/ocorrencias/para-aprovacao",
        headers={"Authorization": f"Bearer {_token(ambiente['sindico'])}"},
    )

    assert r.status_code == 200, r.text
    ocorrencias = r.json()["ocorrencias"]
    assert [ocorrencia["id"] for ocorrencia in ocorrencias] == [oid]
    assert ocorrencias[0]["responsavel_sugerido"] == "zelador"
    assert ocorrencias[0]["motivo"] == "Vazamento"
