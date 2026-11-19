from datetime import date, datetime

import psycopg2.errors
import pytest

from lib.registrar_decisao import registrar_decisao

VALIDOS = [
    ("entrada", {"quemDecidiu": "sistema", "origem": "morador", "prioridadeSugerida": "urgente"}),
    ("entrada", {"quemDecidiu": "sistema", "origem": "whatsapp_sindico"}),
    ("prioridade_confirmada", {"quemDecidiu": "sindico", "prioridadeSugerida": "urgente", "prioridadeFinal": "urgente"}),
    (
        "prioridade_alterada",
        {"quemDecidiu": "sindico", "prioridadeSugerida": "urgente", "prioridadeFinal": "normal", "motivo": "alarme falso"},
    ),
    ("acao", {"quemDecidiu": "sindico", "acao": "delegar", "responsavel": "zelador", "nota": "levar hoje"}),
    ("acao", {"quemDecidiu": "sindico", "acao": "agendar", "dataAgendada": "2026-12-05"}),
    ("acao", {"quemDecidiu": "sindico", "acao": "eu_mesmo"}),
    ("conclusao", {"quemDecidiu": "sindico"}),
    ("aprovacao_lote", {"quemDecidiu": "sindico", "prioridadeFinal": "normal", "responsavel": "portaria"}),
]

INVALIDOS = [
    ("entrada", {"quemDecidiu": "sistema", "origem": "vizinho"}, {"origem": "Origem inválida"}),
    ("entrada", {"quemDecidiu": "sistema"}, {"origem": "Origem inválida"}),
    (
        "entrada",
        {"quemDecidiu": "sistema", "origem": "morador", "prioridadeSugerida": "critica"},
        {"prioridadeSugerida": "Prioridade inválida"},
    ),
    ("prioridade_confirmada", {"quemDecidiu": "sindico", "prioridadeFinal": "normal"}, {"prioridadeSugerida": "Prioridade inválida"}),
    ("prioridade_confirmada", {"quemDecidiu": "sindico", "prioridadeSugerida": "normal"}, {"prioridadeFinal": "Prioridade inválida"}),
    (
        "prioridade_alterada",
        {"quemDecidiu": "sindico", "prioridadeSugerida": "urgente", "prioridadeFinal": "normal"},
        {"motivo": "Informe o motivo da mudança"},
    ),
    (
        "prioridade_alterada",
        {"quemDecidiu": "sindico", "prioridadeSugerida": "urgente", "prioridadeFinal": "normal", "motivo": "   "},
        {"motivo": "Informe o motivo da mudança"},
    ),
    ("acao", {"quemDecidiu": "sindico"}, {"acao": "Escolha a ação"}),
    ("acao", {"quemDecidiu": "sindico", "acao": "ignorar"}, {"acao": "Escolha a ação"}),
    ("acao", {"quemDecidiu": "sindico", "acao": "delegar"}, {"responsavel": "Escolha o responsável"}),
    ("acao", {"quemDecidiu": "sindico", "acao": "delegar", "responsavel": "vizinho"}, {"responsavel": "Escolha o responsável"}),
    ("acao", {"quemDecidiu": "sindico", "acao": "agendar"}, {"dataAgendada": "Escolha a data do agendamento"}),
    ("acao", {"quemDecidiu": "sindico", "acao": "agendar", "dataAgendada": "05/12/2026"}, {"dataAgendada": "Escolha a data do agendamento"}),
    ("acao", {"quemDecidiu": "sindico", "acao": "agendar", "dataAgendada": "2026-02-30"}, {"dataAgendada": "Escolha a data do agendamento"}),
    ("aprovacao_lote", {"quemDecidiu": "sindico", "prioridadeFinal": "normal"}, {"responsavel": "Escolha o responsável"}),
    ("aprovacao_lote", {"quemDecidiu": "sindico", "responsavel": "zelador"}, {"prioridadeFinal": "Prioridade inválida"}),
    ("conclusao", {}, {"quemDecidiu": "Informe quem decidiu"}),
    ("conclusao", {"quemDecidiu": "robo"}, {"quemDecidiu": "Informe quem decidiu"}),
]


def contar(conexao):
    """Conta os registros gravados no histórico."""
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM registros_decisao")
        return cur.fetchone()[0]


def ler(conexao, coluna):
    """Lê uma coluna do único registro gravado."""
    with conexao.cursor() as cur:
        cur.execute(f"SELECT {coluna} FROM registros_decisao")
        return cur.fetchone()[0]


COMUNS = {"ocorrenciaId": "Ocorrência não encontrada", "quemDecidiu": "Informe quem decidiu"}


@pytest.mark.parametrize(
    "dados, erros",
    [
        (None, {"tipo": "Informe o tipo de registro", **COMUNS}),
        ({}, {"tipo": "Informe o tipo de registro", **COMUNS}),
        ({"tipo": "   "}, {"tipo": "Informe o tipo de registro", **COMUNS}),
        ({"tipo": "apagar"}, {"tipo": "Tipo de registro inválido", **COMUNS}),
        ({"tipo": "apagar", "ocorrenciaId": 1, "quemDecidiu": "sindico"}, {"tipo": "Tipo de registro inválido"}),
        ({"tipo": "conclusao"}, COMUNS),
        ({"tipo": "conclusao", "quemDecidiu": "sindico"}, {"ocorrenciaId": "Ocorrência não encontrada"}),
        ({"tipo": "conclusao", "ocorrenciaId": "abc", "quemDecidiu": "sindico"}, {"ocorrenciaId": "Ocorrência não encontrada"}),
        ({"tipo": "conclusao", "ocorrenciaId": True, "quemDecidiu": "sindico"}, {"ocorrenciaId": "Ocorrência não encontrada"}),
        ({"tipo": "conclusao", "ocorrenciaId": "9" * 5000, "quemDecidiu": "sindico"}, {"ocorrenciaId": "Ocorrência não encontrada"}),
    ],
)
def test_erros_que_nao_precisam_de_banco(dados, erros):
    assert registrar_decisao(dados) == {"ok": False, "erros": erros}


@pytest.mark.parametrize("tipo, campos", VALIDOS)
def test_grava_cada_tipo(conexao, criar_ocorrencia, tipo, campos):
    ocorrencia_id = criar_ocorrencia()
    resposta = registrar_decisao({"tipo": tipo, "ocorrenciaId": ocorrencia_id, **campos}, conexao=conexao)
    assert resposta["ok"] is True
    assert isinstance(resposta["registroId"], int)
    assert datetime.fromisoformat(resposta["dataHora"]).tzinfo is not None
    assert contar(conexao) == 1
    assert ler(conexao, "tipo") == tipo


@pytest.mark.parametrize("tipo, campos, erros", INVALIDOS)
def test_devolve_o_erro_certo_e_nao_grava(conexao, criar_ocorrencia, tipo, campos, erros):
    ocorrencia_id = criar_ocorrencia()
    resposta = registrar_decisao({"tipo": tipo, "ocorrenciaId": ocorrencia_id, **campos}, conexao=conexao)
    assert resposta == {"ok": False, "erros": erros}
    assert contar(conexao) == 0


def test_ocorrencia_que_nao_existe(conexao):
    resposta = registrar_decisao({"tipo": "conclusao", "ocorrenciaId": 999, "quemDecidiu": "sindico"}, conexao=conexao)
    assert resposta == {"ok": False, "erros": {"ocorrenciaId": "Ocorrência não encontrada"}}
    assert contar(conexao) == 0


def test_agendar_grava_a_data(conexao, criar_ocorrencia):
    registrar_decisao(
        {"tipo": "acao", "ocorrenciaId": criar_ocorrencia(), "quemDecidiu": "sindico", "acao": "agendar", "dataAgendada": "2026-12-05"},
        conexao=conexao,
    )
    assert ler(conexao, "data_agendada") == date(2026, 12, 5)


def test_eu_mesmo_cuido_grava_o_sindico_como_responsavel(conexao, criar_ocorrencia):
    registrar_decisao(
        {"tipo": "acao", "ocorrenciaId": criar_ocorrencia(), "quemDecidiu": "sindico", "acao": "eu_mesmo"},
        conexao=conexao,
    )
    assert ler(conexao, "responsavel") == "sindico"


@pytest.mark.parametrize(
    "travada, prioridade_final, esperado",
    [(True, "normal", True), (True, "baixa", True), (True, "urgente", False), (False, "normal", False)],
)
def test_rebaixou_travada_so_quando_a_travada_cai_abaixo_de_urgente(conexao, criar_ocorrencia, travada, prioridade_final, esperado):
    registrar_decisao(
        {
            "tipo": "prioridade_alterada",
            "ocorrenciaId": criar_ocorrencia(travada=travada),
            "quemDecidiu": "sindico",
            "prioridadeSugerida": "urgente",
            "prioridadeFinal": prioridade_final,
            "motivo": "conferido no local",
        },
        conexao=conexao,
    )
    assert ler(conexao, "rebaixou_travada") is esperado


def test_confirmar_uma_travada_nao_marca_rebaixamento(conexao, criar_ocorrencia):
    registrar_decisao(
        {
            "tipo": "prioridade_confirmada",
            "ocorrenciaId": criar_ocorrencia(travada=True),
            "quemDecidiu": "sindico",
            "prioridadeSugerida": "urgente",
            "prioridadeFinal": "urgente",
        },
        conexao=conexao,
    )
    assert ler(conexao, "rebaixou_travada") is False


def test_limpa_caractere_nulo_do_texto_livre(conexao, criar_ocorrencia):
    resposta = registrar_decisao(
        {"tipo": "acao", "ocorrenciaId": criar_ocorrencia(), "quemDecidiu": "sindico", "acao": "delegar", "responsavel": "zelador", "nota": "a\x00b"},
        conexao=conexao,
    )
    assert resposta["ok"] is True
    assert ler(conexao, "nota") == "ab"


def test_nao_confirma_a_transacao_quando_recebe_a_conexao(conexao, criar_ocorrencia):
    registrar_decisao({"tipo": "conclusao", "ocorrenciaId": criar_ocorrencia(), "quemDecidiu": "sindico"}, conexao=conexao)
    conexao.rollback()
    assert contar(conexao) == 0


@pytest.mark.parametrize("comando", ["UPDATE registros_decisao SET nota = 'x'", "DELETE FROM registros_decisao"])
def test_banco_recusa_alterar_ou_apagar_registro(conexao, criar_ocorrencia, comando):
    registrar_decisao({"tipo": "conclusao", "ocorrenciaId": criar_ocorrencia(), "quemDecidiu": "sindico"}, conexao=conexao)
    with pytest.raises(psycopg2.errors.RaiseException):
        with conexao.cursor() as cur:
            cur.execute(comando)
