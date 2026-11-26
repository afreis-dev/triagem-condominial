from contextlib import nullcontext

from fastapi.testclient import TestClient
import pytest

import backend.main as main
from lib.registrar_decisao import registrar_decisao


client = TestClient(main.app)

@pytest.fixture(autouse=True)
def autenticar_sindico_do_teste(sindico):
    main.app.dependency_overrides[main.sindico_autenticado] = (
        lambda: {"id": sindico, "nome": "Síndico Teste"}
    )

    try:
        yield
    finally:
        main.app.dependency_overrides.pop(
            main.sindico_autenticado, None
        )



def preparar_conexao(monkeypatch, conexao):
    monkeypatch.setattr(main, "conectar", lambda: conexao)
    monkeypatch.setattr(main, "closing", nullcontext)


def test_endpoint_retorna_historico(
    monkeypatch, conexao, criar_ocorrencia
):
    preparar_conexao(monkeypatch, conexao)
    ocorrencia_id = criar_ocorrencia()

    resultado = registrar_decisao(
        {
            "ocorrenciaId": ocorrencia_id,
            "tipo": "entrada",
            "quemDecidiu": "sistema",
            "origem": "morador",
            "prioridadeSugerida": "normal",
        },
        conexao=conexao,
    )

    assert resultado["ok"] is True

    resposta = client.get(
        f"/api/ocorrencias/{ocorrencia_id}/decisoes"
    )

    assert resposta.status_code == 200

    historico = resposta.json()

    assert len(historico) == 1
    assert historico[0]["ocorrenciaId"] == ocorrencia_id
    assert historico[0]["tipo"] == "entrada"
    assert historico[0]["prioridadeSugerida"] == "normal"


def test_endpoint_historico_vazio(
    monkeypatch, conexao, criar_ocorrencia
):
    preparar_conexao(monkeypatch, conexao)
    ocorrencia_id = criar_ocorrencia()

    resposta = client.get(
        f"/api/ocorrencias/{ocorrencia_id}/decisoes"
    )

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_endpoint_ocorrencia_inexistente(
    monkeypatch, conexao
):
    preparar_conexao(monkeypatch, conexao)

    resposta = client.get(
        "/api/ocorrencias/999999/decisoes"
    )

    assert resposta.status_code == 404


def test_endpoint_id_invalido():
    # Simula um síndico autenticado para testar
    # especificamente a validação do identificador.
    main.app.dependency_overrides[main.sindico_autenticado] = (
        lambda: {"id": 1, "nome": "Síndico Teste"}
    )

    try:
        resposta = client.get(
            "/api/ocorrencias/abc/decisoes"
        )

        assert resposta.status_code == 422
    finally:
        main.app.dependency_overrides.pop(
            main.sindico_autenticado, None
        )


def test_endpoint_sem_prefixo_api(
    monkeypatch, conexao, criar_ocorrencia
):
    preparar_conexao(monkeypatch, conexao)
    ocorrencia_id = criar_ocorrencia()

    resposta = client.get(
        f"/ocorrencias/{ocorrencia_id}/decisoes"
    )

    assert resposta.status_code == 200
    assert resposta.json() == []
