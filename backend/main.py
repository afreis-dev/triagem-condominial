from contextlib import closing
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .lib.conexao import conectar
from .lib.salvar_ocorrencia import salvar_ocorrencia

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(?:localhost|127[.]0[.]0[.]1)(?::[0-9]+)?",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ChamadoForm(BaseModel):
    perfil: Literal["morador", "proprietario", "funcionario"]
    nome: str = ""
    apartamento: str = ""
    celular: str
    local: str = ""
    descricao: str


def buscar_condominio(identificador: str):
    with closing(conectar()) as conexao, conexao.cursor() as cursor:
        cursor.execute(
            "SELECT id, nome FROM condominios WHERE LOWER(id) = LOWER(%s)",
            (identificador,),
        )
        condominio = cursor.fetchone()
    if condominio is None:
        raise HTTPException(status_code=404, detail="Link de condomínio inválido")
    condominio_id, nome = condominio
    return {"id": condominio_id, "nome": nome}


@app.get("/api/condominios/{identificador}")
def consultar_condominio(identificador: str):
    return buscar_condominio(identificador)


@app.post("/api/condominios/{identificador}/ocorrencias")
def registrar_ocorrencia(identificador: str, formulario: ChamadoForm):
    condominio = buscar_condominio(identificador)
    dados = formulario.model_dump(exclude={"perfil"})
    return salvar_ocorrencia({
        **dados,
        "origem": formulario.perfil,
        "condominioId": condominio["id"],
    })

class AprovarLoteBody(BaseModel):
    ids: list[str]

@app.get("/ocorrencias/para-aprovacao")
def listar_para_aprovacao_api():
    conn = conectar()
    try:
        from .lib.aprovar_lote import listar_para_aprovacao
        return listar_para_aprovacao(conn)
    finally:
        conn.close()

@app.post("/ocorrencias/aprovar-lote", status_code=200)
def aprovar_lote_api(body: AprovarLoteBody):
    conn = conectar()
    try:
        from .lib.aprovar_lote import aprovar_lote
        return aprovar_lote(body.ids, conn)
    finally:
        conn.close()

@app.post("/ocorrencias/desfazer-lote", status_code=200)
def desfazer_lote_api(body: AprovarLoteBody):
    conn = conectar()
    try:
        from .lib.aprovar_lote import desfazer_lote
        return desfazer_lote(body.ids, conn)
    finally:
        conn.close()