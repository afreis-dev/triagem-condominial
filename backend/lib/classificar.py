import re
import unicodedata

from .dominio import PRIORIDADES
from .regras import REGRAS


def normalizar(texto):
    """Devolve o texto em minúsculas, sem acento e sem pontuação. Se não for texto, devolve vazio."""
    if not isinstance(texto, str):
        return ""
    decomposto = unicodedata.normalize("NFKD", texto.lower())
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sem_acento).strip()


REGRAS_NORMALIZADAS = tuple((tuple(normalizar(palavra) for palavra in regra.palavras), regra) for regra in REGRAS)

NAO_RECONHECIDA = {
    "prioridade": "normal",
    "categoria": "duvida",
    "responsavelSugerido": "sindico",
    "motivo": "não reconhecida, revisar",
    "travada": False,
    "palavraDeRisco": None,
    "fonte": "regras",
}


def _aparece(palavra, texto):
    """Diz se a palavra aparece inteira no texto já padronizado."""
    return f" {palavra} " in f" {texto} "


def _resultado(regra):
    """Monta a resposta no formato do contrato a partir da regra encontrada."""
    return {
        "prioridade": regra.prioridade,
        "categoria": regra.categoria,
        "responsavelSugerido": regra.responsavel,
        "motivo": regra.motivo,
        "travada": False,
        "palavraDeRisco": None,
        "fonte": "regras",
    }


def classificar(texto):
    """Procura no texto as palavras das regras do PO e devolve a de maior prioridade (no empate, a primeira da tabela). Sem regra, devolve "não reconhecida, revisar"."""
    limpo = normalizar(texto)
    escolhida = None
    for palavras, regra in REGRAS_NORMALIZADAS:
        if any(_aparece(palavra, limpo) for palavra in palavras):
            if escolhida is None or PRIORIDADES.index(regra.prioridade) < PRIORIDADES.index(escolhida.prioridade):
                escolhida = regra
    if escolhida is None:
        return dict(NAO_RECONHECIDA)
    return _resultado(escolhida)
