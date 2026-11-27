import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { OCORRENCIAS } from "@/lib/ocorrencias";
import { PrioridadeSecao } from "./PrioridadeSecao";

vi.mock("@/lib/auth", () => ({
  requisitarAutenticado: (caminho: string, init: RequestInit = {}) => fetch(
    `http://localhost:8000${caminho}`,
    { ...init, credentials: "include", headers: new Headers(init.headers) },
  ),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function abrir() {
  const ocorrencia = OCORRENCIAS.find((o) => o.id === 5)!;
  const fetchApi = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
  vi.stubGlobal("fetch", fetchApi);
  render(
    <QueryClientProvider client={new QueryClient()}>
      <PrioridadeSecao ocorrencia={ocorrencia} demonstracao={false} />
    </QueryClientProvider>,
  );
  return fetchApi;
}

it("confirma a sugestão urgente com cookie e sem enviar motivo", async () => {
  const fetchApi = abrir();
  expect(screen.getAllByRole("radio")).toHaveLength(4);
  expect(screen.getByRole("radio", { name: "Urgente Sugerida" }).getAttribute("aria-checked")).toBe("true");
  fireEvent.click(screen.getByRole("button", { name: "Confirmar urgente" }));
  await waitFor(() => expect(fetchApi).toHaveBeenCalledOnce());
  expect(fetchApi).toHaveBeenCalledWith("http://localhost:8000/ocorrencias/5/prioridade", {
    method: "PATCH",
    credentials: "include",
    headers: expect.any(Headers),
    body: JSON.stringify({ prioridade: "urgente" }),
  });
});

it("avisa sobre gás e impede o envio até receber um motivo", async () => {
  const fetchApi = abrir();
  fireEvent.click(screen.getByRole("radio", { name: "Normal" }));
  expect(screen.getByText("Esta ocorrência tem palavra de risco: gás. Explique por que não é urgente.")).toBeTruthy();
  const confirmar = screen.getByRole("button", { name: "Confirmar prioridade" });
  fireEvent.click(confirmar);
  expect(screen.getByText("Informe o motivo da mudança")).toBeTruthy();
  expect(fetchApi).not.toHaveBeenCalled();
  fireEvent.change(screen.getByRole("textbox", { name: /Motivo da mudança/ }), {
    target: { value: "  Vistoria concluída  " },
  });
  fireEvent.click(confirmar);
  await waitFor(() => expect(fetchApi).toHaveBeenCalledOnce());
  expect(JSON.parse(fetchApi.mock.calls[0]![1].body)).toEqual({
    prioridade: "normal", motivo: "Vistoria concluída",
  });
});
