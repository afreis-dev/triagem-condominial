import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()
ALGORITMO = "HS256"


def gerar_hash(senha: str) -> str:
    return password_hash.hash(senha)


def verificar_senha(senha: str, hash_salvo: str) -> bool:
    try:
        return password_hash.verify(senha, hash_salvo)
    except Exception:
        return False


def criar_token(sindico_id: int) -> str:
    segredo = os.getenv("JWT_SECRET")
    if not segredo:
        raise RuntimeError("JWT_SECRET não configurado")

    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(sindico_id),
        "iat": agora,
        "exp": agora + timedelta(hours=8),
    }
    return jwt.encode(payload, segredo, algorithm=ALGORITMO)


def validar_token(token: str) -> int:
    segredo = os.getenv("JWT_SECRET")
    if not segredo:
        raise RuntimeError("JWT_SECRET não configurado")

    try:
        payload = jwt.decode(token, segredo, algorithms=[ALGORITMO])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
