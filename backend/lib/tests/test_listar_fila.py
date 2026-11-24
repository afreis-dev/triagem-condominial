from datetime import datetime
from unittest.mock import MagicMock

import lib.listar_fila as modulo
from lib.listar_fila import CAMPOS, listar_fila
from lib.registrar_decisao import registrar_decisao


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


def outro_condominio(conexao):
    """Cria um segundo condomínio e devolve o id."""
    with conexao.cursor() as cur:
        cur.execute(
            "INSERT INTO condominios (identificador, nome, bairro) VALUES ('vila-sol', 'Vila do Sol', 'Madalena') RETURNING id"
        )
        return cur.fetchone()[0]


def test_sem_ocorrencias_devolve_lista_vazia(conexao):
    assert listar_fila(conexao=conexao) == {"ok": True, "ocorrencias": []}


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
    resposta = listar_fila(conexao=conexao)
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
            "acao": None,
            "marcaAcao": None,
        }
    ]
    assert list(resposta["ocorrencias"][0]) == list(CAMPOS)


def test_criada_em_e_texto_iso_com_fuso(conexao, condominio):
    inserir(conexao, condominio)
    criada_em = listar_fila(conexao=conexao)["ocorrencias"][0]["criadaEm"]
    assert datetime.fromisoformat(criada_em).tzinfo is not None


def test_junta_as_ocorrencias_de_todos_os_condominios(conexao, condominio):
    vila = outro_condominio(conexao)
    inserir(conexao, condominio, descricao="do Aurora")
    inserir(conexao, vila, descricao="da Vila")
    cartoes = listar_fila(conexao=conexao)["ocorrencias"]
    assert {(c["descricao"], c["condominio"]) for c in cartoes} == {
        ("do Aurora", "Residencial Aurora"),
        ("da Vila", "Vila do Sol"),
    }


def test_traz_ocorrencias_de_todos_os_status(conexao, condominio):
    for status in ("nova", "em_andamento", "concluida"):
        inserir(conexao, condominio, status=status)
    cartoes = listar_fila(conexao=conexao)["ocorrencias"]
    assert sorted(c["status"] for c in cartoes) == ["concluida", "em_andamento", "nova"]


def test_vem_na_ordem_de_chegada_e_desempata_pelo_id(conexao, condominio):
    nova = inserir(conexao, condominio, criada_em="2026-11-19 12:00:00+00")
    antiga = inserir(conexao, condominio, criada_em="2026-11-19 08:00:00+00")
    empate_1 = inserir(conexao, condominio, criada_em="2026-11-19 10:00:00+00")
    empate_2 = inserir(conexao, condominio, criada_em="2026-11-19 10:00:00+00")
    ids = [c["id"] for c in listar_fila(conexao=conexao)["ocorrencias"]]
    assert ids == [antiga, empate_1, empate_2, nova]


def test_ocorrencia_sem_classificacao_vem_com_campos_vazios(conexao, condominio):
    inserir(conexao, condominio, motivo="não classificada, revisar")
    cartao = listar_fila(conexao=conexao)["ocorrencias"][0]
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
    cartoes = {c["id"]: c for c in listar_fila(conexao=conexao)["ocorrencias"]}
    assert cartoes[com_acao]["acao"] == "eu_mesmo"
    assert cartoes[com_acao]["marcaAcao"] == "Responsável: você"
    assert cartoes[sem_acao]["acao"] is None


def test_outros_tipos_de_registro_nao_viram_marca_de_acao(conexao, condominio):
    ocorrencia_id = inserir(conexao, condominio)
    registrar_decisao(
        {"tipo": "entrada", "ocorrenciaId": ocorrencia_id, "quemDecidiu": "sistema", "origem": "morador"},
        conexao=conexao,
    )
    assert listar_fila(conexao=conexao)["ocorrencias"][0]["acao"] is None


def test_busca_de_novo_a_cada_chamada(conexao, condominio):
    inserir(conexao, condominio, descricao="primeira")
    assert len(listar_fila(conexao=conexao)["ocorrencias"]) == 1
    inserir(conexao, condominio, descricao="nova urgente", prioridade="urgente")
    cartoes = listar_fila(conexao=conexao)["ocorrencias"]
    assert [c["descricao"] for c in cartoes] == ["primeira", "nova urgente"]


def test_so_le_e_nao_confirma_nada_quando_recebe_a_conexao(conexao, condominio):
    inserir(conexao, condominio)
    conexao.commit()
    listar_fila(conexao=conexao)
    conexao.rollback()
    assert len(listar_fila(conexao=conexao)["ocorrencias"]) == 1


def test_fecha_a_conexao_que_abriu(monkeypatch):
    conexao = MagicMock()
    conexao.cursor.return_value.__enter__.return_value.fetchall.return_value = []
    monkeypatch.setattr(modulo, "conectar", lambda: conexao)
    assert listar_fila() == {"ok": True, "ocorrencias": []}
    conexao.close.assert_called_once()


def test_nao_fecha_a_conexao_recebida():
    conexao = MagicMock()
    conexao.cursor.return_value.__enter__.return_value.fetchall.return_value = []
    listar_fila(conexao=conexao)
    conexao.close.assert_not_called()
