from lib.dominio import CATEGORIAS, PRIORIDADES, RESPONSAVEIS
from lib.regras import REGRAS


def test_tem_as_28_regras_do_po():
    assert len(REGRAS) == 28


def test_cada_regra_tem_todos_os_campos_com_valores_permitidos():
    for regra in REGRAS:
        assert regra.palavras
        assert all(isinstance(palavra, str) and palavra.strip() for palavra in regra.palavras)
        assert regra.categoria in CATEGORIAS
        assert regra.prioridade in PRIORIDADES
        assert regra.responsavel in RESPONSAVEIS
        assert regra.motivo.strip()


def test_nenhuma_palavra_aparece_em_duas_regras():
    palavras = [palavra for regra in REGRAS for palavra in regra.palavras]
    assert len(palavras) == len(set(palavras))


def test_regra_da_lampada_bate_com_a_lista_do_po():
    regra = next(regra for regra in REGRAS if "lâmpada" in regra.palavras)
    assert regra.palavras == ("lâmpada", "luz queimada", "lâmpada queimada")
    assert (regra.categoria, regra.prioridade, regra.responsavel) == ("manutencao", "normal", "zelador")
    assert regra.motivo == "manutenção simples de área comum"


def test_regra_da_falta_de_agua_e_alta():
    regra = next(regra for regra in REGRAS if "falta de água" in regra.palavras)
    assert regra.prioridade == "alta"
    assert regra.motivo == "falta de água afeta muitos moradores"
