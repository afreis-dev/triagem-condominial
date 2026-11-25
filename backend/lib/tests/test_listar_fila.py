from datetime import datetime
from unittest.mock import MagicMock

import lib.listar_fila as modulo
from lib.listar_fila import CAMPOS, listar_fila
from lib.registrar_decisao import registrar_decisao


SINDICO_TESTE_ID = 1


def inserir(conexao, condominio_id, descricao="teste", criada_em="2026-11-19 10:00:00+00", **campos):
    """Insere uma ocorrência com os campos dados e devolve o id."""
    valores = {"status": "nova", "origem": "morador", **campos}
    with conexao.cursor() as cur:
        cur.execute("SELECT nextval(pg_get_serial_sequence('ocorrencias', 'id'))")
        ocorrencia_id = cur.fetchone()[0]
        colunas = ["id", "protocolo", "condominio_id", "descricao", "criada_em", *valores]
        marcadores = ", ".join(["%s"] * len(colunas))
        cur.execute(
            f"INSERT INTO ocorrencias ({', '.join(colunas)}) VALUES ({marcadores})",
            (ocorrencia_id, f"TS-{ocorrencia_id:06d}", condominio_id, descricao, criada_em, *valores.values()),
        )
    return ocorrencia_id


def outro_condominio(conexao, sindico_id):
    """Cria um segundo condomínio e devolve o id."""
    with conexao.cursor() as cur:
        cur.execute(
            """
            INSERT INTO condominios (identificador, nome, bairro, sindico_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            ("vila-sol", "Vila do Sol", "Madalena", sindico_id),
        )
        return cur.fetchone()[0]


def test_sem_ocorrencias_devolve_lista_vazia(conexao):
    assert listar_fila(SINDICO_TESTE_ID, conexao=conexao) == {"ok": True, "ocorrencias": []}


def test_devolve_os_campos_do_cartao(conexao, condominio):
    ocorrencia_id = inserir(
        conexao,
        condominio,
        descricao="Lâmpada do hall queimada",
        prioridade="normal",
        categoria="manutencao",
        responsavel_sugerido="zelador",
        motivo="manutenção simples de área comum",
    )
    resposta = listar_fila(SINDICO_TESTE_ID, conexao=conexao)
    assert resposta["ok"] is True
    assert resposta["ocorrencias"] == [
        {
            "id": ocorrencia_id,
            "protocolo": f"TS-{ocorrencia_id:06d}",
            "condominioId": condominio,
            "condominio": "Residencial Aurora",
            "descricao": "Lâmpada do hall queimada",
            "origem": "morador",
            "status": "nova",
            "prioridade": "normal",
            "categoria": "manutencao",
            "responsavelSugerido": "zelador",
            "motivo": "manutenção simples de área comum",
            "travada": False,
            "criadaEm": "2026-11-19T10:00:00+00:00",
            "concluidaEm": None,
            "acao": None,
            "marcaAcao": None,
        }
    ]
    assert list(resposta["ocorrencias"][0]) == list(CAMPOS)


def test_criada_em_e_texto_iso_com_fuso(conexao, condominio):
    inserir(conexao, condominio)
    criada_em = listar_fila(SINDICO_TESTE_ID, conexao=conexao)["ocorrencias"][0]["criadaEm"]
    assert datetime.fromisoformat(criada_em).tzinfo is not None


def test_devolve_data_de_conclusao_em_utc(conexao, condominio):
    inserir(conexao, condominio, status="concluida", concluida_em="2026-11-20 09:00:00-03")
    cartao, = listar_fila(conexao=conexao)["ocorrencias"]
    assert cartao["concluidaEm"] == "2026-11-20T12:00:00+00:00"


def test_junta_as_ocorrencias_de_todos_os_condominios(conexao, condominio):
    vila = outro_condominio(conexao, SINDICO_TESTE_ID)
    inserir(conexao, condominio, descricao="do Aurora")
    inserir(conexao, vila, descricao="da Vila")
    cartoes = listar_fila(SINDICO_TESTE_ID, conexao=conexao)["ocorrencias"]
    assert {(c["descricao"], c["condominio"]) for c in cartoes} == {
        ("do Aurora", "Residencial Aurora"),
        ("da Vila", "Vila do Sol"),
    }


def test_traz_ocorrencias_de_todos_os_status(conexao, condominio):
    for status in ("nova", "em_andamento", "concluida"):
        inserir(conexao, condominio, status=status)
    cartoes = listar_fila(SINDICO_TESTE_ID, conexao=conexao)["ocorrencias"]
    assert sorted(c["status"] for c in cartoes) == ["concluida", "em_andamento", "nova"]


def test_vem_na_ordem_de_chegada_e_desempata_pelo_id(conexao, condominio):
    nova = inserir(conexao, condominio, criada_em="2026-11-19 12:00:00+00")
    antiga = inserir(conexao, condominio, criada_em="2026-11-19 08:00:00+00")
    empate_1 = inserir(conexao, condominio, criada_em="2026-11-19 10:00:00+00")
    empate_2 = inserir(conexao, condominio, criada_em="2026-11-19 10:00:00+00")
    ids = [c["id"] for c in listar_fila(SINDICO_TESTE_ID, conexao=conexao)["ocorrencias"]]
    assert ids == [antiga, empate_1, empate_2, nova]


def test_ocorrencia_sem_classificacao_vem_com_campos_vazios(conexao, condominio):
    inserir(conexao, condominio, motivo="não classificada, revisar")
    cartao = listar_fila(SINDICO_TESTE_ID, conexao=conexao)["ocorrencias"][0]
    assert cartao["prioridade"] is None
    assert cartao["categoria"] is None
    assert cartao["responsavelSugerido"] is None
    assert cartao["motivo"] == "não classificada, revisar"


def test_traz_a_marca_da_ultima_acao_do_sindico(conexao, condominio):
    com_acao = inserir(conexao, condominio, descricao="com ação")
    sem_acao = inserir(conexao, condominio, descricao="sem ação")
    for acao in ({"acao": "delegar", "responsavel": "zelador"}, {"acao": "eu_mesmo"}):
        resposta = registrar_decisao(
            {"tipo": "acao", "ocorrenciaId": com_acao, "quemDecidiu": "sindico", **acao}, conexao=conexao
        )
        assert resposta["ok"] is True
    cartoes = {c["id"]: c for c in listar_fila(SINDICO_TESTE_ID, conexao=conexao)["ocorrencias"]}
    assert cartoes[com_acao]["acao"] == "eu_mesmo"
    assert cartoes[com_acao]["marcaAcao"] == "Responsável: você"
    assert cartoes[sem_acao]["acao"] is None


def test_outros_tipos_de_registro_nao_viram_marca_de_acao(conexao, condominio):
    ocorrencia_id = inserir(conexao, condominio)
    registrar_decisao(
        {"tipo": "entrada", "ocorrenciaId": ocorrencia_id, "quemDecidiu": "sistema", "origem": "morador"},
        conexao=conexao,
    )
    assert listar_fila(SINDICO_TESTE_ID, conexao=conexao)["ocorrencias"][0]["acao"] is None


def test_busca_de_novo_a_cada_chamada(conexao, condominio):
    inserir(conexao, condominio, descricao="primeira")
    assert len(listar_fila(SINDICO_TESTE_ID, conexao=conexao)["ocorrencias"]) == 1
    inserir(conexao, condominio, descricao="nova urgente", prioridade="urgente")
    cartoes = listar_fila(SINDICO_TESTE_ID, conexao=conexao)["ocorrencias"]
    assert [c["descricao"] for c in cartoes] == ["primeira", "nova urgente"]


def test_so_le_e_nao_confirma_nada_quando_recebe_a_conexao(conexao, condominio):
    inserir(conexao, condominio)
    conexao.commit()
    listar_fila(SINDICO_TESTE_ID, conexao=conexao)
    conexao.rollback()
    assert len(listar_fila(SINDICO_TESTE_ID, conexao=conexao)["ocorrencias"]) == 1


def test_fecha_a_conexao_que_abriu(monkeypatch):
    conexao = MagicMock()
    conexao.cursor.return_value.__enter__.return_value.fetchall.return_value = []
    monkeypatch.setattr(modulo, "conectar", lambda: conexao)
    assert listar_fila(SINDICO_TESTE_ID) == {"ok": True, "ocorrencias": []}
    conexao.close.assert_called_once()


def test_nao_fecha_a_conexao_recebida():
    conexao = MagicMock()
    conexao.cursor.return_value.__enter__.return_value.fetchall.return_value = []
    listar_fila(SINDICO_TESTE_ID, conexao=conexao)
    conexao.close.assert_not_called()


def test_fila_filtra_pelo_sindico_autenticado():
    conexao = MagicMock()
    cursor = conexao.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = []

    sindico_id = 42

    resultado = listar_fila(sindico_id, conexao=conexao)

    consulta, parametros = cursor.execute.call_args.args

    assert "c.sindico_id = %s" in consulta
    assert parametros == (42,)
    assert resultado == {"ok": True, "ocorrencias": []}
    conexao.close.assert_not_called()


def test_sindico_nao_visualiza_ocorrencias_de_outro(
    conexao, condominio, sindico
):
    with conexao.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sindicos (nome, email)
            VALUES (%s, %s)
            RETURNING id
            """,
            ("Outro Síndico", "outro@teste.com"),
        )
        outro_sindico_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO condominios (
                identificador, nome, bairro, sindico_id
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            ("outro-condominio", "Outro Condomínio", "Centro", outro_sindico_id),
        )
        outro_condominio_id = cur.fetchone()[0]

    ocorrencia_propria = inserir(
        conexao, condominio, descricao="Ocorrência permitida"
    )
    ocorrencia_alheia = inserir(
        conexao, outro_condominio_id, descricao="Ocorrência proibida"
    )

    resultado = listar_fila(sindico, conexao=conexao)
    ids = [item["id"] for item in resultado["ocorrencias"]]

    assert ocorrencia_propria in ids
    assert ocorrencia_alheia not in ids

    resultado_outro = listar_fila(outro_sindico_id, conexao=conexao)
    ids_outro = [item["id"] for item in resultado_outro["ocorrencias"]]

    assert ocorrencia_alheia in ids_outro
    assert ocorrencia_propria not in ids_outro
