import json
from types import SimpleNamespace

import pytest

import lib.classificar as classificacao
import lib.classificar_ia as ia
from lib.dominio import PRIORIDADES, RESPONSAVEIS
from lib.regras import REGRAS

AGUA = "a água tá descendo pela parede da garagem desde ontem"
GAS = "tem cheiro de gás no bloco B"
RESPOSTA = {
    "prioridade": "alta",
    "categoria": "manutencao",
    "responsavelSugerido": "zelador",
    "motivo": "vazamento ativo que pode piorar",
}


class ClienteFalso:
    """Imita o cliente da IA: guarda as chamadas e devolve a resposta combinada ou levanta o erro."""

    def __init__(self, texto=None, parada="end_turn", tipo="text", erro=None):
        self.chamadas = []
        self.erro = erro
        self.resposta = SimpleNamespace(stop_reason=parada, content=[SimpleNamespace(type=tipo, text=texto)])
        self.messages = self

    def create(self, **pedido):
        self.chamadas.append(pedido)
        if self.erro:
            raise self.erro
        return self.resposta


def cliente(dados=None, **opcoes):
    return ClienteFalso(json.dumps(dados or RESPOSTA), **opcoes)


def com_ia(monkeypatch, falso):
    monkeypatch.setattr(ia, "_cliente", lambda: falso)
    return falso


def test_devolve_os_campos_do_contrato_com_fonte_ia():
    assert ia.classificar_com_ia(AGUA, cliente()) == {
        "prioridade": "alta",
        "categoria": "manutencao",
        "responsavel": "zelador",
        "motivo": "vazamento ativo que pode piorar",
        "travada": False,
        "palavraDeRisco": None,
        "responsavelSugerido": "zelador",
        "responsavel_sugerido": "zelador",
        "palavra_de_risco": None,
        "fonte": "ia",
    }


def test_envia_so_a_descricao():
    falso = cliente()
    ia.classificar_com_ia(AGUA, falso)
    assert falso.chamadas[0]["messages"] == [{"role": "user", "content": AGUA}]


def test_pede_a_resposta_no_formato_do_contrato():
    falso = cliente()
    ia.classificar_com_ia(AGUA, falso)
    pedido = falso.chamadas[0]["output_config"]
    esquema = pedido["format"]["schema"]
    assert pedido["format"]["type"] == "json_schema"
    assert esquema["properties"]["prioridade"]["enum"] == list(PRIORIDADES)
    assert esquema["properties"]["responsavelSugerido"]["enum"] == list(RESPONSAVEIS)
    assert set(esquema["required"]) == {"prioridade", "categoria", "responsavelSugerido", "motivo"}
    assert esquema["additionalProperties"] is False


def test_o_sdk_envia_so_a_descricao_e_le_a_resposta():
    anthropic = pytest.importorskip("anthropic")
    httpx2 = pytest.importorskip("httpx2")
    recebidos = []

    def responder(requisicao):
        recebidos.append(json.loads(requisicao.content))
        return httpx2.Response(
            200,
            json={
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-5-5",
                "content": [{"type": "text", "text": json.dumps(RESPOSTA)}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    sdk = anthropic.Anthropic(
        api_key="chave-de-teste", max_retries=0, http_client=httpx2.Client(transport=httpx2.MockTransport(responder))
    )
    assert ia.classificar_com_ia(AGUA, sdk)["fonte"] == "ia"
    assert recebidos[0]["messages"] == [{"role": "user", "content": AGUA}]
    assert set(recebidos[0]) == {"model", "max_tokens", "system", "messages", "output_config"}


def test_instrucoes_trazem_a_tabela_do_po():
    for regra in REGRAS:
        assert all(palavra in ia.INSTRUCOES for palavra in regra.palavras)


def test_usa_o_modelo_padrao_e_aceita_trocar_pela_variavel(monkeypatch):
    monkeypatch.delenv("IA_MODELO", raising=False)
    padrao = cliente()
    ia.classificar_com_ia(AGUA, padrao)
    monkeypatch.setenv("IA_MODELO", "claude-haiku-5-5")
    trocado = cliente()
    ia.classificar_com_ia(AGUA, trocado)
    assert (padrao.chamadas[0]["model"], trocado.chamadas[0]["model"]) == ("claude-opus-5-5", "claude-haiku-5-5")


def test_motivo_vem_sem_espacos_nas_pontas_e_com_no_maximo_300_caracteres():
    resultado = ia.classificar_com_ia(AGUA, cliente({**RESPOSTA, "motivo": "  " + "a" * 400 + "  "}))
    assert resultado["motivo"] == "a" * 300


@pytest.mark.parametrize(
    "falso",
    [
        ClienteFalso("isso não é json"),
        ClienteFalso("[]"),
        ClienteFalso(json.dumps({**RESPOSTA, "prioridade": "critica"})),
        ClienteFalso(json.dumps({**RESPOSTA, "categoria": "limpeza"})),
        ClienteFalso(json.dumps({**RESPOSTA, "responsavelSugerido": "porteiro"})),
        ClienteFalso(json.dumps({**RESPOSTA, "motivo": ""})),
        ClienteFalso(json.dumps({**RESPOSTA, "motivo": "   "})),
        ClienteFalso(json.dumps({**RESPOSTA, "motivo": None})),
        ClienteFalso(json.dumps({"prioridade": "alta"})),
        ClienteFalso(json.dumps(RESPOSTA), parada="refusal"),
        ClienteFalso(json.dumps(RESPOSTA), parada="max_tokens"),
        ClienteFalso(json.dumps(RESPOSTA), tipo="thinking"),
        ClienteFalso(erro=TimeoutError("demorou")),
        ClienteFalso(erro=ConnectionError("fora do ar")),
    ],
)
def test_resposta_invalida_ou_erro_devolve_none(falso):
    assert ia.classificar_com_ia(AGUA, falso) is None


@pytest.mark.parametrize("texto", ["", "   ", None, 5])
def test_texto_sem_conteudo_nem_chama_a_ia(texto):
    falso = cliente()
    assert ia.classificar_com_ia(texto, falso) is None
    assert falso.chamadas == []


def test_fica_desligada_por_padrao(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-de-teste")
    monkeypatch.setattr(ia, "_criar_cliente", lambda: pytest.fail("não podia criar o cliente"))
    assert ia.classificar_com_ia(AGUA) is None


def test_ligada_sem_chave_nao_chama_a_ia(monkeypatch):
    monkeypatch.setenv("IA_ATIVA", "true")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(ia, "_criar_cliente", lambda: pytest.fail("não podia criar o cliente"))
    assert ia.classificar_com_ia(AGUA) is None


def test_ligada_com_chave_usa_o_cliente_criado(monkeypatch):
    monkeypatch.setenv("IA_ATIVA", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-de-teste")
    monkeypatch.setattr(ia, "_criar_cliente", lambda: cliente())
    assert ia.classificar_com_ia(AGUA)["fonte"] == "ia"


def test_classificar_usa_a_ia_quando_ela_responde(monkeypatch):
    com_ia(monkeypatch, cliente())
    resultado = classificacao.classificar(AGUA)
    assert (resultado["prioridade"], resultado["categoria"], resultado["responsavelSugerido"]) == (
        "alta",
        "manutencao",
        "zelador",
    )
    assert resultado["motivo"] == "vazamento ativo que pode piorar"
    assert resultado["fonte"] == "ia"
    assert resultado["travada"] is False


def test_a_trava_de_risco_vence_a_ia(monkeypatch):
    com_ia(monkeypatch, cliente({**RESPOSTA, "prioridade": "baixa", "responsavelSugerido": "portaria"}))
    resultado = classificacao.classificar(GAS)
    assert resultado["prioridade"] == "urgente"
    assert resultado["travada"] is True
    assert resultado["palavraDeRisco"] == "gás"
    assert resultado["responsavelSugerido"] == "sindico"
    assert resultado["motivo"] == "palavra de risco: gás"


def test_risco_com_categoria_nao_reconhecida_ganha_a_categoria_das_regras(monkeypatch):
    com_ia(monkeypatch, cliente({**RESPOSTA, "categoria": "nao_reconhecida"}))
    assert classificacao.classificar(GAS)["categoria"] == "manutencao"


def test_sem_resposta_da_ia_valem_as_regras(monkeypatch):
    com_ia(monkeypatch, ClienteFalso(erro=ConnectionError("fora do ar")))
    resultado = classificacao.classificar("lâmpada do hall queimada")
    assert resultado == classificacao.classificar_por_regras("lâmpada do hall queimada")
    assert resultado["fonte"] == "regras"
