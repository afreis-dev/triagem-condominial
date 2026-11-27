import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { buscarResponsaveis, registrarAcao } from "@/lib/h11-api";
import { DecisaoSecao } from "./DecisaoSecao";

vi.mock("@/lib/h11-api", () => ({
  buscarResponsaveis: vi.fn(),
  registrarAcao: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

it("delegates to the suggested person and passes the saved contact", async () => {
  vi.mocked(buscarResponsaveis).mockResolvedValue({
    responsaveis: ["zelador", "portaria"],
    responsavelSugerido: "zelador",
  });
  const contato = { papel: "zelador", temCelular: true as const, celular: "+55 (11) 99999-1234" };
  vi.mocked(registrarAcao).mockResolvedValue(contato);
  const aoRegistrar = vi.fn();
  render(<DecisaoSecao idReal="42" aoRegistrar={aoRegistrar} />);

  fireEvent.click(screen.getByRole("radio", { name: "Delegar" }));
  await waitFor(() => expect(screen.getByRole("combobox").textContent).toMatch(/zelador/i));
  fireEvent.click(screen.getByRole("button", { name: "Confirmar decisão" }));

  await waitFor(() => expect(aoRegistrar).toHaveBeenCalledExactlyOnceWith("delegar", contato));
  expect(registrarAcao).toHaveBeenCalledWith("42", "delegar", "", "zelador", undefined);
});

it("requires a date before scheduling", () => {
  const aoRegistrar = vi.fn();
  render(<DecisaoSecao idReal="42" aoRegistrar={aoRegistrar} />);

  fireEvent.click(screen.getByRole("radio", { name: "Agendar" }));
  fireEvent.click(screen.getByRole("button", { name: "Confirmar decisão" }));

  expect(screen.getByText("Escolha a data do agendamento")).toBeTruthy();
  expect(registrarAcao).not.toHaveBeenCalled();
  expect(aoRegistrar).not.toHaveBeenCalled();
});
