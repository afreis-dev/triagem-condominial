import { useState } from "react";
import { ptBR } from "date-fns/locale";
import { CalendarDays, CalendarIcon, ListChecks, UserRound, Users } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  aplicarDecisao,
  dataLocalISO,
  descreverDecisao,
  formatarData,
  validarDecisao,
  type ErrosDecisao,
  type RascunhoDecisao,
  type Ocorrencia,
  type Responsavel,
  type TipoDecisao,
} from "@/lib/ocorrencias";
import { atualizarOcorrencia } from "@/lib/ocorrencias-store";
import { cn } from "@/lib/utils";
import { ErroCampo, Secao, campoErro } from "./Secao";

const OPCOES: { id: TipoDecisao; label: string; icone: typeof Users }[] = [
  { id: "delegar", label: "Delegar", icone: Users },
  { id: "agendar", label: "Agendar", icone: CalendarDays },
  { id: "eu_mesmo", label: "Eu mesmo cuido", icone: UserRound },
];

const RESPONSAVEIS: Responsavel[] = ["Zelador", "Portaria", "Síndico"];

function paraData(iso: string): Date {
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(a!, m! - 1, d!);
}

export function DecisaoSecao({ ocorrencia }: { ocorrencia: Ocorrencia }) {
  const [tipo, setTipo] = useState<TipoDecisao | undefined>(undefined);
  const [responsavel, setResponsavel] = useState<Responsavel | undefined>(undefined);
  const [data, setData] = useState<string | undefined>(undefined);
  const [nota, setNota] = useState("");
  const [tentou, setTentou] = useState(false);
  const [calendarioAberto, setCalendarioAberto] = useState(false);

  const rascunho: RascunhoDecisao = { tipo, responsavel, data, nota };
  const todos = validarDecisao(rascunho, dataLocalISO(new Date()));
  // Past dates are flagged as soon as they are picked; other errors after a submit attempt.
  const erros: ErrosDecisao = tentou ? todos : data && todos.data ? { data: todos.data } : {};

  function confirmar() {
    setTentou(true);
    if (Object.keys(validarDecisao(rascunho, dataLocalISO(new Date()))).length > 0 || !tipo) return;
    atualizarOcorrencia(ocorrencia.id, (o) =>
      aplicarDecisao(o, { tipo, responsavel, data, nota }, new Date().toISOString()),
    );
    toast.success("Decisão confirmada", { description: "Ocorrência movida para Em andamento." });
    setTipo(undefined);
    setResponsavel(undefined);
    setData(undefined);
    setNota("");
    setTentou(false);
  }

  return (
    <Secao titulo="O que você vai fazer" icone={<ListChecks className="size-4" />}>
      {ocorrencia.decisao && (
        <p className="mb-3 rounded-lg bg-secondary px-3 py-2 text-sm text-secondary-foreground">
          Decisão atual: <span className="font-semibold">{descreverDecisao(ocorrencia.decisao)}</span>
        </p>
      )}

      <div role="radiogroup" aria-label="O que você vai fazer" className="grid grid-cols-3 gap-2">
        {OPCOES.map((op) => {
          const ativo = tipo === op.id;
          const Icone = op.icone;
          return (
            <button
              key={op.id}
              type="button"
              role="radio"
              aria-checked={ativo}
              onClick={() => setTipo(op.id)}
              className={cn(
                "flex min-h-16 flex-col items-center justify-center gap-1 rounded-lg border px-1 py-2 text-center text-[13px] font-semibold leading-tight transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                ativo
                  ? "border-primary bg-accent text-accent-foreground ring-1 ring-primary"
                  : "bg-surface text-muted-foreground hover:text-foreground",
                tentou && erros.tipo && "border-destructive",
              )}
            >
              <Icone className="size-5" aria-hidden />
              {op.label}
            </button>
          );
        })}
      </div>
      {erros.tipo && <ErroCampo>{erros.tipo}</ErroCampo>}

      <div className="mt-4 grid gap-4">
        {tipo === "delegar" && (
          <div>
            <Label htmlFor="responsavel" className={erros.responsavel ? "text-destructive" : undefined}>
              Delegar para <span className="text-destructive">*</span>
            </Label>
            <Select value={responsavel ?? ""} onValueChange={(v) => setResponsavel(v as Responsavel)}>
              <SelectTrigger
                id="responsavel"
                aria-invalid={Boolean(erros.responsavel)}
                className={`mt-1.5 h-11 bg-card ${campoErro}`}
              >
                <SelectValue placeholder="Escolha o responsável" />
              </SelectTrigger>
              <SelectContent>
                {RESPONSAVEIS.map((r) => (
                  <SelectItem key={r} value={r}>
                    {r}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {erros.responsavel && <ErroCampo>{erros.responsavel}</ErroCampo>}
          </div>
        )}

        {tipo === "agendar" && (
          <div>
            <Label htmlFor="data-agendada" className={erros.data ? "text-destructive" : undefined}>
              Data <span className="text-destructive">*</span>
            </Label>
            <Popover open={calendarioAberto} onOpenChange={setCalendarioAberto}>
              <PopoverTrigger asChild>
                <Button
                  id="data-agendada"
                  variant="outline"
                  aria-invalid={Boolean(erros.data)}
                  className={cn(
                    "mt-1.5 h-11 w-full justify-start bg-card font-normal",
                    !data && "text-muted-foreground",
                    campoErro,
                  )}
                >
                  <CalendarIcon />
                  {data ? formatarData(data) : "Escolha uma data"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  locale={ptBR}
                  selected={data ? paraData(data) : undefined}
                  onSelect={(d) => {
                    setData(d ? dataLocalISO(d) : undefined);
                    setCalendarioAberto(false);
                  }}
                  modifiers={{ passado: { before: new Date() } }}
                  modifiersClassNames={{ passado: "opacity-40 line-through" }}
                  initialFocus
                  className="pointer-events-auto p-3"
                />
              </PopoverContent>
            </Popover>
            {erros.data && <ErroCampo>{erros.data}</ErroCampo>}
          </div>
        )}

        <div>
          <Label htmlFor="nota-decisao">Nota (opcional)</Label>
          <Textarea
            id="nota-decisao"
            rows={3}
            maxLength={500}
            value={nota}
            onChange={(e) => setNota(e.target.value)}
            placeholder="Ex.: técnico confirmado para a tarde"
            className="mt-1.5 resize-none bg-card"
          />
        </div>

        <Button size="lg" className="h-12 w-full text-base" onClick={confirmar}>
          Confirmar decisão
        </Button>
      </div>
    </Secao>
  );
}
