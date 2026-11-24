from .conexao import conectar
from .dominio import texto

def _validar(dados):
    """Confere os campos do registro e devolve (erros, valores prontos para gravar)."""
    erros = {}

    ocorrencia_id = texto(dados.get("ocorrenciaId")) or texto(dados.get("ocorrencia_id"))
    if ocorrencia_id is None:
        erros["ocorrenciaId"] = "Ocorrência não encontrada"

    acao = texto(dados.get("acao")) or texto(dados.get("tipo"))
    if acao is None:
        erros["acao"] = "Informe a ação"

    nota = texto(dados.get("nota"))
    if nota is None:
        partes = []
        if texto(dados.get("quemDecidiu")):
            partes.append(f"por {texto(dados.get('quemDecidiu'))}")
        if texto(dados.get("origem")):
            partes.append(f"origem: {texto(dados.get('origem'))}")
        if texto(dados.get("prioridadeSugerida")):
            partes.append(f"prioridade sugerida: {texto(dados.get('prioridadeSugerida'))}")
        if texto(dados.get("prioridadeFinal")):
            partes.append(f"prioridade final: {texto(dados.get('prioridadeFinal'))}")
        if texto(dados.get("motivo")):
            partes.append(f"motivo: {texto(dados.get('motivo'))}")
        if texto(dados.get("responsavel")):
            partes.append(f"responsável: {texto(dados.get('responsavel'))}")
        nota = " ".join(partes) or acao or "Registro"
        nota = nota.strip() or "Registro"

    valores = {
        "ocorrencia_id": ocorrencia_id,
        "acao": acao,
        "nota": nota,
    }
    return erros, valores

def _gravar(conexao, erros, valores):
    """Confere a ocorrência no banco e insere o registro."""
    with conexao.cursor() as cur:
        cur.execute("SELECT 1 FROM ocorrencias WHERE id = %s", (valores["ocorrencia_id"],))
        if cur.fetchone() is None:
            erros["ocorrenciaId"] = "Ocorrência não encontrada"
        if erros:
            return {"ok": False, "erros": erros}
        cur.execute(
            """
            INSERT INTO registros_decisao (ocorrencia_id, acao, nota)
            VALUES (%(ocorrencia_id)s, %(acao)s, %(nota)s)
            RETURNING id, criado_em
            """,
            valores,
        )
        registro_id, criado_em = cur.fetchone()
    return {"ok": True, "registroId": registro_id, "dataHora": criado_em.isoformat() if criado_em else None}

def registrar_decisao(dados, conexao=None):
    """Valida e grava um registro no histórico da ocorrência. Só insere, nunca altera nem apaga."""
    erros, valores = _validar(dados if isinstance(dados, dict) else {})
    if valores["ocorrencia_id"] is None or valores["acao"] is None:
        return {"ok": False, "erros": erros}
    proprio = conexao is None
    if proprio:
        conexao = conectar()
    try:
        resultado = _gravar(conexao, erros, valores)
        if proprio:
            conexao.commit()
        return resultado
    except Exception:
        if proprio:
            conexao.rollback()
        raise
    finally:
        if proprio:
            conexao.close()

def buscar_decisoes(ocorrencia_id, conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, acao, nota, criado_em
        FROM registros_decisao
        WHERE ocorrencia_id = %s
        ORDER BY criado_em ASC
        """,
        (str(ocorrencia_id),),
    )
    linhas = cur.fetchall()
    cur.close()

    decisoes = []
    for id_, acao, nota, criado_em in linhas:
        nota_texto = nota or ""
        rebaixou = "rebaix" in nota_texto.lower()
        decisoes.append({
            "id": str(id_),
            "tipo": acao,
            "acao": acao,
            "nota": nota_texto,
            "rebaixou_travada": rebaixou,
            "criado_em": criado_em.isoformat() if criado_em else None,
        })

    return decisoes