import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AuthGuard } from "./AuthGuard";
import { CHAVE_SINDICO, obterSindico } from "@/lib/auth";

const { navegar } = vi.hoisted(() => ({ navegar: vi.fn() }));
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...await importOriginal<typeof import("@tanstack/react-router")>(),
  useNavigate: () => navegar,
}));
vi.mock("@/lib/auth", () => ({
  CHAVE_SINDICO: ["sindico"],
  obterSindico: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.mocked(obterSindico).mockReset();
  navegar.mockReset();
});

it("reaproveita o perfil do login sem consultar /auth/me novamente", () => {
  const queryClient = new QueryClient();
  queryClient.setQueryData(CHAVE_SINDICO, { id: 7, nome: "Ana", email: "ana@teste.com" });
  render(
    <QueryClientProvider client={queryClient}>
      <AuthGuard><p>Fila autenticada</p></AuthGuard>
    </QueryClientProvider>,
  );

  expect(screen.getByText("Fila autenticada")).toBeTruthy();
  expect(obterSindico).not.toHaveBeenCalled();
});

it("consulta /auth/me ao abrir uma página protegida sem perfil em memória", async () => {
  const perfil = { id: 7, nome: "Ana", email: "ana@teste.com" };
  vi.mocked(obterSindico).mockResolvedValue(perfil);
  const queryClient = new QueryClient();
  render(
    <QueryClientProvider client={queryClient}>
      <AuthGuard><p>Fila autenticada</p></AuthGuard>
    </QueryClientProvider>,
  );

  await waitFor(() => expect(screen.getByText("Fila autenticada")).toBeTruthy());
  expect(obterSindico).toHaveBeenCalledOnce();
  expect(queryClient.getQueryData(CHAVE_SINDICO)).toEqual(perfil);
});
