from datetime import timezone

from .conexao import conectar

CONSULTA = """
    SELECT o.id, o.protocolo, o.condominio_id, c.nome, o.descricao, o.origem, o.status,
           o.prioridade, o.categoria, o.responsavel_sugerido, o.motivo, o.travada, o.criada_em,
           (SELECT r.acao FROM registros_decisao r
             WHERE r.ocorrencia_id = o.id AND r.tipo = 'acao'
             ORDER BY r.data_hora DESC, r.id DESC LIMIT 1)
    FROM ocorrencias o
    JOIN condominios c ON c.id = o.condominio_id
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
    "travada",
    "criadaEm",
    "acao",
)


def _cartao(linha):
    """Monta o cartão da fila no formato do contrato."""
    cartao = dict(zip(CAMPOS, linha))
    cartao["criadaEm"] = cartao["criadaEm"].astimezone(timezone.utc).isoformat()
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
