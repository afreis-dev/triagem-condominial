import { Link, createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
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
import {
  STATUS,
  concluirOcorrencia,
  formatarTelefone,
  nomeCondominio,
  podeConcluir,
  porQueEstaAqui,
  tempoDecorrido,
} from "@/lib/ocorrencias";
import { atualizarOcorrencia, useOcorrencias } from "@/lib/ocorrencias-store";
import { buscarFilaH11, h11Local } from "@/lib/h11-api";

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
  component: OcorrenciaPage,
});

function OcorrenciaPage() {
  const { id } = Route.useParams();
  if (h11Local && id.startsWith("h11-")) {
    return <AuthGuard><DetalheH11 key={id} id={id} /></AuthGuard>;
  }
  return <DetalheLocal id={id} />;
}

function DetalheH11({ id }: { id: string }) {
  const navigate = Route.useNavigate();
  const [resultado, setResultado] = useState<
    Awaited<ReturnType<typeof buscarFilaH11>>[number] | null | undefined
  >();
  const [falhou, setFalhou] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    buscarFilaH11(controller.signal)
      .then((ocorrencias) => {
        if (!controller.signal.aborted) setResultado(ocorrencias.find((item) => item.id === id) ?? null);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFalhou(true);
      });
    return () => controller.abort();
  }, [id]);

  return (
    <main className="mx-auto grid max-w-3xl gap-4 px-4 py-6 sm:px-6">
      <div>
        <Button asChild variant="outline">
          <Link to="/fila"><ArrowLeft /> Voltar para a fila</Link>
        </Button>
      </div>
      {falhou && <p role="alert">Não foi possível carregar a ocorrência.</p>}
      {!falhou && resultado === undefined && <p role="status">Carregando ocorrência…</p>}
      {resultado === null && <p>Ocorrência não encontrada.</p>}
      {resultado && (
        <>
          <header className="flex flex-wrap items-center gap-3">
            <h1 className="text-lg font-semibold">{resultado.condominio}</h1>
            {resultado.prioridade && <PriorityBadge prioridade={resultado.prioridade} />}
            <span>{STATUS.find((status) => status.id === resultado.status)?.label}</span>
          </header>
          <Secao titulo="Por que está aqui" icone={<Lightbulb className="size-4" />}>
            <p>{resultado.motivo || "Motivo indisponível"}</p>
          </Secao>
          <Secao titulo="Descrição" icone={<FileText className="size-4" />}>
            <p className="whitespace-pre-wrap">{resultado.titulo}</p>
          </Secao>
          {resultado.status === "nova" && (
            <DecisaoSecao
              idReal={id.slice("h11-".length)}
              aoRegistrar={() => void navigate({ to: "/fila", search: { aba: "andamento" } })}
            />
          )}
          {resultado.marcaAcao && <p className="font-semibold">{resultado.marcaAcao}</p>}
        </>
      )}
    </main>
  );
}

function DetalheLocal({ id }: { id: string }) {
  const o = useOcorrencias().find((x) => String(x.id) === id);

  if (!o) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10 text-center">
        <p className="text-muted-foreground">Ocorrência não encontrada.</p>
        <Button asChild variant="outline" className="mt-4">
          <Link to="/fila">Voltar para a fila</Link>
        </Button>
      </div>
    );
  }

  const status = STATUS.find((s) => s.id === o.status)?.label;

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
            <p className="truncate text-sm font-semibold leading-tight">{nomeCondominio(o.condominioId)}</p>
            <div className="mt-1 flex items-center gap-2">
              <span className="font-mono text-[11px] text-muted-foreground">{o.protocolo}</span>
              <PriorityBadge prioridade={o.prioridade} />
            </div>
          </div>
          {podeConcluir(o) && (
            <Button
              className="h-10 shrink-0"
              onClick={() => {
                atualizarOcorrencia(o.id, (x) => concluirOcorrencia(x, new Date().toISOString()));
                toast.success("Ocorrência concluída");
              }}
            >
              <CheckCheck />
              Concluir
            </Button>
          )}
        </div>
      </header>

      <main className="mx-auto grid max-w-3xl gap-3 px-4 pt-4 sm:gap-4 sm:px-6 sm:pt-6">
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
            <div className="flex items-start gap-2.5">
              <UserRound className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
              <div className="min-w-0 text-sm">
                <p className="font-semibold">{o.relator.nome}</p>
                <p className="text-muted-foreground">
                  {o.relator.perfil}
                  {o.relator.apartamento && ` · Apto ${o.relator.apartamento}`}
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2.5">
              <MessageCircle className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
              <p className="text-sm">
                <span className="text-muted-foreground">Origem: </span>
                <span className="font-semibold">{o.origem}</span>
              </p>
            </div>
          </div>
          {o.relator.celular ? (
            <div className="mt-3 flex items-center justify-between gap-3 rounded-lg bg-muted px-3 py-2">
              <span className="font-mono text-sm">{formatarTelefone(o.relator.celular)}</span>
              <Button asChild size="sm" className="h-9">
                <a href={`tel:+55${o.relator.celular}`}>
                  <Phone />
                  Ligar
                </a>
              </Button>
            </div>
          ) : (
            <p className="mt-3 text-sm text-muted-foreground">Telefone não informado.</p>
          )}
        </Secao>

        <PrioridadeSecao key={`p-${o.prioridade}`} ocorrencia={o} />

        {o.status !== "concluida" && <DecisaoSecao ocorrencia={o} />}

        <Historico ocorrencia={o} />
      </main>
    </div>
  );
}
