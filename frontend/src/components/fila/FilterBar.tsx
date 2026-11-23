import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CONDOMINIOS, PRIORIDADES, type Prioridade } from "@/lib/ocorrencias";

const TODOS = "todos";

export function FilterBar({
  condominio,
  prioridade,
  onCondominio,
  onPrioridade,
  onLimpar,
}: {
  condominio?: string | undefined;
  prioridade?: Prioridade | undefined;
  onCondominio: (v: string | undefined) => void;
  onPrioridade: (v: Prioridade | undefined) => void;
  onLimpar: () => void;
}) {
  const ativos = Boolean(condominio || prioridade);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={condominio ?? TODOS}
        onValueChange={(v) => onCondominio(v === TODOS ? undefined : v)}
      >
        <SelectTrigger aria-label="Filtrar por condomínio" className="h-10 min-w-0 flex-[1_1_9rem] bg-card sm:max-w-64">
          <SelectValue placeholder="Condomínio" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={TODOS}>Todos condomínios</SelectItem>
          {CONDOMINIOS.map((c) => (
            <SelectItem key={c.id} value={c.id}>
              {c.nome}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={prioridade ?? TODOS}
        onValueChange={(v) => onPrioridade(v === TODOS ? undefined : (v as Prioridade))}
      >
        <SelectTrigger aria-label="Filtrar por prioridade" className="h-10 min-w-0 flex-[1_1_9rem] bg-card sm:max-w-44">
          <SelectValue placeholder="Prioridade" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={TODOS}>Todas prioridades</SelectItem>
          {PRIORIDADES.map((p) => (
            <SelectItem key={p.id} value={p.id}>
              {p.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button
        variant="ghost"
        size="sm"
        onClick={onLimpar}
        disabled={!ativos}
        className="h-10 shrink-0 text-muted-foreground"
      >
        <X />
        Limpar Filtros
      </Button>
    </div>
  );
}
