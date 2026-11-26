from fastapi import HTTPException
from .registrar_decisao import registrar_decisao
from .dominio import LIMITE_ID

def listar_para_aprovacao(conn, sindico_id):
    """H15: novas não-urgentes, sem travada, só da carteira do síndico."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT o.id, o.protocolo, o.descricao, o.status, o.prioridade, 
            o.responsavel_sugerido, o.motivo
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
        {"id": r[0], "protocolo": r[1], "descricao": r[2], "status": r[3], "prioridade": r[4],
         "responsavel_sugerido": r[5], "motivo": r[6],}
        for r in linhas
    ]

def _validar_ids(ids):
    if not isinstance(ids, (list, tuple)) or not ids:
        raise HTTPException(status_code=422, detail="Informe pelo menos 1 ocorrência")
    ids_int = []
    for valor in ids:
        if isinstance(valor, bool):
            raise HTTPException(status_code=422, detail="Ids devem ser inteiros positivos")
        if isinstance(valor, int):
            id_ = valor
        elif isinstance(valor, str) and valor.strip().isascii() and valor.strip().isdecimal():
            id_ = int(valor.strip())
        else:
            raise HTTPException(status_code=422, detail="Ids devem ser inteiros positivos")
        if not 1 <= id_ <= LIMITE_ID:
            raise HTTPException(status_code=422, detail="Ids devem ser inteiros positivos")
        if id_ in ids_int:
            raise HTTPException(status_code=422, detail="A lista contém IDs duplicados")
        ids_int.append(id_)
    return ids_int

def aprovar_lote(conn, ids, sindico_id):
    """H15: aprova o lote todo-ou-nada + registra no histórico."""
    ids_int = _validar_ids(ids)
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
                RETURNING o.id, o.prioridade
            """, (ids_int, sindico_id))
            linhas = cur.fetchall()
            if len(linhas) != len(ids_int):
                conn.rollback()
                raise HTTPException(
                    status_code=409,
                    detail="Algum id não é seu, já foi aprovado, está travado ou é urgente",
                )
            for oid, prioridade in linhas:
                resultado = registrar_decisao(
                    {
                        "tipo": "aprovacao_lote",
                        "ocorrenciaId": oid,
                        "quemDecidiu": "sindico",
                        "prioridadeFinal": prioridade,
                        "responsavel": "sindico",
                    },
                    conexao=conn,
                )
                if not resultado.get("ok"):
                    conn.rollback()
                    raise HTTPException(status_code=409, detail="Falha ao registrar decisão do lote")
        conn.commit()
        aprovados = [r[0] for r in linhas]
        return {"ok": True, "aprovadas": len(aprovados), "aprovados": aprovados, "quantidade": len(aprovados)}
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Falha ao aprovar lote")

def desfazer_lote(conn, ids, sindico_id):
    """H15 undo: só desfaz se o último evento foi aprovacao_lote."""
    ids_int = _validar_ids(ids)
    try:
        with conn.cursor() as cur:
            # 1. Trava as ocorrências na mesma transação
            cur.execute("""
                SELECT o.id, o.prioridade
                FROM ocorrencias o
                JOIN condominios c ON c.id = o.condominio_id
                WHERE o.id = ANY(%s)
                  AND o.condominio_id = c.id
                  AND c.sindico_id = %s
                  AND o.status = 'em_andamento'
                FOR UPDATE OF o
            """, (ids_int, sindico_id))
            linhas = cur.fetchall()
            if len(linhas) != len(ids_int):
                conn.rollback()
                raise HTTPException(status_code=409, detail="Algum id não pode ser desfeito")

            # 2. Verifica se o último evento de cada uma foi aprovacao_lote
            cur.execute("""
                SELECT DISTINCT ON (ocorrencia_id) ocorrencia_id, tipo
                FROM registros_decisao
                WHERE ocorrencia_id = ANY(%s)
                ORDER BY ocorrencia_id, data_hora DESC, id DESC
            """, (ids_int,))
            ultimo_tipo = {r[0]: r[1] for r in cur.fetchall()}
            for oid, _ in linhas:
                if ultimo_tipo.get(oid) != "aprovacao_lote":
                    conn.rollback()
                    raise HTTPException(
                        status_code=409,
                        detail="Algum id não pode ser desfeito: último evento não foi aprovação em lote",
                    )

            # 3. Só agora volta pra nova
            cur.execute("""
                UPDATE ocorrencias
                SET status = 'nova'
                WHERE id = ANY(%s)
                RETURNING id
            """, (ids_int,))
            desfeitos = [r[0] for r in cur.fetchall()]
            prioridades = {oid: prio for oid, prio in linhas}
            for oid in desfeitos:
                resultado = registrar_decisao(
                    {
                        "tipo": "desfazer_aprovacao_lote",
                        "ocorrenciaId": oid,
                        "quemDecidiu": "sindico",
                        "prioridadeFinal": prioridades.get(oid),
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
