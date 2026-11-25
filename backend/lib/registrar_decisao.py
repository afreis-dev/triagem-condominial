import re
from datetime import date

from .conexao import conectar
from .dominio import ORIGENS, PRIORIDADES, RESPONSAVEIS, inteiro, texto

TIPOS = ("entrada", "prioridade_confirmada", "prioridade_alterada", "acao", "conclusao", "aprovacao_lote")
QUEM_DECIDIU = ("sistema", "sindico")
ACOES = ("delegar", "agendar", "eu_mesmo")
CAMPOS = (
    "ocorrencia_id", "tipo", "quem_decidiu", "origem", "prioridade_sugerida", "prioridade_final",
    "motivo", "acao", "responsavel", "data_agendada", "nota", "rebaixou_travada",
)

INSERIR = """
    INSERT INTO registros_decisao
        (ocorrencia_id, tipo, quem_decidiu, origem, prioridade_sugerida, prioridade_final,
         motivo, acao, responsavel, data_agendada, nota, rebaixou_travada)
    VALUES
        (%(ocorrencia_id)s, %(tipo)s, %(quem_decidiu)s, %(origem)s, %(prioridade_sugerida)s,
         %(prioridade_final)s, %(motivo)s, %(acao)s, %(responsavel)s, %(data_agendada)s,
         %(nota)s, %(rebaixou_travada)s)
    RETURNING id, data_hora
"""


def _data(valor):
    """Converte AAAA-MM-DD em date, ou devolve None se a data for inválida."""
    if isinstance(valor, date):
        return valor
    valor = texto(valor)
    if valor is None or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", valor):
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None


def _prioridade(dados, chave, erros, obrigatoria=True):
    """Lê uma prioridade do registro e anota o erro se ela estiver vazia ou fora da lista."""
    valor = texto(dados.get(chave))
    if valor is None and not obrigatoria:
        return None
    if valor not in PRIORIDADES:
        erros[chave] = "Prioridade inválida"
        return None
    return valor


def _validar_acao(dados, erros, valores):
    """Valida os campos do registro de ação: delegar, agendar ou eu mesmo cuido."""
    acao = texto(dados.get("acao"))
    valores["acao"] = acao
    valores["nota"] = texto(dados.get("nota"))
    if acao not in ACOES:
        erros["acao"] = "Escolha a ação"
    elif acao == "delegar":
        valores["responsavel"] = texto(dados.get("responsavel"))
        if valores["responsavel"] not in RESPONSAVEIS:
            erros["responsavel"] = "Escolha o responsável"
    elif acao == "agendar":
        valores["data_agendada"] = _data(dados.get("dataAgendada"))
        if valores["data_agendada"] is None:
            erros["dataAgendada"] = "Escolha a data do agendamento"
    else:
        valores["responsavel"] = "sindico"


def _validar(dados):
    """Confere os campos do registro e devolve (erros, valores prontos para gravar)."""
    erros = {}
    valores = dict.fromkeys(CAMPOS)
    valores["rebaixou_travada"] = False
    valores["ocorrencia_id"] = inteiro(dados.get("ocorrenciaId"))
    if valores["ocorrencia_id"] is None:
        erros["ocorrenciaId"] = "Ocorrência não encontrada"
    valores["quem_decidiu"] = texto(dados.get("quemDecidiu"))
    if valores["quem_decidiu"] not in QUEM_DECIDIU:
        erros["quemDecidiu"] = "Informe quem decidiu"

    tipo = texto(dados.get("tipo"))
    if tipo is None:
        erros["tipo"] = "Informe o tipo de registro"
    elif tipo not in TIPOS:
        erros["tipo"] = "Tipo de registro inválido"
    if "tipo" in erros:
        return erros, None
    valores["tipo"] = tipo

    if tipo == "entrada":
        valores["origem"] = texto(dados.get("origem"))
        if valores["origem"] not in ORIGENS:
            erros["origem"] = "Origem inválida"
        valores["prioridade_sugerida"] = _prioridade(dados, "prioridadeSugerida", erros, obrigatoria=False)
    elif tipo in ("prioridade_confirmada", "prioridade_alterada"):
        valores["prioridade_sugerida"] = _prioridade(dados, "prioridadeSugerida", erros)
        valores["prioridade_final"] = _prioridade(dados, "prioridadeFinal", erros)
        if tipo == "prioridade_alterada":
            valores["motivo"] = texto(dados.get("motivo"))
            if valores["motivo"] is None:
                erros["motivo"] = "Informe o motivo da mudança"
    elif tipo == "acao":
        _validar_acao(dados, erros, valores)
    elif tipo == "aprovacao_lote":
        valores["prioridade_final"] = _prioridade(dados, "prioridadeFinal", erros)
        valores["responsavel"] = texto(dados.get("responsavel"))
        if valores["responsavel"] not in RESPONSAVEIS:
            erros["responsavel"] = "Escolha o responsável"
    return erros, valores


def _gravar(conexao, erros, valores):
    """Confere a ocorrência no banco e insere o registro."""
    with conexao.cursor() as cur:
        cur.execute("SELECT travada FROM ocorrencias WHERE id = %s FOR SHARE", (valores["ocorrencia_id"],))
        ocorrencia = cur.fetchone()
        if ocorrencia is None:
            erros["ocorrenciaId"] = "Ocorrência não encontrada"
        if erros:
            return {"ok": False, "erros": erros}
        valores["rebaixou_travada"] = (
            valores["tipo"] == "prioridade_alterada"
            and bool(ocorrencia[0])
            and valores["prioridade_final"] != "urgente"
        )
        cur.execute(INSERIR, valores)
        registro_id, data_hora = cur.fetchone()
    return {"ok": True, "registroId": registro_id, "dataHora": data_hora.isoformat()}


def registrar_decisao(dados, conexao=None):
    """Valida e grava um registro no histórico da ocorrência. Só insere, nunca altera nem apaga."""
    erros, valores = _validar(dados if isinstance(dados, dict) else {})
    if valores is None or valores["ocorrencia_id"] is None:
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
    """Consulta os registros de decisão em ordem cronológica."""
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
            "dataHora": linha[13].isoformat(),
        }
        for linha in linhas
    ]
