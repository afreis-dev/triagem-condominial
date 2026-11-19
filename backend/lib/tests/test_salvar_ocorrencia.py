import pytest

import lib.salvar_ocorrencia as modulo
from lib.salvar_ocorrencia import salvar_ocorrencia

CLASSIFICACAO = {
    "prioridade": "urgente",
    "categoria": "manutencao",
    "responsavelSugerido": "zelador",
    "motivo": "palavra de risco: gás",
    "travada": True,
    "palavraDeRisco": "gás",
    "fonte": "regras",
}

ERROS_SEM_BANCO = [
    (None, {"origem": "Origem inválida", "condominioId": "Escolha o condomínio", "descricao": "Descreva a ocorrência"}),
    ({}, {"origem": "Origem inválida", "condominioId": "Escolha o condomínio", "descricao": "Descreva a ocorrência"}),
    (
        {"condominioId": "  ", "origem": "morador", "celular": "81999991234", "descricao": "x"},
        {"condominioId": "Escolha o condomínio"},
    ),
    (
        {"condominioId": "abc", "origem": "morador", "celular": "81999991234", "descricao": "x"},
        {"condominioId": "Condomínio não encontrado"},
    ),
    (
        {"condominioId": True, "origem": "morador", "celular": "81999991234", "descricao": "x"},
        {"condominioId": "Condomínio não encontrado"},
    ),
    (
        {"condominioId": "9" * 5000, "origem": "morador", "celular": "81999991234", "descricao": "x"},
        {"condominioId": "Condomínio não encontrado"},
    ),
]

ERROS_COM_BANCO = [
    ({"descricao": ""}, {"descricao": "Descreva a ocorrência"}),
    ({"descricao": "   "}, {"descricao": "Descreva a ocorrência"}),
    ({"descricao": "a" * 2001}, {"descricao": "A descrição deve ter no máximo 2000 caracteres"}),
    ({"celular": ""}, {"celular": "Informe o celular"}),
    ({"celular": "()-"}, {"celular": "Informe o celular"}),
    ({"celular": "12345"}, {"celular": "Celular deve ter 10 ou 11 dígitos"}),
    ({"celular": "8199999abcd"}, {"celular": "Celular deve ter 10 ou 11 dígitos"}),
    ({"celular": "819999912345"}, {"celular": "Celular deve ter 10 ou 11 dígitos"}),
    ({"origem": "vizinho"}, {"origem": "Origem inválida"}),
    ({"condominioId": 9999}, {"condominioId": "Condomínio não encontrado"}),
    (
        {"descricao": "", "celular": "1", "origem": "vizinho", "condominioId": 9999},
        {
            "descricao": "Descreva a ocorrência",
            "celular": "Celular deve ter 10 ou 11 dígitos",
            "origem": "Origem inválida",
            "condominioId": "Condomínio não encontrado",
        },
    ),
]


def formulario(condominio, **campos):
    """Monta os dados de uma ocorrência completa vinda do formulário."""
    base = {
        "condominioId": condominio,
        "origem": "morador",
        "nome": "Ana Lima",
        "apartamento": "302",
        "celular": "(81) 99999-1234",
        "local": "garagem",
        "descricao": "o portão da garagem travou aberto",
    }
    return {**base, **campos}


def contar(conexao, tabela):
    """Conta as linhas de uma tabela."""
    with conexao.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {tabela}")
        return cur.fetchone()[0]


def linha(conexao, consulta):
    """Devolve a primeira linha de uma consulta."""
    with conexao.cursor() as cur:
        cur.execute(consulta)
        return cur.fetchone()


@pytest.mark.parametrize("dados, erros", ERROS_SEM_BANCO)
def test_erros_que_nao_precisam_de_banco(dados, erros):
    assert salvar_ocorrencia(dados) == {"ok": False, "erros": erros}


def test_grava_a_ocorrencia_do_formulario(conexao, condominio):
    resposta = salvar_ocorrencia(formulario(condominio), conexao=conexao)
    assert resposta == {"ok": True, "ocorrenciaId": 1, "protocolo": "TS-000001"}
    assert linha(
        conexao,
        "SELECT condominio_id, origem, nome, apartamento, celular, local, descricao, status FROM ocorrencias",
    ) == (condominio, "morador", "Ana Lima", "302", "81999991234", "garagem", "o portão da garagem travou aberto", "nova")
    assert linha(conexao, "SELECT prioridade, motivo FROM ocorrencias")[0] in ("urgente", "alta", "normal", "baixa")


def test_protocolo_vem_do_id(conexao, condominio):
    protocolos = [salvar_ocorrencia(formulario(condominio), conexao=conexao)["protocolo"] for _ in range(3)]
    assert protocolos == ["TS-000001", "TS-000002", "TS-000003"]


def test_protocolo_cresce_depois_de_999999(conexao, condominio):
    linha(conexao, "SELECT setval(pg_get_serial_sequence('ocorrencias', 'id'), 999999)")
    resposta = salvar_ocorrencia(formulario(condominio), conexao=conexao)
    assert resposta["ocorrenciaId"] == 1000000
    assert resposta["protocolo"] == "TS-1000000"


def test_guarda_a_classificacao(conexao, condominio, monkeypatch):
    monkeypatch.setattr(modulo, "classificar", lambda texto: CLASSIFICACAO)
    salvar_ocorrencia(formulario(condominio, descricao="cheiro de gás no bloco B"), conexao=conexao)
    assert linha(
        conexao,
        "SELECT prioridade, categoria, responsavel_sugerido, motivo, travada, palavra_de_risco, fonte FROM ocorrencias",
    ) == ("urgente", "manutencao", "zelador", "palavra de risco: gás", True, "gás", "regras")


def test_chama_a_classificacao_com_a_descricao(conexao, condominio, monkeypatch):
    recebidos = []
    monkeypatch.setattr(modulo, "classificar", lambda texto: recebidos.append(texto) or CLASSIFICACAO)
    salvar_ocorrencia(formulario(condominio, descricao="  cheiro de gás  "), conexao=conexao)
    assert recebidos == ["cheiro de gás"]


def test_registra_a_entrada_no_historico(conexao, condominio, monkeypatch):
    monkeypatch.setattr(modulo, "classificar", lambda texto: CLASSIFICACAO)
    resposta = salvar_ocorrencia(formulario(condominio), conexao=conexao)
    assert contar(conexao, "registros_decisao") == 1
    assert linha(
        conexao,
        "SELECT ocorrencia_id, tipo, quem_decidiu, origem, prioridade_sugerida FROM registros_decisao",
    ) == (resposta["ocorrenciaId"], "entrada", "sistema", "morador", "urgente")


def test_mensagem_colada_sem_nome_nem_celular(conexao, condominio):
    resposta = salvar_ocorrencia(
        {"condominioId": condominio, "origem": "whatsapp_sindico", "descricao": "o portão da garagem travou aberto"},
        conexao=conexao,
    )
    assert resposta["ok"] is True
    assert linha(conexao, "SELECT origem, nome, celular FROM ocorrencias") == ("whatsapp_sindico", None, None)


def test_funcionario_sem_apartamento(conexao, condominio):
    resposta = salvar_ocorrencia(formulario(condominio, origem="funcionario", apartamento=""), conexao=conexao)
    assert resposta["ok"] is True
    assert linha(conexao, "SELECT apartamento FROM ocorrencias") == (None,)


def test_aceita_condominio_como_texto_numerico(conexao, condominio):
    assert salvar_ocorrencia(formulario(str(condominio)), conexao=conexao)["ok"] is True


def test_aceita_descricao_com_2000_caracteres_emoji_e_quebra_de_linha(conexao, condominio):
    descricao = ("água 💧\n" * 400)[:2000]
    resposta = salvar_ocorrencia(formulario(condominio, descricao=descricao), conexao=conexao)
    assert resposta["ok"] is True
    assert linha(conexao, "SELECT descricao FROM ocorrencias") == (descricao.strip(),)


@pytest.mark.parametrize("campos, erros", ERROS_COM_BANCO)
def test_devolve_os_erros_e_nao_grava(conexao, condominio, campos, erros):
    assert salvar_ocorrencia(formulario(condominio, **campos), conexao=conexao) == {"ok": False, "erros": erros}
    assert contar(conexao, "ocorrencias") == 0
    assert contar(conexao, "registros_decisao") == 0


def test_apartamento_obrigatorio_quando_o_po_decidir(conexao, condominio, monkeypatch):
    monkeypatch.setattr(modulo, "EXIGEM_APARTAMENTO", ("morador", "proprietario"))
    assert salvar_ocorrencia(formulario(condominio, apartamento=""), conexao=conexao) == {
        "ok": False,
        "erros": {"apartamento": "Informe o apartamento"},
    }
    assert salvar_ocorrencia(formulario(condominio, origem="funcionario", apartamento=""), conexao=conexao)["ok"] is True


def classificacao_que_falha(texto):
    """Simula uma classificação que quebra."""
    raise RuntimeError("serviço fora do ar")


def test_aceita_celular_e_apartamento_numericos(conexao, condominio):
    resposta = salvar_ocorrencia(formulario(condominio, celular=81999991234, apartamento=101), conexao=conexao)
    assert resposta["ok"] is True
    assert linha(conexao, "SELECT celular, apartamento FROM ocorrencias") == ("81999991234", "101")


def test_limpa_caractere_nulo_e_surrogate_do_texto(conexao, condominio):
    resposta = salvar_ocorrencia(formulario(condominio, descricao="abc\x00def \ud800", nome="Ana\x00"), conexao=conexao)
    assert resposta["ok"] is True
    assert linha(conexao, "SELECT descricao, nome FROM ocorrencias") == ("abcdef ?", "Ana")


def test_nao_confirma_a_transacao_quando_recebe_a_conexao(conexao, condominio):
    salvar_ocorrencia(formulario(condominio), conexao=conexao)
    conexao.rollback()
    assert contar(conexao, "ocorrencias") == 0
    assert contar(conexao, "registros_decisao") == 0


def test_etapa_final_que_falha_cai_em_nao_classificada_e_registra_a_entrada(conexao, condominio, monkeypatch):
    monkeypatch.setattr(modulo, "classificar", lambda texto: {**CLASSIFICACAO, "motivo": "a\x00b"})
    resposta = salvar_ocorrencia(formulario(condominio), conexao=conexao)
    assert resposta == {"ok": True, "ocorrenciaId": 1, "protocolo": "TS-000001"}
    assert linha(conexao, "SELECT prioridade, motivo FROM ocorrencias") == (None, "não classificada, revisar")
    assert contar(conexao, "registros_decisao") == 1
    assert linha(conexao, "SELECT tipo, prioridade_sugerida FROM registros_decisao") == ("entrada", None)


@pytest.mark.parametrize(
    "classificar",
    [classificacao_que_falha, lambda texto: {}, lambda texto: None, lambda texto: {**CLASSIFICACAO, "prioridade": "critica"}],
)
def test_ocorrencia_continua_salva_se_a_classificacao_falhar(conexao, condominio, monkeypatch, classificar):
    monkeypatch.setattr(modulo, "classificar", classificar)
    resposta = salvar_ocorrencia(formulario(condominio), conexao=conexao)
    assert resposta == {"ok": True, "ocorrenciaId": 1, "protocolo": "TS-000001"}
    assert linha(
        conexao,
        "SELECT status, prioridade, categoria, responsavel_sugerido, motivo, travada, fonte FROM ocorrencias",
    ) == ("nova", None, None, None, "não classificada, revisar", False, None)
    assert linha(conexao, "SELECT tipo, prioridade_sugerida FROM registros_decisao") == ("entrada", None)


def test_ocorrencia_e_gravada_antes_de_classificar(conexao, condominio, monkeypatch):
    vistas = []

    def espiar(texto):
        vistas.append(contar(conexao, "ocorrencias"))
        return CLASSIFICACAO

    monkeypatch.setattr(modulo, "classificar", espiar)
    salvar_ocorrencia(formulario(condominio), conexao=conexao)
    assert vistas == [1]
