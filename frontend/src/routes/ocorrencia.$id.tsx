import { Link, createFileRoute } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCheck,
  FileText,
  Lightbulb,
  MessageCircle,
  Phone,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";
import { AuthGuard } from "@/components/AuthGuard";
import { DecisaoSecao } from "@/components/ocorrencia/DecisaoSecao";
import { Historico } from "@/components/ocorrencia/Historico";
import { PrioridadeSecao } from "@/components/ocorrencia/PrioridadeSecao";
import { Secao } from "@/components/ocorrencia/Secao";
import { PriorityBadge } from "@/components/fila/PriorityBadge";
import { Button } from "@/components/ui/button";
import { chaveFila, useConclusaoApi, useOcorrenciaApi } from "@/lib/fila-api";
import {
  STATUS,
  concluirOcorrencia,
  formatarTelefone,
  nomeCondominio,
  podeConcluir,
  porQueEstaAqui,
  tempoDecorrido,
  type Ocorrencia,
} from "@/lib/ocorrencias";
import { atualizarOcorrencia, useOcorrencias } from "@/lib/ocorrencias-store";
import { useHistoricoApi } from "@/lib/historico-api";

export const Route = createFileRoute("/ocorrencia/$id")({
  head: ({ params }) => ({
    meta: [
      { title: `Ocorrência #${params.id} — Painel do Síndico` },
      { name: "description", content: `Detalhes, prioridade e histórico da ocorrência #${params.id}.` },
      { property: "og:title", content: `Ocorrência #${params.id} — Painel do Síndico` },
      { property: "og:description", content: `Detalhes da ocorrência #${params.id}.` },
      { property: "og:type", content: "article" },
      { name: "twitter:card", content: "summary" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: OcorrenciaProtegida,
});

function OcorrenciaProtegida() {
  return (
    <AuthGuard>
      <OcorrenciaPage />
    </AuthGuard>
  );
}

function OcorrenciaPage() {
  const { id } = Route.useParams();
  const navigate = Route.useNavigate();
  const demonstracao = id.startsWith("demo-");
  const detalhe = useOcorrenciaApi(id, !demonstracao);
  const ocorrenciasDemo = useOcorrencias();
  const conclusao = useConclusaoApi();
  const queryClient = useQueryClient();
  const o = demonstracao ? ocorrenciasDemo.find((x) => `demo-${x.id}` === id) : detalhe.data;
  const historico = useHistoricoApi(Number(id), !demonstracao && Boolean(o));

  if (!demonstracao && detalhe.isPending) {
    return <p role="status" className="py-10 text-center">Carregando ocorrência…</p>;
  }

  if (!o) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10 text-center">
        <p className="text-muted-foreground">
          {!demonstracao && detalhe.isError
            ? "Não foi possível consultar a ocorrência."
            : "Ocorrência não encontrada."}
        </p>
        <Button asChild variant="outline" className="mt-4">
          <Link to="/fila">Voltar para a fila</Link>
        </Button>
      </div>
    );
  }

  const status = STATUS.find((s) => s.id === o.status)?.label;
  const relator = o.relator;

  async function concluir(ocorrencia: Ocorrencia) {
    if (!podeConcluir(ocorrencia) || conclusao.isPending) return;
    try {
      if (demonstracao) {
        atualizarOcorrencia(ocorrencia.id, (x) => concluirOcorrencia(x, new Date().toISOString()));
      } else {
        await conclusao.mutateAsync(ocorrencia.id);
      }
    } catch (erro) {
      toast.error(erro instanceof Error ? erro.message : "Não foi possível concluir a ocorrência.");
      return;
    }
    toast.success(demonstracao ? "Ocorrência de demonstração concluída" : "Ocorrência concluída");
    await navigate({ to: "/fila", search: { aba: "concluida" } });
  }

  return (
    <div className="min-h-screen pb-12">
      <header className="sticky top-0 z-20 border-b bg-surface/95 shadow-bar backdrop-blur supports-[backdrop-filter]:bg-surface/80">
        <div className="mx-auto flex max-w-3xl items-center gap-2 px-2 py-2.5 sm:px-6">
          <Button asChild variant="ghost" size="icon" className="size-10 shrink-0">
            <Link to="/fila" aria-label="Voltar para a fila">
              <ArrowLeft className="size-5" />
            </Link>
          </Button>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold leading-tight">
              {o.condominioNome ?? nomeCondominio(o.condominioId)}
            </p>
            <div className="mt-1 flex items-center gap-2">
              <span className="font-mono text-[11px] text-muted-foreground">{o.protocolo}</span>
              <PriorityBadge prioridade={o.prioridade} />
            </div>
          </div>
          {podeConcluir(o) && (
            <Button
              className="h-10 shrink-0"
              disabled={conclusao.isPending}
              onClick={() => void concluir(o)}
            >
              <CheckCheck />
              {conclusao.isPending ? "Concluindo…" : "Concluir"}
            </Button>
          )}
        </div>
      </header>

      <main className="mx-auto grid max-w-3xl gap-3 px-4 pt-4 sm:gap-4 sm:px-6 sm:pt-6">
        {demonstracao && <p role="status">Ocorrência de demonstração</p>}
        <div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className="rounded-full bg-muted px-2.5 py-0.5 font-medium">{status}</span>
            <span className="font-mono">Aberta {tempoDecorrido(o.minutosAtras)}</span>
          </div>
          <h1 className="mt-2 text-xl font-semibold leading-snug sm:text-2xl">{o.titulo}</h1>
        </div>

        <Secao titulo="Por que está aqui" icone={<Lightbulb className="size-4" />}>
          <ul className="grid gap-1.5 text-[15px]">
            {porQueEstaAqui(o).map((r) => (
              <li key={r} className="flex gap-2">
                <span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-primary" />
                {r}
              </li>
            ))}
          </ul>
        </Secao>

        <Secao titulo="Descrição" icone={<FileText className="size-4" />}>
          <p className="whitespace-pre-line text-[15px] leading-relaxed">{o.descricao}</p>
          <div className="mt-4 grid gap-3 border-t pt-4 sm:grid-cols-2">
            {relator && (
              <div className="flex items-start gap-2.5">
                <UserRound className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                <div className="min-w-0 text-sm">
                  <p className="font-semibold">{relator.nome}</p>
                  <p className="text-muted-foreground">
                    {relator.perfil}
                    {relator.apartamento && ` · Apto ${relator.apartamento}`}
                  </p>
                </div>
              </div>
            )}
            <div className="flex items-start gap-2.5">
              <MessageCircle className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
              <p className="text-sm">
                <span className="text-muted-foreground">Origem: </span>
                <span className="font-semibold">{o.origem}</span>
              </p>
            </div>
            <p className="text-sm">
              <span className="text-muted-foreground">Onde fica: </span>
              {o.local ?? "Não informado"}
            </p>
            {o.criadaEm && (
              <p className="text-sm">
                <span className="text-muted-foreground">Hora de entrada: </span>
                <time dateTime={o.criadaEm}>
                  {new Intl.DateTimeFormat("pt-BR", {
                    dateStyle: "short", timeStyle: "short", timeZone: "America/Sao_Paulo",
                  }).format(new Date(o.criadaEm))}
                </time>
              </p>
            )}
          </div>
          {relator?.celular ? (
            <div className="mt-3 flex items-center justify-between gap-3 rounded-lg bg-muted px-3 py-2">
              <span className="font-mono text-sm">{formatarTelefone(relator.celular)}</span>
              <Button asChild size="sm" className="h-9">
                <a href={`tel:+55${relator.celular}`}>
                  <Phone />
                  Ligar
                </a>
              </Button>
            </div>
          ) : (
            relator && <p className="mt-3 text-sm text-muted-foreground">Telefone não informado.</p>
          )}
        </Secao>

        <PrioridadeSecao key={id} ocorrencia={o} demonstracao={demonstracao} />

        {demonstracao && o.status !== "concluida" && <DecisaoSecao ocorrencia={o} />}
        {!demonstracao && o.status === "nova" && (
          <DecisaoSecao
            idReal={String(o.id)}
            aoRegistrar={() => {
              void queryClient.invalidateQueries({ queryKey: chaveFila() });
              void queryClient.invalidateQueries({ queryKey: ["historico", o.id] });
              void navigate({ to: "/fila", search: { aba: "andamento" } });
            }}
          />
        )}

        {demonstracao ? (
          <Historico ocorrencia={o} />
        ) : (
          <Historico
            ocorrencia={{
              ...o,
              historico: historico.data ?? [],
            }}
            carregando={historico.isPending}
            erro={historico.isError}
            aoTentarNovamente={() => void historico.refetch()}
          />
        )}
      </main>
    </div>
  );
}
