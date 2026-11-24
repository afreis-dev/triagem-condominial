import psycopg2
import pytest
from fastapi import FastAPI

try:
    from fastapi.testclient import TestClient
except RuntimeError:
    pytest.skip("instale o httpx2 para testar a rota", allow_module_level=True)

import rotas.fila as modulo  # noqa: E402
from lib.listar_fila import listar_fila  # noqa: E402

MENSAGEM_BANCO = "Não foi possível buscar a fila agora. Tente de novo."


@pytest.fixture
def cliente():
    app = FastAPI()
    app.include_router(modulo.router)
    return TestClient(app)


def inserir(conexao, condominio_id, descricao, prioridade):
    """Insere uma ocorrência nova com a prioridade dada e devolve o id."""
    with conexao.cursor() as cur:
        cur.execute("SELECT nextval(pg_get_serial_sequence('ocorrencias', 'id'))")
        ocorrencia_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO ocorrencias (id, protocolo, condominio_id, origem, descricao, status, prioridade) "
            "VALUES (%s, %s, %s, 'morador', %s, 'nova', %s)",
            (ocorrencia_id, f"TS-{ocorrencia_id:06d}", condominio_id, descricao, prioridade),
        )
    return ocorrencia_id


def test_devolve_o_que_listar_fila_devolve(cliente, monkeypatch):
    resposta_da_funcao = {"ok": True, "ocorrencias": [{"id": 1, "protocolo": "TS-000001"}]}
    monkeypatch.setattr(modulo, "listar_fila", lambda: resposta_da_funcao)
    resposta = cliente.get("/ocorrencias")
    assert resposta.status_code == 200
    assert resposta.json() == resposta_da_funcao


def test_cada_chamada_busca_de_novo(cliente, monkeypatch):
    chamadas = []

    def falsa():
        chamadas.append(1)
        return {"ok": True, "ocorrencias": [{"id": n} for n in range(len(chamadas))]}

    monkeypatch.setattr(modulo, "listar_fila", falsa)
    assert len(cliente.get("/ocorrencias").json()["ocorrencias"]) == 1
    assert len(cliente.get("/ocorrencias").json()["ocorrencias"]) == 2
    assert len(chamadas) == 2


def test_so_aceita_get(cliente):
    assert cliente.post("/ocorrencias").status_code == 405
    assert cliente.delete("/ocorrencias").status_code == 405


@pytest.mark.parametrize(
    "erro",
    [
        psycopg2.OperationalError("connection to server at db.exemplo.com failed: password=segredo"),
        RuntimeError("DATABASE_URL não definida"),
    ],
)
def test_banco_fora_do_ar_devolve_503_sem_expor_o_erro(cliente, monkeypatch, erro):
    def falha():
        raise erro

    monkeypatch.setattr(modulo, "listar_fila", falha)
    resposta = cliente.get("/ocorrencias")
    assert resposta.status_code == 503
    assert resposta.json() == {"ok": False, "erros": {"banco": MENSAGEM_BANCO}}
    assert "segredo" not in resposta.text
    assert "db.exemplo.com" not in resposta.text


def test_outro_erro_nao_e_escondido(cliente, monkeypatch):
    def falha():
        raise ValueError("bug")

    monkeypatch.setattr(modulo, "listar_fila", falha)
    with pytest.raises(ValueError):
        cliente.get("/ocorrencias")


def test_nova_urgente_aparece_ao_buscar_de_novo(cliente, conexao, condominio, monkeypatch):
    monkeypatch.setattr(modulo, "listar_fila", lambda: listar_fila(conexao=conexao))
    assert cliente.get("/ocorrencias").json() == {"ok": True, "ocorrencias": []}

    inserir(conexao, condominio, "Lâmpada do hall queimada", "normal")
    antes = cliente.get("/ocorrencias").json()["ocorrencias"]
    assert [o["descricao"] for o in antes] == ["Lâmpada do hall queimada"]

    urgente_id = inserir(conexao, condominio, "Falta de água no bloco A", "urgente")
    depois = cliente.get("/ocorrencias").json()["ocorrencias"]
    assert len(depois) == 2
    assert [o for o in depois if o["id"] == urgente_id][0]["prioridade"] == "urgente"
