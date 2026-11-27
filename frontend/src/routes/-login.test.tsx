import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { CHAVE_SINDICO, entrar } from "@/lib/auth";
import { Route } from "./login";

const { navegar } = vi.hoisted(() => ({ navegar: vi.fn() }));
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...await importOriginal<typeof import("@tanstack/react-router")>(),
  useNavigate: () => navegar,
}));
vi.mock("@/lib/auth", () => ({ CHAVE_SINDICO: ["sindico"], entrar: vi.fn() }));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.mocked(entrar).mockReset();
  navegar.mockReset();
});

function abrirLogin() {
  const Login = Route.options.component!;
  const queryClient = new QueryClient();
  render(<QueryClientProvider client={queryClient}><Login /></QueryClientProvider>);
  return { navegar, queryClient };
}

it("mostra os erros nos campos sem enviar e alterna a visibilidade da senha", () => {
  abrirLogin();
  fireEvent.click(screen.getByRole("button", { name: "Entrar" }));
  expect(screen.getByText("Informe o e-mail ou celular.")).toBeTruthy();
  expect(screen.getByText("Informe a senha.")).toBeTruthy();
  expect(entrar).not.toHaveBeenCalled();

  const senha = screen.getByLabelText("Senha") as HTMLInputElement;
  expect(senha.type).toBe("password");
  fireEvent.click(screen.getByRole("button", { name: "Mostrar senha" }));
  expect(senha.type).toBe("text");
  fireEvent.click(screen.getByRole("button", { name: "Ocultar senha" }));
  expect(senha.type).toBe("password");
  expect(screen.getByText("Esqueci minha senha")).toBeTruthy();
});

it("aceita celular no identificador e encaminha para a fila após o login", async () => {
  const sindico = { id: 7, nome: "Síndico Teste", email: "sindico@teste.com" };
  vi.mocked(entrar).mockResolvedValue(sindico);
  const { navegar, queryClient } = abrirLogin();
  fireEvent.change(screen.getByLabelText("E-mail ou celular"), { target: { value: "(19) 99123-4567" } });
  fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "senha" } });
  fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

  await waitFor(() => expect(entrar).toHaveBeenCalledWith("(19) 99123-4567", "senha"));
  await waitFor(() => expect(navegar).toHaveBeenCalledWith({ to: "/fila", search: {} }));
  expect(queryClient.getQueryData(CHAVE_SINDICO)).toEqual(sindico);
});
