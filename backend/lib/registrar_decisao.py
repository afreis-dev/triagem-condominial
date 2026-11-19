from datetime import datetime, timezone


def registrar_decisao(dados):
    """Versão de teste: não grava nada, mostra no console o que recebeu e devolve um registro fixo."""
    print(dados)
    return {
        "ok": True,
        "registroId": 1,
        "dataHora": datetime.now(timezone.utc).isoformat(),
    }
