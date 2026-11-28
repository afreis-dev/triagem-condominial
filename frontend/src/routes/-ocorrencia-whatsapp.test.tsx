import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { OCORRENCIAS, type Ocorrencia } from "@/lib/ocorrencias";
import { useOcorrenciaApi } from "@/lib/fila-api";
import { Route } from "./ocorrencia.$id";

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => (options: object) => ({
    options,
    useParams: () => ({ id: "42" }),
    useNavigate: () => vi.fn(),
  }),
  Link: ({ to, children, ...props }: { to: string; children: React.ReactNode }) =>
    <a href={to} {...props}>{children}</a>,
}));
vi.mock("@/components/AuthGuard", () => ({ AuthGuard: ({ children }: { children: React.ReactNode }) => children }));
vi.mock("@/components/MenuSindico", () => ({ MenuSindico: () => null }));
vi.mock("@/components/ocorrencia/PrioridadeSecao", () => ({ PrioridadeSecao: () => null }));
vi.mock("@/components/ocorrencia/Historico", () => ({ Historico: () => null }));
vi.mock("@/components/ocorrencia/DecisaoSecao", () => ({ DecisaoSecao: () => null }));
vi.mock("@/lib/ocorrencias-store", () => ({ useOcorrencias: () => [], atualizarOcorrencia: vi.fn() }));
vi.mock("@/lib/historico-api", () => ({ useHistoricoApi: () => ({ data: [], isPending: false, isError: false }) }));
vi.mock("@/lib/fila-api", () => ({
  useOcorrenciaApi: vi.fn(),
  useConclusaoApi: () => ({ isPending: false }),
  chaveFila: () => ["fila"],
}));

afterEach(() => {
  cleanup();
  vi.mocked(useOcorrenciaApi).mockReset();
});

function abrirOcorrencia(celular: string | null, dados: Partial<Ocorrencia> = {}) {
  const ocorrencia = {
    ...OCORRENCIAS[0]!,
    id: 42,
    status: "andamento",
    condominioNome: "Residencial Aurora",
    local: "Hall do bloco B",
    descricao: "Lâmpada queimada",
    protocolo: "AUR-0042",
    contatoResponsavel: {
      papel: "zelador",
      temCelular: celular !== null,
      celular,
    },
    ...dados,
  };
  vi.mocked(useOcorrenciaApi).mockReturnValue({
    data: ocorrencia,
    isPending: false,
    isError: false,
  } as ReturnType<typeof useOcorrenciaApi>);
  const Componente = Route.options.component!;
  render(<QueryClientProvider client={new QueryClient()}><Componente /></QueryClientProvider>);
}

it("liga o botão da H12 à mensagem pronta da SQU-99", () => {
  abrirOcorrencia("(19) 99888-1122");
  const botao = screen.getByRole("link", { name: "Avisar pelo WhatsApp" });
  const href = botao.getAttribute("href")!;
  expect(href).toContain("https://wa.me/5519998881122?text=");
  expect(new URL(href).searchParams.get("text")).toBe(
    "Condomínio: Residencial Aurora\nLocal: Hall do bloco B\n" +
    "Descrição: Lâmpada queimada\nProtocolo: AUR-0042",
  );
  expect(botao.getAttribute("target")).toBe("_blank");
});

it("mostra a origem da IA e três frases com os dados da classificação sugerida", () => {
  abrirOcorrencia(null, {
    fonte: "ia",
    prioridade: "normal",
    prioridadeSugerida: "alta",
    categoria: "manutencao",
    responsavelSugerido: "zelador",
    motivo: "A água escorrendo pela parede indica uma possível infiltração",
    travada: false,
    palavraDeRisco: null,
  });

  expect(screen.getByText("Sugerido pelo sistema (IA)")).toBeTruthy();
  const frases = within(screen.getByRole("list")).getAllByRole("listitem");
  expect(frases.map((frase) => frase.textContent)).toEqual([
    "A água escorrendo pela parede indica uma possível infiltração.",
    "A classificação sugeriu prioridade Alta na categoria Manutenção.",
    "A sugestão de responsável pelo atendimento é Zelador.",
  ]);
});

it("mostra a origem por regras e mantém a palavra de risco no detalhe", () => {
  abrirOcorrencia(null, {
    fonte: "regras",
    travada: true,
    palavraDeRisco: "gás",
    motivo: "Palavra de risco: gás",
  });

  expect(screen.getByText("Classificado por regras")).toBeTruthy();
  const frases = within(screen.getByRole("list")).getAllByRole("listitem");
  expect(frases.map((frase) => frase.textContent)).toEqual([
    "A prioridade sugerida foi Urgente por causa da palavra de risco “gás”.",
  ]);
});

it("oculta o botão quando o responsável não tem celular", () => {
  abrirOcorrencia(null);
  expect(screen.queryByRole("link", { name: "Avisar pelo WhatsApp" })).toBeNull();
  expect(screen.getByText("O responsável não tem celular cadastrado.")).toBeTruthy();
});
