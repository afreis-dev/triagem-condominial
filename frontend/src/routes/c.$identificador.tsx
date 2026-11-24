import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { AlertCircle, Building2, CheckCircle2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  PERFIS,
  LIMITE_DESCRICAO,
  apartamentoObrigatorio,
  mascaraCelular,
  nomeDoIdentificador,
  somenteDigitos,
  validarChamado,
  type ChamadoForm,
  type ErrosChamado,
} from "@/lib/chamado";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/c/$identificador")({
  head: ({ params }) => {
    const nome = nomeDoIdentificador(params.identificador);
    return {
      meta: [
        { title: `Registrar ocorrência — ${nome}` },
        { name: "description", content: `Envie uma ocorrência ao síndico do ${nome}.` },
        { property: "og:title", content: `Registrar ocorrência — ${nome}` },
        {
          property: "og:description",
          content: `Canal para moradores do ${nome} falarem com o síndico.`,
        },
        { property: "og:type", content: "website" },
        { name: "twitter:card", content: "summary" },
      ],
    };
  },
  component: ChamadoPage,
});

const VAZIO: ChamadoForm = {
  perfil: "morador",
  nome: "",
  apartamento: "",
  celular: "",
  local: "",
  descricao: "",
};

const campoInvalido =
  "h-11 bg-card text-base sm:text-sm aria-[invalid=true]:border-destructive aria-[invalid=true]:bg-destructive/5 aria-[invalid=true]:ring-1 aria-[invalid=true]:ring-destructive/40";

function ChamadoPage() {
  const { identificador } = Route.useParams();
  return <ChamadoCondominio key={identificador} identificador={identificador} />;
}

type ConsultaCondominio =
  { status: "carregando" | "invalido" | "erro" } | { status: "encontrado"; nome: string };

type RespostaOcorrencia =
  | { ok: true; ocorrenciaId: number; protocolo: string }
  | { ok: false; erros: ErrosChamado & { condominioId?: string; origem?: string } };

function ChamadoCondominio({ identificador }: { identificador: string }) {
  const url = `/api/condominios/${encodeURIComponent(identificador)}`;
  const [condominio, setCondominio] = useState<ConsultaCondominio>({ status: "carregando" });
  const [form, setForm] = useState<ChamadoForm>(VAZIO);
  const [tentou, setTentou] = useState(false);
  const [protocolo, setProtocolo] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [errosApi, setErrosApi] = useState<ErrosChamado>({});
  const [erroEnvio, setErroEnvio] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function consultar() {
      try {
        const resposta = await fetch(url, { signal: controller.signal });
        if (resposta.status === 404) {
          if (!controller.signal.aborted) setCondominio({ status: "invalido" });
          return;
        }
        if (!resposta.ok) throw new Error();
        const { nome } = (await resposta.json()) as { id: number; nome: string };
        if (!controller.signal.aborted) setCondominio({ status: "encontrado", nome });
      } catch {
        if (!controller.signal.aborted) setCondominio({ status: "erro" });
      }
    }

    void consultar();
    return () => controller.abort();
  }, [url]);

  const errosLocais = validarChamado(form);
  const erroCelular = errosLocais.celular;
  const erros: ErrosChamado = tentou
    ? { ...errosApi, ...errosLocais }
    : erroCelular && somenteDigitos(form.celular).length > 11
      ? { celular: erroCelular }
      : {};
  const aptoObrigatorio = apartamentoObrigatorio(form.perfil);

  const set = <K extends keyof ChamadoForm>(k: K, v: ChamadoForm[K]) => {
    setForm((f) => ({ ...f, [k]: v }));
    setErrosApi({});
    setErroEnvio(null);
  };

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (enviando || condominio.status !== "encontrado") return;
    setTentou(true);
    setErrosApi({});
    setErroEnvio(null);
    const r = validarChamado(form);
    if (Object.keys(r).length > 0) {
      requestAnimationFrame(() => {
        formRef.current?.querySelector<HTMLElement>("[aria-invalid=true]")?.focus();
      });
      return;
    }
    setEnviando(true);
    try {
      const resposta = await fetch(`${url}/ocorrencias`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (resposta.status === 404) {
        setCondominio({ status: "invalido" });
        return;
      }
      if (!resposta.ok) throw new Error();
      const resultado = (await resposta.json()) as RespostaOcorrencia;
      if (resultado.ok) {
        setProtocolo(resultado.protocolo);
        window.scrollTo({ top: 0 });
      } else {
        setErrosApi(resultado.erros);
        setErroEnvio(resultado.erros.condominioId ?? resultado.erros.origem ?? null);
      }
    } catch {
      setErroEnvio("Não foi possível confirmar o registro da ocorrência.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="min-h-screen pb-12">
      <header className="border-b bg-surface">
        <div className="mx-auto flex max-w-xl items-center gap-3 px-4 py-4 sm:px-6">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Building2 className="size-5" aria-hidden />
          </div>
          <div className="min-w-0">
            <p className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Canal do condomínio
            </p>
            {condominio.status === "encontrado" && (
              <h1 className="truncate text-lg font-semibold leading-tight">{condominio.nome}</h1>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-xl px-4 pt-5 sm:px-6 sm:pt-8">
        {condominio.status === "carregando" ? (
          <p role="status">Consultando condomínio…</p>
        ) : condominio.status === "invalido" ? (
          <h1 className="text-xl font-semibold">Link de condomínio inválido</h1>
        ) : condominio.status === "erro" ? (
          <p role="alert">
            Não foi possível consultar o condomínio. Recarregue a página para tentar novamente.
          </p>
        ) : protocolo ? (
          <section
            role="status"
            className="flex flex-col items-center rounded-xl border bg-card px-6 py-10 text-center shadow-card"
          >
            <div className="flex size-14 items-center justify-center rounded-full bg-secondary text-primary">
              <CheckCircle2 className="size-8" aria-hidden />
            </div>
            <h2 className="mt-4 text-xl font-semibold">Ocorrência registrada</h2>
            <p className="mt-1 text-sm text-muted-foreground">Número de protocolo</p>
            <p className="mt-1 rounded-lg bg-muted px-4 py-2 font-mono text-2xl font-semibold tracking-wider">
              {protocolo}
            </p>
            <p className="mt-4 text-[15px]">O síndico já recebeu sua ocorrência.</p>
            <Button
              variant="outline"
              className="mt-6"
              onClick={() => {
                setForm(VAZIO);
                setTentou(false);
                setProtocolo(null);
              }}
            >
              Registrar outra ocorrência
            </Button>
          </section>
        ) : (
          <>
            <h2 className="text-xl font-semibold">Registrar ocorrência</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Conte o que aconteceu. Campos com * são obrigatórios.
            </p>

            <form ref={formRef} onSubmit={enviar} noValidate className="mt-5 grid gap-5">
              <fieldset className="grid gap-2">
                <legend className="mb-2 text-sm font-medium">Você é</legend>
                <div
                  role="radiogroup"
                  className="grid grid-cols-3 gap-1 rounded-lg border bg-muted p-1"
                >
                  {PERFIS.map((p) => {
                    const ativo = form.perfil === p.id;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        role="radio"
                        aria-checked={ativo}
                        onClick={() => set("perfil", p.id)}
                        className={cn(
                          "h-10 truncate rounded-md px-2 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                          ativo
                            ? "bg-card text-foreground shadow-card"
                            : "text-muted-foreground hover:text-foreground",
                        )}
                      >
                        {p.label}
                      </button>
                    );
                  })}
                </div>
              </fieldset>

              <Campo id="nome" label="Nome" obrigatorio erro={erros.nome}>
                <Input
                  id="nome"
                  autoComplete="name"
                  maxLength={100}
                  value={form.nome}
                  onChange={(e) => set("nome", e.target.value)}
                  aria-invalid={Boolean(erros.nome)}
                  aria-describedby={erros.nome ? "nome-erro" : undefined}
                  className={campoInvalido}
                />
              </Campo>

              <Campo
                id="apartamento"
                label="Apartamento"
                obrigatorio={aptoObrigatorio}
                dica={aptoObrigatorio ? undefined : "Opcional para funcionários"}
                erro={erros.apartamento}
              >
                <Input
                  id="apartamento"
                  placeholder="Ex.: Bloco B, 204"
                  maxLength={20}
                  value={form.apartamento}
                  onChange={(e) => set("apartamento", e.target.value)}
                  aria-invalid={Boolean(erros.apartamento)}
                  aria-describedby={erros.apartamento ? "apartamento-erro" : undefined}
                  className={campoInvalido}
                />
              </Campo>

              <Campo id="celular" label="Celular" obrigatorio erro={erros.celular}>
                <Input
                  id="celular"
                  type="tel"
                  inputMode="numeric"
                  autoComplete="tel-national"
                  placeholder="(11) 91234-5678"
                  value={form.celular}
                  onChange={(e) => set("celular", mascaraCelular(e.target.value))}
                  aria-invalid={Boolean(erros.celular)}
                  aria-describedby={erros.celular ? "celular-erro" : undefined}
                  className={cn(campoInvalido, "font-mono")}
                />
              </Campo>

              <Campo id="local" label="Onde fica o problema" dica="Opcional" erro={erros.local}>
                <Input
                  id="local"
                  placeholder="Ex.: garagem, hall do bloco A"
                  maxLength={120}
                  value={form.local}
                  onChange={(e) => set("local", e.target.value)}
                  aria-invalid={Boolean(erros.local)}
                  className={campoInvalido}
                />
              </Campo>

              <Campo id="descricao" label="Descrição" obrigatorio erro={erros.descricao}>
                <Textarea
                  id="descricao"
                  rows={5}
                  maxLength={LIMITE_DESCRICAO}
                  placeholder="Descreva o que está acontecendo"
                  value={form.descricao}
                  onChange={(e) => set("descricao", e.target.value)}
                  aria-invalid={Boolean(erros.descricao)}
                  aria-describedby={erros.descricao ? "descricao-erro" : undefined}
                  className={cn(campoInvalido, "h-auto resize-none")}
                />
              </Campo>

              <div className="grid gap-3">
                <p className="flex gap-2 rounded-lg border bg-surface p-3 text-[13px] leading-relaxed text-muted-foreground">
                  <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
                  Seus dados (nome, apartamento e celular) são usados só para o síndico responder
                  esta ocorrência.
                </p>
                {erroEnvio && (
                  <p role="alert" className="text-sm text-destructive">
                    {erroEnvio}
                  </p>
                )}
                <Button
                  type="submit"
                  disabled={enviando}
                  size="lg"
                  className="h-12 w-full text-base"
                >
                  {enviando ? "Enviando…" : "Enviar ocorrência"}
                </Button>
              </div>
            </form>
          </>
        )}
      </main>
    </div>
  );
}

function Campo({
  id,
  label,
  obrigatorio,
  dica,
  erro,
  children,
}: {
  id: string;
  label: string;
  obrigatorio?: boolean;
  dica?: string | undefined;
  erro?: string | undefined;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <Label htmlFor={id} className={cn(erro && "text-destructive")}>
          {label}
          {obrigatorio && <span className="text-destructive"> *</span>}
        </Label>
        {dica && <span className="text-xs text-muted-foreground">{dica}</span>}
      </div>
      {children}
      {erro && (
        <p
          id={`${id}-erro`}
          className="flex items-center gap-1 text-xs font-medium text-destructive"
        >
          <AlertCircle className="size-3.5" aria-hidden />
          {erro}
        </p>
      )}
    </div>
  );
}
