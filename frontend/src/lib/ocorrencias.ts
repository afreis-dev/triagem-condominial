export type Prioridade = "urgente" | "alta" | "normal" | "baixa";
export type Status = "nova" | "andamento" | "concluida";
export type Origem = "WhatsApp" | "Portaria" | "E-mail" | "Telefone" | "App";

export interface Condominio {
  id: string;
  nome: string;
}

export type PerfilRelator = "Morador" | "Proprietário" | "Funcionário";

export interface Relator {
  nome: string;
  perfil: PerfilRelator;
  apartamento?: string | undefined;
  /** Digits only (10 or 11). Empty when unknown, e.g. pasted messages. */
  celular: string;
}

export type TipoDecisao = "delegar" | "agendar" | "eu_mesmo";
export type Responsavel = "Zelador" | "Portaria" | "Síndico";

export interface Decisao {
  tipo: TipoDecisao;
  responsavel?: Responsavel | undefined;
  /** Local date, yyyy-mm-dd. */
  data?: string | undefined;
  nota?: string | undefined;
}

export interface EventoHistorico {
  /** ISO timestamp. */
  quando: string;
  autor: string;
  acao: string;
  motivo?: string | undefined;
}

export interface Ocorrencia {
  id: number;
  protocolo: string;
  condominioId: string;
  condominioNome?: string;
  titulo: string;
  origem: Origem;
  prioridade: Prioridade;
  /** Priority the system suggested when the occurrence arrived. */
  prioridadeSugerida: Prioridade;
  status: Status;
  criadaEm?: string;
  concluidaEm?: string;
  marcaAcao?: string;
  /** Minutes since the occurrence was opened (mock data, avoids clock-dependent SSR). */
  minutosAtras: number;
  motivo: string;
  descricao: string;
  relator?: Relator;
  decisao?: Decisao | undefined;
  historico: EventoHistorico[];
  mensagem?: string;
}

export const ITENS_POR_PAGINA = 10;

export const PRIORIDADES: { id: Prioridade; label: string }[] = [
  { id: "urgente", label: "Urgente" },
  { id: "alta", label: "Alta" },
  { id: "normal", label: "Normal" },
  { id: "baixa", label: "Baixa" },
];

export const STATUS: { id: Status; label: string; vazio: string }[] = [
  { id: "nova", label: "Nova", vazio: "Nenhuma ocorrência nova" },
  { id: "andamento", label: "Em andamento", vazio: "Nenhuma ocorrência em andamento" },
  { id: "concluida", label: "Concluída", vazio: "Nenhuma ocorrência concluída" },
];

export const CONDOMINIOS: Condominio[] = [
  { id: "jardim-aurora", nome: "Residencial Jardim Aurora" },
  { id: "solar-ipes", nome: "Condomínio Solar dos Ipês" },
  { id: "torre-atlantica", nome: "Edifício Torre Atlântica" },
];

type OcorrenciaBase = Pick<
  Ocorrencia,
  "id" | "condominioId" | "titulo" | "origem" | "prioridade" | "status" | "minutosAtras" | "motivo"
>;

const BASE: OcorrenciaBase[] = [
  { id: 1, condominioId: "jardim-aurora", titulo: "Vazamento de água no hall do Bloco B", origem: "WhatsApp", prioridade: "urgente", status: "nova", minutosAtras: 12, motivo: "Água escorrendo próximo ao quadro de energia" },
  { id: 2, condominioId: "torre-atlantica", titulo: "Elevador social parado no 7º andar", origem: "Portaria", prioridade: "urgente", status: "nova", minutosAtras: 25, motivo: "Morador idoso preso na cabine" },
  { id: 3, condominioId: "solar-ipes", titulo: "Portão da garagem não fecha", origem: "WhatsApp", prioridade: "alta", status: "nova", minutosAtras: 48, motivo: "Risco de acesso de pessoas não autorizadas" },
  { id: 4, condominioId: "jardim-aurora", titulo: "Barulho excessivo no apto 302", origem: "App", prioridade: "normal", status: "nova", minutosAtras: 95, motivo: "Festa após 22h, terceira reclamação" },
  { id: 5, condominioId: "torre-atlantica", titulo: "Cheiro de gás na escada de serviço", origem: "Telefone", prioridade: "urgente", status: "nova", minutosAtras: 6, motivo: "Possível vazamento na tubulação central" },
  { id: 6, condominioId: "solar-ipes", titulo: "Lâmpada queimada no corredor do 4º", origem: "App", prioridade: "baixa", status: "nova", minutosAtras: 320, motivo: "Corredor escuro à noite" },
  { id: 7, condominioId: "jardim-aurora", titulo: "Interfone da guarita sem som", origem: "Portaria", prioridade: "alta", status: "nova", minutosAtras: 140, motivo: "Portaria não consegue anunciar visitas" },
  { id: 8, condominioId: "torre-atlantica", titulo: "Infiltração no teto da garagem G2", origem: "E-mail", prioridade: "normal", status: "nova", minutosAtras: 1440, motivo: "Mancha crescendo sobre vaga 41" },
  { id: 9, condominioId: "solar-ipes", titulo: "Lixo acumulado na área da piscina", origem: "WhatsApp", prioridade: "baixa", status: "nova", minutosAtras: 210, motivo: "Sacos deixados após o fim de semana" },
  { id: 10, condominioId: "jardim-aurora", titulo: "Câmera da entrada principal offline", origem: "Portaria", prioridade: "alta", status: "nova", minutosAtras: 380, motivo: "Sem gravação desde a madrugada" },
  { id: 11, condominioId: "torre-atlantica", titulo: "Pedido de reserva do salão de festas", origem: "App", prioridade: "baixa", status: "nova", minutosAtras: 2880, motivo: "Data solicitada já tem pré-reserva" },
  { id: 12, condominioId: "solar-ipes", titulo: "Cachorro solto nas áreas comuns", origem: "WhatsApp", prioridade: "normal", status: "nova", minutosAtras: 65, motivo: "Moradores com crianças reclamaram" },
  { id: 13, condominioId: "jardim-aurora", titulo: "Bomba da cisterna fazendo ruído", origem: "Telefone", prioridade: "alta", status: "andamento", minutosAtras: 600, motivo: "Técnico agendado para hoje às 14h" },
  { id: 14, condominioId: "torre-atlantica", titulo: "Vidro trincado na porta do lobby", origem: "Portaria", prioridade: "normal", status: "andamento", minutosAtras: 4320, motivo: "Aguardando orçamento da vidraçaria" },
  { id: 15, condominioId: "solar-ipes", titulo: "Poda das árvores do jardim frontal", origem: "E-mail", prioridade: "baixa", status: "andamento", minutosAtras: 10080, motivo: "Empresa de jardinagem confirmada" },
];

const DETALHES: Record<number, { descricao: string; relator: Relator; decisao?: Decisao }> = {
  1: { descricao: "Está saindo bastante água do teto do hall do Bloco B, bem perto do quadro de luz. O chão já está molhado até a porta do elevador.", relator: { nome: "Carla Mendes", perfil: "Morador", apartamento: "B-104", celular: "11987654321" } },
  2: { descricao: "Seu Antônio do 702 ficou preso no elevador social entre o 7º e o 8º andar. Ele está calmo, mas pediu ajuda com urgência.", relator: { nome: "José Ribeiro", perfil: "Funcionário", celular: "2134567890" } },
  3: { descricao: "O portão da garagem abre, mas não fecha mais. Já tentamos pelo controle e pelo botão da guarita e ele fica parado no meio.", relator: { nome: "Rafael Costa", perfil: "Morador", apartamento: "12", celular: "31991234567" } },
  4: { descricao: "Música alta e gritaria no 302 desde as 22h. É a terceira vez este mês. Tenho criança pequena em casa.", relator: { nome: "Patrícia Alves", perfil: "Proprietário", apartamento: "402", celular: "11976543210" } },
  5: { descricao: "Cheiro forte de gás na escada de serviço entre o 3º e o 4º andar. Abri as janelas e avisei os vizinhos do andar.", relator: { nome: "Luciana Prado", perfil: "Proprietário", apartamento: "403", celular: "21998765432" } },
  6: { descricao: "A lâmpada do corredor do 4º andar queimou. À noite fica tudo escuro perto dos apartamentos 401 a 404.", relator: { nome: "Bruno Teixeira", perfil: "Morador", apartamento: "402", celular: "31987651234" } },
  7: { descricao: "O interfone da guarita está sem som desde a manhã. Não estamos conseguindo anunciar visitas nem entregas.", relator: { nome: "Sandra Lopes", perfil: "Funcionário", celular: "1133224455" } },
  8: { descricao: "Tem uma mancha de infiltração no teto da garagem G2, em cima da vaga 41, que está aumentando a cada chuva.", relator: { nome: "Eduardo Martins", perfil: "Proprietário", apartamento: "1101", celular: "21987001122" } },
  9: { descricao: "Deixaram vários sacos de lixo na área da piscina depois do fim de semana. Está atraindo bichos.", relator: { nome: "Fernanda Rocha", perfil: "Morador", apartamento: "203", celular: "31996655443" } },
  10: { descricao: "A câmera da entrada principal está offline. O sistema mostra que não grava nada desde as 3h da manhã.", relator: { nome: "Marcelo Dias", perfil: "Funcionário", celular: "11955443322" } },
  11: { descricao: "Gostaria de reservar o salão de festas para o dia 12/12, mas o aplicativo diz que já tem pré-reserva.", relator: { nome: "Juliana Freitas", perfil: "Morador", apartamento: "804", celular: "21991112233" } },
  12: { descricao: "Tem um cachorro grande andando solto no playground. Várias mães tiraram as crianças de lá.", relator: { nome: "Ricardo Nunes", perfil: "Morador", apartamento: "305", celular: "31988776655" } },
  13: { descricao: "A bomba da cisterna está fazendo um barulho alto e intermitente desde ontem à noite.", relator: { nome: "Antônio Souza", perfil: "Funcionário", celular: "11944332211" }, decisao: { tipo: "agendar", data: "2026-11-18", nota: "Técnico da Hidrobombas às 14h" } },
  14: { descricao: "O vidro da porta do lobby trincou depois de uma batida com carrinho de compras.", relator: { nome: "Helena Castro", perfil: "Proprietário", apartamento: "501", celular: "21993334455" }, decisao: { tipo: "delegar", responsavel: "Zelador", nota: "Pedir 3 orçamentos" } },
  15: { descricao: "As árvores do jardim frontal estão encostando na fiação da rua e escondendo a placa do prédio.", relator: { nome: "Gustavo Pires", perfil: "Morador", apartamento: "702", celular: "31992223344" }, decisao: { tipo: "agendar", data: "2026-11-25" } },
};

/** Fixed mock "now" so server and browser render the same dates. */
const AGORA_MOCK = Date.parse("2026-11-17T21:00:00-03:00");
export const AUTOR_ATUAL = "Síndico";

export function protocoloDe(id: number): string {
  return `PROT-${String((id * 104729 + 318201) % 1_000_000).padStart(6, "0")}`;
}

function semear(b: OcorrenciaBase): Ocorrencia {
  const d = DETALHES[b.id]!;
  const criada = AGORA_MOCK - b.minutosAtras * 60_000;
  const historico: EventoHistorico[] = [
    { quando: new Date(criada).toISOString(), autor: "Sistema", acao: `Recebida via ${b.origem}` },
    {
      quando: new Date(criada + 60_000).toISOString(),
      autor: "Sistema",
      acao: `Prioridade sugerida: ${labelPrioridade(b.prioridade)}`,
      motivo: b.motivo,
    },
  ];
  if (d.decisao) {
    historico.push({
      quando: new Date(criada + 45 * 60_000).toISOString(),
      autor: AUTOR_ATUAL,
      acao: descreverDecisao(d.decisao),
      motivo: d.decisao.nota,
    });
  }
  return {
    ...b,
    protocolo: protocoloDe(b.id),
    prioridadeSugerida: b.prioridade,
    descricao: d.descricao,
    relator: d.relator,
    decisao: d.decisao,
    historico,
  };
}

export const OCORRENCIAS: Ocorrencia[] = BASE.map(semear);

export function nomeCondominio(id: string): string {
  return CONDOMINIOS.find((c) => c.id === id)?.nome ?? "Condomínio";
}

export function tempoDecorrido(minutos: number): string {
  if (minutos < 1) return "agora";
  if (minutos < 60) return `há ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `há ${horas} h`;
  const dias = Math.floor(horas / 24);
  return dias === 1 ? "há 1 dia" : `há ${dias} dias`;
}

const ORDEM: Record<Prioridade, number> = { urgente: 0, alta: 1, normal: 2, baixa: 3 };

export interface Filtros {
  status: Status;
  condominio?: string | undefined;
  prioridade?: Prioridade | undefined;
}

/** Filters by tab, condo and priority; sorts by priority, then most recent. */
export function filtrarOcorrencias(lista: Ocorrencia[], f: Filtros): Ocorrencia[] {
  return lista
    .filter(
      (o) =>
        o.status === f.status &&
        (!f.condominio || o.condominioId === f.condominio) &&
        (!f.prioridade || o.prioridade === f.prioridade),
    )
    .sort((a, b) => ORDEM[a.prioridade] - ORDEM[b.prioridade] || a.minutosAtras - b.minutosAtras);
}

export function contarPorPrioridade(lista: Ocorrencia[]): Record<Prioridade, number> {
  const out: Record<Prioridade, number> = { urgente: 0, alta: 0, normal: 0, baixa: 0 };
  for (const o of lista) out[o.prioridade]++;
  return out;
}

export function paginar<T>(lista: T[], pagina: number, porPagina = ITENS_POR_PAGINA) {
  const totalPaginas = Math.max(1, Math.ceil(lista.length / porPagina));
  const atual = Math.min(Math.max(1, pagina), totalPaginas);
  const inicio = (atual - 1) * porPagina;
  return { itens: lista.slice(inicio, inicio + porPagina), pagina: atual, totalPaginas };
}

const PALAVRAS: [Prioridade, RegExp][] = [
  ["urgente", /(g[áa]s|inc[êe]ndio|fogo|vazamento|preso|curto|fuma[çc]a|desab|emerg[êe]ncia)/i],
  ["alta", /(port[ãa]o|elevador|c[âa]mera|interfone|seguran[çc]a|infiltra|sem [áa]gua|sem luz)/i],
  ["baixa", /(l[âa]mpada|reserva|sugest|d[úu]vida|poda|limpeza)/i],
];

/** Suggests a priority from a pasted WhatsApp message using keywords. */
export function sugerirPrioridade(texto: string): Prioridade {
  for (const [p, re] of PALAVRAS) if (re.test(texto)) return p;
  return "normal";
}

/** Turns a pasted WhatsApp message into a new occurrence in the "Nova" queue. */
export function criarDeMensagem(
  id: number,
  condominioId: string,
  texto: string,
  quando: string = new Date().toISOString(),
): Ocorrencia {
  const autorMsg = texto.match(/^\s*(?:\[[^\]]*\]\s*)?([^:\n]{1,40}):/)?.[1]?.trim();
  const limpo = texto
    .split("\n")
    .map((l) => l.replace(/^\[[^\]]*\]\s*/, "").replace(/^[^:]{1,40}:\s*/, "").trim())
    .filter(Boolean);
  const primeira = limpo[0] ?? "Nova mensagem";
  const titulo = primeira.length > 60 ? `${primeira.slice(0, 57)}…` : primeira;
  const resto = limpo.slice(1).join(" ") || primeira;
  const prioridade = sugerirPrioridade(texto);
  const motivo = resto.length > 80 ? `${resto.slice(0, 77)}…` : resto;
  return {
    id,
    protocolo: protocoloDe(id),
    condominioId,
    titulo,
    origem: "WhatsApp",
    prioridade,
    prioridadeSugerida: prioridade,
    status: "nova",
    minutosAtras: 0,
    motivo,
    descricao: limpo.join("\n") || texto,
    relator: { nome: autorMsg || "Contato do WhatsApp", perfil: "Morador", celular: "" },
    historico: [
      { quando, autor: AUTOR_ATUAL, acao: "Mensagem colada do WhatsApp" },
      { quando, autor: "Sistema", acao: `Prioridade sugerida: ${labelPrioridade(prioridade)}`, motivo },
    ],
    mensagem: texto,
  };
}

/* ------------------------------------------------------------------ */
/* Detail page rules                                                   */
/* ------------------------------------------------------------------ */

export function labelPrioridade(p: Prioridade): string {
  return PRIORIDADES.find((x) => x.id === p)?.label ?? p;
}

const RISCO: [string, RegExp][] = [
  ["gás", /\bg[áa]s\b/i],
  ["incêndio", /inc[êe]ndio/i],
  ["fogo", /\bfogo\b/i],
  ["fumaça", /fuma[çc]a/i],
  ["explosão", /explos/i],
  ["curto-circuito", /curto[- ]?circuito/i],
  ["choque", /\bchoque\b/i],
  ["vazamento", /vazamento/i],
  ["preso", /\bpres[oa]s?\b/i],
  ["desabamento", /desab/i],
];

/** First risk keyword found in the occurrence text, or null. */
export function palavraDeRisco(o: Pick<Ocorrencia, "titulo" | "motivo" | "descricao">): string | null {
  const texto = `${o.titulo} ${o.motivo} ${o.descricao}`;
  for (const [palavra, re] of RISCO) if (re.test(texto)) return palavra;
  return null;
}

export function ehRebaixamento(atual: Prioridade, nova: Prioridade): boolean {
  return ORDEM[nova] > ORDEM[atual];
}

/** Warning shown when lowering the priority of an occurrence that has a risk keyword. */
export function alertaDeRisco(o: Ocorrencia, nova: Prioridade): string | null {
  const palavra = palavraDeRisco(o);
  if (!palavra || !ehRebaixamento(o.prioridade, nova)) return null;
  return `Esta ocorrência tem palavra de risco: ${palavra}. Explique por que não é urgente`;
}

/** Reasons shown in "Por que está aqui". */
export function porQueEstaAqui(o: Ocorrencia): string[] {
  const itens = [`Classificada como ${labelPrioridade(o.prioridadeSugerida)} pelo sistema`];
  const palavra = palavraDeRisco(o);
  if (palavra) itens.push(`Palavra de risco encontrada: "${palavra}"`);
  itens.push(o.motivo);
  return itens;
}

export function validarMudancaPrioridade(motivo: string): string | undefined {
  return motivo.trim() ? undefined : "Informe o motivo da mudança";
}

export function aplicarMudancaPrioridade(
  o: Ocorrencia,
  nova: Prioridade,
  motivo: string,
  quando: string,
  autor = AUTOR_ATUAL,
): Ocorrencia {
  if (nova === o.prioridade) return o;
  return {
    ...o,
    prioridade: nova,
    historico: [
      ...o.historico,
      {
        quando,
        autor,
        acao: `Prioridade alterada: ${labelPrioridade(o.prioridade)} → ${labelPrioridade(nova)}`,
        motivo: motivo.trim(),
      },
    ],
  };
}

/** Local calendar date as yyyy-mm-dd. */
export function dataLocalISO(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function formatarData(iso: string): string {
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}

export const ERRO_DATA_PASSADA = "Escolha uma data de hoje em diante";

export type ErrosDecisao = Partial<Record<"tipo" | "responsavel" | "data", string>>;

export type RascunhoDecisao = { [K in keyof Decisao]?: Decisao[K] | undefined };

export function validarDecisao(d: RascunhoDecisao, hoje: string): ErrosDecisao {
  const e: ErrosDecisao = {};
  if (!d.tipo) e.tipo = "Escolha o que você vai fazer";
  if (d.tipo === "delegar" && !d.responsavel) e.responsavel = "Escolha para quem delegar";
  if (d.tipo === "agendar") {
    if (!d.data) e.data = "Escolha uma data";
    else if (d.data < hoje) e.data = ERRO_DATA_PASSADA;
  }
  return e;
}

export function descreverDecisao(d: Decisao): string {
  if (d.tipo === "delegar") return `Delegada para ${d.responsavel ?? "—"}`;
  if (d.tipo === "agendar") return `Agendada para ${d.data ? formatarData(d.data) : "—"}`;
  return "Síndico vai cuidar pessoalmente";
}

export function aplicarDecisao(o: Ocorrencia, d: Decisao, quando: string, autor = AUTOR_ATUAL): Ocorrencia {
  const nota = d.nota?.trim() || undefined;
  const decisao: Decisao = {
    tipo: d.tipo,
    responsavel: d.tipo === "delegar" ? d.responsavel : undefined,
    data: d.tipo === "agendar" ? d.data : undefined,
    nota,
  };
  return {
    ...o,
    status: "andamento",
    decisao,
    historico: [...o.historico, { quando, autor, acao: descreverDecisao(decisao), motivo: nota }],
  };
}

export function podeConcluir(o: Ocorrencia): boolean {
  return o.status === "andamento";
}

export function concluirOcorrencia(o: Ocorrencia, quando: string, autor = AUTOR_ATUAL): Ocorrencia {
  if (!podeConcluir(o)) return o;
  return {
    ...o,
    status: "concluida",
    concluidaEm: quando,
    historico: [...o.historico, { quando, autor, acao: "Ocorrência concluída" }],
  };
}

/** Chronological (oldest first) history. */
export function historicoOrdenado(o: Ocorrencia): EventoHistorico[] {
  return [...o.historico].sort((a, b) => a.quando.localeCompare(b.quando));
}

const FMT_DATA_HORA = new Intl.DateTimeFormat("pt-BR", {
  timeZone: "America/Sao_Paulo",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatarDataHora(iso: string): { data: string; hora: string } {
  const partes = FMT_DATA_HORA.formatToParts(new Date(iso));
  const v = (t: string) => partes.find((p) => p.type === t)?.value ?? "";
  return { data: `${v("day")}/${v("month")}/${v("year")}`, hora: `${v("hour")}:${v("minute")}` };
}

export function formatarTelefone(digitos: string): string {
  const d = digitos.replace(/\D/g, "");
  if (d.length === 11) return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
  if (d.length === 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return d;
}
