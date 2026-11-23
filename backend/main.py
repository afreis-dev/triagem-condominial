from contextlib import closing

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from backend.config import RAIZ
from backend.lib.auth import criar_token, validar_token, verificar_senha
from backend.lib.conexao import conectar

app = FastAPI(title="Triagem Condominial")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

seguranca = HTTPBearer()


class DadosLogin(BaseModel):
    email: str
    senha: str


def sindico_autenticado(
    credenciais: HTTPAuthorizationCredentials = Depends(seguranca),
):
    sindico_id = validar_token(credenciais.credentials)

    with closing(conectar()) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT id, nome, email FROM sindicos WHERE id = %s",
                (sindico_id,),
            )
            sindico = cursor.fetchone()

    if sindico is None:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    return {
        "id": sindico[0],
        "nome": sindico[1],
        "email": sindico[2],
    }


@app.post("/auth/login")
def login(dados: DadosLogin):
    with closing(conectar()) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, senha_hash
                FROM sindicos
                WHERE LOWER(email) = LOWER(%s)
                """,
                (dados.email.strip(),),
            )
            resultado = cursor.fetchone()

    if not resultado or not resultado[1]:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not verificar_senha(dados.senha, resultado[1]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    return {
        "access_token": criar_token(resultado[0]),
        "token_type": "bearer",
    }


@app.get("/auth/me")
def consultar_perfil(sindico=Depends(sindico_autenticado)):
    return sindico
