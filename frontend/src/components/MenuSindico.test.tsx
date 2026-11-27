import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { sair } from "@/lib/auth";
import { MenuSindico } from "./MenuSindico";
import { SindicoContext } from "./sindico-context";

const { navegar } = vi.hoisted(() => ({ navegar: vi.fn() }));
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...await importOriginal<typeof import("@tanstack/react-router")>(),
  useNavigate: () => navegar,
}));
vi.mock("@/lib/auth", () => ({ sair: vi.fn() }));

afterEach(() => {
  cleanup();
  vi.mocked(sair).mockReset();
  navegar.mockReset();
});

it("mostra o nome do síndico e encerra a sessão pelo menu", async () => {
  vi.mocked(sair).mockResolvedValue();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <SindicoContext.Provider value={{ id: 1, nome: "Síndica Ana", email: "ana@teste.com" }}>
        <MenuSindico />
      </SindicoContext.Provider>
    </QueryClientProvider>,
  );

  fireEvent.keyDown(screen.getByRole("button", { name: "Síndica Ana" }), { key: "ArrowDown" });
  fireEvent.click(await screen.findByRole("menuitem", { name: "Sair" }));

  await waitFor(() => expect(sair).toHaveBeenCalledOnce());
  await waitFor(() => expect(navegar).toHaveBeenCalledWith({ to: "/login" }));
});
