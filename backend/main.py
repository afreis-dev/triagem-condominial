from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv
import psycopg2
import os
import unicodedata
import re
import uuid
from typing import Literal, Optional
from datetime import date
from contextlib import closing

load_dotenv()

app = FastAPI()

def get_db():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=500, detail="DATABASE_URL não configurada")
    return psycopg2.connect(url)

class ColarMensagemRequest(BaseModel):
    condominio_id: str = Field(..., description="aurora, vista-verde ou palmeiras")
    texto_colado: str = Field(..., max_length=2000)
    nome_remetente: str | None = None
    celular_remetente: str | None = None

    @field_validator("condominio_id")
    @classmethod
    def condominio_obrigatorio(cls, v):
        if not v or not v.strip():
            raise ValueError("Escolha o condomínio")
        return v.strip()

    @field_validator("texto_colado")
    @classmethod
    def texto_obrigatorio(cls, v):
        if not v or not v.strip():
            raise ValueError("Cole a mensagem")
        return v

REGRAS = [
    (1, ["falta de água", "sem água", "faltou água"], "manutencao", "alta", "zelador", "falta de água afeta muitos moradores"),
    (2, ["vazamento", "infiltração", "água caindo", "água descendo", "goteira"], "manutencao", "alta", "zelador", "vazamento ativo que pode piorar"),
    (3, ["elevador parado", "elevador quebrado", "elevador travado"], "manutencao", "alta", "zelador", "elevador parado afeta todos os moradores do bloco"),
    (4, ["portão aberto", "portão travado", "portão quebrado", "portão não fecha", "portão travou", "travou aberto", "portao da garagem travou"], "seguranca_acesso", "alta", "portaria", "deixa o acesso ao prédio aberto"),
    (5, ["furto", "roubo", "arrombamento", "invasão"], "seguranca_acesso", "alta", "sindico", "situação de segurança que exige decisão do síndico"),
    (6, ["sem energia", "falta de luz", "disjuntor", "queda de energia"], "manutencao", "alta", "zelador", "falta de energia em área comum afeta muitos moradores"),
    (7, ["entupimento", "entupido", "esgoto", "refluxo"], "manutencao", "alta", "zelador", "entupimento tende a piorar rápido"),
    (8, ["bomba d'água", "caixa d'água", "reservatório"], "manutencao", "alta", "zelador", "afeta o abastecimento do prédio"),
    (9, ["lâmpada", "luz queimada", "lâmpada queimada"], "manutencao", "normal", "zelador", "manutenção simples de área comum"),
    (10, ["interfone", "campainha"], "seguranca_acesso", "normal", "portaria", "afeta a comunicação, mas tem alternativa"),
    (11, ["câmera", "cftv", "monitoramento"], "seguranca_acesso", "normal", "portaria", "equipamento de segurança sem risco imediato"),
    (12, ["fechadura", "chave", "tag", "controle remoto", "crachá"], "seguranca_acesso", "normal", "portaria", "acesso individual, sem risco ao prédio"),
    (13, ["torneira", "descarga", "vaso sanitário", "sifão"], "manutencao", "normal", "zelador", "manutenção simples de área comum"),
    (14, ["pintura", "reboco", "azulejo", "piso solto"], "manutencao", "normal", "zelador", "conservação sem risco imediato"),
    (15, ["jardim", "poda", "grama", "árvore"], "manutencao", "normal", "zelador", "conservação de área externa"),
    (16, ["piscina", "sauna", "academia", "playground"], "manutencao", "normal", "zelador", "área de lazer, sem risco imediato"),
    (17, ["lixo", "lixeira", "coleta"], "manutencao", "normal", "zelador", "limpeza de área comum"),
    (18, ["barulho", "som alto", "festa", "vizinho"], "convivencia", "normal", "sindico", "conflito entre moradores, sem risco imediato"),
    (19, ["cachorro", "gato", "animal", "cocô", "coleira"], "convivencia", "normal", "sindico", "regra de convivência do regimento"),
    (20, ["vaga", "estacionamento", "carro parado", "moto parada"], "convivencia", "normal", "sindico", "uso de área comum entre moradores"),
    (21, ["cigarro", "fumando", "fumaça de cigarro"], "convivencia", "normal", "sindico", "regra de convivência do regimento"),
    (22, ["mudança", "caminhão de mudança", "autorização de mudança"], "pedido_administrativo", "normal", "sindico", "precisa de autorização do síndico"),
    (23, ["obra", "reforma", "furadeira", "martelete"], "pedido_administrativo", "normal", "sindico", "precisa de autorização e tem regra de horário"),
    (24, ["boleto", "segunda via", "taxa", "cota condominial", "multa"], "pedido_administrativo", "baixa", "sindico", "pedido administrativo sem prazo curto"),
    (25, ["reserva", "reservar", "salão de festas", "churrasqueira"], "pedido_administrativo", "baixa", "sindico", "pedido administrativo sem prazo curto"),
    (26, ["declaração", "documento", "ata", "cópia do regimento", "comprovante"], "pedido_administrativo", "baixa", "sindico", "pedido administrativo sem prazo curto"),
    (27, ["sugestão", "sugiro", "proposta", "ideia"], "pedido_administrativo", "baixa", "sindico", "sugestão, sem prazo nem risco"),
    (28, ["dúvida", "pergunta", "como faço", "posso", "qual o horário", "é permitido"], "duvida", "baixa", "sindico", "dúvida sobre regra do condomínio"),
]

PESO_PRIORIDADE = {"urgente": 4, "alta": 3, "normal": 2, "baixa": 1}

def normalizar(texto: str) -> str:
    t = texto.lower()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9\s']", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def buscarPalavrasDeRisco():
    # Leitua feita do banco, e não do código
    # Se incluir uma palavra pelo painel do Neon, ela aparece aqui sem novo deploy
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT palavra, categoria FROM palavras_risco")
        rows = cur.fetchall()
    finally:
        conn.close()
    return [(r[0], r[1]) for r in rows]

def aplicarTravaDeRisco(texto: str, resultado: dict):
    t = normalizar(texto)
    t_sem_cigarro = t.replace("fumaca de cigarro", "")

    palavras = buscarPalavrasDeRisco()
    palavras.sort(key=lambda x: len(normalizar(x[0])), reverse=True)

    for palavra, categoria in palavras:
        if normalizar(palavra) in t_sem_cigarro:
            palavra_curta = "gás" if normalizar(palavra) == "cheiro de gas" else palavra
            return {
                "prioridade": "urgente",
                "categoria": categoria,
                "responsavel": "sindico",
                "motivo": f"palavra de risco: {palavra_curta}",
                "travada": True,
                "palavraDeRisco": palavra_curta,
            }

    return {**resultado, "travada": False, "palavraDeRisco": None}

def classificar(texto: str):
    t = normalizar(texto)
    melhor = None
    for ordem, palavras, categoria, prioridade, responsavel, motivo in REGRAS:
        for palavra in palavras:
            if normalizar(palavra) in t:
                if melhor is None or PESO_PRIORIDADE[prioridade] > PESO_PRIORIDADE[melhor["prioridade"]]:
                    melhor = {"prioridade": prioridade, "categoria": categoria, "responsavel": responsavel, "motivo": motivo}
                break
    if melhor is None:
        melhor = {"prioridade": "normal", "categoria": "nao_reconhecida", "responsavel": "sindico", "motivo": "não reconhecida, revisar"}

    return aplicarTravaDeRisco(texto, melhor)

@app.post("/ocorrencias/colar")
def colar_mensagem(dados: ColarMensagemRequest):
    resultado = classificar(dados.texto_colado)
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO ocorrencias
            (texto_original, condominio_id, nome_remetente, celular_remetente, origem, prioridade, categoria, responsavel_sugerido, motivo, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Em andamento')
            RETURNING id
        """, (
            dados.texto_colado,
            dados.condominio_id,
            dados.nome_remetente,
            dados.celular_remetente,
            "WhatsApp, registrada pelo síndico",
            resultado["prioridade"],
            resultado["categoria"],
            resultado["responsavel"],
            resultado["motivo"]
        ))
        id_novo = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    return {
        "id": str(id_novo),
        "prioridade": resultado["prioridade"],
        "categoria": resultado["categoria"],
        "responsavel": resultado["responsavel"],
        "motivo": resultado["motivo"],
        "origem": "WhatsApp, registrada pelo síndico"
    }

@app.get("/ocorrencias")
def listar_ocorrencias():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, texto_original, condominio_id, prioridade, categoria,
                   responsavel_sugerido, motivo, origem, status, created_at,
                   (SELECT r.marca_acao FROM registros_decisao r
                    WHERE r.ocorrencia_id = ocorrencias.id AND r.tipo = 'acao'
                    ORDER BY r.criado_em DESC, r.id DESC LIMIT 1)
            FROM ocorrencias
            ORDER BY
              CASE prioridade
                WHEN 'urgente' THEN 0
                WHEN 'alta' THEN 1
                WHEN 'normal' THEN 2
                WHEN 'baixa' THEN 3
                ELSE 4
              END,
              created_at ASC
        """)
        rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "id": str(r[0]),
            "titulo": r[1],
            "condominio_id": r[2],
            "prioridade": r[3],
            "categoria": r[4],
            "responsavel": r[5],
            "motivo": r[6],
            "origem": r[7],
            "status": r[8],
            "created_at": str(r[9]),
            "marcaAcao": r[10],
        }
        for r in rows
    ]

class DecisaoAcao(BaseModel):
    acao: Literal["delegar", "agendar", "eu_mesmo"]
    responsavel: str | None = None
    dataAgendada: date | None = None
    nota: str = Field(default="", max_length=500)


def consultar_ocorrencia_acao(cursor, id: uuid.UUID, *, bloquear: bool = False):
    consulta = """
        SELECT condominio_id, responsavel_sugerido, status
        FROM ocorrencias WHERE id = %s
    """
    if bloquear:
        consulta += " FOR UPDATE"
    cursor.execute(consulta, (str(id),))
    ocorrencia = cursor.fetchone()
    if ocorrencia is None:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
    return ocorrencia


@app.get("/ocorrencias/{id}/responsaveis")
def listar_responsaveis_ocorrencia(id: uuid.UUID):
    with closing(get_db()) as conn, conn.cursor() as cursor:
        condominio_id, sugerido, _ = consultar_ocorrencia_acao(cursor, id)
        cursor.execute(
            "SELECT papel FROM responsaveis WHERE condominio_id = %s ORDER BY papel",
            (condominio_id,),
        )
        responsaveis = [linha[0] for linha in cursor.fetchall()]
    return {
        "responsaveis": responsaveis,
        "responsavelSugerido": sugerido if sugerido in responsaveis else None,
    }


def registrar_decisao(cursor, id, acao, responsavel, data_agendada, nota, marca):
    cursor.execute(
        """
        INSERT INTO registros_decisao
            (ocorrencia_id, tipo, acao, responsavel, data_agendada, nota, marca_acao)
        VALUES (%s, 'acao', %s, %s, %s, %s, %s)
        """,
        (str(id), acao, responsavel, data_agendada, nota, marca),
    )


@app.post("/ocorrencias/{id}/acoes", status_code=201)
def confirmar_acao(id: uuid.UUID, decisao: DecisaoAcao):
    responsavel = decisao.responsavel if decisao.acao == "delegar" else None
    data_agendada = decisao.dataAgendada if decisao.acao == "agendar" else None
    if decisao.acao == "agendar" and data_agendada is None:
        raise HTTPException(status_code=422, detail="Escolha a data do agendamento")

    with closing(get_db()) as conn, conn, conn.cursor() as cursor:
        condominio_id, _, status = consultar_ocorrencia_acao(cursor, id, bloquear=True)
        if status != "Nova":
            raise HTTPException(status_code=409, detail="A ocorrência precisa estar em Nova")

        if decisao.acao == "delegar":
            cursor.execute(
                "SELECT papel FROM responsaveis WHERE condominio_id = %s AND papel = %s",
                (condominio_id, responsavel),
            )
            if cursor.fetchone() is None:
                raise HTTPException(status_code=422, detail="Escolha um responsável do condomínio")
            marca = f"Delegado: {responsavel}"
        elif data_agendada is not None:
            marca = f"Agendado para {data_agendada:%d/%m}"
        else:
            marca = "Responsável: você"

        registrar_decisao(
            cursor, id, decisao.acao, responsavel, data_agendada, decisao.nota.strip(), marca
        )
        cursor.execute("UPDATE ocorrencias SET status = 'Em andamento' WHERE id = %s", (str(id),))

    return {"id": str(id), "status": "Em andamento", "marcaAcao": marca}


@app.patch("/ocorrencias/{id}/concluir")
def concluir_ocorrencia(id: str):
    try:
        uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido, deve ser UUID")

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT status FROM ocorrencias WHERE id = %s", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Ocorrência não encontrada")

        if row[0] not in ("Em andamento"):
            raise HTTPException(status_code=400, detail="Só dá pra concluir quem está Em andamento")

        cur.execute(
            "UPDATE ocorrencias SET status = 'Fechado' WHERE id = %s RETURNING id, status",
            (id,)
        )
        atualizado = cur.fetchone()
        conn.commit()
    finally:
        conn.close()

    return {"id": str(atualizado[0]), "status": atualizado[1]}

class OcorrenciaFormBody(BaseModel):
    perfil: str
    nome: Optional[str] = None
    apartamento: Optional[str] = None
    celular: Optional[str] = None
    local: Optional[str] = None
    descricao: str

def _buscar_condominio_por_slug(identificador: str, conn):
    cur = conn.cursor()
    # id já é o slug: 'aurora', 'vista-verde', 'palmeiras'
    cur.execute("SELECT id, nome FROM condominios WHERE LOWER(id) = LOWER(%s)", (identificador,))
    row = cur.fetchone()
    if row:
        cur.close()
        return row
    cur.execute("SELECT id, nome FROM condominios WHERE LOWER(nome) = LOWER(%s)", (identificador,))
    row = cur.fetchone()
    cur.close()
    return row

@app.get("/api/condominios/{identificador}")
def get_condominio_api(identificador: str):
    conn = get_db()
    try:
        row = _buscar_condominio_por_slug(identificador, conn)
        if not row:
            raise HTTPException(status_code=404, detail="condomínio não encontrado")
        return {"id": row[0], "nome": row[1]}
    finally:
        conn.close()

@app.post("/api/condominios/{identificador}/ocorrencias", status_code=201)
def criar_ocorrencia_form(identificador: str, body: OcorrenciaFormBody):
    conn = get_db()
    try:
        row = _buscar_condominio_por_slug(identificador, conn)
        if not row:
            raise HTTPException(status_code=404, detail="condomínio não encontrado")
        resultado = classificar(body.descricao)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ocorrencias
            (texto_original, condominio_id, nome_remetente, celular_remetente, origem, prioridade, categoria, responsavel_sugerido, motivo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            body.descricao,
            str(row[0]),
            body.nome,
            body.celular,
            body.perfil,
            resultado["prioridade"],
            resultado["categoria"],
            resultado["responsavel"],
            resultado["motivo"]
        ))
        id_novo = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return {"ok": True, "ocorrenciaId": str(id_novo), "protocolo": str(id_novo)[:8]}
    finally:
        conn.close()
