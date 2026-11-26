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
        return {"ok": False, "erros": {"ids": "Informe pelo menos 1 ocorrência"}}
    try:
        ids_int = [int(i) for i in ids]
    except (ValueError, TypeError):
        return {"ok": False, "erros": {"ids": "Ids devem ser inteiros"}}
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
                RETURNING o.id
            """, (ids_int, sindico_id))
            aprovados = [r[0] for r in cur.fetchall()]
            if len(aprovados) != len(ids_int):
                conn.rollback()
                return {"ok": False, "erros": {"ids": "Algum id não é seu, já foi aprovado ou está travado"}}
            for oid in aprovados:
                resultado = registrar_decisao(
                    {
                        "ocorrenciaId": oid,
                        "acao": "aprovacao_lote",
                        "nota": f"aprovado em lote por {sindico_id} — status nova -> em_andamento",
                    },
                    conexao=conn,
                )
                if not resultado.get("ok"):
                    conn.rollback()
                    return {"ok": False, "erros": resultado.get("erros", {})}
        conn.commit()
        return {"ok": True, "aprovados": aprovados, "quantidade": len(aprovados)}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "erros": {"ids": str(e)}}

def desfazer_lote(conn, ids, sindico_id):
    """H15 undo: volta em_andamento -> nova + registra desfazer."""
    if not ids:
        return {"ok": False, "erros": {"ids": "Informe pelo menos 1 ocorrência"}}
    try:
        ids_int = [int(i) for i in ids]
    except (ValueError, TypeError):
        return {"ok": False, "erros": {"ids": "Ids devem ser inteiros"}}
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
                return {"ok": False, "erros": {"ids": "Algum id não pode ser desfeito"}}
            for oid in desfeitos:
                resultado = registrar_decisao(
                    {
                        "ocorrenciaId": oid,
                        "acao": "desfazer_aprovacao_lote",
                        "nota": f"desfeito por {sindico_id} — status em_andamento -> nova",
                    },
                    conexao=conn,
                )
                if not resultado.get("ok"):
                    conn.rollback()
                    return {"ok": False, "erros": resultado.get("erros", {})}
        conn.commit()
        return {"ok": True, "desfeitos": desfeitos}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "erros": {"ids": str(e)}}