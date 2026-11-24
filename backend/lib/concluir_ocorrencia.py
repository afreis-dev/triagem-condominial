from .conexao import conectar
from .dominio import inteiro
from .registrar_decisao import registrar_decisao


def _erro(campo, mensagem):
    """Monta a resposta de erro no formato do contrato."""
    return {"ok": False, "erros": {campo: mensagem}}


def _nao_encontrada():
    """Resposta de erro para uma ocorrência que não existe."""
    return _erro("ocorrenciaId", "Ocorrência não encontrada")


def _concluir(conexao, ocorrencia_id, proprio):
    """Conclui a ocorrência se ela estiver em andamento e registra a conclusão no histórico."""
    with conexao.cursor() as cur:
        cur.execute("SELECT status FROM ocorrencias WHERE id = %s FOR UPDATE", (ocorrencia_id,))
        ocorrencia = cur.fetchone()
        if ocorrencia is None:
            return _nao_encontrada()
        if ocorrencia[0] != "em_andamento":
            return _erro("status", "Só dá para concluir uma ocorrência em andamento")
        cur.execute(
            "UPDATE ocorrencias SET status = 'concluida', concluida_em = now() "
            "WHERE id = %s RETURNING concluida_em",
            (ocorrencia_id,),
        )
        concluida_em = cur.fetchone()[0]
    conclusao = registrar_decisao(
        {"tipo": "conclusao", "ocorrenciaId": ocorrencia_id, "quemDecidiu": "sindico"},
        conexao=conexao,
    )
    if not conclusao["ok"]:
        raise RuntimeError(f"registro de conclusão recusado: {conclusao['erros']}")
    if proprio:
        conexao.commit()
    return {"ok": True, "ocorrenciaId": ocorrencia_id, "concluidaEm": concluida_em.isoformat()}


def concluir_ocorrencia(ocorrencia_id, conexao=None):
    """Conclui uma ocorrência em andamento, com horário do servidor, e registra a conclusão. Com conexão própria, confirma sozinha."""
    ocorrencia_id = inteiro(ocorrencia_id)
    if ocorrencia_id is None:
        return _nao_encontrada()
    proprio = conexao is None
    if proprio:
        conexao = conectar()
    try:
        return _concluir(conexao, ocorrencia_id, proprio)
    except Exception:
        if proprio:
            conexao.rollback()
        raise
    finally:
        if proprio:
            conexao.close()
