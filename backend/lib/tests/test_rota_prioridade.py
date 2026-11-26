import pytest

try:
    from fastapi.testclient import TestClient
except RuntimeError:
    pytest.skip("instale o httpx2 para testar a rota", allow_module_level=True)

import main  # noqa: E402
from lib import auth_deps
from lib.auth import criar_token


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
def cliente(conexao, monkeypatch, sindico):
    monkeypatch.setattr(main, "conectar", lambda: ConexaoDoTeste(conexao))
    monkeypatch.setattr(auth_deps, "conectar", lambda: ConexaoDoTeste(conexao))
    monkeypatch.setenv("JWT_SECRET", "segredo-local-do-pytest-h10-1234567890")
    return TestClient(
        main.app, raise_server_exceptions=False,
        headers={"Authorization": f"Bearer {criar_token(sindico)}"},
    )


@pytest.fixture
def nova(conexao, criar_ocorrencia):
    """Cria uma ocorrência com a prioridade dada e, se pedido, a entrada do sistema no histórico."""

    def criar(prioridade, travada=False, sugerida_pelo_sistema=None):
        ocorrencia_id = criar_ocorrencia(travada=travada)
        with conexao.cursor() as cur:
            cur.execute("UPDATE ocorrencias SET prioridade = %s WHERE id = %s", (prioridade, ocorrencia_id))
            if sugerida_pelo_sistema:
                cur.execute(
                    "INSERT INTO registros_decisao (ocorrencia_id, tipo, quem_decidiu, origem, prioridade_sugerida) "
                    "VALUES (%s, 'entrada', 'sistema', 'morador', %s)",
                    (ocorrencia_id, sugerida_pelo_sistema),
                )
        conexao.commit()
        return ocorrencia_id

    return criar


def prioridade_de(conexao, ocorrencia_id):
    with conexao.cursor() as cur:
        cur.execute("SELECT prioridade FROM ocorrencias WHERE id = %s", (ocorrencia_id,))
        return cur.fetchone()[0]


def registros_de(conexao, ocorrencia_id):
    """Devolve os registros da ocorrência, sem a entrada, do mais antigo ao mais novo."""
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT tipo, quem_decidiu, prioridade_sugerida, prioridade_final, motivo, rebaixou_travada "
            "FROM registros_decisao WHERE ocorrencia_id = %s AND tipo <> 'entrada' ORDER BY id",
            (ocorrencia_id,),
        )
        return cur.fetchall()


def alterar(cliente, ocorrencia_id, prioridade, motivo="o síndico viu o problema de perto"):
    return cliente.patch(f"/ocorrencias/{ocorrencia_id}/prioridade", json={"prioridade": prioridade, "motivo": motivo})


def test_altera_a_prioridade_e_grava_o_registro(cliente, conexao, nova):
    ocorrencia_id = nova("normal")
    resposta = alterar(cliente, ocorrencia_id, "alta", "vai atingir o bloco inteiro")
    assert resposta.status_code == 200
    assert resposta.json() == {"id": ocorrencia_id, "prioridade": "alta"}
    assert prioridade_de(conexao, ocorrencia_id) == "alta"
    assert registros_de(conexao, ocorrencia_id) == [
        ("prioridade_alterada", "sindico", "normal", "alta", "vai atingir o bloco inteiro", False)
    ]


def test_rebaixar_uma_travada_marca_o_rebaixamento_no_registro(cliente, conexao, nova):
    ocorrencia_id = nova("urgente", travada=True)
    assert alterar(cliente, ocorrencia_id, "normal", " ").status_code == 422
    assert prioridade_de(conexao, ocorrencia_id) == "urgente"
    assert registros_de(conexao, ocorrencia_id) == []
    assert alterar(cliente, ocorrencia_id, "normal").status_code == 200
    assert registros_de(conexao, ocorrencia_id)[0][5] is True


def test_confirma_sugestao_sem_motivo(cliente, conexao, nova):
    ocorrencia_id = nova("urgente", travada=True, sugerida_pelo_sistema="urgente")
    assert alterar(cliente, ocorrencia_id, "urgente", None).status_code == 200
    assert prioridade_de(conexao, ocorrencia_id) == "urgente"
    assert registros_de(conexao, ocorrencia_id) == [
        ("prioridade_confirmada", "sindico", "urgente", "urgente", None, False)
    ]


def test_detalhe_retorna_dados_e_classificacao_da_ocorrencia(cliente, conexao, nova):
    ocorrencia_id = nova("urgente", travada=True, sugerida_pelo_sistema="urgente")
    with conexao, conexao.cursor() as cur:
        cur.execute(
            """UPDATE ocorrencias SET nome = 'Ana', apartamento = '101', celular = '11987654321',
               local = 'Hall', palavra_de_risco = 'gás' WHERE id = %s""",
            (ocorrencia_id,),
        )
    resposta = cliente.get(f"/ocorrencias/{ocorrencia_id}")
    assert resposta.status_code == 200
    detalhe = resposta.json()
    assert (detalhe["nome"], detalhe["apartamento"], detalhe["celular"], detalhe["local"]) == (
        "Ana", "101", "11987654321", "Hall",
    )
    assert detalhe["criadaEm"]
    assert detalhe["travada"] is True
    assert detalhe["palavraDeRisco"] == "gás"
    assert detalhe["prioridadeSugerida"] == "urgente"


def test_autenticacao_e_carteira_protegem_leitura_e_alteracao(cliente, conexao, nova):
    ocorrencia_id = nova("urgente", travada=True)
    with conexao, conexao.cursor() as cur:
        cur.execute("INSERT INTO sindicos (nome, email) VALUES ('Outro', 'outro@teste.com') RETURNING id")
        outro_id = cur.fetchone()[0]

    protegido = f"/ocorrencias/{ocorrencia_id}"
    for token, status in [(None, 401), ("invalido", 401), (criar_token(outro_id), 404)]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        with TestClient(main.app, headers=headers) as visitante:
            assert visitante.get(protegido).status_code == status
            assert visitante.get(f"{protegido}/decisoes").status_code == status
            assert visitante.get(f"{protegido}/responsaveis").status_code == status
            assert visitante.post(f"{protegido}/acoes", json={"acao": "eu_mesmo"}).status_code == status
            assert visitante.patch(f"{protegido}/concluir").status_code == status
            assert visitante.patch(
                f"{protegido}/prioridade", json={"prioridade": "normal", "motivo": "Verificado"},
            ).status_code == status
    assert prioridade_de(conexao, ocorrencia_id) == "urgente"
    assert registros_de(conexao, ocorrencia_id) == []


def test_a_sugerida_do_registro_e_a_do_sistema_mesmo_depois_de_outra_mudanca(cliente, conexao, nova):
    ocorrencia_id = nova("normal", sugerida_pelo_sistema="normal")
    assert alterar(cliente, ocorrencia_id, "alta").status_code == 200
    assert alterar(cliente, ocorrencia_id, "baixa").status_code == 200
    registros = registros_de(conexao, ocorrencia_id)
    assert [(r[2], r[3]) for r in registros] == [("normal", "alta"), ("normal", "baixa")]


def test_sem_entrada_no_historico_a_sugerida_e_a_prioridade_de_antes(cliente, conexao, nova):
    ocorrencia_id = nova("normal")
    assert alterar(cliente, ocorrencia_id, "alta").status_code == 200
    assert registros_de(conexao, ocorrencia_id)[0][2] == "normal"


@pytest.mark.parametrize(
    "prioridade, motivo, erros",
    [
        ("alta", "", {"motivo": "Informe o motivo da mudança"}),
        ("alta", "   ", {"motivo": "Informe o motivo da mudança"}),
        ("alta", None, {"motivo": "Informe o motivo da mudança"}),
        ("critica", "porque sim", {"prioridadeFinal": "Prioridade inválida"}),
    ],
)
def test_dado_invalido_devolve_422_e_nao_muda_nada(cliente, conexao, nova, prioridade, motivo, erros):
    ocorrencia_id = nova("normal")
    resposta = alterar(cliente, ocorrencia_id, prioridade, motivo)
    assert resposta.status_code == 422
    assert resposta.json()["detail"] == erros
    assert prioridade_de(conexao, ocorrencia_id) == "normal"
    assert registros_de(conexao, ocorrencia_id) == []


def test_ocorrencia_sem_prioridade_nao_tem_sugerida_para_registrar(cliente, conexao, nova):
    ocorrencia_id = nova(None)
    resposta = alterar(cliente, ocorrencia_id, "alta")
    assert resposta.status_code == 422
    assert resposta.json()["detail"] == {"prioridadeSugerida": "Prioridade inválida"}
    assert prioridade_de(conexao, ocorrencia_id) is None


def test_ocorrencia_que_nao_existe_devolve_404(cliente, conexao):
    assert alterar(cliente, 999999, "alta").status_code == 404
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM registros_decisao")
        assert cur.fetchone()[0] == 0


def test_id_que_nao_e_numero_devolve_422(cliente):
    assert alterar(cliente, "abc", "alta").status_code == 422


def test_se_algo_falha_depois_do_registro_ele_nao_fica_gravado(cliente, conexao, nova, monkeypatch):
    ocorrencia_id = nova("normal")
    registrar = main.registrar_decisao

    def grava_e_falha(dados, conexao=None):
        registrar(dados, conexao=conexao)
        raise RuntimeError("falhou depois de gravar")

    monkeypatch.setattr(main, "registrar_decisao", grava_e_falha)
    assert alterar(cliente, ocorrencia_id, "alta").status_code == 500
    assert prioridade_de(conexao, ocorrencia_id) == "normal"
    assert registros_de(conexao, ocorrencia_id) == []
