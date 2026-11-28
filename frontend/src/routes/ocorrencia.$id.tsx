import { useState } from "react";
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
import { MenuSindico } from "@/components/MenuSindico";
import { DecisaoSecao } from "@/components/ocorrencia/DecisaoSecao";
import { Historico } from "@/components/ocorrencia/Historico";
import { PrioridadeSecao } from "@/components/ocorrencia/PrioridadeSecao";
import { Secao } from "@/components/ocorrencia/Secao";
import { PriorityBadge } from "@/components/fila/PriorityBadge";
import { Button } from "@/components/ui/button";
import { chaveFila, useConclusaoApi, useOcorrenciaApi } from "@/lib/fila-api";
import type { ContatoResponsavel } from "@/lib/h11-api";
import {
  PAPEIS_RESPONSAVEL,
  STATUS,
  concluirOcorrencia,
  formatarTelefone,
  montarLinkAvisoWhatsapp,
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
  const { id } = Route.useParams();
  return (
    <AuthGuard>
      <OcorrenciaPage key={id} />
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
  const [delegacao, setDelegacao] = useState<{ contato?: ContatoResponsavel | null | undefined }>();
  const o = demonstracao ? ocorrenciasDemo.find((x) => `demo-${x.id}` === id) : detalhe.data;
  const historico = useHistoricoApi(Number(id), !demonstracao && Boolean(o));

  if (!demonstracao && detalhe.isPending) {
    return <p role="status" className="py-10 text-center">Carregando ocorrência…</p>;
  }

  if (!o || (!demonstracao && detalhe.isError)) {
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
  const contato = detalhe.data?.contatoResponsavel ?? delegacao?.contato;
  const linkAvisoWhatsapp = contato?.temCelular
    ? montarLinkAvisoWhatsapp({
        celular: contato.celular,
        condominio: o.condominioNome ?? nomeCondominio(o.condominioId),
        local: o.local,
        descricao: o.descricao,
        protocolo: o.protocolo,
      })
    : null;

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
          <MenuSindico />
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
          {o.fonte && (
            <p className="mb-2 text-sm font-medium text-muted-foreground">
              {o.fonte === "ia" ? "Sugerido pelo sistema (IA)" : "Classificado por regras"}
            </p>
          )}
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
        {!demonstracao && o.status === "nova" && !delegacao && (
          <DecisaoSecao
            idReal={String(o.id)}
            aoRegistrar={(tipo, contato) => {
              void queryClient.invalidateQueries({ queryKey: chaveFila() });
              void queryClient.invalidateQueries({ queryKey: ["historico", o.id] });
              if (tipo === "delegar") {
                setDelegacao({ contato });
                void queryClient.invalidateQueries({ queryKey: ["ocorrencia", id], exact: true });
                return;
              }
              void navigate({ to: "/fila", search: { aba: "andamento" } });
            }}
          />
        )}
        {(delegacao || contato) && o.status !== "concluida" && (
          <Secao titulo="Delegação registrada" icone={<MessageCircle className="size-4" />}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              {contato && (
                <div className="text-sm">
                  <p>Delegada para <strong>{PAPEIS_RESPONSAVEL.get(contato.papel) ?? contato.papel}</strong></p>
                  {contato.temCelular && (
                    <p className="text-muted-foreground">{contato.celular}</p>
                  )}
                </div>
              )}
              {linkAvisoWhatsapp ? (
                <Button asChild>
                  <a href={linkAvisoWhatsapp} target="_blank" rel="noopener noreferrer">
                    <svg aria-hidden="true" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12.04 2a9.91 9.91 0 0 0-8.59 14.85L2 22l5.27-1.38A9.96 9.96 0 1 0 12.04 2Zm0 18.24a8.26 8.26 0 0 1-4.21-1.15l-.3-.18-3.13.82.84-3.05-.2-.31a8.28 8.28 0 1 1 7 3.87Zm4.54-6.18c-.25-.12-1.47-.72-1.7-.81-.23-.08-.4-.12-.56.13-.17.24-.65.81-.8.98-.14.16-.29.18-.54.06-.25-.13-1.05-.39-2-1.24-.74-.66-1.24-1.47-1.38-1.72-.15-.25-.02-.38.11-.51.11-.11.25-.29.37-.44.13-.14.17-.25.25-.42.08-.16.04-.31-.02-.44-.06-.12-.56-1.35-.77-1.84-.2-.49-.41-.42-.56-.43h-.48c-.16 0-.43.06-.66.31-.23.25-.87.85-.87 2.08 0 1.22.89 2.41 1.02 2.57.12.17 1.75 2.68 4.24 3.75.59.26 1.05.41 1.41.52.6.19 1.14.17 1.57.1.48-.07 1.47-.6 1.68-1.18.21-.58.21-1.08.15-1.19-.06-.1-.23-.16-.48-.29Z" />
                    </svg>
                    Avisar pelo WhatsApp
                  </a>
                </Button>
              ) : (
                <p role="status" className="text-sm text-muted-foreground">
                  {contato?.temCelular === false
                    ? "O responsável não tem celular cadastrado."
                    : "O celular do responsável não está disponível para aviso pelo WhatsApp."}
                </p>
              )}
            </div>
          </Secao>
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
