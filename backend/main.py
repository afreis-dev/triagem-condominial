from dotenv import load_dotenv
load_dotenv()

import os
from contextlib import closing
from datetime import date, timezone
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Literal, Optional

from lib.conexao import conectar
from lib.listar_fila import marca_acao
from lib.registrar_decisao import buscar_decisoes, registrar_decisao
from lib.salvar_ocorrencia import salvar_ocorrencia
from lib.concluir_ocorrencia import concluir_ocorrencia
from lib.auth import criar_token, verificar_senha
from lib.auth_deps import COOKIE_SESSAO, sindico_autenticado, sindico_com_csrf, verificar_acesso_ocorrencia
from rotas.fila import rota_listar_fila

app = FastAPI(title="Triagem Condominial")
ORIGENS_FRONTEND = [
    origem.strip() for origem in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:8080,http://127.0.0.1:8080" if os.getenv("APP_ENV") != "production" else "",
    ).split(",") if origem.strip()
]
COOKIE_SECURE = os.getenv("APP_ENV") == "production"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()
if COOKIE_SAMESITE not in {"lax", "strict", "none"} or (COOKIE_SAMESITE == "none" and not COOKIE_SECURE):
    raise RuntimeError("COOKIE_SAMESITE inválido para o ambiente")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS_FRONTEND,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Requested-With"],
)


def verificar_origem(request: Request):
    origem = request.headers.get("origin")
    if origem and origem not in ORIGENS_FRONTEND and origem != str(request.base_url).rstrip("/"):
        raise HTTPException(status_code=403, detail="Origem não autorizada")

class DadosLogin(BaseModel):
    identificador: str
    senha: str


@app.post("/auth/login")
def login(dados: DadosLogin, request: Request, response: Response):
    verificar_origem(request)
    if (request.headers.get("X-Requested-With") != "XMLHttpRequest"
            and request.headers.get("origin") != str(request.base_url).rstrip("/")):
        raise HTTPException(status_code=403, detail="Requisição não autorizada")
    identificador = dados.identificador.strip()
    celular = "".join(c for c in identificador if c.isdigit())
    if not identificador or ("@" not in identificador and len(celular) not in {10, 11}):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    with closing(conectar()) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, senha_hash
                FROM sindicos
                WHERE LOWER(email) = LOWER(%s)
                   OR (%s <> '' AND regexp_replace(COALESCE(celular, ''), '[^0-9]', '', 'g') = %s)
                """,
                (identificador, celular if "@" not in identificador else "", celular if "@" not in identificador else ""),
            )
            resultado = cursor.fetchone()

    if not resultado or not resultado[1]:
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas",
        )

    if not verificar_senha(dados.senha, resultado[1]):
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas",
        )

    response.set_cookie(
        key=COOKIE_SESSAO,
        value=criar_token(resultado[0]),
        max_age=8 * 60 * 60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"ok": True}


@app.get("/auth/me")
def consultar_perfil(request: Request, response: Response, sindico=Depends(sindico_autenticado)):
    response.headers["Cache-Control"] = "no-store"
    return {**sindico, "csrfToken": request.state.csrf_token}


@app.post("/auth/logout")
def logout(request: Request, response: Response, sindico=Depends(sindico_com_csrf)):
    verificar_origem(request)
    response.delete_cookie(COOKIE_SESSAO, path="/", secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE)
    response.headers["Cache-Control"] = "no-store"
    return {"ok": True}


class ColarBody(BaseModel):
    condominioId: int
    descricao: str = Field(max_length=2000)
    texto_colado: Optional[str] = None
    nome: Optional[str] = None
    celular: Optional[str] = None
    apartamento: Optional[str] = None
    local: Optional[str] = None

class PrioridadeBody(BaseModel):
    prioridade: str
    motivo: Optional[str] = Field(default=None, max_length=500)

def _ocorrencia_da_carteira(cursor, id: int, sindico_id: int, *, bloquear=False):
    consulta = """
        SELECT o.id, o.protocolo, o.condominio_id, c.nome, o.descricao, o.origem,
               o.status, o.prioridade, o.motivo, o.criada_em, o.concluida_em,
               o.nome, o.apartamento, o.celular, o.local, o.travada,
               o.palavra_de_risco, COALESCE(entrada.prioridade_sugerida, o.prioridade),
               o.categoria, o.responsavel_sugerido
        FROM ocorrencias o
        JOIN condominios c ON c.id = o.condominio_id
        LEFT JOIN LATERAL (
            SELECT prioridade_sugerida
            FROM registros_decisao
            WHERE ocorrencia_id = o.id AND prioridade_sugerida IS NOT NULL
              AND tipo IN ('entrada', 'prioridade_alterada', 'prioridade_confirmada')
            ORDER BY (tipo = 'entrada') DESC, data_hora, id LIMIT 1
        ) entrada ON TRUE
        WHERE o.id = %s AND c.sindico_id = %s
    """
    if bloquear:
        consulta += " FOR UPDATE OF o FOR SHARE OF c"
    cursor.execute(consulta, (id, sindico_id))
    linha = cursor.fetchone()
    if linha is None:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
    campos = (
        "id", "protocolo", "condominioId", "condominio", "descricao", "origem",
        "status", "prioridade", "motivo", "criadaEm", "concluidaEm",
        "nome", "apartamento", "celular", "local", "travada",
        "palavraDeRisco", "prioridadeSugerida", "categoria", "responsavel",
    )
    return dict(zip(campos, linha))

# Endpoint - H04
@app.get("/api/condominios")
def listar_condominios_da_carteira(sindico=Depends(sindico_autenticado)):
    with closing(conectar()) as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, nome FROM condominios WHERE sindico_id = %s ORDER BY nome, id",
            (sindico["id"],),
        )
        return [{"id": id_, "nome": nome} for id_, nome in cursor.fetchall()]


@app.post("/ocorrencias/colar", status_code=201)
def colar(body: ColarBody, sindico=Depends(sindico_com_csrf)):
    dados = {
        "origem": "whatsapp_sindico",
        "condominioId": body.condominioId,
        "descricao": body.texto_colado or body.descricao,
        "nome": body.nome,
        "celular": body.celular,
        "apartamento": body.apartamento,
        "local": body.local,
    }
    with closing(conectar()) as conn, conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM condominios WHERE id = %s AND sindico_id = %s FOR SHARE",
                (body.condominioId, sindico["id"]),
            )
            if cursor.fetchone() is None:
                raise HTTPException(status_code=403, detail="Condomínio fora da sua carteira")

        resultado = salvar_ocorrencia(dados, conn)
    if not resultado["ok"]:
        raise HTTPException(status_code=422, detail=resultado["erros"])
    return resultado

# Endpoint - H03
@app.get("/api/ocorrencias")
@app.get("/ocorrencias")
def listar_ocorrencias(sindico=Depends(sindico_autenticado)):
    return rota_listar_fila(sindico)

from lib.aprovar_lote import listar_para_aprovacao, aprovar_lote, desfazer_lote

@app.get("/ocorrencias/para-aprovacao")
def rota_para_aprovacao(sindico=Depends(sindico_autenticado)):
    conn = conectar()
    try:
        return {"ok": True, "ocorrencias": listar_para_aprovacao(conn, sindico["id"])}
    finally:
        conn.close()

@app.post("/ocorrencias/aprovar-lote")
def rota_aprovar_lote(payload: dict, sindico=Depends(sindico_com_csrf)):
    conn = conectar()
    try:
        return aprovar_lote(conn, payload.get("ids", []), sindico["id"])
    finally:
        conn.close()

@app.post("/ocorrencias/desfazer-lote")
def rota_desfazer_lote(payload: dict, sindico=Depends(sindico_com_csrf)):
    conn = conectar()
    try:
        return desfazer_lote(conn, payload.get("ids", []), sindico["id"])
    finally:
        conn.close()

# Detalhe
@app.get("/ocorrencias/{id}")
def buscar_ocorrencia(id: int, sindico=Depends(sindico_autenticado)):
    with closing(conectar()) as conn, conn.cursor() as cursor:
        ocorrencia = _ocorrencia_da_carteira(cursor, id, sindico["id"])
    for campo in ("criadaEm", "concluidaEm"):
        if ocorrencia[campo] is not None:
            ocorrencia[campo] = ocorrencia[campo].astimezone(timezone.utc).isoformat()
    return {
        **ocorrencia,
        "condominio_id": ocorrencia["condominioId"],
        "texto_colado": ocorrencia["descricao"],
        "criado_em": ocorrencia["criadaEm"],
    }

# Endpoint - H14
@app.get("/api/ocorrencias/{id}/decisoes")
@app.get("/ocorrencias/{id}/decisoes")
def listar_decisoes(id: int, sindico=Depends(sindico_autenticado)):
    with closing(conectar()) as conn:
        with conn.cursor() as cur:
            verificar_acesso_ocorrencia(cur, id, sindico["id"])

        return buscar_decisoes(id, conn)


# Endpoint - H13
@app.patch("/api/ocorrencias/{id}/concluir")
@app.patch("/ocorrencias/{id}/concluir")
def concluir(id: int, sindico=Depends(sindico_com_csrf)):
    with closing(conectar()) as conn, conn:
        with conn.cursor() as cursor:
            verificar_acesso_ocorrencia(cursor, id, sindico["id"])

        resultado = concluir_ocorrencia(id, conexao=conn)

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
def listar_responsaveis_ocorrencia(
    id: int,
    sindico=Depends(sindico_autenticado),
):
    with closing(conectar()) as conn, conn.cursor() as cursor:
        verificar_acesso_ocorrencia(cursor, id, sindico["id"])
        condominio_id, sugerido, _ = _consultar_ocorrencia_acao(cursor, id)
        papeis = _papeis_delegaveis(cursor, condominio_id)
    return {
        "responsaveis": papeis,
        "responsavelSugerido": sugerido if sugerido in papeis else None,
    }


@app.post("/ocorrencias/{id}/acoes", status_code=201)
def confirmar_acao(
    id: int,
    decisao: DecisaoAcao,
    sindico=Depends(sindico_com_csrf),
):
    if decisao.acao == "agendar" and decisao.dataAgendada is None:
        raise HTTPException(status_code=422, detail="Escolha a data do agendamento")

    with closing(conectar()) as conn, conn, conn.cursor() as cursor:
        verificar_acesso_ocorrencia(cursor, id, sindico["id"])
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
def alterar_prioridade(id: int, body: PrioridadeBody, sindico=Depends(sindico_com_csrf)):
    with closing(conectar()) as conn, conn, conn.cursor() as cursor:
        ocorrencia = _ocorrencia_da_carteira(cursor, id, sindico["id"], bloquear=True)
        if ocorrencia["status"] == "concluida":
            raise HTTPException(status_code=409, detail="A ocorrência está concluída")
        sugerida = ocorrencia["prioridadeSugerida"]
        alterada = body.prioridade != sugerida or (
            ocorrencia["travada"] and body.prioridade != "urgente"
        )
        resultado = registrar_decisao(
            {
                "tipo": "prioridade_alterada" if alterada else "prioridade_confirmada",
                "ocorrenciaId": id,
                "quemDecidiu": "sindico",
                "prioridadeSugerida": sugerida,
                "prioridadeFinal": body.prioridade,
                "motivo": body.motivo,
            },
            conexao=conn,
        )
        if not resultado["ok"]:
            raise HTTPException(status_code=422, detail=resultado["erros"])
        if body.prioridade != ocorrencia["prioridade"]:
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
