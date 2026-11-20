import unicodedata
import re

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

REGRAS = [
    (["falta de agua", "sem agua", "falta agua"], "alta", "manutencao", "zelador"),
    (["vazamento"], "alta", "manutencao", "zelador"),
    (["elevador parado", "elevador quebrou", "elevador travado"], "alta", "manutencao", "zelador"),
    (["portao travou", "portao travado", "travou aberto"], "alta", "seguranca_acesso", "portaria"),
    (["furto", "roubo", "assalto"], "alta", "seguranca_acesso", "sindico"),
    (["sem energia", "sem luz", "falta de energia"], "alta", "manutencao", "zelador"),
    (["esgoto entupido", "entupido", "refluxo"], "alta", "manutencao", "zelador"),
    (["bomba d'agua", "bomba de agua", "bomba queimou"], "alta", "manutencao", "zelador"),
    (["lampada"], "normal", "manutencao", "zelador"),
    (["interfone"], "normal", "seguranca_acesso", "portaria"),
    (["camera"], "normal", "seguranca_acesso", "portaria"),
    (["torneira"], "normal", "manutencao", "zelador"),
    (["barulho", "festa", "som alto"], "normal", "convivencia", "sindico"),
    (["cachorro", "latindo"], "normal", "convivencia", "sindico"),
    (["vaga", "carro parado na minha"], "normal", "convivencia", "sindico"),
    (["mudanca"], "normal", "pedido_administrativo", "sindico"),
    (["fumaca de cigarro"], "normal", "convivencia", "sindico"),
    (["boleto", "segunda via"], "baixa", "pedido_administrativo", "sindico"),
    (["reservar", "reserva", "churrasqueira", "salao"], "baixa", "pedido_administrativo", "sindico"),
    (["declaracao"], "baixa", "pedido_administrativo", "sindico"),
    (["duvida", "regimento"], "baixa", "duvida", "sindico"),
]

ORDEM = {"urgente": 4, "alta": 3, "normal": 2, "baixa": 1}

def _normalizar(texto):
    texto = texto.lower()
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9 ]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto

def _palavra_risco(texto_norm):
    if "fumaca de cigarro" in texto_norm:
        texto_sem_excecao = texto_norm.replace("fumaca de cigarro", "")
    else:
        texto_sem_excecao = texto_norm
    if "cheiro de gas" in texto_sem_excecao:
        return "gas"
    for palavra in PALAVRAS_RISCO:
        if re.search(r"\b" + re.escape(palavra) + r"\b", texto_sem_excecao):
            return palavra
    return None

def classificar(texto):
    texto_norm = _normalizar(texto)
    melhor = None
    for chaves, prioridade, categoria, responsavel in REGRAS:
        if any(re.search(r"\b" + re.escape(_normalizar(c)) + r"\b", texto_norm) for c in chaves):
            if melhor is None or ORDEM[prioridade] > ORDEM[melhor["prioridade"]]:
                melhor = {
                    "prioridade": prioridade,
                    "categoria": categoria,
                    "responsavel": responsavel,
                    "motivo": "classificação de teste",
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
    return melhor

def aplicarTravaDeRisco(texto, resultado):
    palavra = _palavra_risco(_normalizar(texto))
    if palavra:
        exibicao = EXIBICAO_RISCO.get(palavra, palavra)
        resultado["prioridade"] = "urgente"
        resultado["motivo"] = f"palavra de risco: {exibicao}"
        resultado["travada"] = True
        resultado["palavraDeRisco"] = exibicao
        resultado["responsavel"] = "sindico"
    
    return resultado