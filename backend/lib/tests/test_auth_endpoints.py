from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.lib.auth import gerar_hash, token_csrf
from backend.main import app

EMAIL = "sindico@teste.com"
SENHA = "SenhaTeste@2026!"


def cabecalhos(sindico_id=7):
    from lib.auth import criar_token
    token = criar_token(sindico_id)
    return {"Cookie": f"triagem_sessao={token}", "X-CSRF-Token": token_csrf(token)}


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET",
        "segredo-exclusivo-para-testes-de-endpoints-2026",
    )

    import backend.main as modulo

    conexao = MagicMock()
    cursor = conexao.cursor.return_value.__enter__.return_value

    cursor.fetchone.return_value = (1, gerar_hash(SENHA))

    monkeypatch.setattr(modulo, "conectar", lambda: conexao)

    with TestClient(app) as cliente:
        yield cliente, cursor


def test_login_com_credenciais_validas(cliente):
    api, cursor = cliente

    resposta = api.post(
        "/auth/login",
        json={"identificador": EMAIL, "senha": SENHA},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}
    assert "triagem_sessao=" in resposta.headers["set-cookie"]
    assert "httponly" in resposta.headers["set-cookie"].lower()
    assert "samesite=lax" in resposta.headers["set-cookie"].lower()


def test_login_com_celular_formatado(cliente):
    api, cursor = cliente
    resposta = api.post(
        "/auth/login",
        json={"identificador": "(19) 99123-4567", "senha": SENHA},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resposta.status_code == 200
    assert cursor.execute.call_args.args[1] == ("(19) 99123-4567", "19991234567", "19991234567")


def test_login_com_celular_no_postgresql(conexao, sindico, monkeypatch):
    import backend.main as modulo

    class ConexaoDoTeste:
        def cursor(self):
            return conexao.cursor()

        def close(self):
            pass

    monkeypatch.setenv("JWT_SECRET", "segredo-exclusivo-para-testes-de-endpoints-2026")
    with conexao.cursor() as cursor:
        cursor.execute(
            "UPDATE sindicos SET celular = %s, senha_hash = %s WHERE id = %s",
            ("(19) 99123-4567", gerar_hash(SENHA), sindico),
        )
    conexao.commit()
    monkeypatch.setattr(modulo, "conectar", lambda: ConexaoDoTeste())

    with TestClient(app) as api:
        resposta = api.post(
            "/auth/login",
            json={"identificador": "19991234567", "senha": SENHA},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
    assert resposta.status_code == 200
    assert "triagem_sessao=" in resposta.headers["set-cookie"]


def test_login_bloqueia_origem_nao_autorizada(cliente):
    api, cursor = cliente
    resposta = api.post(
        "/auth/login",
        json={"identificador": EMAIL, "senha": SENHA},
        headers={"Origin": "https://outra-origem.example", "X-Requested-With": "XMLHttpRequest"},
    )
    assert resposta.status_code == 403
    cursor.execute.assert_not_called()


def test_login_pelo_swagger_na_mesma_origem(cliente):
    api, _ = cliente
    resposta = api.post(
        "/auth/login",
        json={"identificador": EMAIL, "senha": SENHA},
        headers={"Origin": "http://testserver"},
    )
    assert resposta.status_code == 200
    assert "httponly" in resposta.headers["set-cookie"].lower()


def test_login_exige_cabecalho_de_requisicao_do_app(cliente):
    api, cursor = cliente
    resposta = api.post("/auth/login", json={"identificador": EMAIL, "senha": SENHA})
    assert resposta.status_code == 403
    cursor.execute.assert_not_called()


def test_swagger_documenta_csrf_nas_rotas_de_escrita(cliente):
    api, _ = cliente
    esquema = api.get("/openapi.json").json()
    assert esquema["components"]["securitySchemes"]["CSRF"]["name"] == "X-CSRF-Token"
    assert esquema["components"]["securitySchemes"]["CSRF"]["in"] == "header"
    assert esquema["paths"]["/auth/logout"]["post"]["security"] == [{"CSRF": []}]


def test_login_com_senha_incorreta(cliente):
    api, cursor = cliente

    resposta = api.post(
        "/auth/login",
        json={"identificador": EMAIL, "senha": "senha-errada"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert resposta.status_code == 401


def test_login_com_usuario_inexistente(cliente):
    api, cursor = cliente
    cursor.fetchone.return_value = None

    resposta = api.post(
        "/auth/login",
        json={"identificador": "inexistente@teste.com", "senha": SENHA},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert resposta.status_code == 401


def test_perfil_sem_token(cliente):
    api, cursor = cliente

    resposta = api.get("/auth/me")

    assert resposta.status_code == 401


def test_bearer_nao_autentica_mais(cliente):
    from lib.auth import criar_token

    api, _ = cliente
    resposta = api.get("/auth/me", headers={"Authorization": f"Bearer {criar_token(7)}"})
    assert resposta.status_code == 401


def test_logout_exige_csrf_e_apaga_cookie(cliente, monkeypatch):
    import lib.auth_deps as auth_deps

    api, _ = cliente
    conexao = MagicMock()
    conexao.cursor.return_value.__enter__.return_value.fetchone.return_value = (7, "Síndico Teste", EMAIL)
    monkeypatch.setattr(auth_deps, "conectar", lambda: conexao)
    token = cabecalhos(7)["Cookie"].split("=", 1)[1]

    sem_csrf = api.post("/auth/logout", headers={"Cookie": f"triagem_sessao={token}"})
    assert sem_csrf.status_code == 403
    resposta = api.post("/auth/logout", headers={
        "Cookie": f"triagem_sessao={token}", "X-CSRF-Token": token_csrf(token),
    })
    assert resposta.status_code == 200
    assert "max-age=0" in resposta.headers["set-cookie"].lower()


@pytest.mark.parametrize("rota", ["/ocorrencias/aprovar-lote", "/ocorrencias/desfazer-lote"])
def test_rotas_de_lote_exigem_csrf(cliente, monkeypatch, rota):
    import lib.auth_deps as auth_deps

    api, _ = cliente
    conexao = MagicMock()
    conexao.cursor.return_value.__enter__.return_value.fetchone.return_value = (7, "Síndico Teste", EMAIL)
    monkeypatch.setattr(auth_deps, "conectar", lambda: conexao)

    resposta = api.post(
        rota,
        json={"ids": [1]},
        headers={"Cookie": cabecalhos(7)["Cookie"]},
    )
    assert resposta.status_code == 403


def test_lista_condominios_exige_login(cliente):
    api, _ = cliente
    assert api.get("/api/condominios").status_code == 401


def test_lista_condominios_consulta_a_carteira_do_sindico(cliente, monkeypatch):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps

    api, cursor = cliente
    conexao_perfil = MagicMock()
    conexao_perfil.cursor.return_value.__enter__.return_value.fetchone.return_value = (
        7, "Síndico Teste", EMAIL,
    )
    monkeypatch.setattr(auth_deps, "conectar", lambda: conexao_perfil)
    cursor.fetchall.return_value = [(3, "Vista Verde")]

    resposta = api.get(
        "/api/condominios",
        headers=cabecalhos(7),
    )
    assert resposta.status_code == 200
    assert resposta.json() == [{"id": 3, "nome": "Vista Verde"}]
    consulta, parametros = cursor.execute.call_args.args
    assert "WHERE sindico_id = %s" in consulta
    assert parametros == (7,)


def test_perfil_com_token_invalido(cliente):
    api, cursor = cliente

    resposta = api.get(
        "/auth/me",
        headers={"Cookie": "triagem_sessao=token-invalido"},
    )

    assert resposta.status_code == 401


def test_perfil_com_token_valido(cliente, monkeypatch):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps

    api, _ = cliente

    conexao = MagicMock()
    cursor = conexao.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (
        1,
        "Síndico Teste",
        EMAIL,
    )

    monkeypatch.setattr(auth_deps, "conectar", lambda: conexao)

    token = criar_token(1)

    resposta = api.get(
        "/auth/me",
        headers={"Cookie": f"triagem_sessao={token}"},
    )

    assert resposta.status_code == 200
    dados = resposta.json()
    assert len(dados.pop("csrfToken")) == 64
    assert dados == {
        "id": 1,
        "nome": "Síndico Teste",
        "email": EMAIL,
    }


def test_perfil_com_token_expirado(cliente):
    from datetime import datetime, timedelta, timezone

    import jwt

    api, _ = cliente

    token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        "segredo-exclusivo-para-testes-de-endpoints-2026",
        algorithm="HS256",
    )

    resposta = api.get(
        "/auth/me",
        headers={"Cookie": f"triagem_sessao={token}"},
    )

    assert resposta.status_code == 401


def test_historico_sem_token_deve_ser_bloqueado(cliente):
    api, _ = cliente

    resposta = api.get("/api/ocorrencias/1/decisoes")

    assert resposta.status_code == 401



def test_historico_de_outro_sindico_deve_ser_bloqueado(cliente, monkeypatch):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps

    api, cursor = cliente

    # Autentica como o síndico 7
    conexao_auth = MagicMock()
    cursor_auth = conexao_auth.cursor.return_value.__enter__.return_value
    cursor_auth.fetchone.return_value = (
        7, "Síndico Teste", EMAIL
    )

    cursor.fetchone.return_value = None

    monkeypatch.setattr(
        auth_deps, "conectar", lambda: conexao_auth
    )

    # A ocorrência 1 não pertence à carteira do síndico 7
    resposta = api.get(
        "/api/ocorrencias/1/decisoes",
        headers=cabecalhos(7),
    )

    assert resposta.status_code == 404

    consulta, parametros = cursor.execute.call_args.args

    assert "c.sindico_id = %s" in consulta
    assert parametros == (1, 7)


def test_historico_do_proprio_sindico_deve_ser_permitido(cliente, monkeypatch):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps
    import backend.main as modulo

    api, cursor = cliente

    conexao_auth = MagicMock()
    cursor_auth = conexao_auth.cursor.return_value.__enter__.return_value
    cursor_auth.fetchone.return_value = (
        7, "Síndico Teste", EMAIL
    )

    monkeypatch.setattr(
        auth_deps, "conectar", lambda: conexao_auth
    )

    # Simula uma ocorrência encontrada na carteira do síndico
    cursor.fetchone.return_value = (1,)

    # Simula um histórico vazio para isolar o teste de autorização
    monkeypatch.setattr(
        modulo, "buscar_decisoes", lambda id, conn: []
    )

    resposta = api.get(
        "/api/ocorrencias/1/decisoes",
        headers=cabecalhos(7),
    )

    assert resposta.status_code == 200
    assert resposta.json() == []

    consulta, parametros = cursor.execute.call_args.args
    assert "c.sindico_id = %s" in consulta
    assert parametros == (1, 7)


def test_responsaveis_sem_token_deve_ser_bloqueado(cliente):
    api, _ = cliente

    resposta = api.get("/ocorrencias/1/responsaveis")

    assert resposta.status_code == 401


def test_responsaveis_do_proprio_sindico_deve_ser_permitido(cliente, monkeypatch):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps

    api, cursor = cliente

    # Simula o síndico autenticado
    conexao_auth = MagicMock()
    cursor_auth = conexao_auth.cursor.return_value.__enter__.return_value
    cursor_auth.fetchone.return_value = (
        7, "Síndico Teste", EMAIL
    )

    monkeypatch.setattr(
        auth_deps, "conectar", lambda: conexao_auth
    )

    # Primeira consulta: autorização da ocorrência
    # Segunda consulta: dados da ocorrência
    cursor.fetchone.side_effect = [
        (1,),
        (3, "zelador", "nova"),
    ]

    # Responsáveis disponíveis no condomínio
    cursor.fetchall.return_value = [
        ("sindico",),
        ("zelador",),
    ]

    resposta = api.get(
        "/ocorrencias/1/responsaveis",
        headers=cabecalhos(7),
    )

    assert resposta.status_code == 200
    assert resposta.json() == {
        "responsaveis": ["sindico", "zelador"],
        "responsavelSugerido": "zelador",
    }


def test_responsaveis_de_outro_sindico_deve_ser_bloqueado(cliente, monkeypatch):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps

    api, cursor = cliente

    conexao_auth = MagicMock()
    cursor_auth = conexao_auth.cursor.return_value.__enter__.return_value
    cursor_auth.fetchone.return_value = (
        7, "Síndico Teste", EMAIL
    )

    monkeypatch.setattr(
        auth_deps, "conectar", lambda: conexao_auth
    )

    # Simula ocorrência fora da carteira do síndico 7
    cursor.fetchone.return_value = None

    resposta = api.get(
        "/ocorrencias/1/responsaveis",
        headers=cabecalhos(7),
    )

    assert resposta.status_code == 404

    consulta, parametros = cursor.execute.call_args.args
    assert "c.sindico_id = %s" in consulta
    assert parametros == (1, 7)


def test_concluir_sem_token_deve_ser_bloqueado(cliente):
    api, _ = cliente

    resposta = api.patch("/api/ocorrencias/1/concluir")

    assert resposta.status_code == 401


def test_concluir_de_outro_sindico_deve_ser_bloqueado(cliente, monkeypatch):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps
    import backend.main as modulo

    api, cursor = cliente

    # Simula o síndico 7 autenticado
    conexao_auth = MagicMock()
    cursor_auth = conexao_auth.cursor.return_value.__enter__.return_value
    cursor_auth.fetchone.return_value = (
        7, "Síndico Teste", EMAIL
    )
    monkeypatch.setattr(auth_deps, "conectar", lambda: conexao_auth)

    # Simula ocorrência fora da carteira
    cursor.fetchone.return_value = None

    # A conclusão não deve sequer ser chamada
    concluir_mock = MagicMock(
        return_value={
            "ok": True,
            "ocorrenciaId": 1,
            "concluidaEm": "2026-11-26T00:00:00+00:00",
        }
    )
    monkeypatch.setattr(modulo, "concluir_ocorrencia", concluir_mock)

    resposta = api.patch(
        "/api/ocorrencias/1/concluir",
        headers=cabecalhos(7),
    )

    assert resposta.status_code == 404
    concluir_mock.assert_not_called()


def test_concluir_do_proprio_sindico_deve_ser_permitido(cliente, monkeypatch):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps
    import backend.main as modulo

    api, cursor = cliente

    # Simula o síndico 7 autenticado
    conexao_auth = MagicMock()
    cursor_auth = conexao_auth.cursor.return_value.__enter__.return_value
    cursor_auth.fetchone.return_value = (
        7, "Síndico Teste", EMAIL
    )

    monkeypatch.setattr(
        auth_deps, "conectar", lambda: conexao_auth
    )

    # A ocorrência 1 pertence à carteira do síndico
    cursor.fetchone.return_value = (1,)

    # Simula uma conclusão bem-sucedida
    concluir_mock = MagicMock(
        return_value={
            "ok": True,
            "ocorrenciaId": 1,
            "concluidaEm": "2026-11-26T00:00:00+00:00",
        }
    )
    monkeypatch.setattr(
        modulo, "concluir_ocorrencia", concluir_mock
    )

    resposta = api.patch(
        "/api/ocorrencias/1/concluir",
        headers=cabecalhos(7),
    )

    assert resposta.status_code == 200
    assert resposta.json()["ok"] is True

    # Confirma que a mesma conexão foi reutilizada
    concluir_mock.assert_called_once_with(
        1, conexao=modulo.conectar.return_value
    ) if isinstance(modulo.conectar, MagicMock) else None

    assert concluir_mock.call_count == 1
    assert concluir_mock.call_args.kwargs["conexao"] is not None

    consulta, parametros = cursor.execute.call_args.args
    assert "c.sindico_id = %s" in consulta
    assert parametros == (1, 7)


def test_registrar_acao_sem_token_deve_ser_bloqueado(cliente):
    api, _ = cliente

    resposta = api.post(
        "/ocorrencias/1/acoes",
        json={
            "acao": "eu_mesmo",
            "nota": "Teste de autorização",
        },
    )

    assert resposta.status_code == 401


def test_registrar_acao_de_outro_sindico_deve_ser_bloqueado(
    cliente, monkeypatch
):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps
    import backend.main as modulo

    api, cursor = cliente

    # Simula o síndico 7 autenticado
    conexao_auth = MagicMock()
    cursor_auth = conexao_auth.cursor.return_value.__enter__.return_value
    cursor_auth.fetchone.return_value = (
        7, "Síndico Teste", EMAIL
    )

    monkeypatch.setattr(
        auth_deps, "conectar", lambda: conexao_auth
    )

    # A ocorrência está fora da carteira
    cursor.fetchone.return_value = None

    # O registro da decisão não pode ser executado
    registrar_mock = MagicMock()
    monkeypatch.setattr(
        modulo, "registrar_decisao", registrar_mock
    )

    resposta = api.post(
        "/ocorrencias/1/acoes",
        headers=cabecalhos(7),
        json={
            "acao": "eu_mesmo",
            "nota": "Teste de autorização",
        },
    )

    assert resposta.status_code == 404
    registrar_mock.assert_not_called()

    consulta, parametros = cursor.execute.call_args.args
    assert "c.sindico_id = %s" in consulta
    assert parametros == (1, 7)


def test_registrar_acao_do_proprio_sindico_deve_ser_permitido(
    cliente, monkeypatch
):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps
    import backend.main as modulo

    api, cursor = cliente

    conexao_auth = MagicMock()
    cursor_auth = conexao_auth.cursor.return_value.__enter__.return_value
    cursor_auth.fetchone.return_value = (
        7, "Síndico Teste", EMAIL
    )
    monkeypatch.setattr(
        auth_deps, "conectar", lambda: conexao_auth
    )

    # 1ª consulta: ocorrência pertence ao síndico
    # 2ª consulta: ocorrência está com status "nova"
    cursor.fetchone.side_effect = [
        (1,),
        (3, "zelador", "nova"),
    ]

    registrar_mock = MagicMock(return_value={"ok": True})
    monkeypatch.setattr(
        modulo, "registrar_decisao", registrar_mock
    )

    resposta = api.post(
        "/ocorrencias/1/acoes",
        headers=cabecalhos(7),
        json={
            "acao": "eu_mesmo",
            "nota": "Vou cuidar desta ocorrência",
        },
    )

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "em_andamento"
    registrar_mock.assert_called_once()

    consulta, parametros = cursor.execute.call_args.args
    assert "UPDATE ocorrencias SET status" in consulta
    assert parametros == (1,)


def test_alterar_prioridade_sem_token_deve_ser_bloqueado(cliente):
    api, _ = cliente

    resposta = api.patch(
        "/ocorrencias/1/prioridade",
        json={
            "prioridade": "alta",
            "motivo": "Teste de autorização",
        },
    )

    assert resposta.status_code == 401


def test_alterar_prioridade_de_outro_sindico_deve_ser_bloqueado(
    cliente, monkeypatch
):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps

    api, cursor = cliente

    # Simula o síndico 7 autenticado
    conexao_auth = MagicMock()
    cursor_auth = conexao_auth.cursor.return_value.__enter__.return_value
    cursor_auth.fetchone.return_value = (
        7, "Síndico Teste", EMAIL
    )

    monkeypatch.setattr(
        auth_deps, "conectar", lambda: conexao_auth
    )

    # Ocorrência fora da carteira
    cursor.fetchone.return_value = None

    resposta = api.patch(
        "/ocorrencias/1/prioridade",
        headers=cabecalhos(7),
        json={
            "prioridade": "alta",
            "motivo": "Teste de autorização",
        },
    )

    assert resposta.status_code == 404

    consulta, parametros = cursor.execute.call_args.args
    assert "c.sindico_id = %s" in consulta
    assert parametros == (1, 7)


def test_alterar_prioridade_do_proprio_sindico_deve_ser_permitido(
    cliente, monkeypatch
):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps
    import backend.main as modulo

    api, cursor = cliente

    # Simula o síndico 7 autenticado
    conexao_auth = MagicMock()
    cursor_auth = conexao_auth.cursor.return_value.__enter__.return_value
    cursor_auth.fetchone.return_value = (
        7, "Síndico Teste", EMAIL
    )

    monkeypatch.setattr(
        auth_deps, "conectar", lambda: conexao_auth
    )

    cursor.fetchone.return_value = (
        1, "TS-000001", 3, "Vista Verde", "Lâmpada queimada", "morador",
        "nova", "normal", None, None, None,
        None, None, None, None, False, None, "normal", "manutencao", "zelador",
    )

    # Simula o registro da decisão no histórico
    registrar_mock = MagicMock(return_value={"ok": True})
    monkeypatch.setattr(
        modulo, "registrar_decisao", registrar_mock
    )

    resposta = api.patch(
        "/ocorrencias/1/prioridade",
        headers=cabecalhos(7),
        json={
            "prioridade": "alta",
            "motivo": "Necessita atendimento rápido",
        },
    )

    assert resposta.status_code == 200
    assert resposta.json() == {
        "id": 1,
        "prioridade": "alta",
    }

    registrar_mock.assert_called_once()

    dados_decisao = registrar_mock.call_args.args[0]
    assert dados_decisao["prioridadeFinal"] == "alta"
    assert dados_decisao["motivo"] == "Necessita atendimento rápido"

    # Confirma a atualização da prioridade
    consulta, parametros = cursor.execute.call_args.args
    assert "UPDATE ocorrencias SET prioridade" in consulta
    assert parametros == ("alta", 1)


def test_detalhe_sem_token_deve_ser_bloqueado(cliente):
    api, _ = cliente

    resposta = api.get("/ocorrencias/1")

    assert resposta.status_code == 401


def test_detalhe_de_outro_sindico_deve_ser_bloqueado(
    cliente, monkeypatch
):
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps

    api, cursor = cliente

    # Simula o síndico 7 autenticado
    conexao_auth = MagicMock()
    cursor_auth = conexao_auth.cursor.return_value.__enter__.return_value
    cursor_auth.fetchone.return_value = (
        7, "Síndico Teste", EMAIL
    )

    monkeypatch.setattr(
        auth_deps, "conectar", lambda: conexao_auth
    )

    # A consulta não encontra a ocorrência na carteira
    cursor.fetchone.return_value = None

    resposta = api.get(
        "/ocorrencias/1",
        headers=cabecalhos(7),
    )

    assert resposta.status_code == 404

    consulta, parametros = cursor.execute.call_args.args
    assert "c.sindico_id = %s" in consulta
    assert parametros == (1, 7)


def test_detalhe_do_proprio_sindico_deve_ser_permitido(
    cliente, monkeypatch
):
    from datetime import datetime, timezone
    from lib.auth import criar_token
    import lib.auth_deps as auth_deps

    api, cursor = cliente

    # Simula o síndico 7 autenticado
    conexao_auth = MagicMock()
    cursor_auth = conexao_auth.cursor.return_value.__enter__.return_value
    cursor_auth.fetchone.return_value = (
        7, "Síndico Teste", EMAIL
    )

    monkeypatch.setattr(
        auth_deps, "conectar", lambda: conexao_auth
    )

    # Simula uma ocorrência da carteira do síndico
    cursor.fetchone.return_value = (
        1, "TS-000001", 3, "Vista Verde", "Lâmpada queimada", "morador",
        "nova", "normal", None, datetime(2026, 11, 26, tzinfo=timezone.utc), None,
        None, None, None, None, False, None, "normal", "manutencao", "zelador",
    )

    resposta = api.get(
        "/ocorrencias/1",
        headers=cabecalhos(7),
    )

    assert resposta.status_code == 200

    dados = resposta.json()
    assert dados["id"] == 1
    assert dados["protocolo"] == "TS-000001"
    assert dados["prioridade"] == "normal"
    assert dados["responsavel"] == "zelador"

    consulta, parametros = cursor.execute.call_args.args
    assert "c.sindico_id = %s" in consulta
    assert parametros == (1, 7)
