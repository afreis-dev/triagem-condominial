import { afterEach, expect, it, vi } from "vitest";
import { buscarFila } from "./fila-api";

vi.mock("./auth", () => ({
  API_URL: "http://localhost:8000",
  obterToken: () => "token-de-teste",
}));

afterEach(() => vi.unstubAllGlobals());

it("consulta de novo e retorna a nova urgente com os dados do condomínio", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(Response.json({ ok: true, ocorrencias: [] }))
    .mockResolvedValueOnce(Response.json({
      ok: true,
      ocorrencias: [{
        id: 42,
        condominioId: 7,
        condominio: "Residencial Aurora",
        descricao: "Cheiro de gás",
        origem: "morador",
        status: "nova",
        prioridade: "urgente",
        motivo: "Palavra de risco",
        criadaEm: "2026-11-19T10:00:00+00:00",
      }],
    }));
  vi.stubGlobal("fetch", fetchMock);
  const { signal } = new AbortController();

  expect(await buscarFila(signal)).toEqual([]);
  expect(await buscarFila(signal)).toEqual([
    expect.objectContaining({
      condominioId: "7",
      condominio: "Residencial Aurora",
      titulo: "Cheiro de gás",
      status: "nova",
      prioridade: "urgente",
    }),
  ]);
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(fetchMock).toHaveBeenLastCalledWith("http://localhost:8000/ocorrencias", {
    headers: { Authorization: "Bearer token-de-teste" },
    cache: "no-store",
    signal,
  });
});
