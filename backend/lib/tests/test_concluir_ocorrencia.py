from datetime import datetime

import pytest

from lib.concluir_ocorrencia import concluir_ocorrencia


def ocorrencia(conexao, ocorrencia_id):
    """Lê status e data de conclusão da ocorrência."""
    with conexao.cursor() as cur:
        cur.execute("SELECT status, concluida_em FROM ocorrencias WHERE id = %s", (ocorrencia_id,))
        return cur.fetchone()


def registros(conexao):
    """Lê tipo e quem decidiu de todos os registros do histórico."""
    with conexao.cursor() as cur:
        cur.execute("SELECT tipo, quem_decidiu FROM registros_decisao ORDER BY id")
        return cur.fetchall()


def test_conclui_a_ocorrencia_em_andamento(conexao, criar_ocorrencia):
    ocorrencia_id = criar_ocorrencia(status="em_andamento")
    resposta = concluir_ocorrencia(ocorrencia_id, conexao=conexao)
    assert resposta["ok"] is True
    assert resposta["ocorrenciaId"] == ocorrencia_id
    assert datetime.fromisoformat(resposta["concluidaEm"]).tzinfo is not None
    status, concluida_em = ocorrencia(conexao, ocorrencia_id)
    assert status == "concluida"
    assert concluida_em is not None
    assert registros(conexao) == [("conclusao", "sindico")]


@pytest.mark.parametrize("status", ["nova", "concluida"])
def test_so_conclui_quem_esta_em_andamento(conexao, criar_ocorrencia, status):
    ocorrencia_id = criar_ocorrencia(status=status)
    resposta = concluir_ocorrencia(ocorrencia_id, conexao=conexao)
    assert resposta == {"ok": False, "erros": {"status": "Só dá para concluir uma ocorrência em andamento"}}
    assert ocorrencia(conexao, ocorrencia_id) == (status, None)
    assert registros(conexao) == []


def test_ocorrencia_que_nao_existe(conexao):
    assert concluir_ocorrencia(999, conexao=conexao) == {
        "ok": False,
        "erros": {"ocorrenciaId": "Ocorrência não encontrada"},
    }


def test_nao_confirma_a_transacao_quando_recebe_a_conexao(conexao, criar_ocorrencia):
    ocorrencia_id = criar_ocorrencia(status="em_andamento")
    concluir_ocorrencia(ocorrencia_id, conexao=conexao)
    conexao.rollback()
    assert ocorrencia(conexao, ocorrencia_id) == ("em_andamento", None)
    assert registros(conexao) == []


@pytest.mark.parametrize("valor", [None, "abc", 0, -1, True, 2**40, "9" * 5000])
def test_id_invalido_nao_precisa_de_banco(valor):
    assert concluir_ocorrencia(valor) == {"ok": False, "erros": {"ocorrenciaId": "Ocorrência não encontrada"}}


def test_aceita_o_id_como_texto(conexao, criar_ocorrencia):
    ocorrencia_id = criar_ocorrencia(status="em_andamento")
    assert concluir_ocorrencia(str(ocorrencia_id), conexao=conexao)["ok"] is True
