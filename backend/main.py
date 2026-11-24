from contextlib import closing
from pathlib import Path
from typing import Literal, Optional
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).parent / ".env")

from .lib.conexao import conectar
from .lib.registrar_decisao import buscar_decisoes, registrar_decisao
from .lib.salvar_ocorrencia import salvar_ocorrencia
from .lib.concluir_ocorrencia import concluir_ocorrencia
from .lib.prioridade import ordenar_ocorrencias

app = FastAPI(title="Triagem Condominial")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(?:localhost|127[.]0[.]0[.]1)(?::[0-9]+)?",
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)

def _validar_uuid(id: str):
    try:
        return UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="id inválido")

def _buscar_condominio_por_slug(identificador: str, conn):
    cur = conn.cursor()
    cur.execute("SELECT id, nome FROM condominios WHERE LOWER(id) = LOWER(%s)", (identificador,))
    row = cur.fetchone()
    if row:
        cur.close()
        return row
    cur.execute("SELECT id, nome FROM condominios WHERE LOWER(nome) = LOWER(%s)", (identificador,))
    row = cur.fetchone()
    cur.close()
    return row

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

# ---------- H04 ----------
class ColarBody(BaseModel):
    condominioId: str
    descricao: str = Field(max_length=2000)
    texto_colado: Optional[str] = None
    nome: Optional[str] = None
    celular: Optional[str] = None
    apartamento: Optional[str] = None
    origem: Optional[str] = "whatsapp_sindico"
    local: Optional[str] = None

@app.post("/ocorrencias/colar", status_code=201)
def colar(body: ColarBody):
    dados = {
        "condominioId": body.condominioId,
        "descricao": body.texto_colado or body.descricao,
        "nome": body.nome,
        "celular": body.celular,
        "origem": body.origem or "whatsapp_sindico",
        "apartamento": body.apartamento,
        "local": body.local,
    }
    conn = conectar()
    try:
        resultado = salvar_ocorrencia(dados, conn)
        if isinstance(resultado, dict) and resultado.get("erros"):
            raise HTTPException(status_code=400, detail=resultado["erros"])
        return resultado
    finally:
        conn.close()

# ---------- H03 ----------
@app.get("/ocorrencias")
def listar_ocorrencias():
    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, condominio_id, texto_original, prioridade, categoria,
                   responsavel_sugerido AS responsavel, status, created_at
            FROM ocorrencias ORDER BY created_at ASC
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

@app.get("/ocorrencias/{id}")
def buscar_ocorrencia(id: str):
    oid = _validar_uuid(id)
    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, condominio_id, texto_original, prioridade, categoria,
                   responsavel_sugerido, status, created_at
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

# ---------- H14 ----------
@app.get("/ocorrencias/{id}/decisoes")
def listar_decisoes(id: str):
    oid = _validar_uuid(id)
    conn = conectar()
    try:
        return buscar_decisoes(oid, conn)
    finally:
        conn.close()

# ---------- H13 ----------
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

# ---------- H10 ----------
class PrioridadeBody(BaseModel):
    prioridade: str
    motivo: Optional[str] = None

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

# ---------- H01 ----------
class ChamadoForm(BaseModel):
    perfil: Literal["morador", "proprietario", "funcionario"]
    nome: str = ""
    apartamento: str = ""
    celular: str
    local: str = ""
    descricao: str

class OcorrenciaFormBody(BaseModel):
    perfil: str
    nome: Optional[str] = None
    apartamento: Optional[str] = None
    celular: Optional[str] = None
    local: Optional[str] = None
    descricao: str

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

# ---------- H15 ----------
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