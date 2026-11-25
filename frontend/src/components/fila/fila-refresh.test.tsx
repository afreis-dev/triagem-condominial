import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Route } from "@/routes/fila";

vi.mock("@/components/AuthGuard", () => ({
  AuthGuard: ({ children }: { children: ReactNode }) => children,
}));

vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...await importOriginal<typeof import("@tanstack/react-router")>(),
  Link: ({ children }: { children: ReactNode }) => <a>{children}</a>,
}));

vi.mock("@/lib/auth", () => ({
  API_URL: "http://localhost:8000",
  obterToken: () => "token-de-teste",
  sair: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it("Atualizar exibe uma urgente que chegou depois da abertura da fila", async () => {
  vi.spyOn(Route, "useSearch").mockReturnValue({});
  vi.spyOn(Route, "useNavigate").mockReturnValue(vi.fn());
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(Response.json({ ok: true, ocorrencias: [] }))
    .mockResolvedValueOnce(Response.json({
      ok: true,
      ocorrencias: [{
        id: 42,
        condominioId: 7,
        condominio: "Residencial Aurora",
        descricao: "Cheiro de gás no corredor",
        origem: "morador",
        status: "nova",
        prioridade: "urgente",
        motivo: "Palavra de risco",
        criadaEm: "2026-11-19T10:00:00+00:00",
      }],
    }));
  vi.stubGlobal("fetch", fetchMock);
  const Fila = Route.options.component!;
  render(
    <QueryClientProvider client={new QueryClient()}>
      <Fila />
    </QueryClientProvider>,
  );

  const atualizar = screen.getByRole("button", { name: "Atualizar" }) as HTMLButtonElement;
  await waitFor(() => expect(atualizar.disabled).toBe(false));
  expect(screen.queryByText("Cheiro de gás no corredor")).toBeNull();

  fireEvent.click(atualizar);

  expect(await screen.findByText("Cheiro de gás no corredor")).toBeTruthy();
  expect(screen.getByRole("tab", { name: "Nova 1" })).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledTimes(2);
});
