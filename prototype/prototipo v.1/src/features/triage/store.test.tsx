import { fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { TriageProvider, useTriage } from "./store";
import { demoAccounts } from "./demo-auth";

afterEach(cleanup);

function StoreProbe() {
  const { user, login, logout, tickets } = useTriage();
  const manager = demoAccounts.find((account) => account.user.role === "manager");
  const resident = demoAccounts.find((account) => account.user.role === "resident");
  if (!manager || !resident) throw new Error("Missing demonstration accounts");
  return <>
    <output aria-label="session">{user?.role ?? "signed-out"}</output>
    <output aria-label="tickets">{tickets.length}</output>
    <button onClick={() => login(manager.user)}>Manager</button>
    <button onClick={() => login(resident.user)}>Resident</button>
    <button onClick={logout}>Exit</button>
  </>;
}

describe("prototype provider", () => {
  it("mounts hooks and switches both demo sessions without losing shared tickets", async () => {
    render(<TriageProvider><StoreProbe /></TriageProvider>);
    await waitFor(() => expect(screen.getByLabelText("tickets").textContent).toBe("23"));
    expect(screen.getByLabelText("session").textContent).toBe("signed-out");
    fireEvent.click(screen.getByText("Manager"));
    expect(screen.getByLabelText("session").textContent).toBe("manager");
    fireEvent.click(screen.getByText("Exit"));
    expect(screen.getByLabelText("session").textContent).toBe("signed-out");
    fireEvent.click(screen.getByText("Resident"));
    expect(screen.getByLabelText("session").textContent).toBe("resident");
    expect(screen.getByLabelText("tickets").textContent).toBe("23");
  });
});