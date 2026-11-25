from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from backend.lib.auth import (
    criar_token,
    gerar_hash,
    validar_token,
    verificar_senha,
)


@pytest.fixture(autouse=True)
def configurar_segredo(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "segredo-exclusivo-para-testes-automatizados")


def test_hash_de_senha():
    senha = "SenhaSegura@2026!"
    hash_salvo = gerar_hash(senha)

    assert hash_salvo != senha
    assert verificar_senha(senha, hash_salvo)
    assert not verificar_senha("senha-incorreta", hash_salvo)


def test_token_valido():
    token = criar_token(42)
    assert validar_token(token) == 42


def test_token_invalido():
    with pytest.raises(HTTPException) as erro:
        validar_token("token.invalido")

    assert erro.value.status_code == 401


def test_token_expirado():
    payload = {
        "sub": "42",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    token = jwt.encode(
        payload,
        "segredo-exclusivo-para-testes-automatizados",
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as erro:
        validar_token(token)

    assert erro.value.status_code == 401


def test_token_assinado_com_outro_segredo():
    token = jwt.encode(
        {"sub": "42", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "outro-segredo-de-testes-com-mais-de-32-bytes",
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as erro:
        validar_token(token)

    assert erro.value.status_code == 401
