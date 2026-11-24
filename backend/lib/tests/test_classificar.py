import pytest

from lib.classificar import classificar, normalizar
from lib.dominio import CATEGORIAS, PRIORIDADES, RESPONSAVEIS
from lib.regras import REGRAS

CHAVES = {"prioridade", "categoria", "responsavelSugerido", "motivo", "travada", "palavraDeRisco", "fonte"}

EXEMPLOS_DO_CONTRATO = [
    ("lâmpada do hall queimada", "normal", "manutencao", "zelador", "manutenção simples de área comum", False, None),
    ("barulho no salão e falta de água no bloco A", "alta", "manutencao", "zelador", "falta de água afeta muitos moradores", False, None),
    ("tem cheiro de gás no bloco B", "urgente", "manutencao", "sindico", "palavra de risco: gás", True, "gás"),
    ("a lâmpada queimou e está com cheiro de gás", "urgente", "manutencao", "sindico", "palavra de risco: gás", True, "gás"),
    ("teste asdf", "normal", "nao_reconhecida", "sindico", "não reconhecida, revisar", False, None),
]


def campos_do_contrato(resposta):
    """Separa da resposta só os sete campos que o contrato define."""
    return {chave: resposta[chave] for chave in CHAVES}


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
    assert campos_do_contrato(classificar("lâmpada do hall queimada")) == {
        "prioridade": "normal",
        "categoria": "manutencao",
        "responsavelSugerido": "zelador",
        "motivo": "manutenção simples de área comum",
        "travada": False,
        "palavraDeRisco": None,
        "fonte": "regras",
    }


@pytest.mark.parametrize("texto, prioridade, categoria, responsavel, motivo, travada, palavra", EXEMPLOS_DO_CONTRATO)
def test_os_exemplos_do_contrato_devolvem_os_sete_campos(texto, prioridade, categoria, responsavel, motivo, travada, palavra):
    assert campos_do_contrato(classificar(texto)) == {
        "prioridade": prioridade,
        "categoria": categoria,
        "responsavelSugerido": responsavel,
        "motivo": motivo,
        "travada": travada,
        "palavraDeRisco": palavra,
        "fonte": "regras",
    }


def test_luz_queimada_no_hall_acha_a_regra_da_lampada():
    resposta = classificar("luz queimada no hall")
    assert resposta["categoria"] == "manutencao"
    assert resposta["motivo"] == "manutenção simples de área comum"


def test_acha_a_palavra_com_maiuscula_acento_e_pontuacao():
    assert classificar("LAMPADA queimada!!!")["motivo"] == "manutenção simples de área comum"
    assert classificar("Tá faltando Água? SEM ÁGUA desde cedo")["prioridade"] == "alta"


def test_o_motivo_vem_da_regra_encontrada():
    resposta = classificar("tem barulho depois das 22h")
    assert resposta["categoria"] == "convivencia"
    assert resposta["responsavelSugerido"] == "sindico"
    assert resposta["motivo"] == "conflito entre moradores, sem risco imediato"


def test_a_palavra_precisa_aparecer_inteira():
    assert classificar("a lampadinha do poste")["categoria"] == "nao_reconhecida"
    assert classificar("o gasto do condomínio subiu")["travada"] is False


def test_regra_de_maior_prioridade_vence_a_de_menor():
    resposta = classificar("barulho no salão e falta de água no bloco A")
    assert resposta["prioridade"] == "alta"
    assert resposta["motivo"] == "falta de água afeta muitos moradores"


@pytest.mark.parametrize("texto", ["furto na garagem e vazamento no teto", "vazamento no teto e furto na garagem"])
def test_empate_de_prioridade_vale_a_primeira_regra_da_tabela(texto):
    resposta = classificar(texto)
    assert resposta["categoria"] == "manutencao"
    assert resposta["responsavelSugerido"] == "zelador"


@pytest.mark.parametrize("regra", REGRAS, ids=lambda regra: regra.palavras[0])
def test_cada_palavra_da_tabela_encontra_a_propria_regra(regra):
    for palavra in regra.palavras:
        assert classificar(f"aviso sobre {palavra} no bloco A")["motivo"] == regra.motivo


def test_a_resposta_tem_os_campos_e_valores_do_contrato():
    for regra in REGRAS:
        resposta = classificar(regra.palavras[0])
        assert CHAVES <= set(resposta)
        assert resposta["prioridade"] in PRIORIDADES
        assert resposta["categoria"] in CATEGORIAS
        assert resposta["responsavelSugerido"] in RESPONSAVEIS
        assert resposta["travada"] is False
        assert resposta["palavraDeRisco"] is None
        assert resposta["fonte"] == "regras"
