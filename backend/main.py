from contextlib import closing

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.lib.auth import criar_token, verificar_senha
from backend.lib.auth_deps import sindico_autenticado
from backend.rotas.fila import router as fila_router
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

class DadosLogin(BaseModel):
    email: str
    senha: str


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

app.include_router(fila_router)
