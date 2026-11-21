import pytest

import lib.classificar as modulo
from lib.classificar import classificar, normalizar
from lib.dominio import CATEGORIAS, PRIORIDADES, RESPONSAVEIS
from lib.regras import REGRAS, Regra
from lib.salvar_ocorrencia import salvar_ocorrencia

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


def test_texto_com_duas_regras_usa_a_de_maior_prioridade():
    resposta = classificar("barulho no salão e falta de água no bloco A")
    assert resposta["prioridade"] == "alta"
    assert resposta["motivo"] == "falta de água afeta muitos moradores"


def test_a_ordem_das_palavras_no_texto_nao_muda_o_resultado():
    assert classificar("falta de água no bloco A e barulho no salão") == classificar(
        "barulho no salão e falta de água no bloco A"
    )


def test_no_empate_vale_a_primeira_regra_da_tabela():
    assert classificar("cachorro latindo e barulho")["motivo"] == "conflito entre moradores, sem risco imediato"


def test_maior_prioridade_vale_mesmo_com_a_regra_depois_na_tabela(monkeypatch):
    baixa = Regra(("reserva",), "pedido_administrativo", "baixa", "sindico", "pedido simples")
    alta = Regra(("goteira",), "manutencao", "alta", "zelador", "vazamento ativo")
    monkeypatch.setattr(modulo, "REGRAS_NORMALIZADAS", ((("reserva",), baixa), (("goteira",), alta)))
    assert classificar("reserva do salão e goteira no teto")["motivo"] == "vazamento ativo"


def test_a_palavra_precisa_aparecer_inteira():
    assert classificar("a lampadinha do poste")["motivo"] == "não reconhecida, revisar"


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


def test_texto_sem_regra_devolve_normal_e_pede_revisao():
    assert classificar("teste asdf") == {
        "prioridade": "normal",
        "categoria": "duvida",
        "responsavelSugerido": "sindico",
        "motivo": "não reconhecida, revisar",
        "travada": False,
        "palavraDeRisco": None,
        "fonte": "regras",
    }


@pytest.mark.parametrize("texto", ["", "   ", None, 123, "!!! ???"])
def test_texto_vazio_ou_sem_palavras_tambem_cai_em_nao_reconhecida(texto):
    assert classificar(texto)["motivo"] == "não reconhecida, revisar"


def test_resposta_de_texto_sem_regra_segue_o_contrato():
    resposta = classificar("teste asdf")
    assert set(resposta) == CHAVES
    assert resposta["categoria"] in CATEGORIAS
    assert resposta["responsavelSugerido"] in RESPONSAVEIS


def test_cada_chamada_devolve_um_dicionario_novo():
    classificar("teste asdf")["prioridade"] = "urgente"
    assert classificar("teste asdf")["prioridade"] == "normal"


def guardado(conexao, ocorrencia_id):
    """Lê a classificação guardada na ocorrência."""
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT prioridade, categoria, responsavel_sugerido, motivo, fonte FROM ocorrencias WHERE id = %s",
            (ocorrencia_id,),
        )
        return cur.fetchone()


@pytest.mark.parametrize(
    "descricao, esperado",
    [
        ("lâmpada do hall queimada", ("normal", "manutencao", "zelador", "manutenção simples de área comum", "regras")),
        ("teste asdf", ("normal", "duvida", "sindico", "não reconhecida, revisar", "regras")),
    ],
)
def test_salvar_ocorrencia_guarda_a_classificacao_de_verdade(conexao, condominio, descricao, esperado):
    dados = {"condominioId": condominio, "origem": "morador", "celular": "81999998888", "descricao": descricao}
    resposta = salvar_ocorrencia(dados, conexao=conexao)
    assert resposta["ok"] is True
    assert guardado(conexao, resposta["ocorrenciaId"]) == esperado
