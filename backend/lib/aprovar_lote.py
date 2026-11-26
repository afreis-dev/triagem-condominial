from fastapi import HTTPException
from .registrar_decisao import registrar_decisao

def listar_para_aprovacao(conn, sindico_id):
    """H15: novas não-urgentes, sem travada, só da carteira do síndico."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT o.id, o.protocolo, o.descricao, o.status, o.prioridade
            FROM ocorrencias o
            JOIN condominios c ON c.id = o.condominio_id
            WHERE o.status = 'nova'
              AND o.travada = FALSE
              AND o.prioridade != 'urgente'
              AND c.sindico_id = %s
            ORDER BY o.id
        """, (sindico_id,))
        linhas = cur.fetchall()
    return [
        {"id": r[0], "protocolo": r[1], "descricao": r[2], "status": r[3], "prioridade": r[4]}
        for r in linhas
    ]

def aprovar_lote(conn, ids, sindico_id):
    """H15: aprova o lote todo-ou-nada + registra no histórico."""
    if not ids:
        raise HTTPException(status_code=422, detail="Informe pelo menos 1 ocorrência")
    try:
        ids_int = [int(i) for i in ids]
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Ids devem ser inteiros")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE ocorrencias o
                SET status = 'em_andamento'
                FROM condominios c
                WHERE o.id = ANY(%s)
                  AND o.condominio_id = c.id
                  AND c.sindico_id = %s
                  AND o.status = 'nova'
                  AND o.travada = FALSE
                  AND o.prioridade <> 'urgente'
                RETURNING o.id
            """, (ids_int, sindico_id))
            aprovados = [r[0] for r in cur.fetchall()]
            if len(aprovados) != len(ids_int):
                conn.rollback()
                raise HTTPException(
                    status_code=409,
                    detail="Algum id não é seu, já foi aprovado, está travado ou é urgente",
                )
            for oid in aprovados:
                resultado = registrar_decisao(
                    {
                        "tipo": "aprovacao_lote",
                        "ocorrenciaId": oid,
                        "quemDecidiu": "sindico",
                        "prioridadeFinal": "normal",
                        "responsavel": "sindico",
                    },
                    conexao=conn,
                )
                if not resultado.get("ok"):
                    conn.rollback()
                    raise HTTPException(status_code=409, detail="Falha ao registrar decisão do lote")
        conn.commit()
        return {"ok": True, "aprovadas": len(aprovados), "aprovados": aprovados, "quantidade": len(aprovados)}
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Falha ao aprovar lote")

def desfazer_lote(conn, ids, sindico_id):
    """H15 undo: volta em_andamento -> nova + registra desfazer."""
    if not ids:
        raise HTTPException(status_code=422, detail="Informe pelo menos 1 ocorrência")
    try:
        ids_int = [int(i) for i in ids]
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Ids devem ser inteiros")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE ocorrencias o
                SET status = 'nova'
                FROM condominios c
                WHERE o.id = ANY(%s)
                  AND o.condominio_id = c.id
                  AND c.sindico_id = %s
                  AND o.status = 'em_andamento'
                RETURNING o.id
            """, (ids_int, sindico_id))
            desfeitos = [r[0] for r in cur.fetchall()]
            if len(desfeitos) != len(ids_int):
                conn.rollback()
                raise HTTPException(status_code=409, detail="Algum id não pode ser desfeito")
            for oid in desfeitos:
                resultado = registrar_decisao(
                    {
                        "tipo": "desfazer_aprovacao_lote",
                        "ocorrenciaId": oid,
                        "quemDecidiu": "sindico",
                        "prioridadeFinal": "normal",
                        "responsavel": "sindico",
                    },
                    conexao=conn,
                )
                if not resultado.get("ok"):
                    conn.rollback()
                    raise HTTPException(status_code=409, detail=f"Falha desfazer {oid}: {resultado.get('erros')}")
        conn.commit()
        return {"ok": True, "desfeitos": desfeitos}
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Falha ao desfazer lote")