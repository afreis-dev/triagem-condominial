import re

from .classificar import classificar
from .conexao import conectar
from .dominio import ORIGENS, PRIORIDADES, inteiro, texto
from .registrar_decisao import registrar_decisao

ORIGENS_FORMULARIO = ("morador", "proprietario", "funcionario")
EXIGEM_APARTAMENTO = ()
LIMITE_DESCRICAO = 2000
SEM_CLASSIFICACAO = {
    "prioridade": None,
    "categoria": None,
    "responsavel_sugerido": None,
    "motivo": "não classificada, revisar",
    "travada": False,
    "palavra_de_risco": None,
    "fonte": None,
}

INSERIR = """
    INSERT INTO ocorrencias
        (id, protocolo, condominio_id, origem, nome, apartamento, celular, local, descricao, status)
    VALUES
        (%(id)s, %(protocolo)s, %(condominio_id)s, %(origem)s, %(nome)s, %(apartamento)s,
         %(celular)s, %(local)s, %(descricao)s, 'nova')
"""

GUARDAR_CLASSIFICACAO = """
    UPDATE ocorrencias
       SET prioridade = %(prioridade)s, categoria = %(categoria)s,
           responsavel_sugerido = %(responsavel_sugerido)s, motivo = %(motivo)s,
           travada = %(travada)s, palavra_de_risco = %(palavra_de_risco)s, fonte = %(fonte)s
     WHERE id = %(id)s
"""


def _validar(dados):
    """Confere os campos da ocorrência e devolve (erros, valores prontos para gravar)."""
    erros = {}

    origem = texto(dados.get("origem"))
    if origem not in ORIGENS:
        erros["origem"] = "Origem inválida"

    condominio = dados.get("condominioId")
    condominio_id = inteiro(condominio)
    if condominio is None or (isinstance(condominio, str) and not condominio.strip()):
        erros["condominioId"] = "Escolha o condomínio"
    elif condominio_id is None:
        erros["condominioId"] = "Condomínio não encontrado"

    apartamento = texto(dados.get("apartamento"))
    if apartamento is None and origem in EXIGEM_APARTAMENTO:
        erros["apartamento"] = "Informe o apartamento"

    celular = re.sub(r"[\s()\-]", "", texto(dados.get("celular")) or "")
    if not celular:
        celular = None
        if origem in ORIGENS_FORMULARIO:
            erros["celular"] = "Informe o celular"
    elif not re.fullmatch(r"[0-9]{10,11}", celular):
        erros["celular"] = "Celular deve ter 10 ou 11 dígitos"

    descricao = texto(dados.get("descricao"))
    if descricao is None:
        erros["descricao"] = "Descreva a ocorrência"
    elif len(descricao) > LIMITE_DESCRICAO:
        erros["descricao"] = "A descrição deve ter no máximo 2000 caracteres"

    valores = {
        "condominio_id": condominio_id,
        "origem": origem,
        "nome": texto(dados.get("nome")),
        "apartamento": apartamento,
        "celular": celular,
        "local": texto(dados.get("local")),
        "descricao": descricao,
    }
    return erros, valores


def _classificar(descricao):
    """Classifica a descrição. Se a classificação falhar ou vier inválida, devolve None."""
    try:
        resultado = classificar(descricao)
        if resultado["prioridade"] not in PRIORIDADES:
            return None
        return {
            "prioridade": resultado["prioridade"],
            "categoria": resultado["categoria"],
            "responsavel_sugerido": resultado["responsavelSugerido"],
            "motivo": resultado["motivo"],
            "travada": bool(resultado["travada"]),
            "palavra_de_risco": resultado["palavraDeRisco"],
            "fonte": resultado["fonte"],
        }
    except Exception:
        return None


def _guardar_e_registrar(conexao, ocorrencia_id, origem, classificacao):
    """Guarda a classificação e registra a entrada. Se algo falhar, desfaz só esta etapa e levanta o erro."""
    with conexao.cursor() as cur:
        cur.execute("SAVEPOINT guardar_classificacao")
        try:
            cur.execute(GUARDAR_CLASSIFICACAO, {**classificacao, "id": ocorrencia_id})
            entrada = registrar_decisao(
                {
                    "tipo": "entrada",
                    "ocorrenciaId": ocorrencia_id,
                    "quemDecidiu": "sistema",
                    "origem": origem,
                    "prioridadeSugerida": classificacao["prioridade"],
                },
                conexao=conexao,
            )
            if not entrada["ok"]:
                raise RuntimeError(f"registro de entrada recusado: {entrada['erros']}")
        except Exception:
            cur.execute("ROLLBACK TO SAVEPOINT guardar_classificacao")
            raise
        cur.execute("RELEASE SAVEPOINT guardar_classificacao")


def _salvar(conexao, erros, valores, proprio):
    """Confere o condomínio, grava a ocorrência, guarda a classificação e registra a entrada."""
    with conexao.cursor() as cur:
        cur.execute("SELECT 1 FROM condominios WHERE id = %s", (valores["condominio_id"],))
        if cur.fetchone() is None:
            erros["condominioId"] = "Condomínio não encontrado"
        if erros:
            return {"ok": False, "erros": erros}
        cur.execute("SELECT nextval(pg_get_serial_sequence('ocorrencias', 'id'))")
        ocorrencia_id = cur.fetchone()[0]
        protocolo = f"TS-{ocorrencia_id:06d}"
        cur.execute(INSERIR, {**valores, "id": ocorrencia_id, "protocolo": protocolo})
    if proprio:
        conexao.commit()

    classificacao = _classificar(valores["descricao"]) or SEM_CLASSIFICACAO
    try:
        _guardar_e_registrar(conexao, ocorrencia_id, valores["origem"], classificacao)
    except Exception:
        _guardar_e_registrar(conexao, ocorrencia_id, valores["origem"], SEM_CLASSIFICACAO)
    if proprio:
        conexao.commit()
    return {"ok": True, "ocorrenciaId": ocorrencia_id, "protocolo": protocolo}


def salvar_ocorrencia(dados, conexao=None):
    """Valida e grava a ocorrência, classifica o texto e registra a entrada. Com conexão própria, confirma sozinha."""
    erros, valores = _validar(dados if isinstance(dados, dict) else {})
    if valores["condominio_id"] is None:
        return {"ok": False, "erros": erros}
    proprio = conexao is None
    if proprio:
        conexao = conectar()
    try:
        return _salvar(conexao, erros, valores, proprio)
    except Exception:
        if proprio:
            conexao.rollback()
        raise
    finally:
        if proprio:
            conexao.close()
