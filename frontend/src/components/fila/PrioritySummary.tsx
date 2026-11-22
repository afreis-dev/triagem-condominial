import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { PRIORIDADES, type Prioridade } from "@/lib/ocorrencias";
import { PriorityBadge } from "./PriorityBadge";

const tile = cva(
  "group flex min-w-0 flex-col items-start gap-1 rounded-lg border px-3 py-2.5 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
  {
    variants: {
      prioridade: {
        urgente: "border-urgente/20 bg-urgente-soft text-urgente",
        alta: "border-alta/20 bg-alta-soft text-alta",
        normal: "border-normal/20 bg-normal-soft text-normal",
        baixa: "border-baixa/20 bg-baixa-soft text-baixa",
      },
      ativo: {
        true: "ring-2 ring-current ring-offset-1 ring-offset-background",
        false: "hover:border-current/40",
      },
    },
  },
);

export function PrioritySummary({
  contagem,
  selecionada,
  onSelect,
}: {
  contagem: Record<Prioridade, number>;
  selecionada?: Prioridade | undefined;
  onSelect: (p: Prioridade | undefined) => void;
}) {
  return (
    <section aria-label="Resumo por prioridade" className="grid grid-cols-4 gap-2">
      {PRIORIDADES.map((p) => {
        const ativo = selecionada === p.id;
        return (
          <button
            key={p.id}
            type="button"
            aria-pressed={ativo}
            onClick={() => onSelect(ativo ? undefined : p.id)}
            className={tile({ prioridade: p.id, ativo })}
          >
            <PriorityBadge prioridade={p.id} />
            <span className="font-mono text-2xl font-semibold leading-none tabular-nums">
              {contagem[p.id]}
            </span>
          </button>
        );
      })}
    </section>
  );
}
