import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PRIORIDADES } from "@/lib/ocorrencias";
import { priorityBadgeVariants } from "./PriorityBadge";
import { PrioritySummary } from "./PrioritySummary";

const contagem = { urgente: 3, alta: 2, normal: 5, baixa: 0 };

describe("PrioritySummary", () => {
  it("shows the name and the count of each priority", () => {
    render(<PrioritySummary contagem={contagem} onSelect={() => {}} />);
    for (const { id, label } of PRIORIDADES) {
      const bloco = screen.getByRole("button", { name: new RegExp(label, "i") });
      expect(bloco).toHaveTextContent(String(contagem[id]));
    }
  });

  it("writes each name with the priority badge", () => {
    render(<PrioritySummary contagem={contagem} onSelect={() => {}} />);
    for (const { id, label } of PRIORIDADES) {
      const bloco = screen.getByRole("button", { name: new RegExp(label, "i") });
      const etiqueta = within(bloco).getByText(label);
      expect(etiqueta).toHaveClass(...priorityBadgeVariants({ prioridade: id }).split(" "));
    }
  });

  it("selects a priority on click and clears it on a second click", () => {
    const aoSelecionar = vi.fn();
    const { rerender } = render(<PrioritySummary contagem={contagem} onSelect={aoSelecionar} />);
    fireEvent.click(screen.getByRole("button", { name: /alta/i }));
    expect(aoSelecionar).toHaveBeenLastCalledWith("alta");

    rerender(<PrioritySummary contagem={contagem} selecionada="alta" onSelect={aoSelecionar} />);
    const selecionado = screen.getByRole("button", { name: /alta/i });
    expect(selecionado).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(selecionado);
    expect(aoSelecionar).toHaveBeenLastCalledWith(undefined);
  });
});
