import { useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowUpRight,
  Check,
  ChevronRight,
  ClipboardList,
  MessageSquare,
  Plus,
  X,
} from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import { Button } from "@/components/ui/button";
import { useClassification, useTriage } from "./store";
import {
  age,
  batchEligible,
  condos,
  priorities,
  sortTickets,
  statusDescriptions,
  type Priority,
  type Status,
  type Ticket,
} from "./domain";
export function PriorityLabel({ priority }: { priority: Priority }) {
  return (
    <span className={`priority-label priority-${priority}`}>
      <span className="priority-dot" />
      {priority}
    </span>
  );
}
function TicketCard({ ticket, now }: { ticket: Ticket; now: number }) {
  return (
    <Link
      to="/chamado/$id"
      params={{ id: ticket.id }}
      className={`ticket-card priority-${ticket.priority} ${ticket.pending ? "pending-ticket" : ""}`}
    >
      <div className="ticket-first">
        <div>
          {ticket.pending ? (
            <span className="classifying">
              <span />
              Classificando...
            </span>
          ) : (
            <PriorityLabel priority={ticket.priority} />
          )}
          <span className="ticket-condo">{condos[ticket.condo]}</span>
        </div>
        <span className="mono ticket-time">{age(ticket.arrived, now)}</span>
      </div>
      <h3>{ticket.title}</h3>
      <div className="ticket-bottom">
        <p>
          {ticket.pending ? (
            "Analisando a descrição do chamado…"
          ) : (
            <>
              <span className="suggested">sugerido</span>
              {ticket.reasons[0]}
            </>
          )}
        </p>
        {ticket.origin === "WhatsApp" && (
          <span className="origin">
            <MessageSquare size={12} />
            WhatsApp
          </span>
        )}
      </div>
      <ChevronRight className="ticket-arrow" size={19} />
    </Link>
  );
}
export function Queue() {
  useClassification();
  const { tickets, now } = useTriage();
  const [condo, setCondo] = useState<number | null>(null);
  const [status, setStatus] = useState<Status>("Aberto");
  const [priority, setPriority] = useState<Priority | null>(null);
  const [paste, setPaste] = useState(false);
  const urgent = tickets.filter(
    (t) => t.status === "Aberto" && t.priority === "Urgente" && !t.pending,
  );
  const eligible = batchEligible(tickets);
  const working = tickets.filter((t) => t.status === "Em andamento");
  const filtered = sortTickets(
    tickets.filter(
      (t) =>
        (condo === null || t.condo === condo) &&
        t.status === status &&
        (!priority || t.priority === priority),
    ),
  );
  const urgentList = filtered.filter((t) => t.priority === "Urgente" && !t.pending);
  const otherList = filtered.filter((t) => t.priority !== "Urgente" || t.pending);
  const cards = [
    null,
    ...condos
      .map((_, i) => i)
      .sort(
        (a, b) =>
          Number(urgent.some((t) => t.condo === b)) - Number(urgent.some((t) => t.condo === a)),
      ),
  ];
  return (
    <main className="page queue-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">VISÃO DO SÍNDICO</div>
          <h1>Fila da carteira</h1>
          <p className="summary">
            {urgent.length ? (
              <>
                <span className="urgent-summary">
                  <span className="live-dot" />
                  {urgent.length} urgentes agora
                </span>
                <span className="summary-separator">·</span>
                {eligible.length} para aprovar em lote<span className="summary-separator">·</span>
                {working.length} em andamento
              </>
            ) : (
              "Nenhuma urgência. Tudo em dia."
            )}
          </p>
        </div>
        <div className="heading-actions">
          <Button variant="outline" onClick={() => setPaste(true)}>
            <Plus />
            Colar mensagem
          </Button>
          <Button asChild>
            <Link to="/lote">
              <Check />
              Revisar lote ({eligible.length})<ArrowUpRight />
            </Link>
          </Button>
        </div>
      </div>
      <section className="condo-section" aria-label="Condomínios">
        <div className="section-caption">
          <h2>Condomínios</h2>
          <span>{condos.length} na carteira</span>
        </div>
        <div className="condo-grid">
          {cards.map((index) => {
            const group = tickets.filter((t) => index === null || t.condo === index);
            const risk = group.filter(
              (t) => t.status === "Aberto" && t.priority === "Urgente" && !t.pending,
            );
            const oldest = Math.min(...risk.map((t) => t.arrived));
            return (
              <Button
                key={index ?? "all"}
                variant="outline"
                onClick={() => setCondo(index)}
                className={`condo-card ${index === condo ? "active" : ""} ${risk.length ? "has-urgent" : ""}`}
              >
                <div className="condo-alert">
                  {risk.length ? (
                    <>
                      <AlertCircle size={13} />
                      <span>URGENTE</span>
                      <span className="mono">{age(oldest, now)}</span>
                    </>
                  ) : (
                    <>
                      <Check size={13} />
                      <span>Sem urgências</span>
                    </>
                  )}
                </div>
                <div className="condo-card-body">
                  <h3>{index === null ? "Todos" : condos[index]}</h3>
                  <div className="condo-stats">
                    <span>
                      <strong className={risk.length ? "urgent-number" : ""}>{risk.length}</strong>
                      urgentes
                    </span>
                    <span>
                      <strong>{group.filter((t) => t.status === "Aberto").length}</strong>abertos
                    </span>
                    <span>
                      <strong>{group.filter((t) => t.status === "Em andamento").length}</strong>em
                      andamento
                    </span>
                  </div>
                </div>
                {index === condo && (
                  <span className="selected-condo">
                    <Check size={12} />
                  </span>
                )}
              </Button>
            );
          })}
        </div>
      </section>
      <section className="tickets-section">
        <div className="status-tabs">
          {(["Aberto", "Em andamento", "Fechado"] as Status[]).map((s) => (
            <Button
              key={s}
              variant="ghost"
              className={status === s ? "active" : ""}
              onClick={() => setStatus(s)}
            >
              {s}
              <span className="tab-count">
                {
                  tickets.filter((t) => t.status === s && (condo === null || t.condo === condo))
                    .length
                }
              </span>
            </Button>
          ))}
        </div>
        <div className="filter-row">
          <p>{statusDescriptions[status]}</p>
          <div className="priority-filters">
            <span>Prioridade</span>
            <Button
              variant="ghost"
              className={!priority ? "active" : ""}
              onClick={() => setPriority(null)}
            >
              Todas
            </Button>
            {priorities.map((p) => (
              <Button
                variant="ghost"
                key={p}
                className={priority === p ? "active" : ""}
                onClick={() => setPriority(priority === p ? null : p)}
              >
                <PriorityLabel priority={p} />
              </Button>
            ))}
          </div>
        </div>
        {urgentList.length > 0 && (
          <div className="urgent-group">
            <div className="group-label">
              <AlertCircle size={16} />
              <h2>{status === "Aberto" ? "Urgentes agora" : "Prioridade urgente"}</h2>
              <span>{urgentList.length}</span>
              {status === "Aberto" && <p>Precisam da sua decisão, uma por uma</p>}
            </div>
            {urgentList.map((t) => (
              <TicketCard key={t.id} ticket={t} now={now} />
            ))}
          </div>
        )}
        {otherList.length > 0 && (
          <div className="regular-group">
            <div className="group-label neutral">
              <h2>{status === "Aberto" ? "Demais chamados" : "Chamados"}</h2>
              <span>{otherList.length}</span>
              {status === "Aberto" && <p>Revisão individual ou aprovação em lote</p>}
            </div>
            {otherList.map((t) => (
              <TicketCard key={t.id} ticket={t} now={now} />
            ))}
          </div>
        )}
        {!filtered.length && (
          <div className="empty">
            <ClipboardList />
            <h3>
              {status === "Aberto"
                ? "Nenhum chamado aberto"
                : `Nenhum chamado ${status.toLowerCase()}`}
            </h3>
          </div>
        )}
      </section>
      <footer className="page-footer">
        <span>Triagem do Síndico</span>
        <span>
          <span className="footer-dot" />
          Todas as decisões ficam registradas
        </span>
      </footer>
      <PastePanel open={paste} onOpenChange={setPaste} />
    </main>
  );
}
function PastePanel({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { addTicket } = useTriage();
  const [text, setText] = useState("");
  const [condo, setCondo] = useState(0);
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="panel-overlay" />
        <Dialog.Content className="bottom-panel">
          <div className="panel-handle" />
          <div className="panel-heading">
            <Dialog.Title>Colar mensagem</Dialog.Title>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Fechar">
                <X />
              </Button>
            </Dialog.Close>
          </div>
          <Dialog.Description className="muted">Mensagem recebida pelo WhatsApp</Dialog.Description>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!text.trim()) return;
              addTicket({
                title: text,
                condo,
                name: "Registrado pelo síndico",
                apartment: "Não informado",
                phone: "11999990000",
                location: "Não informado",
                origin: "WhatsApp",
                role: "Síndico",
              });
              setText("");
              onOpenChange(false);
            }}
          >
            <label>
              Condomínio
              <select value={condo} onChange={(e) => setCondo(Number(e.target.value))}>
                {condos.map((c, i) => (
                  <option key={c} value={i}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Mensagem
              <textarea
                required
                rows={5}
                placeholder="Cole a mensagem do morador aqui"
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </label>
            <Button type="submit" className="w-full">
              Salvar chamado
              <ChevronRight />
            </Button>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
