import re

PRIORIDADES = ("urgente", "alta", "normal", "baixa")
ORIGENS = ("morador", "proprietario", "funcionario", "whatsapp_sindico")
RESPONSAVEIS = ("zelador", "portaria", "sindico")
LIMITE_ID = 2_147_483_647


def texto(valor):
    """Devolve o texto limpo (sem NUL e sem espaços nas pontas), ou None se não for texto ou estiver vazio."""
    if isinstance(valor, int) and not isinstance(valor, bool):
        try:
            valor = str(valor)
        except ValueError:
            return None
    if not isinstance(valor, str):
        return None
    valor = valor.replace("\x00", "").encode("utf-8", "replace").decode("utf-8")
    return valor.strip() or None


def inteiro(valor):
    """Converte número inteiro ou texto só com dígitos em int, ou devolve None se não der."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        valor = int(valor) if re.fullmatch(r"[0-9]{1,10}", valor) else None
    if isinstance(valor, int) and 0 < valor <= LIMITE_ID:
        return valor
    return None
