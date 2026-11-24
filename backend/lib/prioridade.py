from datetime import datetime

ORDEM_PRIORIDADE = {"urgente": 0, "alta": 1, "normal": 2, "baixa": 3}

def ordenar_ocorrencias(ocorrencias):
    """Ordena por prioridade e, no empate, pela hora de entrada (mais antiga primeiro)."""
    def chave(o):
        prioridade = ORDEM_PRIORIDADE.get(o.get("prioridade", "baixa"), 4)
        entrada = o.get("created_at", "")
        # Aceita string "2026-11-20 08:30" ou datetime
        if isinstance(entrada, str):
            try:
                entrada = datetime.fromisoformat(entrada)
            except ValueError:
                entrada = datetime.min
        return (prioridade, entrada)
    return sorted(ocorrencias, key=chave)


if __name__ == "__main__":
    # Lista falsa - igual o PO pediu
    lista_falsa = [
        {"id": "1", "titulo": "lampada queimada", "prioridade": "normal", "created_at": "2026-11-20 08:00"},
        {"id": "2", "titulo": "bomba vazando", "prioridade": "urgente", "created_at": "2026-11-20 09:00"},
        {"id": "3", "titulo": "cheiro de gas", "prioridade": "urgente", "created_at": "2026-11-20 08:30"},
        {"id": "4", "titulo": "portao travado", "prioridade": "alta", "created_at": "2026-11-20 08:00"},
        {"id": "5", "titulo": "boleto 2a via", "prioridade": "baixa", "created_at": "2026-11-20 07:00"},
    ]

    ordenadas = ordenar_ocorrencias(lista_falsa)

    print("=== Fila ordenada ===")
    for o in ordenadas:
        print(f"{o['prioridade']:8} - {o['created_at']} - {o['titulo']}")

    # Testes automaticos da task
    assert ordenadas[0]["id"] == "3", "1o tem que ser urgente mais antiga (08:30)"
    assert ordenadas[1]["id"] == "2", "2o tem que ser urgente mais nova (09:00)"
    assert ordenadas[2]["id"] == "4", "3o tem que ser alta"
    assert ordenadas[3]["id"] == "1", "4o tem que ser normal"
    assert ordenadas[4]["id"] == "5", "5o tem que ser baixa"
    print("\n✅ 5 testes passaram - urgentes no topo, mais antiga primeiro no empate")