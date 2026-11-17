import type { Ticket } from "./domain";

export type DemoUser = { role: "manager" | "resident"; name: string; phone: string; condo: number };
export const LOGIN_MS = 1000;
export const demoAccounts = [
  { label: "Síndico", identifier: "sindico@triagem.com", password: "123456", user: { role: "manager", name: "Síndico", phone: "", condo: 0 } },
  { label: "Morador", identifier: "(11) 98765-4321", password: "123456", user: { role: "resident", name: "Ana Souza", phone: "11987654321", condo: 0 } },
] satisfies { label: string; identifier: string; password: string; user: DemoUser }[];

export function formatIdentifier(value: string) {
  if (!/^\s*[\d(]/.test(value)) return value;
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (!digits) return "";
  if (digits.length <= 2) return `(${digits}`;
  if (digits.length <= 7) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
}
export function authenticateDemo(identifier: string, password: string): DemoUser | null {
  const normalized = identifier.trim().toLowerCase();
  const account = demoAccounts.find((a) => a.user.role === "manager"
    ? normalized === a.identifier
    : /^[\d\s()+-]+$/.test(normalized) && normalized.replace(/\D/g, "") === a.user.phone);
  return account && password === account.password ? account.user : null;
}
export function residentTickets(tickets: Ticket[], user: DemoUser) {
  return tickets.filter((t) => user.role === "resident" && t.condo === user.condo && t.phone.replace(/\D/g, "") === user.phone);
}
export function canViewPath(user: DemoUser, path: string) {
  return user.role === "resident" ? path === "/morador" : path !== "/morador";
}