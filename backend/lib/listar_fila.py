from datetime import timezone

from .conexao import conectar

CONSULTA = """
    SELECT o.id, o.protocolo, o.condominio_id, c.nome, o.descricao, o.origem, o.status,
           o.prioridade, o.categoria, o.responsavel_sugerido, o.motivo, o.travada, o.criada_em,
           ultima.acao, ultima.responsavel, ultima.data_agendada
      FROM ocorrencias o
      JOIN condominios c ON c.id = o.condominio_id
      LEFT JOIN LATERAL (
          SELECT r.acao, r.responsavel, r.data_agendada FROM registros_decisao r
          WHERE r.ocorrencia_id = o.id AND r.tipo = 'acao'
          ORDER BY r.data_hora DESC, r.id DESC LIMIT 1
      ) ultima ON TRUE
     ORDER BY o.criada_em, o.id
"""

CAMPOS = (
    "id",
    "protocolo",
    "condominioId",
    "condominio",
    "descricao",
    "origem",
    "status",
    "prioridade",
    "categoria",
    "responsavelSugerido",
    "motivo",
    "travada",
    "criadaEm",
    "acao",
    "marcaAcao",
)


def marca_acao(acao, responsavel, data_agendada):
    if acao == "delegar" and responsavel:
        nome = "você" if responsavel == "sindico" else responsavel
        return f"Responsável: {nome}"
    if acao == "eu_mesmo":
        return "Responsável: você"
    if acao == "agendar" and data_agendada:
        return f"Agendado para {data_agendada:%d/%m}"
    return None


def _cartao(linha):
    """Monta o cartão da fila no formato do contrato."""
    cartao = dict(zip(CAMPOS, (*linha[:-2], marca_acao(*linha[-3:]))))
    cartao["criadaEm"] = cartao["criadaEm"].astimezone(timezone.utc).isoformat()
    return cartao


def listar_fila(conexao=None):
    """Busca no banco as ocorrências de todos os condomínios com os campos do cartão. Só lê, não grava nada."""
    proprio = conexao is None
    if proprio:
        conexao = conectar()
    try:
        with conexao.cursor() as cur:
            cur.execute(CONSULTA)
            linhas = cur.fetchall()
        return {"ok": True, "ocorrencias": [_cartao(linha) for linha in linhas]}
    finally:
        if proprio:
            conexao.close()
