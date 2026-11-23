import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Secao({
  titulo,
  icone,
  children,
  className,
}: {
  titulo: string;
  icone?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-xl border bg-card p-4 shadow-card sm:p-5", className)}>
      <h2 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {icone}
        {titulo}
      </h2>
      {children}
    </section>
  );
}

export function ErroCampo({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p id={id} className="mt-1.5 text-xs font-medium text-destructive">
      {children}
    </p>
  );
}

export const campoErro =
  "aria-[invalid=true]:border-destructive aria-[invalid=true]:bg-destructive/5 aria-[invalid=true]:ring-1 aria-[invalid=true]:ring-destructive/40";
