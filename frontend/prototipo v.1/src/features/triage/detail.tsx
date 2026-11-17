import { useState } from "react";
import {
  Check,
  Phone,
  ShieldCheck,
  Send,
  CalendarDays,
  UserRound,
  LockKeyhole,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTriage } from "./store";
import { actOnTicket, condos, people, priorities, stamp, type Priority } from "./domain";
import { PriorityLabel } from "./queue";
import { PageBack } from "./shell";
export function Detail({ id }: { id: string }) {
  const { tickets, setTickets } = useTriage();
  const ticket = tickets.find((t) => t.id === id);
  const [change, setChange] = useState(false);
  const [newPriority, setNewPriority] = useState<Priority>("Normal");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [action, setAction] = useState("Delegar");
  const [assignee, setAssignee] = useState("");
  const [date, setDate] = useState("");
  if (!ticket)
    return (
      <main className="page">
        <PageBack />
        <h1>Chamado não encontrado</h1>
      </main>
    );
  const chosen = assignee || ticket.assignee;
  const update = (text: string, status: "Aberto" | "Em andamento" | "Fechado") =>
    setTickets((prev) =>
      prev.map((t) => (t.id === id ? actOnTicket({ ...t, assignee: chosen }, text, status) : t)),
    );
  function decide() {
    if (!ticket) return;
    if (change && !reason.trim()) {
      setError("Escreva o motivo para mudar a prioridade.");
      return;
    }
    if (action === "Agendar" && !date) {
      setError("Escolha uma data para agendar.");
      return;
    }
    const motive = change
      ? `Prioridade alterada para ${newPriority} pelo síndico porque ${reason.trim()}. Sugestão original: ${ticket.reasons[0]}`
      : ticket.priority === "Urgente"
        ? `Urgência confirmada pelo síndico. ${ticket.reasons[0]}`
        : `Sugestão confirmada pelo síndico. ${ticket.reasons[0]}`;
    const actionText =
      action === "Delegar"
        ? `Delegado a ${chosen}. ${chosen === ticket.assignee ? ticket.reasons[2] : "Responsável escolhido pelo síndico."}`
        : action === "Agendar"
          ? `Agendado pelo síndico para ${stamp(new Date(date).getTime())}.`
          : "O próprio síndico assumiu o chamado.";
    setTickets((prev) =>
      prev.map((t) =>
        t.id === id
          ? actOnTicket(
              {
                ...t,
                priority: change ? newPriority : t.priority,
                assignee: action === "Delegar" ? chosen : "O próprio síndico",
                history: [...t.history, { at: Date.now(), text: motive }],
              },
              actionText,
              "Em andamento",
            )
          : t,
      ),
    );
    setError("");
    setChange(false);
  }
  const parts = ticket.keyword
    ? ticket.title.split(new RegExp(`(${ticket.keyword})`, "gi"))
    : [ticket.title];
  const message = `${condos[ticket.condo]}\nLocal: ${ticket.location}\n${ticket.title}\nProtocolo: ${ticket.id}`;
  return (
    <main className="page detail-page">
      <PageBack />
      <div className="detail-heading">
        <div>
          <div className="eyebrow">
            DETALHE DO CHAMADO <span className="mono">/ {ticket.id}</span>
          </div>
          <h1>
            <PriorityLabel priority={ticket.priority} />
          </h1>
        </div>
        <span className="status-badge">{ticket.status}</span>
      </div>
      <div className="detail-grid">
        <div>
          <section className="explanation">
            <h2>
              <ShieldCheck size={19} />
              Por que o sistema sugeriu isso
            </h2>
            {ticket.reasons.map((r, i) => (
              <div key={r}>
                <span className="reason-label">
                  {["PRIORIDADE", "CATEGORIA", "RESPONSÁVEL"][i]}
                </span>
                <p>{r}</p>
              </div>
            ))}
          </section>
          <section className="detail-description">
            <div className="section-caption">
              <h2>Descrição do chamado</h2>
              <span className="mono">{stamp(ticket.arrived)}</span>
            </div>
            <p className={`description-text priority-${ticket.priority}`}>
              {parts.map((p, i) =>
                ticket.keyword && p.toLowerCase() === ticket.keyword.toLowerCase() ? (
                  <mark key={i}>{p}</mark>
                ) : (
                  p
                ),
              )}
            </p>
            {ticket.photo && (
              <img className="attachment" src={ticket.photo} alt="Foto enviada do problema" />
            )}
            <dl className="metadata">
              <div>
                <dt>Condomínio</dt>
                <dd>{condos[ticket.condo]}</dd>
              </div>
              <div>
                <dt>Local</dt>
                <dd>{ticket.location || "Não informado"}</dd>
              </div>
              <div>
                <dt>Quem registrou</dt>
                <dd>
                  {ticket.name || "Nome não informado"} ·{" "}
                  {ticket.apartment ? `Apto. ${ticket.apartment}` : ticket.role}
                  <Button variant="outline" asChild>
                    <a href={`tel:${ticket.phone}`}>
                      <Phone />
                      Ligar
                    </a>
                  </Button>
                </dd>
              </div>
              <div>
                <dt>Origem</dt>
                <dd>{ticket.origin}</dd>
              </div>
              <div>
                <dt>Protocolo</dt>
                <dd className="mono">{ticket.id}</dd>
              </div>
            </dl>
          </section>
          <section className="history">
            <div className="section-caption">
              <h2>Histórico</h2>
              <span>
                <LockKeyhole size={12} />
                Registro não editável
              </span>
            </div>
            <ol>
              {ticket.history.map((entry, i) => (
                <li key={i}>
                  <span className="timeline-dot" />
                  <time className="mono">{stamp(entry.at)}</time>
                  <p>{entry.text}</p>
                </li>
              ))}
            </ol>
          </section>
        </div>
        <aside className="decision-panel">
          <h2>
            {ticket.status === "Aberto"
              ? "Sua decisão"
              : ticket.status === "Em andamento"
                ? "Em andamento"
                : "Chamado concluído"}
          </h2>
          {ticket.status === "Aberto" ? (
            <>
              <div className="decision-priority">
                <span>Prioridade sugerida</span>
                <PriorityLabel priority={ticket.priority} />
                <Button variant="ghost" onClick={() => setChange(!change)}>
                  Mudar prioridade
                </Button>
              </div>
              {change && (
                <>
                  <label>
                    Nova prioridade
                    <select
                      value={newPriority}
                      onChange={(e) => setNewPriority(e.target.value as Priority)}
                    >
                      {priorities.map((p) => (
                        <option key={p}>{p}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Motivo da alteração
                    <textarea
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="Por que a prioridade deve mudar?"
                      rows={3}
                    />
                  </label>
                </>
              )}
              <h3>Como será resolvido?</h3>
              <div className="action-options">
                {["Delegar", "Agendar", "Eu mesmo cuido"].map((a, i) => (
                  <Button
                    variant="outline"
                    key={a}
                    className={action === a ? "active" : ""}
                    onClick={() => setAction(a)}
                  >
                    {i === 0 ? <Send /> : i === 1 ? <CalendarDays /> : <UserRound />}
                    {a}
                  </Button>
                ))}
              </div>
              {action === "Delegar" && (
                <>
                  <label>
                    Responsável
                    <select value={chosen} onChange={(e) => setAssignee(e.target.value)}>
                      {people.map((p) => (
                        <option key={p}>{p}</option>
                      ))}
                    </select>
                  </label>
                  <p className="assignee-reason">
                    <span className="suggested">sugerido</span>
                    {ticket.reasons[2]}
                  </p>
                </>
              )}
              {action === "Agendar" && (
                <label>
                  Data e horário
                  <input
                    type="datetime-local"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                  />
                </label>
              )}
              {error && (
                <p className="field-error" role="alert">
                  {error}
                </p>
              )}
              <Button onClick={decide} disabled={ticket.pending} className="w-full">
                <Check />
                {change
                  ? "Salvar decisão"
                  : ticket.priority === "Urgente"
                    ? "Confirmar urgente e agir"
                    : action === "Delegar"
                      ? "Confirmar e delegar"
                      : "Confirmar ação"}
              </Button>
              <p className="decision-footnote">
                <LockKeyhole size={12} />
                Sua decisão será registrada no histórico.
              </p>
            </>
          ) : (
            <>
              <p className="muted">Responsável</p>
              <h3>{ticket.assignee}</h3>
              {ticket.status === "Em andamento" && (
                <>
                  <Button variant="outline" asChild className="w-full">
                    <a
                      target="_blank"
                      rel="noreferrer"
                      href={`https://wa.me/5511999990000?text=${encodeURIComponent(message)}`}
                    >
                      <Send />
                      Avisar pelo WhatsApp
                    </a>
                  </Button>
                  <Button
                    onClick={() => update("Chamado concluído pelo síndico.", "Fechado")}
                    className="w-full mt-4"
                  >
                    <Check />
                    Concluir
                  </Button>
                </>
              )}
              {ticket.status === "Fechado" && (
                <p className="closed-note">
                  <Check />
                  Resolvido e registrado.
                </p>
              )}
            </>
          )}
        </aside>
      </div>
    </main>
  );
}
