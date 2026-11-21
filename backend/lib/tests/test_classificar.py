import pytest

from lib.classificar import classificar, normalizar
from lib.dominio import CATEGORIAS, PRIORIDADES, RESPONSAVEIS
from lib.regras import REGRAS

CHAVES = {"prioridade", "categoria", "responsavelSugerido", "motivo", "travada", "palavraDeRisco", "fonte"}


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("FUMAÇA no corredor!!!", "fumaca no corredor"),
        ("  Bomba d'água   queimou ", "bomba d agua queimou"),
        ("Açaí, Ñandú e Pão", "acai nandu e pao"),
        ("", ""),
        ("   ", ""),
        (None, ""),
        (5, ""),
    ],
)
def test_normalizar(texto, esperado):
    assert normalizar(texto) == esperado


def test_lampada_do_hall_queimada_devolve_a_regra_do_po():
    assert classificar("lâmpada do hall queimada") == {
        "prioridade": "normal",
        "categoria": "manutencao",
        "responsavelSugerido": "zelador",
        "motivo": "manutenção simples de área comum",
        "travada": False,
        "palavraDeRisco": None,
        "fonte": "regras",
    }


def test_acha_a_palavra_com_maiuscula_acento_e_pontuacao():
    assert classificar("LAMPADA queimada!!!")["motivo"] == "manutenção simples de área comum"
    assert classificar("Tá faltando Água? SEM ÁGUA desde cedo")["prioridade"] == "alta"


def test_o_motivo_vem_da_regra_encontrada():
    resposta = classificar("tem barulho depois das 22h")
    assert resposta["categoria"] == "convivencia"
    assert resposta["responsavelSugerido"] == "sindico"
    assert resposta["motivo"] == "conflito entre moradores, sem risco imediato"


def test_a_palavra_precisa_aparecer_inteira():
    with pytest.raises(LookupError):
        classificar("a lampadinha do poste")


@pytest.mark.parametrize("regra", REGRAS, ids=lambda regra: regra.palavras[0])
def test_cada_palavra_da_tabela_encontra_a_propria_regra(regra):
    for palavra in regra.palavras:
        assert classificar(f"aviso sobre {palavra} no bloco A")["motivo"] == regra.motivo


def test_a_resposta_so_tem_os_campos_e_valores_do_contrato():
    for regra in REGRAS:
        resposta = classificar(regra.palavras[0])
        assert set(resposta) == CHAVES
        assert resposta["prioridade"] in PRIORIDADES
        assert resposta["categoria"] in CATEGORIAS
        assert resposta["responsavelSugerido"] in RESPONSAVEIS
        assert resposta["travada"] is False
        assert resposta["palavraDeRisco"] is None
        assert resposta["fonte"] == "regras"


def test_texto_sem_regra_ainda_nao_e_tratado():
    with pytest.raises(LookupError):
        classificar("teste asdf")
