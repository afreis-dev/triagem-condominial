import pytest

try:
    from fastapi.testclient import TestClient
except RuntimeError:
    pytest.skip("instale o httpx2 para testar a rota", allow_module_level=True)

import main  # noqa: E402
from lib import auth_deps  # noqa: E402
from lib.auth import criar_token, token_csrf  # noqa: E402


class ConexaoDoTeste:
    """Entrega a conexão do teste à rota sem deixar a rota fechar essa conexão."""

    def __init__(self, conexao):
        self.conexao = conexao

    def __getattr__(self, nome):
        return getattr(self.conexao, nome)

    def __enter__(self):
        return self.conexao.__enter__()

    def __exit__(self, *erro):
        return self.conexao.__exit__(*erro)

    def close(self):
        pass


@pytest.fixture
def cliente_sem_token(conexao, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "segredo-exclusivo-para-testes-de-endpoints-2026")
    monkeypatch.setattr(main, "conectar", lambda: ConexaoDoTeste(conexao))
    monkeypatch.setattr(auth_deps, "conectar", main.conectar)
    with TestClient(main.app, raise_server_exceptions=False) as cliente:
        yield cliente


@pytest.fixture
def cliente(cliente_sem_token, sindico):
    token = criar_token(sindico)
    cliente_sem_token.headers["Cookie"] = f"triagem_sessao={token}"
    cliente_sem_token.headers["X-CSRF-Token"] = token_csrf(token)
    return cliente_sem_token


def colar(cliente, condominio, **campos):
    corpo = {"condominioId": condominio, "descricao": "lâmpada do hall queimada", **campos}
    return cliente.post("/ocorrencias/colar", json=corpo)


def ocorrencia(conexao, ocorrencia_id):
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT origem, condominio_id, nome, celular, apartamento, local, descricao, prioridade, travada "
            "FROM ocorrencias WHERE id = %s",
            (ocorrencia_id,),
        )
        return cur.fetchone()


def contar(conexao):
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM ocorrencias")
        return cur.fetchone()[0]


@pytest.mark.parametrize("token", [None, "token-invalido"])
def test_exige_token_valido(cliente_sem_token, conexao, condominio, token):
    if token is not None:
        cliente_sem_token.headers["Cookie"] = f"triagem_sessao={token}"
    assert colar(cliente_sem_token, condominio).status_code == 401
    assert contar(conexao) == 0


def test_rejeita_condominio_de_outro_sindico(cliente_sem_token, conexao, condominio):
    with conexao, conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO sindicos (nome, email) VALUES (%s, %s) RETURNING id",
            ("Outro síndico", "outro@teste.com"),
        )
        outro_sindico = cursor.fetchone()[0]

    token = criar_token(outro_sindico)
    cliente_sem_token.headers["Cookie"] = f"triagem_sessao={token}"
    cliente_sem_token.headers["X-CSRF-Token"] = token_csrf(token)
    assert colar(cliente_sem_token, condominio).status_code == 403
    assert contar(conexao) == 0


def test_rejeita_condominio_inexistente(cliente, conexao):
    assert colar(cliente, 999999).status_code == 403
    assert contar(conexao) == 0


def test_grava_a_mensagem_colada_como_whatsapp_do_sindico(cliente, conexao, condominio):
    resposta = colar(cliente, condominio, nome="Dona Rita", celular="(81) 99999-1234", apartamento="301", local="hall")
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["ok"] is True
    assert corpo["protocolo"] == f"TS-{corpo['ocorrenciaId']:06d}"
    assert ocorrencia(conexao, corpo["ocorrenciaId"])[:7] == (
        "whatsapp_sindico", condominio, "Dona Rita", "81999991234", "301", "hall", "lâmpada do hall queimada",
    )


def test_confirma_a_transacao_antes_de_fechar_a_conexao(cliente, conexao, condominio):
    assert colar(cliente, condominio).status_code == 201
    conexao.rollback()
    assert contar(conexao) == 1


def test_aceita_so_o_condominio_e_a_descricao(cliente, conexao, condominio):
    resposta = colar(cliente, condominio)
    assert resposta.status_code == 201
    assert ocorrencia(conexao, resposta.json()["ocorrenciaId"])[:6] == (
        "whatsapp_sindico", condominio, None, None, None, None,
    )


def test_usa_o_texto_colado_quando_ele_vem(cliente, conexao, condominio):
    resposta = colar(cliente, condominio, texto_colado="mensagem colada do grupo")
    assert ocorrencia(conexao, resposta.json()["ocorrenciaId"])[6] == "mensagem colada do grupo"


def test_ignora_a_origem_enviada_no_corpo(cliente, conexao, condominio):
    resposta = colar(cliente, condominio, origem="morador")
    assert ocorrencia(conexao, resposta.json()["ocorrenciaId"])[0] == "whatsapp_sindico"


def test_aceita_2000_caracteres_com_emoji_e_quebra_de_linha(cliente, conexao, condominio):
    descricao = "😀" + "a\n" * 999 + "b"
    assert len(descricao) == 2000
    resposta = colar(cliente, condominio, descricao=descricao)
    assert resposta.status_code == 201
    assert ocorrencia(conexao, resposta.json()["ocorrenciaId"])[6] == descricao


def test_mais_de_2000_caracteres_na_descricao_devolve_422_e_nao_grava(cliente, conexao, condominio):
    assert colar(cliente, condominio, descricao="a" * 2001).status_code == 422
    assert contar(conexao) == 0


def test_mais_de_2000_caracteres_no_texto_colado_devolve_o_erro_da_descricao(cliente, conexao, condominio):
    resposta = colar(cliente, condominio, texto_colado="a" * 2001)
    assert resposta.status_code == 422
    assert resposta.json()["detail"] == {"descricao": "A descrição deve ter no máximo 2000 caracteres"}
    assert contar(conexao) == 0


@pytest.mark.parametrize(
    "campos, erros",
    [
        ({"descricao": "   "}, {"descricao": "Descreva a ocorrência"}),
        ({"celular": "123"}, {"celular": "Celular deve ter 10 ou 11 dígitos"}),
    ],
)
def test_devolve_os_erros_da_funcao_em_422_e_nao_grava(cliente, conexao, condominio, campos, erros):
    corpo = {"condominioId": condominio, "descricao": "lâmpada queimada", **campos}
    resposta = cliente.post("/ocorrencias/colar", json=corpo)
    assert resposta.status_code == 422
    assert resposta.json()["detail"] == erros
    assert contar(conexao) == 0


def test_classifica_a_ocorrencia(cliente, conexao, condominio):
    comum = colar(cliente, condominio, descricao="lâmpada do hall queimada").json()["ocorrenciaId"]
    risco = colar(cliente, condominio, descricao="tem cheiro de gás no bloco B").json()["ocorrenciaId"]
    assert ocorrencia(conexao, comum)[7:] == ("normal", False)
    assert ocorrencia(conexao, risco)[7:] == ("urgente", True)


def test_se_algo_falha_depois_de_gravar_nada_fica_gravado(cliente, conexao, condominio, monkeypatch):
    salvar = main.salvar_ocorrencia

    def grava_e_falha(dados, conexao=None):
        salvar(dados, conexao)
        raise RuntimeError("falhou depois de gravar")

    monkeypatch.setattr(main, "salvar_ocorrencia", grava_e_falha)
    assert colar(cliente, condominio).status_code == 500
    conexao.rollback()
    assert contar(conexao) == 0
