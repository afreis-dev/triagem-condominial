import { describe, expect, it } from "vitest";
import { authenticateDemo, formatIdentifier, LOGIN_MS, residentTickets, canViewPath } from "./demo-auth";
import { initialTickets } from "./domain";

describe("simulated entry", () => {
  it("accepts the manager demo account", () => {
    expect(authenticateDemo("sindico@triagem.com", "123456")?.role).toBe("manager");
  });
  it("accepts the resident demo phone with or without formatting", () => {
    expect(authenticateDemo("(11) 98765-4321", "123456")?.role).toBe("resident");
    expect(authenticateDemo("11987654321", "123456")?.condo).toBe(0);
  });
  it("rejects incorrect credentials", () => {
    expect(authenticateDemo("sindico@triagem.com", "wrong")).toBeNull();
    expect(authenticateDemo("11987654320", "123456")).toBeNull();
    expect(authenticateDemo("abc11987654321", "123456")).toBeNull();
  });
  it("masks numeric input as an eleven-digit cellphone", () => {
    expect(formatIdentifier("11987654321")).toBe("(11) 98765-4321");
    expect(formatIdentifier("1198765432199")).toBe("(11) 98765-4321");
    expect(formatIdentifier("sindico@triagem.com")).toBe("sindico@triagem.com");
  });
  it("simulates entry for one second", () => expect(LOGIN_MS).toBe(1000));
  it("shows only the resident's own Aurora tickets including all three statuses", () => {
    const user = authenticateDemo("11987654321", "123456");
    if (!user) throw new Error("Missing demo resident");
    const mine = residentTickets(initialTickets(), user);
    expect(mine.map((t) => t.id)).toEqual(["TS-2611-0042", "TS-2611-0058", "TS-2611-0064"]);
    expect(mine.map((t) => t.status)).toEqual(["Aberto", "Em andamento", "Fechado"]);
    const otherCondo = { ...mine[0], condo: 1 };
    expect(residentTickets([...initialTickets(), otherCondo as typeof mine[number]], user)).toHaveLength(3);
  });
  it("keeps the resident out of manager views", () => {
    const user = authenticateDemo("11987654321", "123456");
    if (!user) throw new Error("Missing demo resident");
    expect(canViewPath(user, "/morador")).toBe(true);
    expect(canViewPath(user, "/")).toBe(false);
    expect(canViewPath(user, "/chamado/TS-2611-0042")).toBe(false);
    expect(canViewPath(user, "/lote")).toBe(false);
  });
  it("takes the manager to the queue rather than the resident page", () => {
    const user = authenticateDemo("sindico@triagem.com", "123456");
    if (!user) throw new Error("Missing demo manager");
    expect(canViewPath(user, "/")).toBe(true);
    expect(canViewPath(user, "/morador")).toBe(false);
  });
});