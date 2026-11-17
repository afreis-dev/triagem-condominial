import { describe, expect, it } from "vitest";
import {
  classify,
  initialTickets,
  batchEligible,
  approveBatch,
  undoBatch,
  actOnTicket,
  CLASSIFY_MS,
  UNDO_MS,
  sortTickets,
} from "./domain";
describe("triage rules", () => {
  it.each([
    "gás",
    "fogo",
    "incêndio",
    "fumaça",
    "preso no elevador",
    "alagamento",
    "desabamento",
    "choque",
    "fio exposto",
    "agressão",
  ])("classifies %s as urgent with three reasons", (word) => {
    const t = classify(`Há ${word} aqui`, 0);
    expect(t.priority).toBe("Urgente");
    expect(t.reasons).toHaveLength(3);
    expect(t.reasons.every((r) => r.includes(" porque "))).toBe(true);
  });
  it("uses two seconds for classification", () => expect(CLASSIFY_MS).toBe(2000));
  it("allows undo for ten seconds", () => expect(UNDO_MS).toBe(10000));
  it("seeds at least twenty tickets across six condos", () => {
    const tickets = initialTickets();
    expect(tickets.length).toBeGreaterThanOrEqual(20);
    expect(new Set(tickets.map((t) => t.condo)).size).toBe(6);
  });
  it("excludes urgent tickets from batch even if requested", () => {
    const tickets = initialTickets();
    const result = approveBatch(
      tickets,
      tickets.map((t) => t.id),
    );
    expect(result.filter((t) => t.priority === "Urgente").every((t) => t.status === "Aberto")).toBe(
      true,
    );
  });
  it("delegates selected batch tickets", () => {
    const tickets = initialTickets();
    const selected = batchEligible(tickets)[0];
    if (!selected) throw new Error("Missing seed ticket");
    const result = approveBatch(tickets, [selected.id]);
    expect(result.find((t) => t.id === selected.id)?.status).toBe("Em andamento");
    expect(result.find((t) => t.id === selected.id)?.history.at(-1)?.text).toContain(
      selected.assignee,
    );
  });
  it("undo restores open status and keeps non-editable history", () => {
    const tickets = initialTickets();
    const originals = batchEligible(tickets).slice(0, 2);
    const original = originals[0];
    if (!original) throw new Error("Missing seed ticket");
    const approved = approveBatch(
      tickets,
      originals.map((t) => t.id),
    );
    const undone = undoBatch(approved, originals);
    const t = undone.find((t) => t.id === original.id);
    expect(t?.status).toBe("Aberto");
    expect(t?.history.length).toBe(original.history.length + 2);
    expect(t?.history.at(-1)?.text).toBe("Aprovação em lote desfeita pelo síndico");
  });
  it("an action starts work and completion closes the ticket", () => {
    const t = initialTickets()[0];
    if (!t) throw new Error("Missing seed ticket");
    const working = actOnTicket(t, "Delegado", "Em andamento");
    expect(working.status).toBe("Em andamento");
    expect(working.confirmed).toBe(true);
    expect(actOnTicket(working, "Concluído", "Fechado").status).toBe("Fechado");
  });
  it("sorts urgent first and oldest first within priority", () => {
    const rows = sortTickets(initialTickets());
    expect(rows[0]?.priority).toBe("Urgente");
    expect(rows[0]?.title).toBe("Tem cheiro de gás no bloco B");
  });
});
