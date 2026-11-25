import { createFileRoute } from "@tanstack/react-router";
import { useMemo } from "react";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { AuthGuard } from "@/components/AuthGuard";
import { ColarMensagemDialog } from "@/components/fila/ColarMensagemDialog";
import { CartaoOcorrencia } from "@/components/fila/CartaoOcorrencia";
import { EmptyState } from "@/components/fila/EmptyState";
import { FilterBar } from "@/components/fila/FilterBar";
import { Paginacao } from "@/components/fila/Paginacao";
import { PrioritySummary } from "@/components/fila/PrioritySummary";
import { Button } from "@/components/ui/button";
import { sair } from "@/lib/auth";
import {
  CONDOMINIOS,
  PRIORIDADES,
  STATUS,
  contarPorPrioridade,
  filtrarOcorrencias,
  paginar,
  type Prioridade,
  type Status,
} from "@/lib/ocorrencias";
import { useFilaApi } from "@/lib/fila-api";
import { adicionarMensagem, useOcorrencias } from "@/lib/ocorrencias-store";
import { cn } from "@/lib/utils";

interface FilaSearch {
  aba?: Status | undefined;
  condominio?: string | undefined;
  prioridade?: Prioridade | undefined;
  pagina?: number | undefined;
}

export const Route = createFileRoute("/fila")({
  validateSearch: (s: Record<string, unknown>): FilaSearch => {
    const aba = STATUS.some((x) => x.id === s["aba"]) ? (s["aba"] as Status) : undefined;
    const condominio = typeof s["condominio"] === "string" ? s["condominio"] : undefined;
    const prioridade = PRIORIDADES.some((p) => p.id === s["prioridade"])
      ? (s["prioridade"] as Prioridade)
      : undefined;
    const n = Number(s["pagina"]);
    const pagina = Number.isInteger(n) && n > 1 ? n : undefined;
    return { aba, condominio, prioridade, pagina };
  },
  head: () => ({
    meta: [
      { title: "Fila de ocorrências — Painel do Síndico" },
      {
        name: "description",
        content: "Fila de ocorrências dos condomínios por status, prioridade e condomínio.",
      },
      { property: "og:title", content: "Fila de ocorrências — Painel do Síndico" },
      {
        property: "og:description",
        content: "Acompanhe ocorrências novas, em andamento e concluídas dos seus condomínios.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: FilaProtegida,
});

function FilaProtegida() {
  return (
    <AuthGuard>
      <FilaPage />
    </AuthGuard>
  );
}

function FilaPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const fila = useFilaApi();
  const ocorrenciasDemo = useOcorrencias();
  const demonstracao = fila.isError && !fila.data;
  const todas = fila.data ?? ocorrenciasDemo;
  const condominios = useMemo(() => {
    if (!fila.data) return CONDOMINIOS;
    const nomes = new Map(fila.data.map((o) => [o.condominioId, o.condominioNome ?? o.condominioId]));
    return Array.from(nomes, ([id, nome]) => ({ id, nome }));
  }, [fila.data]);
  const aba = search.aba ?? "nova";
  const { condominio, prioridade } = search;

  const set = (patch: Partial<FilaSearch>) =>
    navigate({ search: (prev) => ({ ...prev, pagina: undefined, ...patch }), replace: true });

  const contagemAbas = useMemo(() => {
    const c = {} as Record<Status, number>;
    for (const st of STATUS) c[st.id] = filtrarOcorrencias(todas, { status: st.id, condominio }).length;
    return c;
  }, [todas, condominio]);

  const resumo = useMemo(
    () => contarPorPrioridade(filtrarOcorrencias(todas, { status: aba, condominio })),
    [todas, aba, condominio],
  );
  const lista = useMemo(
    () => filtrarOcorrencias(todas, { status: aba, condominio, prioridade }),
    [todas, aba, condominio, prioridade],
  );
  const { itens, pagina, totalPaginas } = paginar(lista, search.pagina ?? 1);
  const abaInfo = STATUS.find((s) => s.id === aba)!;
  const filtrosAtivos = Boolean(condominio || prioridade);
  const limpar = () => set({ condominio: undefined, prioridade: undefined });

  function colar(condominioId: string, texto: string) {
    const nova = adicionarMensagem(condominioId, texto);
    navigate({ search: { aba: "nova" }, replace: true });
    toast.success("Ocorrência criada", { description: nova.titulo });
  }

  return (
    <div className="min-h-screen pb-10">
      <header className="sticky top-0 z-20 border-b bg-surface/95 shadow-bar backdrop-blur supports-[backdrop-filter]:bg-surface/80">
        <div className="mx-auto max-w-5xl px-4 pt-3 sm:px-6">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Painel do Síndico
              </p>
              <h1 className="truncate text-lg font-semibold leading-tight">Fila de ocorrências</h1>
            </div>
            <div className="flex items-center gap-2">
              {demonstracao && <ColarMensagemDialog onSubmit={colar} />}
              <Button variant="outline" onClick={() => {
                sair();
                void navigate({ to: "/login" });
              }}>
                Sair
              </Button>
            </div>
          </div>
          <nav role="tablist" aria-label="Status" className="-mb-px mt-3 flex">
            {STATUS.map((s) => {
              const ativo = s.id === aba;
              return (
                <button
                  key={s.id}
                  role="tab"
                  aria-selected={ativo}
                  onClick={() => set({ aba: s.id === "nova" ? undefined : s.id })}
                  className={cn(
                    "flex flex-1 items-center justify-center gap-1.5 border-b-2 px-2 pb-2.5 pt-1.5 text-sm font-medium transition-colors sm:flex-none sm:px-4",
                    ativo
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground",
                  )}
                >
                  <span className="whitespace-nowrap">{s.label}</span>
                  <span
                    className={cn(
                      "rounded-full px-1.5 font-mono text-[11px] leading-5 tabular-nums",
                      ativo ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
                    )}
                  >
                    {contagemAbas[s.id]}
                  </span>
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      <main className="mx-auto flex max-w-5xl flex-col gap-4 px-4 pt-4 sm:px-6 sm:pt-6">
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => void fila.refetch()} disabled={fila.isFetching}>
            <RefreshCw className={fila.isFetching ? "animate-spin" : undefined} aria-hidden />
            Atualizar
          </Button>
          {fila.isFetching && <p role="status">Buscando ocorrências…</p>}
        </div>
        <PrioritySummary
          contagem={resumo}
          selecionada={prioridade}
          onSelect={(p) => set({ prioridade: p })}
        />
        {fila.isError && (
          <p role="status">
            {fila.error.message}
            {demonstracao && " Exibindo dados de demonstração."}
          </p>
        )}
        <FilterBar
          condominios={condominios}
          condominio={condominio}
          prioridade={prioridade}
          onCondominio={(v) => set({ condominio: v })}
          onPrioridade={(v) => set({ prioridade: v })}
          onLimpar={limpar}
        />

        {!fila.isPending && (lista.length === 0 ? (
          <EmptyState titulo={abaInfo.vazio} filtrosAtivos={filtrosAtivos} onLimpar={limpar} />
        ) : (
          <>
            <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {lista.length} {lista.length === 1 ? "ocorrência" : "ocorrências"} · página {pagina} de{" "}
              {totalPaginas}
            </p>
            <ul className="grid gap-2.5 lg:grid-cols-2 lg:gap-3">
              {itens.map((o) => (
                <li key={o.id}>
                  <CartaoOcorrencia ocorrencia={o} demonstracao={demonstracao} />
                </li>
              ))}
            </ul>
            <footer className="pt-2">
              <Paginacao
                pagina={pagina}
                totalPaginas={totalPaginas}
                onChange={(p) => {
                  navigate({ search: (prev) => ({ ...prev, pagina: p > 1 ? p : undefined }) });
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              />
            </footer>
          </>
        ))}
      </main>
    </div>
  );
}
