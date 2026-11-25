from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.lib.auth import gerar_hash
from backend.main import app

EMAIL = "sindico@teste.com"
SENHA = "SenhaTeste@2026!"


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET",
        "segredo-exclusivo-para-testes-de-endpoints-2026",
    )

    import backend.main as modulo

    conexao = MagicMock()
    cursor = conexao.cursor.return_value.__enter__.return_value

    cursor.fetchone.return_value = (1, gerar_hash(SENHA))

    monkeypatch.setattr(modulo, "conectar", lambda: conexao)

    with TestClient(app) as cliente:
        yield cliente, cursor


def test_login_com_credenciais_validas(cliente):
    api, cursor = cliente

    resposta = api.post(
        "/auth/login",
        json={"email": EMAIL, "senha": SENHA},
    )

    assert resposta.status_code == 200
    assert resposta.json()["token_type"] == "bearer"
    assert resposta.json()["access_token"]


def test_login_com_senha_incorreta(cliente):
    api, cursor = cliente

    resposta = api.post(
        "/auth/login",
        json={"email": EMAIL, "senha": "senha-errada"},
    )

    assert resposta.status_code == 401


def test_login_com_usuario_inexistente(cliente):
    api, cursor = cliente
    cursor.fetchone.return_value = None

    resposta = api.post(
        "/auth/login",
        json={"email": "inexistente@teste.com", "senha": SENHA},
    )

    assert resposta.status_code == 401


def test_perfil_sem_token(cliente):
    api, cursor = cliente

    resposta = api.get("/auth/me")

    assert resposta.status_code == 401


def test_lista_condominios_exige_login(cliente):
    api, _ = cliente
    assert api.get("/api/condominios").status_code == 401


def test_lista_condominios_consulta_a_carteira_do_sindico(cliente, monkeypatch):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps

    api, cursor = cliente
    conexao_perfil = MagicMock()
    conexao_perfil.cursor.return_value.__enter__.return_value.fetchone.return_value = (
        7, "Síndico Teste", EMAIL,
    )
    monkeypatch.setattr(auth_deps, "conectar", lambda: conexao_perfil)
    cursor.fetchall.return_value = [(3, "Vista Verde")]

    resposta = api.get(
        "/api/condominios",
        headers={"Authorization": f"Bearer {criar_token(7)}"},
    )
    assert resposta.status_code == 200
    assert resposta.json() == [{"id": 3, "nome": "Vista Verde"}]
    consulta, parametros = cursor.execute.call_args.args
    assert "WHERE sindico_id = %s" in consulta
    assert parametros == (7,)


def test_perfil_com_token_invalido(cliente):
    api, cursor = cliente

    resposta = api.get(
        "/auth/me",
        headers={"Authorization": "Bearer token-invalido"},
    )

    assert resposta.status_code == 401


def test_perfil_com_token_valido(cliente, monkeypatch):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps

    api, _ = cliente

    conexao = MagicMock()
    cursor = conexao.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (
        1,
        "Síndico Teste",
        EMAIL,
    )

    monkeypatch.setattr(auth_deps, "conectar", lambda: conexao)

    token = criar_token(1)

    resposta = api.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert resposta.json() == {
        "id": 1,
        "nome": "Síndico Teste",
        "email": EMAIL,
    }


def test_perfil_com_token_expirado(cliente):
    from datetime import datetime, timedelta, timezone

    import jwt

    api, _ = cliente

    token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        "segredo-exclusivo-para-testes-de-endpoints-2026",
        algorithm="HS256",
    )

    resposta = api.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 401
