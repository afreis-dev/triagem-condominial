import pytest

try:
    from fastapi.testclient import TestClient
except RuntimeError:
    pytest.skip("instale o httpx2 para testar a rota", allow_module_level=True)

import lib.salvar_ocorrencia as modulo  # noqa: E402
import main  # noqa: E402

CORPO = {
    "perfil": "morador",
    "nome": "Ana Lima",
    "apartamento": "302",
    "celular": "81999991234",
    "descricao": "o portão da garagem travou aberto",
}


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
def cliente(conexao, monkeypatch):
    monkeypatch.setattr(main, "conectar", lambda: ConexaoDoTeste(conexao))
    with TestClient(main.app, raise_server_exceptions=False) as cliente:
        yield cliente


def enviar(cliente, **campos):
    return cliente.post("/api/condominios/aurora/ocorrencias", json={**CORPO, **campos})


def test_a_ocorrencia_ja_esta_no_banco_quando_a_classificacao_roda(
    cliente, condominio, contar_confirmadas, monkeypatch
):
    classificar = modulo.classificar
    vistas = []

    def espiar(texto):
        vistas.append(contar_confirmadas())
        return classificar(texto)

    monkeypatch.setattr(modulo, "classificar", espiar)
    resposta = enviar(cliente)
    assert resposta.status_code == 201
    assert resposta.json()["protocolo"] == "TS-000001"
    assert vistas == [1]


def test_formulario_sem_apartamento_nao_grava(cliente, condominio, contar_confirmadas):
    assert enviar(cliente, apartamento="").json() == {"ok": False, "erros": {"apartamento": "Informe o apartamento"}}
    assert contar_confirmadas() == 0
