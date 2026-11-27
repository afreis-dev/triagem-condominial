import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ColarMensagemDialog } from "./ColarMensagemDialog";

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

async function abrirPainel() {
  const fetchMock = vi.fn().mockResolvedValueOnce(Response.json([{ id: 7, nome: "Vista Verde" }]));
  vi.stubGlobal("fetch", fetchMock);
  const aoSalvar = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ColarMensagemDialog aoSalvar={aoSalvar} />
    </QueryClientProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Colar mensagem" }));
  await screen.findByRole("option", { name: "Vista Verde" });
  return { fetchMock, aoSalvar };
}

it("saves the pasted message unchanged for a condominium returned by the API", async () => {
  const { fetchMock, aoSalvar } = await abrirPainel();
  fetchMock.mockResolvedValueOnce(Response.json({ ok: true }, { status: 201 }));
  const descricao = "o portão da garagem travou aberto\nObrigado! 🙂";
  fireEvent.change(screen.getByLabelText(/^Condomínio/), { target: { value: "7" } });
  fireEvent.change(screen.getByLabelText(/^Mensagem/), { target: { value: descricao } });
  const celular = screen.getByRole<HTMLInputElement>("textbox", { name: "Celular (opcional)" });
  fireEvent.change(celular, { target: { value: "11912345678" } });
  expect(celular.value).toBe("(11) 91234-5678");
  fireEvent.click(screen.getByRole("button", { name: "Salvar" }));

  await waitFor(() => expect(aoSalvar).toHaveBeenCalledOnce());
  expect(fetchMock).toHaveBeenLastCalledWith(
    "http://localhost:8000/ocorrencias/colar",
    expect.objectContaining({
      method: "POST",
      credentials: "include",
      body: JSON.stringify({ condominioId: 7, descricao, nome: "", celular: "(11) 91234-5678", origem: "whatsapp_sindico" }),
    }),
  );
  expect(screen.queryByRole("dialog")).toBeNull();
});

it("shows the required condominium error and skips the save request", async () => {
  const { fetchMock, aoSalvar } = await abrirPainel();
  fireEvent.change(screen.getByLabelText(/^Mensagem/), { target: { value: "o portão travou" } });
  fireEvent.click(screen.getByRole("button", { name: "Salvar" }));

  expect(screen.getByRole("alert").textContent).toBe("Escolha o condomínio");
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(aoSalvar).not.toHaveBeenCalled();
});
