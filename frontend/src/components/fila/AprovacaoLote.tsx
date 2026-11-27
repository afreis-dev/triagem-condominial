import { useCallback, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ListChecks } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  aprovarLote,
  buscarParaAprovacao,
  desfazerLote,
  responsavelDoLote,
} from "@/lib/aprovacao-lote-api";
import { chaveFila } from "@/lib/fila-api";
import { PriorityBadge } from "./PriorityBadge";

const DEZ_SEGUNDOS = 10_000;
const CHAVE_APROVACAO = ["para-aprovacao"] as const;

interface LoteAprovado {
  ids: number[];
  expiraEm: number;
}

export function AprovacaoLote() {
  const [aberto, setAberto] = useState(false);
  const [desmarcados, setDesmarcados] = useState<number[]>([]);
  const [lotes, setLotes] = useState<LoteAprovado[]>([]);
  const removerLote = useCallback((lote: LoteAprovado) => {
    setLotes((anteriores) => anteriores.filter((item) => item !== lote));
  }, []);
  const queryClient = useQueryClient();
  const lista = useQuery({
    queryKey: CHAVE_APROVACAO,
    queryFn: ({ signal }) => buscarParaAprovacao(signal),
    enabled: aberto,
    retry: false,
  });
  const ocorrencias = lista.data ?? [];
  const selecionados = ocorrencias.filter((o) => !desmarcados.includes(o.id)).map((o) => o.id);

  function atualizar(ids: number[]) {
    void queryClient.invalidateQueries({ queryKey: chaveFila() });
    void queryClient.invalidateQueries({ queryKey: CHAVE_APROVACAO });
    for (const id of ids) {
      void queryClient.invalidateQueries({ queryKey: ["ocorrencia", String(id)] });
      void queryClient.invalidateQueries({ queryKey: ["historico", id] });
    }
  }

  const aprovacao = useMutation({
    mutationFn: aprovarLote,
    onSuccess: (ids) => {
      setLotes((anteriores) => [...anteriores, { ids, expiraEm: Date.now() + DEZ_SEGUNDOS }]);
      setAberto(false);
      atualizar(ids);
    },
    onError: () => {
      void queryClient.invalidateQueries({ queryKey: CHAVE_APROVACAO });
      void queryClient.invalidateQueries({ queryKey: chaveFila() });
    },
  });

  function alternarDialog(proximo: boolean) {
    if (aprovacao.isPending) return;
    if (proximo) {
      setDesmarcados([]);
      aprovacao.reset();
    }
    setAberto(proximo);
  }

  return (
    <>
      <Dialog open={aberto} onOpenChange={alternarDialog}>
        <DialogTrigger asChild>
          <Button variant="outline"><ListChecks aria-hidden="true" /> Aprovação em lote</Button>
        </DialogTrigger>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Aprovação em lote</DialogTitle>
            <DialogDescription>Revise as sugestões e desmarque as ocorrências que deseja manter abertas.</DialogDescription>
          </DialogHeader>
          {lista.isFetching && <p role="status">Buscando ocorrências…</p>}
          {lista.isError && (
            <div>
              <p role="alert">{lista.error.message}</p>
              <Button variant="outline" onClick={() => void lista.refetch()}>Tentar novamente</Button>
            </div>
          )}
          {lista.isSuccess && !lista.isFetching && ocorrencias.length === 0 && (
            <p>Nenhuma ocorrência disponível para aprovação.</p>
          )}
          {ocorrencias.length > 0 && (
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" disabled={aprovacao.isPending || selecionados.length === ocorrencias.length} onClick={() => setDesmarcados([])}>
                Selecionar tudo
              </Button>
              <Button variant="outline" size="sm" disabled={aprovacao.isPending || !selecionados.length} onClick={() => setDesmarcados(ocorrencias.map((o) => o.id))}>
                Limpar tudo
              </Button>
            </div>
          )}
          {ocorrencias.length > 0 && (
            <ul className="max-h-[50vh] divide-y overflow-y-auto">
              {ocorrencias.map((o) => (
                <li key={o.id}>
                  <label className="flex items-start gap-3 px-1 py-2">
                    <input
                      type="checkbox"
                      className="mt-1 size-4 shrink-0 accent-primary"
                      aria-label={o.descricao}
                      checked={!desmarcados.includes(o.id)}
                      disabled={aprovacao.isPending}
                      onChange={(evento) => {
                        const marcada = evento.currentTarget.checked;
                        setDesmarcados((ids) => marcada ? ids.filter((id) => id !== o.id) : [...ids, o.id]);
                      }}
                    />
                    <span className="min-w-0 space-y-1">
                      <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <PriorityBadge prioridade={o.prioridade} />
                        <span className="break-words font-medium">{o.descricao}</span>
                      </span>
                      <span className="block text-sm">{o.condominio} · {responsavelDoLote(o)}</span>
                      <span className="block text-sm text-muted-foreground">
                        {o.motivo ?? "Justificativa não informada"}
                      </span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          )}
          {aprovacao.isError && <p role="alert">{aprovacao.error.message}</p>}
          <DialogFooter>
            <Button variant="outline" disabled={aprovacao.isPending} onClick={() => alternarDialog(false)}>
              Cancelar
            </Button>
            <Button
              disabled={!lista.isSuccess || lista.isFetching || aprovacao.isPending || !selecionados.length}
              onClick={() => aprovacao.mutate(selecionados)}
            >
              {aprovacao.isPending ? "Aprovando…" : `Aprovar (${selecionados.length})`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <div className="fixed bottom-4 right-4 z-30 flex max-w-[calc(100%-2rem)] flex-col gap-2">
        {lotes.map((lote) => (
          <AvisoLote
            key={lote.ids.join(",")}
            lote={lote}
            aoDesfazer={() => atualizar(lote.ids)}
            removerLote={removerLote}
          />
        ))}
      </div>
    </>
  );
}

function AvisoLote({ lote, aoDesfazer, removerLote }: {
  lote: LoteAprovado;
  aoDesfazer: () => void;
  removerLote: (lote: LoteAprovado) => void;
}) {
  const desfazer = useMutation({ mutationFn: () => desfazerLote(lote.ids) });

  useEffect(() => {
    const timer = window.setTimeout(() => removerLote(lote), Math.max(0, lote.expiraEm - Date.now()));
    return () => window.clearTimeout(timer);
  }, [lote, removerLote]);

  async function desfazerAprovacao() {
    if (desfazer.isPending || Date.now() >= lote.expiraEm) return;
    try {
      await desfazer.mutateAsync();
      aoDesfazer();
      removerLote(lote);
    } catch (erro) {
      toast.error(erro instanceof Error ? erro.message : "Não foi possível desfazer a aprovação.");
    }
  }

  const quantidade = lote.ids.length;
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm shadow-lg">
      <span role="status">
        {quantidade === 1 ? "1 ocorrência delegada" : `${quantidade} ocorrências delegadas`}
      </span>
      <span aria-hidden>·</span>
      <Button size="sm" variant="ghost" disabled={desfazer.isPending} onClick={() => void desfazerAprovacao()}>
        Desfazer
      </Button>
    </div>
  );
}
