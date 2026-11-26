import re
import unicodedata

try:
    from .classificar_ia import classificar_com_ia
    from .regras import REGRAS
except ImportError:
    from classificar_ia import classificar_com_ia
    from regras import REGRAS

PALAVRAS_RISCO = [
    "gas",
    "cheiro de gas",
    "fogo",
    "incendio",
    "fumaca",
    "preso no elevador",
    "alagamento",
    "desabamento",
    "trinca na estrutura",
    "choque",
    "fio exposto",
    "agressao",
]

EXIBICAO_RISCO = {
    "gas": "gás",
    "cheiro de gas": "gás",
    "fogo": "fogo",
    "incendio": "incêndio",
    "fumaca": "fumaça",
    "preso no elevador": "preso no elevador",
    "alagamento": "alagamento",
    "desabamento": "desabamento",
    "trinca na estrutura": "trinca na estrutura",
    "choque": "choque",
    "fio exposto": "fio exposto",
    "agressao": "agressão",
}

ORDEM = {"urgente": 4, "alta": 3, "normal": 2, "baixa": 1}


def normalizar(texto):
    """Devolve o texto em minúsculas, sem acento e sem pontuação. Se não for texto, devolve vazio."""
    if not isinstance(texto, str):
        return ""
    decomposto = unicodedata.normalize("NFKD", texto.lower())
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sem_acento).strip()


REGRAS_NORMALIZADAS = tuple((tuple(normalizar(palavra) for palavra in regra.palavras), regra) for regra in REGRAS)


def _aparece(palavra, texto):
    """Diz se a palavra aparece inteira no texto já padronizado."""
    return f" {palavra} " in f" {texto} "

def classificar_por_regras(texto):
    """Acha a regra do PO de maior prioridade, aplica a trava de risco e, sem regra, devolve não reconhecida."""
    texto_norm = normalizar(texto)
    melhor = None
    for palavras, regra in REGRAS_NORMALIZADAS:
        if any(_aparece(palavra, texto_norm) for palavra in palavras):
            if melhor is None or ORDEM[regra.prioridade] > ORDEM[melhor["prioridade"]]:
                melhor = {
                    "prioridade": regra.prioridade,
                    "categoria": regra.categoria,
                    "responsavel": regra.responsavel,
                    "motivo": regra.motivo,
                    "travada": False,
                    "palavraDeRisco": None,
                }
    if melhor is None:
        melhor = {
            "prioridade": "normal",
            "categoria": "nao_reconhecida",
            "responsavel": "sindico",
            "motivo": "não reconhecida, revisar",
            "travada": False,
            "palavraDeRisco": None,
        }
    palavra = _palavra_risco(texto_norm)
    if palavra:
        exibicao = EXIBICAO_RISCO.get(palavra, palavra)
        melhor["prioridade"] = "urgente"
        melhor["motivo"] = f"palavra de risco: {exibicao}"
        melhor["travada"] = True
        melhor["palavraDeRisco"] = exibicao
        melhor["responsavel"] = "sindico"
        if melhor["categoria"] == "nao_reconhecida":
            if palavra in ["fogo", "incendio", "fumaca"]:
                melhor["categoria"] = "seguranca_acesso"
            else:
                melhor["categoria"] = "manutencao"

    melhor["responsavelSugerido"] = melhor["responsavel"]
    melhor["responsavel_sugerido"] = melhor["responsavel"]
    melhor["palavra_de_risco"] = melhor["palavraDeRisco"]
    melhor["fonte"] = "regras"
    return melhor


def aplicarTravaDeRisco(texto, resultado):
    palavra = _palavra_risco(normalizar(texto))
    if palavra:
        exibicao = EXIBICAO_RISCO.get(palavra, palavra)
        resultado["prioridade"] = "urgente"
        resultado["motivo"] = f"palavra de risco: {exibicao}"
        resultado["travada"] = True
        resultado["palavraDeRisco"] = exibicao
        resultado["responsavel"] = "sindico"
        resultado["responsavelSugerido"] = "sindico"
        resultado["palavra_de_risco"] = exibicao
        resultado["fonte"] = "regras"
    return resultado


def classificar(texto):
    """Pede a classificação à IA, se estiver ligada, e usa as regras se ela falhar. A trava de risco roda por último."""
    resultado = classificar_com_ia(texto)
    if resultado is None:
        return classificar_por_regras(texto)
    resultado = aplicarTravaDeRisco(texto, resultado)
    if resultado["travada"] and resultado["categoria"] == "nao_reconhecida":
        resultado["categoria"] = classificar_por_regras(texto)["categoria"]
    return resultado

def buscarPalavrasDeRisco(conexao=None):
    """Lê as palavras do banco. Sem redeploy: inseriu no banco, já trava."""
    try:
        if conexao is None:
            from .conexao import conectar
            conn = conectar()
            fechar = True
        else:
            conn = conexao
            fechar = False
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT palavra FROM palavras_risco ORDER BY LENGTH(palavra) DESC, ordem")
                rows = [r[0] for r in cur.fetchall()]
            # guarda o original com acento pra exibir "vazamento de gás"
            for original in rows:
                EXIBICAO_RISCO.setdefault(normalizar(original), original)
            palavras = [normalizar(r) for r in rows]
            return palavras or list(PALAVRAS_RISCO)
        finally:
            if fechar:
                conn.close()
    except Exception:
        return list(PALAVRAS_RISCO)

def _palavra_risco(texto_norm, palavras=None):
    if palavras is None:
        palavras = buscarPalavrasDeRisco()

    palavras = sorted(palavras, key=len, reverse=True)
    if "fumaca de cigarro" in texto_norm:
        texto_sem_excecao = texto_norm.replace("fumaca de cigarro", "")
    else:
        texto_sem_excecao = texto_norm
    if "cheiro de gas" in texto_sem_excecao:
        return "gas"
    for palavra in palavras:
        if re.search(r"\b" + re.escape(palavra) + r"\b", texto_sem_excecao):
            return palavra
    return None
