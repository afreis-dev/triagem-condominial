import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function Paginacao({
  pagina,
  totalPaginas,
  onChange,
}: {
  pagina: number;
  totalPaginas: number;
  onChange: (p: number) => void;
}) {
  const paginas = Array.from({ length: totalPaginas }, (_, i) => i + 1);
  return (
    <nav aria-label="Paginação" className="flex items-center justify-center gap-1.5">
      <Button
        variant="outline"
        size="sm"
        className="h-9 bg-card px-2.5"
        disabled={pagina <= 1}
        onClick={() => onChange(pagina - 1)}
      >
        <ChevronLeft />
        Anterior
      </Button>
      {paginas.map((p) => (
        <Button
          key={p}
          variant={p === pagina ? "default" : "outline"}
          size="icon"
          aria-current={p === pagina ? "page" : undefined}
          className={cn("size-9 font-mono", p !== pagina && "bg-card")}
          onClick={() => onChange(p)}
        >
          {p}
        </Button>
      ))}
      <Button
        variant="outline"
        size="sm"
        className="h-9 bg-card px-2.5"
        disabled={pagina >= totalPaginas}
        onClick={() => onChange(pagina + 1)}
      >
        Próximo
        <ChevronRight />
      </Button>
    </nav>
  );
}
