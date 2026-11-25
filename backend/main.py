from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Literal, Optional
from uuid import UUID

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).parent / ".env")

from .lib.conexao import conectar
from .lib.listar_fila import marca_acao
from .lib.registrar_decisao import buscar_decisoes, registrar_decisao
from .lib.salvar_ocorrencia import salvar_ocorrencia
from .lib.concluir_ocorrencia import concluir_ocorrencia
from .lib.auth import criar_token, verificar_senha
from .lib.auth_deps import sindico_autenticado
from .rotas.fila import rota_listar_fila

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

# ---------- Auth (develop) ----------
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
    with closing(conectar()) as conn, conn:
        resultado = salvar_ocorrencia(dados, conn)
    if not resultado["ok"]:
        raise HTTPException(status_code=422, detail=resultado["erros"])
    return resultado

# ---------- H03 (develop - fila + auth) ----------
@app.get("/api/ocorrencias")
@app.get("/ocorrencias")
def listar_ocorrencias(sindico=Depends(sindico_autenticado)):
    return rota_listar_fila(sindico)

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
@app.get("/api/ocorrencias/{id}/decisoes")
@app.get("/ocorrencias/{id}/decisoes")
def listar_decisoes(id: str):
    oid = _validar_uuid(id)
    with closing(conectar()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM ocorrencias WHERE id = %s",
                (str(oid),),
            )
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
        return buscar_decisoes(str(oid), conn)

# ---------- H13 ----------
@app.patch("/api/ocorrencias/{id}/concluir")
@app.patch("/ocorrencias/{id}/concluir")
def concluir(id: str):
    oid = _validar_uuid(id)
    resultado = concluir_ocorrencia(str(oid))
    if resultado["ok"]:
        return resultado
    codigo = 404 if "ocorrenciaId" in resultado["erros"] else 409
    return JSONResponse(content=resultado, status_code=codigo)

# ---------- Ações / Responsáveis ----------
class DecisaoAcao(BaseModel):
    acao: Literal["delegar", "agendar", "eu_mesmo"]
    responsavel: str | None = None
    dataAgendada: date | None = None
    nota: str = Field(default="", max_length=500)

def _consultar_ocorrencia_acao(cursor, id: str, *, bloquear: bool = False):
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
def listar_responsaveis_ocorrencia(id: str):
    oid = _validar_uuid(id)
    with closing(conectar()) as conn, conn.cursor() as cursor:
        condominio_id, sugerido, _ = _consultar_ocorrencia_acao(cursor, str(oid))
        papeis = _papeis_delegaveis(cursor, condominio_id)
    return {
        "responsaveis": papeis,
        "responsavelSugerido": sugerido if sugerido in papeis else None,
    }

@app.post("/ocorrencias/{id}/acoes", status_code=201)
def confirmar_acao(id: str, decisao: DecisaoAcao):
    oid = _validar_uuid(id)
    if decisao.acao == "agendar" and decisao.dataAgendada is None:
        raise HTTPException(status_code=422, detail="Escolha a data do agendamento")

    with closing(conectar()) as conn, conn, conn.cursor() as cursor:
        condominio_id, _, status = _consultar_ocorrencia_acao(cursor, str(oid), bloquear=True)
        if status not in ("nova", "Nova"):
            raise HTTPException(status_code=409, detail="A ocorrência precisa estar em Nova")
        if decisao.acao == "delegar" and decisao.responsavel not in _papeis_delegaveis(cursor, condominio_id):
            raise HTTPException(status_code=422, detail="Escolha um responsável do condomínio")

        resultado = registrar_decisao(
            {"tipo": "acao", "ocorrenciaId": str(oid), "quemDecidiu": "sindico", **decisao.model_dump(mode="json")},
            conexao=conn,
        )
        if not resultado["ok"]:
            raise HTTPException(status_code=422, detail=resultado["erros"])
        cursor.execute("UPDATE ocorrencias SET status = 'Em andamento' WHERE id = %s", (str(oid),))

    return {"id": str(oid), "status": "Em andamento",
            "marcaAcao": marca_acao(decisao.acao, decisao.responsavel, decisao.dataAgendada)}

# ---------- H10 ----------
class PrioridadeBody(BaseModel):
    prioridade: str
    motivo: Optional[str] = None

@app.patch("/ocorrencias/{id}/prioridade")
def alterar_prioridade(id: str, body: PrioridadeBody):
    oid = _validar_uuid(id)
    if not body.motivo or not body.motivo.strip():
        raise HTTPException(status_code=400, detail="motivo é obrigatório")
    with closing(conectar()) as conn, conn, conn.cursor() as cursor:
        cursor.execute("SELECT prioridade FROM ocorrencias WHERE id = %s FOR UPDATE", (str(oid),))
        ocorrencia = cursor.fetchone()
        if ocorrencia is None:
            raise HTTPException(status_code=404, detail="ocorrência não encontrada")
        cursor.execute(
            "SELECT nota FROM registros_decisao "
            "WHERE ocorrencia_id = %s AND acao = 'entrada' ORDER BY criado_em, id LIMIT 1",
            (str(oid),),
        )
        entrada = cursor.fetchone()
        resultado = registrar_decisao(
            {
                "tipo": "prioridade_alterada",
                "ocorrenciaId": str(oid),
                "quemDecidiu": "sindico",
                "prioridadeSugerida": ocorrencia[0],
                "prioridadeFinal": body.prioridade,
                "motivo": body.motivo,
            },
            conexao=conn,
        )
        if not resultado["ok"]:
            raise HTTPException(status_code=422, detail=resultado["erros"])
        cursor.execute("UPDATE ocorrencias SET prioridade = %s WHERE id = %s", (body.prioridade, str(oid)))
    return {"id": str(oid), "prioridade": body.prioridade}

# ---------- H01 ----------
class ChamadoForm(BaseModel):
    perfil: Literal["morador", "proprietario", "funcionario"]
    nome: str = ""
    apartamento: str = ""
    celular: str
    local: str = ""
    descricao: str

class OcorrenciaFormBody(BaseModel):
    perfil: Literal["morador", "proprietario", "funcionario"]
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