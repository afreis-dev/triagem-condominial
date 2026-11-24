from dotenv import load_dotenv
load_dotenv()

from contextlib import closing
from datetime import date
from uuid import UUID
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Literal, Optional

from lib.conexao import conectar
from lib.listar_fila import marca_acao
from lib.registrar_decisao import buscar_decisoes, registrar_decisao
from lib.salvar_ocorrencia import salvar_ocorrencia
from lib.concluir_ocorrencia import concluir_ocorrencia
from rotas.fila import rota_listar_fila

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
@app.get("/api/ocorrencias")
@app.get("/ocorrencias")
def listar_ocorrencias():
    return rota_listar_fila()


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
@app.patch("/api/ocorrencias/{id}/concluir")
@app.patch("/ocorrencias/{id}/concluir")
def concluir(id: int):
    resultado = concluir_ocorrencia(id)
    if resultado["ok"]:
        return resultado
    codigo = 404 if "ocorrenciaId" in resultado["erros"] else 409
    return JSONResponse(content=resultado, status_code=codigo)


class DecisaoAcao(BaseModel):
    acao: Literal["delegar", "agendar", "eu_mesmo"]
    responsavel: str | None = None
    dataAgendada: date | None = None
    nota: str = Field(default="", max_length=500)


def _consultar_ocorrencia_acao(cursor, id: int, *, bloquear: bool = False):
    consulta = """
        SELECT condominio_id, responsavel_sugerido, status
        FROM ocorrencias WHERE id = %s
    """
    if bloquear:
        consulta += " FOR UPDATE"
    cursor.execute(consulta, (id,))
    ocorrencia = cursor.fetchone()
    if ocorrencia is None:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
    return ocorrencia


def _papeis_delegaveis(cursor, condominio_id):
    cursor.execute(
        "SELECT papel FROM responsaveis WHERE condominio_id = %s ORDER BY papel",
        (condominio_id,),
    )
    return [papel for (papel,) in cursor.fetchall()]


@app.get("/ocorrencias/{id}/responsaveis")
def listar_responsaveis_ocorrencia(id: int):
    with closing(conectar()) as conn, conn.cursor() as cursor:
        condominio_id, sugerido, _ = _consultar_ocorrencia_acao(cursor, id)
        papeis = _papeis_delegaveis(cursor, condominio_id)
    return {
        "responsaveis": papeis,
        "responsavelSugerido": sugerido if sugerido in papeis else None,
    }


@app.post("/ocorrencias/{id}/acoes", status_code=201)
def confirmar_acao(id: int, decisao: DecisaoAcao):
    if decisao.acao == "agendar" and decisao.dataAgendada is None:
        raise HTTPException(status_code=422, detail="Escolha a data do agendamento")

    with closing(conectar()) as conn, conn, conn.cursor() as cursor:
        condominio_id, _, status = _consultar_ocorrencia_acao(cursor, id, bloquear=True)
        if status != "nova":
            raise HTTPException(status_code=409, detail="A ocorrência precisa estar em Nova")
        if decisao.acao == "delegar" and decisao.responsavel not in _papeis_delegaveis(cursor, condominio_id):
            raise HTTPException(status_code=422, detail="Escolha um responsável do condomínio")

        resultado = registrar_decisao(
            {"tipo": "acao", "ocorrenciaId": id, "quemDecidiu": "sindico", **decisao.model_dump(mode="json")},
            conexao=conn,
        )
        if not resultado["ok"]:
            raise HTTPException(status_code=422, detail=resultado["erros"])
        cursor.execute("UPDATE ocorrencias SET status = 'em_andamento' WHERE id = %s", (id,))

    return {"id": id, "status": "em_andamento",
            "marcaAcao": marca_acao(decisao.acao, decisao.responsavel, decisao.dataAgendada)}


# H10
@app.patch("/ocorrencias/{id}/prioridade")
def alterar_prioridade(id: int, body: PrioridadeBody):
    with closing(conectar()) as conn, conn, conn.cursor() as cursor:
        cursor.execute("SELECT prioridade FROM ocorrencias WHERE id = %s FOR UPDATE", (id,))
        ocorrencia = cursor.fetchone()
        if ocorrencia is None:
            raise HTTPException(status_code=404, detail="ocorrência não encontrada")
        cursor.execute(
            "SELECT prioridade_sugerida FROM registros_decisao "
            "WHERE ocorrencia_id = %s AND tipo = 'entrada' ORDER BY data_hora, id LIMIT 1",
            (id,),
        )
        entrada = cursor.fetchone()
        resultado = registrar_decisao(
            {
                "tipo": "prioridade_alterada",
                "ocorrenciaId": id,
                "quemDecidiu": "sindico",
                "prioridadeSugerida": entrada[0] if entrada and entrada[0] else ocorrencia[0],
                "prioridadeFinal": body.prioridade,
                "motivo": body.motivo,
            },
            conexao=conn,
        )
        if not resultado["ok"]:
            raise HTTPException(status_code=422, detail=resultado["erros"])
        cursor.execute("UPDATE ocorrencias SET prioridade = %s WHERE id = %s", (body.prioridade, id))
    return {"id": id, "prioridade": body.prioridade}


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
