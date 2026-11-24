import { Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";

export function EmptyState({
  titulo,
  filtrosAtivos,
  onLimpar,
}: {
  titulo: string;
  filtrosAtivos: boolean;
  onLimpar: () => void;
}) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed bg-surface px-6 py-14 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
        <Inbox className="size-6" aria-hidden />
      </div>
      <p className="mt-4 text-base font-semibold">{titulo}</p>
      <p className="mt-1 max-w-xs text-sm text-muted-foreground">
        {filtrosAtivos
          ? "Nada corresponde aos filtros selecionados."
          : "Quando chegar uma nova mensagem, ela aparece aqui."}
      </p>
      {filtrosAtivos && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onLimpar}>
          Limpar Filtros
        </Button>
      )}
    </div>
  );
}
