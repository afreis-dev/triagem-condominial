import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Route } from "@/routes/fila";

vi.mock("@/components/AuthGuard", () => ({
  AuthGuard: ({ children }: { children: ReactNode }) => children,
}));
vi.mock("@/components/MenuSindico", () => ({ MenuSindico: () => <button>Sair</button> }));

vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...await importOriginal<typeof import("@tanstack/react-router")>(),
  Link: ({ children }: { children: ReactNode }) => <a>{children}</a>,
}));

vi.mock("@/lib/auth", () => ({
  requisitarAutenticado: (caminho: string, init: RequestInit = {}) => fetch(
    `http://localhost:8000${caminho}`,
    { ...init, credentials: "include", headers: new Headers(init.headers) },
  ),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it("Atualizar mostra a fonte das regras e coloca a ocorrência para revisão acima da urgente", async () => {
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
        fonte: "regras",
        motivo: "Palavra de risco",
        criadaEm: "2026-11-19T10:00:00+00:00",
      }, {
        id: 43,
        condominioId: 7,
        condominio: "Residencial Aurora",
        descricao: "Ocorrência para revisão",
        origem: "morador",
        status: "nova",
        prioridade: null,
        fonte: null,
        motivo: null,
        criadaEm: "2026-11-19T10:01:00+00:00",
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

  const urgente = (await screen.findByText("Cheiro de gás no corredor")).closest("a")!;
  const revisao = screen.getByText("Ocorrência para revisão").closest("a")!;
  expect(within(urgente).getByText("Classificado por regras")).toBeTruthy();
  expect(within(revisao).getByText(/não classificada, revisar/)).toBeTruthy();
  expect(within(revisao).queryByText("Normal")).toBeNull();
  expect(revisao.compareDocumentPosition(urgente) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.getByRole("tab", { name: "Nova 2" })).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledTimes(2);
});
