def listar_para_aprovacao(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, condominio_id, texto_original AS descricao, prioridade, categoria,
               responsavel_sugerido, motivo, status, created_at AS criado_em
        FROM ocorrencias
        WHERE status = 'Nova'
          AND prioridade IN ('alta', 'normal', 'baixa')
        ORDER BY
          CASE prioridade
            WHEN 'alta' THEN 0
            WHEN 'normal' THEN 1
            WHEN 'baixa' THEN 2
          END,
          created_at ASC
    """)
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "id": str(r[0]), "condominio_id": str(r[1]),
            "titulo": r[2], "descricao": r[2],
            "prioridade": r[3], "categoria": r[4],
            "responsavel": r[5], "motivo": r[6],
            "status": r[7],
        } for r in rows
    ]

def aprovar_lote(ids, conn):
    from .registrar_decisao import registrar_decisao
    cur = conn.cursor()
    aprovadas = []
    for oid in ids:
        cur.execute("SELECT status, prioridade FROM ocorrencias WHERE id = %s", (oid,))
        row = cur.fetchone()
        if not row or row[0] != "Nova" or row[1] == "urgente":
            continue
        cur.execute("UPDATE ocorrencias SET status = 'Em andamento' WHERE id = %s", (oid,))
        registrar_decisao({
            "ocorrencia_id": oid,
            "acao": "aprovacao_em_lote",
            "nota": "Aprovação em lote pelo síndico",
        }, conn)
        aprovadas.append(oid)
    conn.commit()
    cur.close()
    return {"aprovadas": aprovadas, "total": len(aprovadas)}

def desfazer_lote(ids, conn):
    from .registrar_decisao import registrar_decisao
    cur = conn.cursor()
    desfeitas = []
    for oid in ids:
        cur.execute("SELECT status FROM ocorrencias WHERE id = %s", (oid,))
        row = cur.fetchone()
        if not row or row[0] != "Em andamento":
            continue
        cur.execute("UPDATE ocorrencias SET status = 'Nova' WHERE id = %s", (oid,))
        registrar_decisao({
            "ocorrencia_id": oid,
            "acao": "aprovacao_em_lote_desfeita",
            "nota": "Aprovação em lote desfeita pelo síndico",
        }, conn)
        desfeitas.append(oid)
    conn.commit()
    cur.close()
    return {"desfeitas": desfeitas, "total": len(desfeitas)}