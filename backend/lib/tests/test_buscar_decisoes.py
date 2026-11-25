from datetime import datetime

from lib.registrar_decisao import buscar_decisoes, registrar_decisao


def test_buscar_historico_completo(conexao, criar_ocorrencia):
    ocorrencia_id = criar_ocorrencia(travada=True)

    registros = [
        {
            "tipo": "entrada",
            "quemDecidiu": "sistema",
            "origem": "morador",
            "prioridadeSugerida": "urgente",
        },
        {
            "tipo": "prioridade_alterada",
            "quemDecidiu": "sindico",
            "prioridadeSugerida": "urgente",
            "prioridadeFinal": "normal",
            "motivo": "Risco descartado após vistoria",
        },
        {
            "tipo": "acao",
            "quemDecidiu": "sindico",
            "acao": "delegar",
            "responsavel": "zelador",
            "nota": "Verificar o local",
        },
        {
            "tipo": "conclusao",
            "quemDecidiu": "sindico",
        },
    ]

    ids = []

    for registro in registros:
        resultado = registrar_decisao(
            {"ocorrenciaId": ocorrencia_id, **registro},
            conexao=conexao,
        )
        assert resultado["ok"] is True
        ids.append(resultado["registroId"])

    historico = buscar_decisoes(ocorrencia_id, conexao)

    assert len(historico) == 4
    assert [r["id"] for r in historico] == ids
    assert [r["tipo"] for r in historico] == [
        "entrada",
        "prioridade_alterada",
        "acao",
        "conclusao",
    ]

    assert historico[0]["quemDecidiu"] == "sistema"
    assert historico[0]["origem"] == "morador"
    assert historico[1]["prioridadeSugerida"] == "urgente"
    assert historico[1]["prioridadeFinal"] == "normal"
    assert historico[1]["motivo"] == "Risco descartado após vistoria"
    assert historico[1]["rebaixouTravada"] is True
    assert historico[2]["acao"] == "delegar"
    assert historico[2]["responsavel"] == "zelador"
    assert historico[2]["nota"] == "Verificar o local"

    datas = [
        datetime.fromisoformat(r["dataHora"])
        for r in historico
    ]

    assert datas == sorted(datas)
    assert all(d.tzinfo is not None for d in datas)
    assert all(
        r["ocorrenciaId"] == ocorrencia_id
        for r in historico
    )


def test_historico_vazio(conexao, criar_ocorrencia):
    ocorrencia_id = criar_ocorrencia()

    assert buscar_decisoes(ocorrencia_id, conexao) == []


def test_historico_nao_mistura_ocorrencias(conexao, criar_ocorrencia):
    primeira = criar_ocorrencia()
    segunda = criar_ocorrencia()

    for ocorrencia_id in (primeira, segunda):
        resultado = registrar_decisao(
            {
                "ocorrenciaId": ocorrencia_id,
                "tipo": "conclusao",
                "quemDecidiu": "sindico",
            },
            conexao=conexao,
        )
        assert resultado["ok"] is True

    historico = buscar_decisoes(primeira, conexao)

    assert len(historico) == 1
    assert historico[0]["ocorrenciaId"] == primeira


def test_historico_retorna_data_agendada(conexao, criar_ocorrencia):
    ocorrencia_id = criar_ocorrencia()

    resultado = registrar_decisao(
        {
            "ocorrenciaId": ocorrencia_id,
            "tipo": "acao",
            "quemDecidiu": "sindico",
            "acao": "agendar",
            "dataAgendada": "2026-12-05",
        },
        conexao=conexao,
    )

    assert resultado["ok"] is True

    historico = buscar_decisoes(ocorrencia_id, conexao)

    assert len(historico) == 1
    assert historico[0]["acao"] == "agendar"
    assert historico[0]["dataAgendada"] == "2026-12-05"
    assert historico[0]["rebaixouTravada"] is False