import { History } from "lucide-react";
import {
  formatarDataHora,
  historicoOrdenado,
  type Ocorrencia,
} from "@/lib/ocorrencias";
import { Button } from "@/components/ui/button";
import { Secao } from "./Secao";

type HistoricoProps = {
  ocorrencia: Ocorrencia;
  carregando?: boolean;
  erro?: boolean;
  aoTentarNovamente?: () => void;
};

export function Historico({
  ocorrencia,
  carregando = false,
  erro = false,
  aoTentarNovamente,
}: HistoricoProps) {
  const eventos = historicoOrdenado(ocorrencia);

  return (
    <Secao titulo="Histórico" icone={<History className="size-4" />}>
      {carregando ? (
        <p role="status" className="text-sm text-muted-foreground">
          Carregando histórico…
        </p>
      ) : erro ? (
        <div role="alert" className="grid gap-2">
          <p className="text-sm text-muted-foreground">
            Não foi possível consultar o histórico.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={aoTentarNovamente}
          >
            Tentar novamente
          </Button>
        </div>
      ) : eventos.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Nenhum registro no histórico.
        </p>
      ) : (
        <ol className="relative ml-1.5 border-l pl-5">
          {eventos.map((e, i) => {
            const { data, hora } = formatarDataHora(e.quando);
            const ultimo = i === eventos.length - 1;

            return (
              <li
                key={`${e.quando}-${i}`}
                className="relative pb-5 last:pb-0"
              >
                <span
                  aria-hidden
                  className={
                    "absolute -left-[26.5px] top-1 size-3 rounded-full border-2 border-card " +
                    (ultimo ? "bg-primary" : "bg-muted-foreground/40")
                  }
                />
                <p className="font-mono text-[11px] text-muted-foreground">
                  <time dateTime={e.quando}>
                    {data} · {hora}
                  </time>{" "}
                  ·{" "}
                  <span className="font-sans font-medium text-foreground/80">
                    {e.autor}
                  </span>
                </p>
                <p className="mt-0.5 text-sm font-semibold">
                  {e.acao}
                </p>
                {e.motivo && (
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    {e.motivo}
                  </p>
                )}
                {e.rebaixouTravada && (
                  <p className="mt-0.5 text-sm text-urgente">Prioridade travada rebaixada</p>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </Secao>
  );
}
