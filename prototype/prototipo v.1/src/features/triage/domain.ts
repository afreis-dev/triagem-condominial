export const condos = [
  "Residencial Aurora",
  "Edifício Vista Verde",
  "Condomínio Jardim das Palmeiras",
  "Residencial Monte Azul",
  "Edifício Solar dos Ipês",
  "Condomínio Bosque Real",
];
export const people = [
  "Carlos",
  "Rita",
  "Marcos",
  "Joana",
  "Pedro",
  "Lúcia",
  "Elétrica Silva",
  "O próprio síndico",
];
export const priorities = ["Urgente", "Alta", "Normal", "Baixa"] as const;
export type Priority = (typeof priorities)[number];
export type Status = "Aberto" | "Em andamento" | "Fechado";
export type Entry = { at: number; text: string; status?: Status };
export type Ticket = {
  id: string;
  title: string;
  condo: number;
  name: string;
  apartment: string;
  phone: string;
  location: string;
  role: string;
  photo?: string | undefined;
  arrived: number;
  origin: string;
  status: Status;
  priority: Priority;
  category: string;
  assignee: string;
  reasons: [string, string, string];
  keyword?: string | undefined;
  pending?: boolean;
  confirmed?: boolean;
  history: Entry[];
};
export const statusDescriptions: Record<Status, string> = {
  Aberto: "Recebido, aguardando decisão",
  "Em andamento": "Alguém foi designado",
  Fechado: "Resolvido",
};
export const UNDO_MS = 10000;
export const CLASSIFY_MS = 2000;
const riskWords = [
  "gás",
  "fogo",
  "incêndio",
  "fumaça",
  "preso no elevador",
  "alagamento",
  "desabamento",
  "choque",
  "fio exposto",
  "agressão",
];
export function classify(
  title: string,
  condo: number,
): Pick<Ticket, "priority" | "category" | "assignee" | "reasons" | "keyword"> {
  const text = title.toLocaleLowerCase("pt-BR");
  const keyword = riskWords.find((word) => text.includes(word));
  let priority: Priority = "Normal";
  let category = "Pedido administrativo";
  let assignee = "O próprio síndico";
  let priorityReason = "Normal porque é uma solicitação sem risco imediato.";
  let categoryReason = "Pedido administrativo porque pede uma avaliação do condomínio.";
  let assigneeReason = "Sugerido o próprio síndico porque a solicitação precisa de avaliação.";
  if (keyword) {
    priority = "Urgente";
    category =
      text.includes("quadro") || keyword === "choque" || keyword === "fio exposto"
        ? "Manutenção elétrica"
        : "Segurança";
    assignee = category === "Manutenção elétrica" ? "Elétrica Silva" : "O próprio síndico";
    priorityReason = `Urgente porque o texto menciona '${keyword}', uma palavra de risco.`;
    categoryReason =
      category === "Manutenção elétrica"
        ? "Manutenção elétrica porque fala de risco na instalação elétrica."
        : "Segurança porque envolve risco às pessoas.";
    assigneeReason =
      assignee === "Elétrica Silva"
        ? "Sugerida a Elétrica Silva porque é problema elétrico."
        : "Sugerido o próprio síndico porque situações de risco pedem decisão dele.";
  } else if (text.includes("vazamento") || text.includes("água descendo")) {
    priority = "Alta";
    category = "Manutenção";
    assignee = people[condo] ?? "O próprio síndico";
    priorityReason = "Alta porque é um vazamento ativo que pode piorar.";
    categoryReason = "Manutenção porque fala de vazamento na parede.";
    assigneeReason = `Sugerido ${assignee} porque é manutenção e cuida do ${condos[condo]}.`;
  } else if (text.includes("portão") || text.includes("interfone")) {
    const gate = text.includes("portão");
    priority = gate ? "Alta" : "Normal";
    category = "Segurança e acesso";
    assignee = people[condo] ?? "O próprio síndico";
    priorityReason = gate
      ? "Alta porque deixa o acesso ao prédio aberto."
      : "Normal porque afeta a comunicação, mas tem alternativa.";
    categoryReason = `Segurança e acesso porque envolve o ${gate ? "portão" : "interfone"}.`;
    assigneeReason = `Sugerido ${assignee} porque cuida do acesso do ${condos[condo]}.`;
  } else if (text.includes("barulho")) {
    category = "Convivência";
    priorityReason = "Normal porque é conflito entre vizinhos, sem risco imediato.";
    categoryReason = "Convivência porque envolve regra do regimento.";
    assigneeReason =
      "Sugerido o próprio síndico porque conflitos entre moradores pedem a mediação dele.";
  } else if (text.includes("sugestão") || text.includes("bicicletário")) {
    priority = "Baixa";
    priorityReason = "Baixa porque é uma sugestão, sem prazo nem risco.";
    categoryReason = "Pedido administrativo porque depende de aprovação em assembleia.";
    assigneeReason = "Sugerido o próprio síndico porque é tema de assembleia.";
  } else if (
    text.includes("lâmpada") ||
    text.includes("limpeza") ||
    text.includes("torneira") ||
    text.includes("pintura")
  ) {
    category = "Manutenção";
    assignee = people[condo] ?? "O próprio síndico";
    priorityReason = "Normal porque é rotina sem risco imediato.";
    categoryReason = text.includes("lâmpada")
      ? "Manutenção porque é troca de lâmpada em área comum."
      : "Manutenção porque envolve conservação de uma área comum.";
    assigneeReason = `Sugerido ${assignee} porque é responsável pela manutenção do ${condos[condo]}.`;
  }
  return {
    priority,
    category,
    assignee,
    reasons: [priorityReason, categoryReason, assigneeReason],
    keyword,
  };
}
export function batchEligible(tickets: Ticket[]) {
  return tickets.filter((t) => t.status === "Aberto" && t.priority !== "Urgente" && !t.pending);
}
export function sortTickets(tickets: Ticket[]) {
  return [...tickets].sort(
    (a, b) =>
      priorities.indexOf(a.priority) - priorities.indexOf(b.priority) || a.arrived - b.arrived,
  );
}
export function actOnTicket(ticket: Ticket, text: string, status: Status, at = Date.now()): Ticket {
  return {
    ...ticket,
    status,
    confirmed: status !== "Aberto",
    history: [...ticket.history, { at, text, status }],
  };
}
export function approveBatch(tickets: Ticket[], ids: string[], at = Date.now()) {
  const eligible = new Set(batchEligible(tickets).map((t) => t.id));
  return tickets.map((t) =>
    ids.includes(t.id) && eligible.has(t.id)
      ? actOnTicket(
          t,
          `Delegado em lote pelo síndico a ${t.assignee}. ${t.reasons[2]}`,
          "Em andamento",
          at,
        )
      : t,
  );
}
export function undoBatch(tickets: Ticket[], originals: Ticket[], at = Date.now()) {
  return tickets.map((t) => {
    const original = originals.find((o) => o.id === t.id);
    return original
      ? {
          ...original,
          history: [
            ...t.history,
            { at, text: "Aprovação em lote desfeita pelo síndico", status: "Aberto" as Status },
          ],
        }
      : t;
  });
}
export function initialTickets(): Ticket[] {
  const rows: [string, number, number, Status?][] = [
    ["Tem cheiro de gás no bloco B", 0, 12],
    ["Fumaça saindo do quadro de luz da garagem", 3, 4],
    ["Água descendo pela parede da garagem desde ontem", 0, 95],
    ["Portão da garagem travou aberto", 1, 48],
    ["Lâmpada do hall queimada", 2, 135],
    ["Barulho no 302 depois das 22h", 0, 120],
    ["Interfone do bloco A sem som", 4, 110],
    ["Sugestão de bicicletário", 5, 102],
    ["Limpeza da escada do bloco C", 1, 85],
    ["Torneira do salão de festas pingando", 3, 76],
    ["Lâmpada da entrada piscando", 5, 69],
    ["Dúvida sobre reserva do salão", 4, 60],
    ["Barulho de obra no domingo", 2, 55],
    ["Sugestão de pintura da quadra", 3, 44],
    ["Lâmpada da escada apagada", 0, 38],
    ["Vazamento na área de serviço", 5, 30],
    ["Limpeza da piscina", 0, 240, "Em andamento"],
    ["Interfone da unidade 204", 1, 210, "Em andamento"],
    ["Pintura do muro lateral", 2, 200, "Em andamento"],
    ["Lâmpada do elevador", 3, 180, "Em andamento"],
    ["Torneira do jardim", 4, 170, "Em andamento"],
    ["Limpeza do salão após evento", 5, 1440, "Fechado"],
    ["Lâmpada da portaria substituída", 0, 1200, "Fechado"],
  ];
  const now = Date.now();
  return rows.map(([title, condo, mins, status = "Aberto"], i) => {
    const classification = classify(title, condo);
    if (i === 1) classification.reasons[1] = "Manutenção elétrica porque fala do quadro de luz.";
    if (i === 2)
      classification.reasons[2] =
        "Sugerido Carlos porque é manutenção e ele é o zelador do Residencial Aurora.";
    if (i === 3)
      classification.reasons[2] = "Sugerida Rita porque cuida da portaria do Edifício Vista Verde.";
    if (i === 4)
      classification.reasons[2] =
        "Sugerido Marcos porque é o zelador do Condomínio Jardim das Palmeiras.";
    if (i === 6)
      classification.reasons[2] =
        "Sugerido Pedro porque cuida da portaria do Edifício Solar dos Ipês.";
    const arrived = now - mins * 60000;
    const id = `TS-2611-${String(42 + i).padStart(4, "0")}`;
    const ticket: Ticket = {
      id,
      title,
      condo,
      name: [0, 16, 22].includes(i) ? "Ana Souza" : ["Ana Souza", "Felipe Santos", "Mariana Costa", "Paulo Oliveira"][i % 4] ?? "Morador",
      apartment: String(101 + i * 11),
      phone: [0, 16, 22].includes(i) ? "11987654321" : "11999990000",
      location: i === 0 ? "Bloco B" : "Área comum",
      role: "Morador",
      arrived,
      origin: i === 3 ? "WhatsApp" : "Link do condomínio",
      status,
      ...classification,
      confirmed: status !== "Aberto",
      history: [
        { at: arrived, text: "Chamado recebido pelo link do condomínio.", status: "Aberto" },
        { at: arrived + 1500, text: classification.reasons.join(" ") },
      ],
    };
    if (status !== "Aberto")
      ticket.history.push({
        at: arrived + 60000,
        text: `Síndico delegou a ${ticket.assignee}.`,
        status: "Em andamento",
      });
    if (status === "Fechado")
      ticket.history.push({
        at: arrived + 120000,
        text: "Síndico concluiu o chamado.",
        status: "Fechado",
      });
    return ticket;
  });
}
export function age(at: number, now = Date.now()) {
  const mins = Math.max(0, Math.floor((now - at) / 60000));
  return mins < 60
    ? `há ${mins} min`
    : mins < 1440
      ? `há ${Math.floor(mins / 60)} h`
      : `há ${Math.floor(mins / 1440)} d`;
}
export function stamp(at: number) {
  return new Date(at).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
