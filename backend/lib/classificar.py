import re
import unicodedata


def _sem_acento(texto):
    """Devolve o texto em minúsculas e sem acento."""
    decomposto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def classificar(texto):
    """Versão de teste: ignora o texto e devolve sempre a mesma classificação, mas vira urgente se o texto tiver "gás"."""
    resultado = {
        "prioridade": "normal",
        "categoria": "manutencao",
        "responsavelSugerido": "zelador",
        "motivo": "classificação de teste",
        "travada": False,
        "palavraDeRisco": None,
        "fonte": "regras",
    }
    if re.search(r"\bgas\b", _sem_acento(texto or "")):
        resultado["prioridade"] = "urgente"
    return resultado
