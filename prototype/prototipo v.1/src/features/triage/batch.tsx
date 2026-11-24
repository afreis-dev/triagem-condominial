import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Check, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTriage } from "./store";
import { batchEligible, condos, sortTickets } from "./domain";
import { PriorityLabel } from "./queue";
import { PageBack } from "./shell";
export function Batch() {
  const { tickets, approve } = useTriage();
  const navigate = useNavigate();
  const [excluded, setExcluded] = useState<string[]>([]);
  const eligible = sortTickets(batchEligible(tickets));
  const selected = eligible.filter((t) => !excluded.includes(t.id));
  return (
    <main className="page batch-page">
      <PageBack />
      <div className="page-heading">
        <div>
          <div className="eyebrow">REVISÃO DO SÍNDICO</div>
          <h1>Aprovação em lote</h1>
          <p className="muted">{eligible.length} chamados aguardando sua decisão</p>
        </div>
        <span className="batch-notice">
          <ShieldCheck size={17} />
          Urgências nunca entram no lote.
        </span>
      </div>
      <div className="batch-list">
        {eligible.map((t) => (
          <label className="batch-row" key={t.id}>
            <input
              type="checkbox"
              checked={!excluded.includes(t.id)}
              onChange={(e) =>
                setExcluded((prev) =>
                  e.target.checked ? prev.filter((id) => id !== t.id) : [...prev, t.id],
                )
              }
            />
            <div>
              <div className="batch-title">
                <PriorityLabel priority={t.priority} />
                <h3>{t.title}</h3>
              </div>
              <p className="muted">
                {condos[t.condo]} <span>·</span> {t.assignee}
              </p>
              <p className="batch-reason">
                <span className="suggested">sugerido</span>
                {t.reasons[2]}
              </p>
            </div>
          </label>
        ))}
      </div>
      {!eligible.length && (
        <div className="empty">
          <Check />
          <h3>Nenhuma sugestão para aprovar</h3>
        </div>
      )}
      <div className="batch-bottom">
        <div>
          <span>
            {selected.length} de {eligible.length} selecionados
          </span>
          <Button
            disabled={!selected.length}
            onClick={() => {
              approve(selected.map((t) => t.id));
              navigate({ to: "/" });
            }}
          >
            <Check />
            Aprovar {selected.length} sugestões
          </Button>
        </div>
      </div>
    </main>
  );
}
