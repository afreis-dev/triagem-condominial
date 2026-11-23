import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { PRIORIDADES, type Prioridade } from "@/lib/ocorrencias";

export const priorityBadgeVariants = cva(
  "inline-flex shrink-0 items-center gap-1.5 rounded-full font-semibold uppercase tracking-wide",
  {
    variants: {
      prioridade: {
        urgente: "bg-urgente text-prio-foreground",
        alta: "bg-alta text-prio-foreground",
        normal: "bg-normal text-prio-foreground",
        baixa: "bg-baixa text-prio-foreground",
      },
      size: {
        sm: "h-5 px-2 text-[10px]",
        md: "h-6 px-2.5 text-[11px]",
      },
    },
    defaultVariants: { size: "sm" },
  },
);

export function PriorityBadge({
  prioridade,
  size,
  className,
}: { prioridade: Prioridade; className?: string } & Pick<
  VariantProps<typeof priorityBadgeVariants>,
  "size"
>) {
  const label = PRIORIDADES.find((p) => p.id === prioridade)?.label;
  return (
    <span className={cn(priorityBadgeVariants({ prioridade, size }), className)}>{label}</span>
  );
}
