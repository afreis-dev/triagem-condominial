import { describe, expect, it } from "vitest";
import {
  CONDOMINIOS,
  OCORRENCIAS,
  PRIORIDADES,
  STATUS,
  contarPorPrioridade,
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

describe("resumo da aba aberta", () => {
  const resumoDa = (status: "nova" | "andamento" | "concluida", condominio?: string) =>
    contarPorPrioridade(filtrarOcorrencias(OCORRENCIAS, { status, condominio }));

  it("counts the occurrences of each priority in the tab", () => {
    expect(resumoDa("nova")).toEqual({ urgente: 3, alta: 3, normal: 3, baixa: 3 });
    expect(resumoDa("andamento")).toEqual({ urgente: 0, alta: 1, normal: 1, baixa: 1 });
  });

  it("is zero for every priority when the tab is empty", () => {
    expect(resumoDa("concluida")).toEqual({ urgente: 0, alta: 0, normal: 0, baixa: 0 });
    expect(contarPorPrioridade([])).toEqual({ urgente: 0, alta: 0, normal: 0, baixa: 0 });
  });

  it("matches the cards listed for each priority, in every tab and condo", () => {
    for (const { id: status } of STATUS) {
      for (const condominio of [undefined, ...CONDOMINIOS.map((c) => c.id)]) {
        const resumo = resumoDa(status, condominio);
        for (const { id: prioridade } of PRIORIDADES) {
          const cartoes = filtrarOcorrencias(OCORRENCIAS, { status, condominio, prioridade });
          expect(resumo[prioridade]).toBe(cartoes.length);
        }
      }
    }
  });

  it("adds up to the number shown on the tab", () => {
    for (const { id: status } of STATUS) {
      const total = Object.values(resumoDa(status)).reduce((soma, n) => soma + n, 0);
      expect(total).toBe(filtrarOcorrencias(OCORRENCIAS, { status }).length);
    }
  });

  it("counts a pasted urgent message in the Nova tab", () => {
    const nova = criarDeMensagem(99, "solar-ipes", "Cheiro de gás no bloco C");
    const lista = [...OCORRENCIAS, nova];
    const resumo = contarPorPrioridade(filtrarOcorrencias(lista, { status: "nova" }));
    expect(resumo.urgente).toBe(resumoDa("nova").urgente + 1);
  });
});
