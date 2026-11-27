import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AprovacaoLote } from "./AprovacaoLote";

vi.mock("@/lib/auth", () => ({
  requisitarAutenticado: (caminho: string, init?: RequestInit) => fetch(caminho, init),
}));

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function abrirLote() {
  const prioridades = ["alta", "normal", "baixa"];
  const ocorrencias = Array.from({ length: 13 }, (_, i) => ({
    id: i + 1,
    descricao: i === 12 ? "Vazamento urgente" : `Ocorrência ${i + 1}`,
    condominio: "Residencial Aurora",
    status: "nova",
    prioridade: i === 12 ? "urgente" : prioridades[i % 3],
    responsavel_sugerido: "zelador",
    motivo: "Manutenção da área comum",
  }));
  const delegadas = new Set<number>();
  const fetchMock = vi.fn(async (caminho: string, init?: RequestInit) => {
    if (caminho.endsWith("/para-aprovacao")) {
      return Response.json({ ocorrencias: ocorrencias.filter((o) => !delegadas.has(o.id)) });
    }
    const { ids }: { ids: number[] } = JSON.parse(String(init?.body));
    if (caminho.endsWith("/aprovar-lote")) {
      ids.forEach((id) => delegadas.add(id));
      return Response.json({ aprovados: ids });
    }
    if (caminho.endsWith("/desfazer-lote")) {
      ids.forEach((id) => delegadas.delete(id));
      return Response.json({ desfeitos: ids });
    }
    throw new Error(`Rota inesperada ${caminho}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  const client = new QueryClient();
  render(
    <QueryClientProvider client={client}>
      <AprovacaoLote />
    </QueryClientProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Aprovação em lote" }));
  return { fetchMock, delegadas };
}

it("marca as 12 não urgentes e aprova e desfaz somente as 10 selecionadas", async () => {
  const { fetchMock, delegadas } = abrirLote();
  const caixas = await screen.findAllByRole("checkbox");
  expect(caixas).toHaveLength(12);
  caixas.forEach((caixa) => expect(caixa).toBeChecked());
  expect(screen.queryByText("Vazamento urgente")).not.toBeInTheDocument();
  expect(screen.getAllByText("Residencial Aurora · Zelador")).toHaveLength(12);
  expect(screen.getAllByText("Manutenção da área comum")).toHaveLength(12);

  fireEvent.click(screen.getByRole("button", { name: "Limpar tudo" }));
  caixas.forEach((caixa) => expect(caixa).not.toBeChecked());
  expect(screen.getByRole("button", { name: "Aprovar (0)" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Selecionar tudo" }));
  caixas.forEach((caixa) => expect(caixa).toBeChecked());

  fireEvent.click(caixas[0]!);
  fireEvent.click(caixas[1]!);
  fireEvent.click(screen.getByRole("button", { name: "Aprovar (10)" }));
  expect(await screen.findByText("10 ocorrências delegadas")).toBeInTheDocument();

  const ids = Array.from({ length: 10 }, (_, i) => i + 3);
  expect([...delegadas]).toEqual(ids);
  expect(fetchMock).toHaveBeenCalledWith("/ocorrencias/aprovar-lote", expect.objectContaining({
    method: "POST",
    body: JSON.stringify({ ids }),
  }));
  fireEvent.click(screen.getByRole("button", { name: "Desfazer" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "Desfazer" })).not.toBeInTheDocument());
  expect(fetchMock).toHaveBeenCalledWith("/ocorrencias/desfazer-lote", expect.objectContaining({
    method: "POST",
    body: JSON.stringify({ ids }),
  }));
  expect(delegadas.size).toBe(0);
});

it("retira a ação de desfazer após 10 segundos e mantém o lote aprovado", async () => {
  const { fetchMock, delegadas } = abrirLote();
  const aprovar = await screen.findByRole("button", { name: "Aprovar (12)" });
  vi.useFakeTimers();
  fireEvent.click(aprovar);
  await act(async () => { await vi.advanceTimersByTimeAsync(1); });
  expect(screen.getByText("12 ocorrências delegadas")).toBeInTheDocument();

  act(() => vi.advanceTimersByTime(9_998));
  expect(screen.getByRole("button", { name: "Desfazer" })).toBeInTheDocument();
  act(() => vi.advanceTimersByTime(2));

  expect(screen.queryByText("12 ocorrências delegadas")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Desfazer" })).not.toBeInTheDocument();
  expect(delegadas.size).toBe(12);
  expect(fetchMock.mock.calls.some(([caminho]) => caminho.endsWith("/desfazer-lote"))).toBe(false);
});
