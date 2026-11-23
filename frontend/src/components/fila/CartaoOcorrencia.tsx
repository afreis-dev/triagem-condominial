import { Link } from "@tanstack/react-router";
import { Clock, MessageCircle, Building2, Phone, Mail, Smartphone, ShieldCheck } from "lucide-react";
import { PriorityBadge } from "./PriorityBadge";
import { nomeCondominio, tempoDecorrido, type Ocorrencia } from "@/lib/ocorrencias";
import { cn } from "@/lib/utils";

const ICONE_ORIGEM: Partial<Record<string, typeof MessageCircle>> = {
  WhatsApp: MessageCircle,
  Portaria: ShieldCheck,
  "E-mail": Mail,
  Telefone: Phone,
  App: Smartphone,
};

const ORIGENS_API: Partial<Record<string, string>> = {
  morador: "Morador",
  proprietario: "Proprietário",
  funcionario: "Funcionário",
  whatsapp_sindico: "WhatsApp",
};

const barra: Record<Ocorrencia["prioridade"], string> = {
  urgente: "before:bg-urgente",
  alta: "before:bg-alta",
  normal: "before:bg-normal",
  baixa: "before:bg-baixa",
};

type DadosCartao = Pick<
  Ocorrencia,
  "condominioId" | "minutosAtras" | "titulo" | "motivo"
> & { id: number | string; origem: string; condominio?: string; prioridade: Ocorrencia["prioridade"] | null; marcaAcao?: string | null };

export function CartaoOcorrencia({ ocorrencia }: { ocorrencia: DadosCartao }) {
  const origem = ORIGENS_API[ocorrencia.origem] ?? ocorrencia.origem;
  const Icone = ICONE_ORIGEM[origem] ?? Smartphone;
  const classe = cn(
        "relative block overflow-hidden rounded-xl border bg-card py-3 pl-4 pr-3.5 shadow-card transition-all",
        "before:absolute before:inset-y-0 before:left-0",
        "hover:-translate-y-px hover:shadow-card-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        ocorrencia.prioridade && barra[ocorrencia.prioridade],
        ocorrencia.prioridade === "urgente" ? "before:w-2" : "before:w-1",
  );
  const conteudo = (
    <>
      {/* 1: priority + condo + elapsed */}
      <div className="flex items-center gap-2">
        {ocorrencia.prioridade ? (
          <PriorityBadge prioridade={ocorrencia.prioridade} />
        ) : (
          <span className="text-xs text-muted-foreground">Sem prioridade</span>
        )}
        <span className="flex min-w-0 flex-1 items-center gap-1 text-xs font-medium text-muted-foreground">
          <Building2 className="size-3.5 shrink-0" aria-hidden />
          <span className="truncate">{ocorrencia.condominio ?? nomeCondominio(ocorrencia.condominioId)}</span>
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
        <Icone className="size-3.5" aria-hidden />
        <span>
          Origem: <span className="font-medium text-foreground">{origem}</span>
        </span>
      </p>
      {/* 4: short reason */}
      <p className="mt-0.5 truncate text-[13px] text-muted-foreground">
        <span className="font-medium text-foreground/80">Motivo:</span> {ocorrencia.motivo}
      </p>
      {ocorrencia.marcaAcao && (
        <p className="mt-2 text-sm font-semibold text-primary">{ocorrencia.marcaAcao}</p>
      )}
    </>
  );
  if (typeof ocorrencia.id === "string" && !ocorrencia.id.startsWith("h11-")) {
    return <article className={classe}>{conteudo}</article>;
  }
  return (
    <Link to="/ocorrencia/$id" params={{ id: String(ocorrencia.id) }} className={classe}>
      {conteudo}
    </Link>
  );
}
