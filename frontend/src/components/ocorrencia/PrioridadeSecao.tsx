import { useState } from "react";
import { cva } from "class-variance-authority";
import { AlertTriangle, Gauge } from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  PRIORIDADES,
  alertaDeRisco,
  aplicarMudancaPrioridade,
  validarMudancaPrioridade,
  type Ocorrencia,
  type Prioridade,
} from "@/lib/ocorrencias";
import { atualizarOcorrencia } from "@/lib/ocorrencias-store";
import { ErroCampo, Secao, campoErro } from "./Secao";

const opcao = cva(
  "relative flex h-12 flex-col items-center justify-center rounded-lg border text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60",
  {
    variants: {
      prioridade: {
        urgente: "data-[ativo=true]:border-urgente data-[ativo=true]:bg-urgente-soft data-[ativo=true]:text-urgente",
        alta: "data-[ativo=true]:border-alta data-[ativo=true]:bg-alta-soft data-[ativo=true]:text-alta",
        normal: "data-[ativo=true]:border-normal data-[ativo=true]:bg-normal-soft data-[ativo=true]:text-normal",
        baixa: "data-[ativo=true]:border-baixa data-[ativo=true]:bg-baixa-soft data-[ativo=true]:text-baixa",
      },
    },
  },
);

export function PrioridadeSecao({ ocorrencia }: { ocorrencia: Ocorrencia }) {
  const [escolhida, setEscolhida] = useState<Prioridade>(ocorrencia.prioridade);
  const [motivo, setMotivo] = useState("");
  const [tentou, setTentou] = useState(false);
  const mudou = escolhida !== ocorrencia.prioridade;
  const alerta = mudou ? alertaDeRisco(ocorrencia, escolhida) : null;
  const erro = tentou ? validarMudancaPrioridade(motivo) : undefined;
  const bloqueado = ocorrencia.status === "concluida";

  function cancelar() {
    setEscolhida(ocorrencia.prioridade);
    setMotivo("");
    setTentou(false);
  }

  function salvar() {
    setTentou(true);
    if (validarMudancaPrioridade(motivo)) return;
    atualizarOcorrencia(ocorrencia.id, (o) =>
      aplicarMudancaPrioridade(o, escolhida, motivo, new Date().toISOString()),
    );
    toast.success("Prioridade alterada");
    setMotivo("");
    setTentou(false);
  }

  return (
    <Secao titulo="Prioridade (sugerida pelo sistema)" icone={<Gauge className="size-4" />}>
      <div role="radiogroup" aria-label="Prioridade" className="grid grid-cols-4 gap-2">
        {PRIORIDADES.map((p) => (
          <button
            key={p.id}
            type="button"
            role="radio"
            aria-checked={escolhida === p.id}
            data-ativo={escolhida === p.id}
            disabled={bloqueado}
            onClick={() => setEscolhida(p.id)}
            className={opcao({ prioridade: p.id }) + " bg-surface text-muted-foreground hover:text-foreground"}
          >
            {p.label}
            {ocorrencia.prioridadeSugerida === p.id && (
              <span className="text-[9px] font-medium uppercase tracking-wider opacity-80">Sugerida</span>
            )}
          </button>
        ))}
      </div>

      {mudou && (
        <div className="mt-4 grid gap-3">
          {alerta && (
            <Alert variant="destructive" className="border-urgente/40 bg-urgente-soft text-urgente">
              <AlertTriangle className="size-4" />
              <AlertDescription className="font-medium text-urgente">{alerta}</AlertDescription>
            </Alert>
          )}
          <div>
            <Label htmlFor="motivo-mudanca" className={erro ? "text-destructive" : undefined}>
              Motivo da mudança <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="motivo-mudanca"
              rows={3}
              maxLength={500}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Explique por que a prioridade mudou"
              aria-invalid={Boolean(erro)}
              aria-describedby={erro ? "motivo-mudanca-erro" : undefined}
              className={`mt-1.5 resize-none bg-card ${campoErro}`}
            />
            {erro && <ErroCampo id="motivo-mudanca-erro">{erro}</ErroCampo>}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" className="flex-1 sm:flex-none" onClick={cancelar}>
              Cancelar
            </Button>
            <Button className="flex-1 sm:flex-none" onClick={salvar}>
              Salvar prioridade
            </Button>
          </div>
        </div>
      )}
    </Secao>
  );
}
