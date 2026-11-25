import json
import threading
import time
from types import SimpleNamespace

import pytest

import lib.classificar as classificacao
import lib.classificar_ia as ia
from lib.dominio import PRIORIDADES, RESPONSAVEIS
from lib.regras import REGRAS
from lib.salvar_ocorrencia import salvar_ocorrencia

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

    def __init__(self, texto=None, status="completed", erro=None):
        self.chamadas = []
        self.erro = erro
        self.resposta = SimpleNamespace(status=status, output_text=texto)
        self.interactions = self

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
    assert falso.chamadas[0]["input"] == AGUA


def test_pede_a_resposta_no_formato_do_contrato():
    falso = cliente()
    ia.classificar_com_ia(AGUA, falso)
    pedido = falso.chamadas[0]["response_format"]
    esquema = pedido["schema"]
    assert (pedido["type"], pedido["mime_type"]) == ("text", "application/json")
    assert esquema["properties"]["prioridade"]["enum"] == list(PRIORIDADES)
    assert esquema["properties"]["responsavelSugerido"]["enum"] == list(RESPONSAVEIS)
    assert set(esquema["required"]) == {"prioridade", "categoria", "responsavelSugerido", "motivo"}
    assert esquema["additionalProperties"] is False


def test_o_sdk_envia_so_a_descricao_e_le_a_resposta():
    genai = pytest.importorskip("google.genai")
    httpx2 = pytest.importorskip("httpx2")
    recebidos = []

    def responder(requisicao):
        recebidos.append((requisicao.headers["x-goog-api-key"], json.loads(requisicao.content)))
        return httpx2.Response(
            200,
            json={
                "id": "interacao_1",
                "status": "completed",
                "created": "2026-11-25T10:00:00Z",
                "model": "gemini-3.5-flash-lite",
                "steps": [
                    {"type": "user_input", "content": [{"type": "text", "text": AGUA}]},
                    {"type": "model_output", "content": [{"type": "text", "text": json.dumps(RESPOSTA)}]},
                ],
            },
        )

    sdk = genai.Client(
        api_key="chave-de-teste",
        http_options=genai.types.HttpOptions(httpx_client=httpx2.Client(transport=httpx2.MockTransport(responder))),
    )
    assert ia.classificar_com_ia(AGUA, sdk)["fonte"] == "ia"
    chave, corpo = recebidos[0]
    assert chave == "chave-de-teste"
    assert corpo["input"] == AGUA
    assert corpo["store"] is False
    assert set(corpo) == {
        "model", "system_instruction", "input", "response_format", "generation_config", "store",
    }


def test_instrucoes_trazem_a_tabela_do_po():
    for regra in REGRAS:
        assert all(palavra in ia.INSTRUCOES for palavra in regra.palavras)


def test_usa_o_modelo_padrao_e_aceita_trocar_pela_variavel(monkeypatch):
    monkeypatch.delenv("IA_MODELO", raising=False)
    padrao = cliente()
    ia.classificar_com_ia(AGUA, padrao)
    monkeypatch.setenv("IA_MODELO", "gemini-3.8-flash")
    trocado = cliente()
    ia.classificar_com_ia(AGUA, trocado)
    assert (padrao.chamadas[0]["model"], trocado.chamadas[0]["model"]) == ("gemini-3.5-flash-lite", "gemini-3.8-flash")


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
        ClienteFalso(json.dumps(RESPOSTA), status="failed"),
        ClienteFalso(json.dumps(RESPOSTA), status="incomplete"),
        ClienteFalso(json.dumps(RESPOSTA), status="in_progress"),
        ClienteFalso(""),
        ClienteFalso(None),
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
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setattr(ia, "_criar_cliente", lambda chave: pytest.fail("não podia criar o cliente"))
    assert ia.classificar_com_ia(AGUA) is None


@pytest.mark.parametrize("chave", [None, "", "   "])
def test_ligada_sem_chave_nao_chama_a_ia(monkeypatch, chave):
    monkeypatch.setenv("IA_ATIVA", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    if chave is not None:
        monkeypatch.setenv("GEMINI_API_KEY", chave)
    monkeypatch.setattr(ia, "_criar_cliente", lambda chave: pytest.fail("não podia criar o cliente"))
    assert ia.classificar_com_ia(AGUA) is None


def test_ligada_com_chave_usa_o_cliente_criado_com_essa_chave(monkeypatch):
    criados = []
    monkeypatch.setenv("IA_ATIVA", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setattr(ia, "_criar_cliente", lambda chave: criados.append(chave) or cliente())
    assert ia.classificar_com_ia(AGUA)["fonte"] == "ia"
    assert criados == ["chave-de-teste"]


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


class ClienteLento(ClienteFalso):
    """Imita uma IA que não responde até alguém liberar a espera."""

    def __init__(self):
        super().__init__(json.dumps(RESPOSTA))
        self.liberar = threading.Event()

    def create(self, **pedido):
        self.chamadas.append(pedido)
        self.liberar.wait(5)
        return self.resposta


def ocorrencia_gravada(conexao):
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT status, prioridade, categoria, responsavel_sugerido, motivo, travada, palavra_de_risco, fonte "
            "FROM ocorrencias"
        )
        return cur.fetchone()


def entrada_gravada(conexao):
    with conexao.cursor() as cur:
        cur.execute("SELECT tipo, prioridade_sugerida FROM registros_decisao")
        return cur.fetchall()


def dados(condominio, descricao):
    return {"origem": "morador", "condominioId": condominio, "celular": "81999991234", "descricao": descricao}


def test_o_prazo_da_ia_e_de_10_segundos():
    assert ia.PRAZO_SEGUNDOS == 10


def test_o_pedido_a_ia_leva_o_mesmo_prazo_e_pede_para_nao_guardar_a_conversa():
    falso = cliente()
    ia.classificar_com_ia(AGUA, falso)
    assert (falso.chamadas[0]["timeout"], falso.chamadas[0]["store"]) == (10, False)


def test_ia_que_passa_do_prazo_nao_e_esperada():
    lento = ClienteLento()
    inicio = time.monotonic()
    try:
        assert ia.classificar_com_ia(AGUA, lento, prazo=0.2) is None
        assert time.monotonic() - inicio < 2
    finally:
        lento.liberar.set()


def test_ia_que_responde_dentro_do_prazo_e_usada():
    assert ia.classificar_com_ia(AGUA, cliente(), prazo=5)["fonte"] == "ia"


def test_ia_fora_do_ar_grava_a_ocorrencia_classificada_por_regras(conexao, condominio, monkeypatch):
    com_ia(monkeypatch, ClienteFalso(erro=ConnectionError("fora do ar")))
    resposta = salvar_ocorrencia(dados(condominio, "lâmpada do hall queimada"), conexao=conexao)
    assert resposta["ok"] is True
    assert ocorrencia_gravada(conexao) == (
        "nova", "normal", "manutencao", "zelador", "manutenção simples de área comum", False, None, "regras",
    )
    assert entrada_gravada(conexao) == [("entrada", "normal")]


def test_ia_lenta_nao_segura_a_ocorrencia_e_valem_as_regras(conexao, condominio, monkeypatch):
    lento = com_ia(monkeypatch, ClienteLento())
    monkeypatch.setattr(ia, "PRAZO_SEGUNDOS", 0.2)
    inicio = time.monotonic()
    try:
        resposta = salvar_ocorrencia(dados(condominio, "lâmpada do hall queimada"), conexao=conexao)
        assert time.monotonic() - inicio < 2
    finally:
        lento.liberar.set()
    assert resposta["ok"] is True
    gravada = ocorrencia_gravada(conexao)
    assert (gravada[1:4], gravada[7]) == (("normal", "manutencao", "zelador"), "regras")


def test_ia_que_responde_e_gravada_com_a_fonte_ia(conexao, condominio, monkeypatch):
    com_ia(monkeypatch, cliente())
    salvar_ocorrencia(dados(condominio, AGUA), conexao=conexao)
    assert ocorrencia_gravada(conexao) == (
        "nova", "alta", "manutencao", "zelador", "vazamento ativo que pode piorar", False, None, "ia",
    )


def test_palavra_de_risco_fica_urgente_mesmo_com_a_ia_sugerindo_menos(conexao, condominio, monkeypatch):
    com_ia(monkeypatch, cliente({**RESPOSTA, "prioridade": "baixa"}))
    salvar_ocorrencia(dados(condominio, GAS), conexao=conexao)
    _, prioridade, _, responsavel, motivo, travada, palavra, _ = ocorrencia_gravada(conexao)
    assert (prioridade, responsavel, motivo, travada, palavra) == ("urgente", "sindico", "palavra de risco: gás", True, "gás")


def test_se_a_ia_e_as_regras_falham_a_ocorrencia_fica_salva_para_revisar(conexao, condominio, monkeypatch):
    def regras_com_defeito(texto):
        raise RuntimeError("defeito nas regras")

    com_ia(monkeypatch, ClienteFalso(erro=ConnectionError("fora do ar")))
    monkeypatch.setattr(classificacao, "classificar_por_regras", regras_com_defeito)
    resposta = salvar_ocorrencia(dados(condominio, "lâmpada do hall queimada"), conexao=conexao)
    assert resposta["ok"] is True
    assert ocorrencia_gravada(conexao) == ("nova", None, None, None, "não classificada, revisar", False, None, None)
    assert entrada_gravada(conexao) == [("entrada", None)]
