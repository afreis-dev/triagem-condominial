import { History } from "lucide-react";
import { formatarDataHora, historicoOrdenado, type Ocorrencia } from "@/lib/ocorrencias";
import { Secao } from "./Secao";

export function Historico({ ocorrencia }: { ocorrencia: Ocorrencia }) {
  const eventos = historicoOrdenado(ocorrencia);
  return (
    <Secao titulo="Histórico" icone={<History className="size-4" />}>
      <ol className="relative ml-1.5 border-l pl-5">
        {eventos.map((e, i) => {
          const { data, hora } = formatarDataHora(e.quando);
          const ultimo = i === eventos.length - 1;
          return (
            <li key={`${e.quando}-${i}`} className="relative pb-5 last:pb-0">
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
                · <span className="font-sans font-medium text-foreground/80">{e.autor}</span>
              </p>
              <p className="mt-0.5 text-sm font-semibold">{e.acao}</p>
              {e.motivo && <p className="mt-0.5 text-sm text-muted-foreground">{e.motivo}</p>}
            </li>
          );
        })}
      </ol>
    </Secao>
  );
}
