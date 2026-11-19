import { describe, expect, it } from "vitest";
import {
  CONDOMINIOS,
  OCORRENCIAS,
  criarDeMensagem,
  filtrarOcorrencias,
  paginar,
  sugerirPrioridade,
} from "./ocorrencias";

describe("fila de ocorrências", () => {
  it("has 15 mock occurrences across 3 condos", () => {
    expect(OCORRENCIAS).toHaveLength(15);
    expect(CONDOMINIOS).toHaveLength(3);
    expect(new Set(OCORRENCIAS.map((o) => o.condominioId)).size).toBe(3);
  });

  it("shows at most 10 cards per page", () => {
    const lista = Array.from({ length: 23 }, (_, i) => i);
    expect(paginar(lista, 1).itens).toHaveLength(10);
    expect(paginar(lista, 3).itens).toHaveLength(3);
    expect(paginar(lista, 1).totalPaginas).toBe(3);
  });

  it("filters by condo and priority within the tab", () => {
    const r = filtrarOcorrencias(OCORRENCIAS, { status: "nova", condominio: "torre-atlantica", prioridade: "urgente" });
    expect(r.map((o) => o.id).sort()).toEqual([2, 5]);
  });

  it("lists urgent occurrences first", () => {
    const r = filtrarOcorrencias(OCORRENCIAS, { status: "nova" });
    expect(r[0]?.prioridade).toBe("urgente");
    expect(r.at(-1)?.prioridade).toBe("baixa");
  });

  it("puts a pasted message in the Nova tab with a suggested priority", () => {
    const o = criarDeMensagem(16, "solar-ipes", "[10:02] Ana: Cheiro de gás no bloco C\nPor favor venham rápido");
    expect(o.status).toBe("nova");
    expect(o.titulo).toBe("Cheiro de gás no bloco C");
    expect(o.prioridade).toBe("urgente");
    expect(sugerirPrioridade("bom dia, tudo certo?")).toBe("normal");
  });
});
