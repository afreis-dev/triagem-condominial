from .conexao import conectar
from .dominio import texto

TIPOS_VALIDOS = {
    "entrada",
    "acao",
    "conclusao",
    "prioridade_alterada",
    "aprovacao_lote",
    "desfazer_aprovacao_lote",
    "delegar",
    "agendar",
    "eu_mesmo",
}

def _p(dados, *chaves):
    for k in chaves:
        v = texto(dados.get(k))
        if v is not None:
            return v
    return None

def _validar_ocorrencia_id(valor_bruto):
    """Valida sem tocar no banco. Retorna (id_int ou None, erro ou None)."""
    # bool é int no Python — tem que rejeitar True/False
    if isinstance(valor_bruto, bool):
        return None, "Ocorrência não encontrada"
    if isinstance(valor_bruto, int):
        if 1 <= valor_bruto <= 2147483647:
            return valor_bruto, None
        return None, "Ocorrência não encontrada"
    if isinstance(valor_bruto, str):
        s = valor_bruto.strip()
        # "abc" -> erro, "9"*5000 -> erro (longo demais, nem tenta o banco)
        if s.isdigit() and 1 <= len(s) <= 9:
            n = int(s)
            if 1 <= n <= 2147483647:
                return n, None
    return None, "Ocorrência não encontrada"

def _validar(dados):
    erros = {}

    # --- tipo: chave tem que ser "tipo", não "acao", pro teste passar ---
    tipo = _p(dados, "tipo", "acao")
    if tipo is None:
        erros["tipo"] = "Informe o tipo de registro"
    elif tipo not in TIPOS_VALIDOS:
        erros["tipo"] = "Tipo de registro inválido"

    # --- ocorrenciaId: valida sem banco ---
    ocorrencia_id, erro_id = _validar_ocorrencia_id(dados.get("ocorrenciaId", dados.get("ocorrencia_id")))
    if erro_id:
        erros["ocorrenciaId"] = erro_id

    # --- quemDecidiu: obrigatório ---
    quem = _p(dados, "quemDecidiu", "quem_decidiu")
    if quem is None:
        erros["quemDecidiu"] = "Informe quem decidiu"

    nota = _p(dados, "nota")
    if nota is None:
        partes = []
        if quem:
            partes.append(f"por {quem}")
        if _p(dados, "origem"):
            partes.append(f"origem: {_p(dados, 'origem')}")
        if _p(dados, "prioridadeSugerida", "prioridade_sugerida"):
            partes.append(f"prioridade sugerida: {_p(dados, 'prioridadeSugerida', 'prioridade_sugerida')}")
        if _p(dados, "prioridadeFinal", "prioridade_final"):
            partes.append(f"prioridade final: {_p(dados, 'prioridadeFinal', 'prioridade_final')}")
        if _p(dados, "motivo"):
            partes.append(f"motivo: {_p(dados, 'motivo')}")
        if _p(dados, "responsavel"):
            partes.append(f"responsável: {_p(dados, 'responsavel')}")
        nota = " ".join(partes) or tipo or "Registro"
        nota = nota.strip() or "Registro"

    valores = {
        "ocorrencia_id": ocorrencia_id,
        "tipo": tipo,
        "quem_decidiu": quem,
        "origem": _p(dados, "origem"),
        "prioridade_sugerida": _p(dados, "prioridadeSugerida", "prioridade_sugerida"),
        "prioridade_final": _p(dados, "prioridadeFinal", "prioridade_final"),
        "motivo": _p(dados, "motivo"),
        "acao": tipo,  # espelha tipo em acao pro histórico
        "responsavel": _p(dados, "responsavel"),
        "data_agendada": dados.get("dataAgendada") or dados.get("data_agendada"),
        "nota": nota,
        "rebaixou_travada": dados.get("rebaixouTravada", dados.get("rebaixou_travada", False)),
    }
    return erros, valores

def _gravar(conexao, erros, valores):
    with conexao.cursor() as cur:
        cur.execute("SELECT 1 FROM ocorrencias WHERE id = %s", (valores["ocorrencia_id"],))
        if cur.fetchone() is None:
            erros["ocorrenciaId"] = "Ocorrência não encontrada"
        if erros:
            return {"ok": False, "erros": erros}
        cur.execute(
            """
            INSERT INTO registros_decisao
                (ocorrencia_id, tipo, quem_decidiu, origem,
                 prioridade_sugerida, prioridade_final, motivo,
                 acao, responsavel, data_agendada, nota, rebaixou_travada)
            VALUES
                (%(ocorrencia_id)s, %(tipo)s, %(quem_decidiu)s, %(origem)s,
                 %(prioridade_sugerida)s, %(prioridade_final)s, %(motivo)s,
                 %(acao)s, %(responsavel)s, %(data_agendada)s, %(nota)s, %(rebaixou_travada)s)
            RETURNING id, data_hora
            """,
            valores,
        )
        registro_id, data_hora = cur.fetchone()
    return {"ok": True, "registroId": registro_id, "dataHora": data_hora.isoformat() if data_hora else None}

def registrar_decisao(dados, conexao=None):
    """Valida e grava um registro no histórico. Só insere, nunca altera nem apaga."""
    erros, valores = _validar(dados if isinstance(dados, dict) else {})
    # Se tem erro de validação, volta SEM conectar no banco
    if erros:
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

def buscar_decisoes(ocorrencia_id: int, conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, ocorrencia_id, tipo, quem_decidiu,
                   origem, prioridade_sugerida, prioridade_final,
                   motivo, acao, responsavel, data_agendada,
                   nota, rebaixou_travada, data_hora
            FROM registros_decisao
            WHERE ocorrencia_id = %s
            ORDER BY data_hora ASC, id ASC
            """,
            (ocorrencia_id,),
        )
        linhas = cur.fetchall()
    return [
        {
            "id": linha[0],
            "ocorrenciaId": linha[1],
            "tipo": linha[2],
            "quemDecidiu": linha[3],
            "origem": linha[4],
            "prioridadeSugerida": linha[5],
            "prioridadeFinal": linha[6],
            "motivo": linha[7],
            "acao": linha[8],
            "responsavel": linha[9],
            "dataAgendada": linha[10].isoformat() if linha[10] else None,
            "nota": linha[11],
            "rebaixouTravada": linha[12],
            "dataHora": linha[13].isoformat() if linha[13] else None,
        }
        for linha in linhas
    ]