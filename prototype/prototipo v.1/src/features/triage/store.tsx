import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
  type Dispatch,
  type SetStateAction,
} from "react";
import {
  CLASSIFY_MS,
  UNDO_MS,
  approveBatch,
  batchEligible,
  classify,
  initialTickets,
  undoBatch,
  type Ticket,
} from "./domain";
import type { DemoUser } from "./demo-auth";
type Store = {
  user: DemoUser | null;
  login: (user: DemoUser) => void;
  logout: () => void;
  tickets: Ticket[];
  setTickets: Dispatch<SetStateAction<Ticket[]>>;
  ownId: string | null;
  addTicket: (
    data: Pick<
      Ticket,
      "title" | "condo" | "name" | "apartment" | "phone" | "location" | "origin" | "role" | "photo"
    >,
    own?: boolean,
  ) => string;
  now: number;
  approve: (ids: string[]) => void;
  undo: () => void;
  undoInfo: { count: number; expires: number } | null;
};
const Context = createContext<Store | null>(null);
export function TriageProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<DemoUser | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [ownId, setOwnId] = useState<string | null>(null);
  const [now, setNow] = useState(0);
  const [undoState, setUndoState] = useState<{ originals: Ticket[]; expires: number } | null>(null);
  useEffect(() => {
    setTickets(initialTickets());
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (undoState && now >= undoState.expires) setUndoState(null);
  }, [now, undoState]);
  function addTicket(data: Parameters<Store["addTicket"]>[0], own = false) {
    const arrived = Date.now();
    const id = `TS-2611-${String(42 + tickets.length).padStart(4, "0")}`;
    const item: Ticket = {
      ...data,
      id,
      arrived,
      status: "Aberto",
      ...classify(data.title, data.condo),
      pending: true,
      history: [{ at: arrived, text: `Chamado recebido por ${data.origin}.`, status: "Aberto" }],
    };
    setTickets((prev) => [...prev, item]);
    if (own) setOwnId(id);
    return id;
  }
  // Start the simulated review when the manager opens the queue, including after a resident submission.
  const approve = (ids: string[]) => {
    const originals = batchEligible(tickets).filter((t) => ids.includes(t.id));
    if (!originals.length) return;
    setTickets((prev) => approveBatch(prev, ids));
    setUndoState({ originals, expires: Date.now() + UNDO_MS });
  };
  const undo = () => {
    if (!undoState || Date.now() >= undoState.expires) return;
    setTickets((prev) => undoBatch(prev, undoState.originals));
    setUndoState(null);
  };
  return (
    <Context.Provider
      value={{
        user,
        login: setUser,
        logout: () => { setUser(null); setOwnId(null); setUndoState(null); },
        tickets,
        setTickets,
        ownId,
        addTicket,
        now,
        approve,
        undo,
        undoInfo: undoState
          ? { count: undoState.originals.length, expires: undoState.expires }
          : null,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useTriage() {
  const context = useContext(Context);
  if (!context) throw new Error("Triage provider missing");
  return context;
}
export function useClassification() {
  const { tickets, setTickets } = useTriage();
  const pending = tickets
    .filter((t) => t.pending)
    .map((t) => t.id)
    .join(",");
  useEffect(() => {
    if (!pending) return;
    const ids = pending.split(",");
    const timer = setTimeout(
      () =>
        setTickets((prev) =>
          prev.map((t) =>
            ids.includes(t.id) && t.pending
              ? {
                  ...t,
                  pending: false,
                  history: [...t.history, { at: Date.now(), text: t.reasons.join(" ") }],
                }
              : t,
          ),
        ),
      CLASSIFY_MS,
    );
    return () => clearTimeout(timer);
  }, [pending, setTickets]);
}
