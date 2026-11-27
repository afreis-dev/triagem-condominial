from fastapi.testclient import TestClient

import main
import lib.auth_deps as auth_deps
from lib.auth import criar_token, token_csrf


class ConexaoDoTeste:
    """Evita fechar a conexão gerenciada pelo pytest."""

    def __init__(self, conexao):
        self.conexao = conexao

    def __getattr__(self, nome):
        return getattr(self.conexao, nome)

    def __enter__(self):
        return self.conexao.__enter__()

    def __exit__(self, *args):
        return self.conexao.__exit__(*args)

    def close(self):
        pass


def test_isolamento_real_entre_duas_carteiras(conexao, monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET",
        "segredo-exclusivo-para-integracao-h16-2026",
    )

    # Cria os dados isolados no schema de teste.
    with conexao.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE responsaveis (
                condominio_id INTEGER REFERENCES condominios(id),
                papel TEXT NOT NULL
            )
        """)

        sindicos = []
        ocorrencias = {}

        for numero in (1, 2):
            cursor.execute(
                """
                INSERT INTO sindicos (nome, email)
                VALUES (%s, %s) RETURNING id
                """,
                (f"Síndico {numero}", f"sindico{numero}@teste.com"),
            )
            sindico_id = cursor.fetchone()[0]
            sindicos.append(sindico_id)

            cursor.execute(
                """
                INSERT INTO condominios
                    (identificador, nome, sindico_id)
                VALUES (%s, %s, %s) RETURNING id
                """,
                (
                    f"condominio-{numero}",
                    f"Condomínio {numero}",
                    sindico_id,
                ),
            )
            condominio_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO responsaveis (condominio_id, papel)
                VALUES (%s, 'sindico')
                """,
                (condominio_id,),
            )

            for tipo, status in (
                ("prioridade", "nova"),
                ("acao", "nova"),
                ("conclusao", "em_andamento"),
            ):
                cursor.execute(
                    """
                    INSERT INTO ocorrencias
                        (protocolo, condominio_id, origem,
                         descricao, status, prioridade)
                    VALUES (%s, %s, 'morador', %s, %s, 'normal')
                    RETURNING id
                    """,
                    (
                        f"TEST-{numero}-{tipo}",
                        condominio_id,
                        f"Ocorrência de teste {tipo}",
                        status,
                    ),
                )
                ocorrencias[(numero, tipo)] = cursor.fetchone()[0]

    conexao.commit()

    # Usa PostgreSQL real, inclusive para validar os tokens.
    monkeypatch.setattr(
        main, "conectar", lambda: ConexaoDoTeste(conexao)
    )
    monkeypatch.setattr(
        auth_deps, "conectar", lambda: ConexaoDoTeste(conexao)
    )

    def requisitar(api, metodo, caminho, headers, dados=None):
        argumentos = {"headers": headers}
        if dados is not None:
            argumentos["json"] = dados
        return getattr(api, metodo)(caminho, **argumentos)

    with TestClient(main.app) as api:
        tokens = []
        for sid in sindicos:
            token = criar_token(sid)
            tokens.append({"Cookie": f"triagem_sessao={token}", "X-CSRF-Token": token_csrf(token)})

        # Cada síndico tenta acessar ocorrências do outro.
        for indice, alvo in ((0, 2), (1, 1)):
            headers = tokens[indice]
            id_alheio = ocorrencias[(alvo, "prioridade")]

            operacoes = [
                ("get", f"/ocorrencias/{id_alheio}", None),
                (
                    "get",
                    f"/api/ocorrencias/{id_alheio}/decisoes",
                    None,
                ),
                (
                    "get",
                    f"/ocorrencias/{id_alheio}/responsaveis",
                    None,
                ),
                (
                    "patch",
                    f"/ocorrencias/{id_alheio}/prioridade",
                    {
                        "prioridade": "alta",
                        "motivo": "Teste de isolamento",
                    },
                ),
                (
                    "post",
                    f"/ocorrencias/{id_alheio}/acoes",
                    {"acao": "eu_mesmo", "nota": "Teste"},
                ),
                (
                    "patch",
                    f"/api/ocorrencias/{id_alheio}/concluir",
                    None,
                ),
            ]

            for metodo, caminho, dados in operacoes:
                resposta = requisitar(
                    api, metodo, caminho, headers, dados
                )
                assert resposta.status_code == 404, (
                    f"{metodo.upper()} {caminho}: "
                    f"esperado 404, recebido {resposta.status_code}"
                )

        # Confirma que as tentativas não alteraram o banco.
        with conexao.cursor() as cursor:
            for numero in (1, 2):
                oid = ocorrencias[(numero, "prioridade")]
                cursor.execute(
                    """
                    SELECT status, prioridade
                    FROM ocorrencias WHERE id = %s
                    """,
                    (oid,),
                )
                assert cursor.fetchone() == ("nova", "normal")

                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM registros_decisao
                    WHERE ocorrencia_id = %s
                    """,
                    (oid,),
                )
                assert cursor.fetchone()[0] == 0

        # Verifica que o síndico 1 acessa a própria carteira.
        headers = tokens[0]
        prioridade_id = ocorrencias[(1, "prioridade")]
        acao_id = ocorrencias[(1, "acao")]
        conclusao_id = ocorrencias[(1, "conclusao")]

        assert api.get(
            f"/ocorrencias/{prioridade_id}",
            headers=headers,
        ).status_code == 200

        assert api.get(
            f"/api/ocorrencias/{prioridade_id}/decisoes",
            headers=headers,
        ).status_code == 200

        assert api.get(
            f"/ocorrencias/{prioridade_id}/responsaveis",
            headers=headers,
        ).status_code == 200

        assert api.patch(
            f"/ocorrencias/{prioridade_id}/prioridade",
            headers=headers,
            json={
                "prioridade": "alta",
                "motivo": "Teste autorizado",
            },
        ).status_code == 200

        assert api.post(
            f"/ocorrencias/{acao_id}/acoes",
            headers=headers,
            json={"acao": "eu_mesmo", "nota": "Autorizado"},
        ).status_code == 201

        assert api.patch(
            f"/api/ocorrencias/{conclusao_id}/concluir",
            headers=headers,
        ).status_code == 200

        # Confere que as alterações foram persistidas.
        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT prioridade FROM ocorrencias WHERE id = %s",
                (prioridade_id,),
            )
            assert cursor.fetchone()[0] == "alta"

            cursor.execute(
                "SELECT status FROM ocorrencias WHERE id = %s",
                (acao_id,),
            )
            assert cursor.fetchone()[0] == "em_andamento"

            cursor.execute(
                "SELECT status FROM ocorrencias WHERE id = %s",
                (conclusao_id,),
            )
            assert cursor.fetchone()[0] == "concluida"

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM registros_decisao
                WHERE ocorrencia_id IN (%s, %s, %s)
                """,
                (prioridade_id, acao_id, conclusao_id),
            )
            assert cursor.fetchone()[0] == 3
