from datetime import timezone

from .conexao import conectar

CONSULTA = """
    SELECT o.id, o.protocolo, o.condominio_id, c.nome, o.descricao, o.origem, o.status,
           o.prioridade, o.categoria, o.responsavel_sugerido, o.motivo, o.fonte, o.travada, o.criada_em,
           o.concluida_em, ultima.acao, ultima.responsavel, ultima.data_agendada
      FROM ocorrencias o
      JOIN condominios c ON c.id = o.condominio_id
      LEFT JOIN LATERAL (
          SELECT CASE WHEN r.tipo = 'aprovacao_lote' THEN 'delegar' ELSE r.acao END AS acao,
                 r.responsavel, r.data_agendada
          FROM registros_decisao r
          WHERE r.ocorrencia_id = o.id
            AND r.tipo IN ('acao', 'aprovacao_lote', 'desfazer_aprovacao_lote')
          ORDER BY r.data_hora DESC, r.id DESC LIMIT 1
      ) ultima ON TRUE
     WHERE c.sindico_id = %s
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
    "fonte",
    "travada",
    "criadaEm",
    "concluidaEm",
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
    if cartao["concluidaEm"] is not None:
        cartao["concluidaEm"] = cartao["concluidaEm"].astimezone(timezone.utc).isoformat()
    return cartao


def listar_fila(sindico_id: int, conexao=None):
    """Busca apenas as ocorrências dos condomínios do síndico autenticado."""
    proprio = conexao is None
    if proprio:
        conexao = conectar()
    try:
        with conexao.cursor() as cur:
            cur.execute(CONSULTA, (sindico_id,))
            linhas = cur.fetchall()
        return {"ok": True, "ocorrencias": [_cartao(linha) for linha in linhas]}
    finally:
        if proprio:
            conexao.close()
