import { Link } from "@tanstack/react-router";
import { Clock, MessageCircle, Building2, Phone, Mail, Smartphone, ShieldCheck } from "lucide-react";
import { PriorityBadge } from "./PriorityBadge";
import { nomeCondominio, tempoDecorrido, type Ocorrencia, type Origem } from "@/lib/ocorrencias";
import { cn } from "@/lib/utils";

const ICONE_ORIGEM: Record<Origem, typeof MessageCircle> = {
  WhatsApp: MessageCircle,
  Portaria: ShieldCheck,
  "E-mail": Mail,
  Telefone: Phone,
  App: Smartphone,
};

const barra: Record<Ocorrencia["prioridade"], string> = {
  urgente: "before:bg-urgente",
  alta: "before:bg-alta",
  normal: "before:bg-normal",
  baixa: "before:bg-baixa",
};

export function CartaoOcorrencia({
  ocorrencia,
  demonstracao = false,
}: {
  ocorrencia: Ocorrencia;
  demonstracao?: boolean;
}) {
  const Icone = ICONE_ORIGEM[ocorrencia.origem];
  return (
    <Link
      to="/ocorrencia/$id"
      params={{ id: demonstracao ? `demo-${ocorrencia.id}` : String(ocorrencia.id) }}
      className={cn(
        "relative block min-h-[44px] overflow-hidden rounded-xl border bg-card py-3 pl-4 pr-3.5 shadow-card transition-all",
        "before:absolute before:inset-y-0 before:left-0",
        "hover:-translate-y-px hover:shadow-card-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        barra[ocorrencia.prioridade],
        ocorrencia.prioridade === "urgente" ? "before:w-2" : "before:w-1",
      )}
    >
      {/* 1: priority + condo + elapsed */}
      <div className="flex items-center gap-2">
        <PriorityBadge prioridade={ocorrencia.prioridade} />
        <span className="flex min-w-0 flex-1 items-center gap-1 text-xs font-medium text-muted-foreground">
          <Building2 className="size-3.5 shrink-0" aria-hidden />
          <span className="truncate">
            {ocorrencia.condominioNome ?? nomeCondominio(ocorrencia.condominioId)}
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-1 font-mono text-[11px] text-muted-foreground">
          <Clock className="size-3" aria-hidden />
          {tempoDecorrido(ocorrencia.minutosAtras)}
        </span>
      </div>
      {/* 2: title */}
      <h3 className="mt-1.5 truncate text-[15px] font-semibold leading-snug text-card-foreground">
        {ocorrencia.titulo}
      </h3>
      {/* 3: origin */}
      <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icone className="size-3.5 shrink-0" aria-hidden />
        <span className="shrink-0">
          Origem: <span className="font-medium text-foreground">{ocorrencia.origem}</span>
        </span>
        {ocorrencia.marcaAcao && (
          <span
            className="min-w-0 truncate border-l pl-1.5 font-semibold text-primary"
            title={ocorrencia.marcaAcao}
          >
            {ocorrencia.marcaAcao}
          </span>
        )}
      </p>
      {/* 4: short reason */}
      <p className="mt-0.5 truncate text-[13px] text-muted-foreground">
        <span className="font-medium text-foreground/80">Motivo:</span> {ocorrencia.motivo}
      </p>
    </Link>
  );
}
