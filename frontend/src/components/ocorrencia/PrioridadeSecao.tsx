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
  exigeMotivoPrioridade,
  validarMudancaPrioridade,
  type Ocorrencia,
  type Prioridade,
} from "@/lib/ocorrencias";
import { atualizarOcorrencia } from "@/lib/ocorrencias-store";
import { usePrioridadeApi } from "@/lib/fila-api";
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

export function PrioridadeSecao({ ocorrencia, demonstracao }: {
  ocorrencia: Ocorrencia;
  demonstracao: boolean;
}) {
  const [escolhida, setEscolhida] = useState<Prioridade>(ocorrencia.prioridadeSugerida);
  const [motivo, setMotivo] = useState("");
  const [tentou, setTentou] = useState(false);
  const api = usePrioridadeApi(String(ocorrencia.id));
  const requerMotivo = exigeMotivoPrioridade(ocorrencia, escolhida);
  const alerta = alertaDeRisco(ocorrencia, escolhida);
  const erro = tentou && requerMotivo ? validarMudancaPrioridade(motivo) : undefined;
  const concluida = ocorrencia.status === "concluida";
  const bloqueado = concluida || api.isPending;

  function cancelar() {
    setEscolhida(ocorrencia.prioridadeSugerida);
    setMotivo("");
    setTentou(false);
  }

  async function salvar() {
    if (bloqueado) return;
    setTentou(true);
    if (requerMotivo && validarMudancaPrioridade(motivo)) return;
    try {
      if (demonstracao) {
        atualizarOcorrencia(ocorrencia.id, (o) =>
          aplicarMudancaPrioridade(o, escolhida, motivo, new Date().toISOString()),
        );
      } else {
        await api.mutateAsync({ prioridade: escolhida, ...(requerMotivo ? { motivo: motivo.trim() } : {}) });
      }
    } catch (erro) {
      toast.error(erro instanceof Error ? erro.message : "Não foi possível confirmar a prioridade.");
      return;
    }
    toast.success(requerMotivo ? "Prioridade alterada" : "Prioridade confirmada");
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
            onClick={() => {
              setEscolhida(p.id);
              setTentou(false);
            }}
            className={opcao({ prioridade: p.id }) + " bg-surface text-muted-foreground hover:text-foreground"}
          >
            {p.label}
            {ocorrencia.prioridadeSugerida === p.id && (
              <span className="text-[9px] font-medium uppercase tracking-wider opacity-80">Sugerida</span>
            )}
          </button>
        ))}
      </div>

      {requerMotivo && !concluida && (
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
              disabled={bloqueado}
              aria-required
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Explique por que a prioridade mudou"
              aria-invalid={Boolean(erro)}
              aria-describedby={erro ? "motivo-mudanca-erro" : undefined}
              className={`mt-1.5 resize-none bg-card ${campoErro}`}
            />
            {erro && <ErroCampo id="motivo-mudanca-erro">{erro}</ErroCampo>}
          </div>
        </div>
      )}
      {!concluida && (
        <div className="mt-4 flex gap-2">
          {requerMotivo && escolhida !== ocorrencia.prioridadeSugerida && (
            <Button disabled={bloqueado} variant="outline" className="flex-1 sm:flex-none" onClick={cancelar}>
              Cancelar
            </Button>
          )}
          <Button disabled={bloqueado} className="flex-1 sm:flex-none" onClick={() => void salvar()}>
            {api.isPending ? "Confirmando…" : escolhida === "urgente" ? "Confirmar urgente" : "Confirmar prioridade"}
          </Button>
        </div>
      )}
    </Secao>
  );
}
