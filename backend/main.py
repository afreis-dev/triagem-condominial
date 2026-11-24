from dotenv import load_dotenv
load_dotenv()

from contextlib import closing
from uuid import UUID
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Literal, Optional

from lib.conexao import conectar
from lib.registrar_decisao import buscar_decisoes, registrar_decisao
from lib.salvar_ocorrencia import salvar_ocorrencia
from lib.concluir_ocorrencia import concluir_ocorrencia
from lib.prioridade import ordenar_ocorrencias

app = FastAPI(title="Triagem Condominial")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ColarBody(BaseModel):
    condominioId: int
    descricao: str = Field(max_length=2000)
    texto_colado: Optional[str] = None
    nome: Optional[str] = None
    celular: Optional[str] = None
    apartamento: Optional[str] = None
    origem: Optional[str] = "whatsapp_sindico"
    local: Optional[str] = None

class PrioridadeBody(BaseModel):
    prioridade: str
    motivo: Optional[str] = None

def _validar_uuid(id: str):
    try:
        return UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="id inválido")

# Endpoint - H04
@app.post("/ocorrencias/colar", status_code=201)
def colar(body: ColarBody):
    dados = {
        "condominio_id": body.condominioId,
        "descricao": body.texto_colado or body.descricao,
        "texto_colado": body.texto_colado,
        "nome": body.nome,
        "celular": body.celular,
        "origem": body.origem or "whatsApp_sindico",
    }
    conn = conectar()
    try:
        resultado = salvar_ocorrencia(dados, conn)
        # Se a função devolver {"erros": [...]} vira 400
        if isinstance(resultado, dict) and resultado.get("erros"):
            raise HTTPException(status_code=400, detail=resultado["erros"])
        return resultado
    finally:
        conn.close()

# Endpoint - H03
@app.get("/ocorrencias")
def listar_ocorrencias():
    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, condominio_id, descricao, prioridade, categoria,
                   responsavel_sugerido AS responsavel, status, criado_em
            FROM ocorrencias ORDER BY criado_em ASC
        """)
        linhas = cur.fetchall()
        cur.close()
        lista = [
            {
                "id": str(r[0]), "condominio_id": str(r[1]),
                "texto_colado": r[2], "descricao": r[2],
                "prioridade": r[3], "categoria": r[4],
                "responsavel": r[5], "status": r[6],
                "criado_em": r[7].isoformat() if r[7] else None,
            } for r in linhas
        ]
        return ordenar_ocorrencias(lista)
    finally:
        conn.close()

# Detalhe
@app.get("/ocorrencias/{id}")
def buscar_ocorrencia(id: str):
    oid = _validar_uuid(id)
    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, condominio_id, descricao, prioridade, categoria,
                   responsavel, status, criado_em
            FROM ocorrencias WHERE id = %s
        """, (str(oid),))
        r = cur.fetchone()
        cur.close()
        if not r:
            raise HTTPException(status_code=404, detail="ocorrência não encontrada")
        return {
            "id": str(r[0]), "condominio_id": str(r[1]),
            "texto_colado": r[2], "descricao": r[2],
            "prioridade": r[3], "categoria": r[4],
            "responsavel": r[5], "status": r[6],
            "criado_em": r[7].isoformat() if r[7] else None,
        }
    finally:
        conn.close()

#Endpoint - H14
@app.get("/ocorrencias/{id}/decisoes")
def listar_decisoes(id: str):
    oid = _validar_uuid(id)
    conn = conectar()
    try:
        return buscar_decisoes(oid, conn)
    finally:
        conn.close()

#Endpoint - H13
@app.patch("/ocorrencias/{id}/concluir")
def concluir(id: str):
    oid = _validar_uuid(id)
    conn = conectar()
    try:
        resultado = concluir_ocorrencia(str(oid), conn)
        if isinstance(resultado, dict) and resultado.get("erros"):
            raise HTTPException(status_code=400, detail=resultado["erros"])
        return resultado
    finally:
        conn.close()

# H10
@app.patch("/ocorrencias/{id}/prioridade")
def alterar_prioridade(id: str, body: PrioridadeBody):
    oid = _validar_uuid(id)
    if not body.motivo or not body.motivo.strip():
        raise HTTPException(status_code=400, detail="motivo é obrigatório")
    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("SELECT prioridade FROM ocorrencias WHERE id = %s", (str(oid),))
        atual = cur.fetchone()
        if not atual:
            cur.close()
            raise HTTPException(status_code=404, detail="ocorrência não encontrada")
        prioridade_atual = atual[0]
        cur.execute(
            "UPDATE ocorrencias SET prioridade = %s WHERE id = %s RETURNING id, prioridade",
            (body.prioridade, str(oid)),
        )
        r = cur.fetchone()
        conn.commit()
        cur.close()
        # Registra no histórico
        try:
            registrar_decisao({
                "ocorrencia_id": str(oid),
                "acao": "prioridade_alterada",
                "nota": f"Prioridade: {prioridade_atual} -> {body.prioridade}. Motivo: {body.motivo}",
            }, conn)
        except Exception as e:
            print("Aviso registrar_decisao:", e)
        return {"id": str(r[0]), "prioridade": r[1]}
    finally:
        conn.close()


class OcorrenciaFormBody(BaseModel):
    perfil: Literal["morador", "proprietario", "funcionario"]
    nome: Optional[str] = None
    apartamento: Optional[str] = None
    celular: Optional[str] = None
    local: Optional[str] = None
    descricao: str


def _buscar_condominio_por_slug(identificador: str, conexao):
    with conexao.cursor() as cursor:
        cursor.execute(
            "SELECT id, nome FROM condominios WHERE identificador = %s",
            (identificador,),
        )
        condominio = cursor.fetchone()
    if condominio is None:
        raise HTTPException(status_code=404, detail="Condomínio não encontrado")
    return condominio


@app.get("/api/condominios/{identificador}")
def get_condominio_api(identificador: str):
    with closing(conectar()) as conexao:
        condominio_id, nome = _buscar_condominio_por_slug(identificador, conexao)
    return {"id": condominio_id, "nome": nome}


@app.post("/api/condominios/{identificador}/ocorrencias", status_code=201)
def criar_ocorrencia_form(identificador: str, body: OcorrenciaFormBody):
    with closing(conectar()) as conexao, conexao:
        condominio_id, _ = _buscar_condominio_por_slug(identificador, conexao)
        if body.perfil != "funcionario" and not (body.apartamento or "").strip():
            return JSONResponse(content={"ok": False, "erros": {"apartamento": "Informe o apartamento"}})
        dados = body.model_dump(exclude={"perfil"})
        resultado = salvar_ocorrencia(
            {**dados, "condominioId": condominio_id, "origem": body.perfil},
            conexao=conexao,
        )
    if not resultado["ok"]:
        return JSONResponse(content=resultado)
    return resultado
