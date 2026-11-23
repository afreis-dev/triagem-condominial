import { z } from "zod";
import type { Status, TipoDecisao } from "./ocorrencias";

export const h11Local = import.meta.env.DEV && import.meta.env["VITE_H11_LOCAL"] === "1";

const filaH11 = z.array(z.object({
  id: z.string().uuid(),
  titulo: z.string(),
  condominio_id: z.string(),
  prioridade: z.enum(["urgente", "alta", "normal", "baixa"]).nullable(),
  origem: z.string().nullable(),
  motivo: z.string().nullable(),
  status: z.enum(["Nova", "Em andamento", "Fechado"]),
  created_at: z.string(),
  marcaAcao: z.string().nullable(),
}));

const statusFila = {
  Nova: "nova",
  "Em andamento": "andamento",
  Fechado: "concluida",
} satisfies Record<string, Status>;

function normalizarMarca(marca: string | null) {
  const delegado = marca?.match(/^Delegado:\s*(.+)$/i)?.[1];
  if (!delegado) return marca;
  const responsavel = /^(sindico|síndico)$/i.test(delegado) ? "você" : delegado;
  return `Responsável: ${responsavel}`;
}

async function requisitar(caminho: string, init: RequestInit = {}) {
  const resposta = await fetch(`/h11-local${caminho}`, { cache: "no-store", ...init });
  const dados: unknown = await resposta.json();
  if (resposta.ok) return dados;
  const erro = z.object({ detail: z.string() }).safeParse(dados);
  throw new Error(erro.success ? erro.data.detail : "Não foi possível concluir a operação.");
}

export async function buscarFilaH11(signal: AbortSignal) {
  const itens = filaH11.parse(await requisitar("/ocorrencias", { signal }));
  const nomes = new Map(await Promise.all(
    [...new Set(itens.map((item) => item.condominio_id))].map(async (id) => {
      const dados = await requisitar(`/api/condominios/${encodeURIComponent(id)}`, { signal });
      return [id, z.object({ nome: z.string() }).parse(dados).nome] as const;
    }),
  ));
  const agora = Date.now();
  return itens.map((item) => ({
    id: `h11-${item.id}`,
    condominioId: item.condominio_id,
    condominio: nomes.get(item.condominio_id) ?? item.condominio_id,
    titulo: item.titulo,
    origem: item.origem ?? "",
    prioridade: item.prioridade,
    motivo: item.motivo ?? "",
    status: statusFila[item.status],
    minutosAtras: Math.max(0, Math.floor((agora - Date.parse(item.created_at)) / 60_000)),
    marcaAcao: normalizarMarca(item.marcaAcao),
  }));
}

export async function buscarResponsaveis(id: string, signal: AbortSignal) {
  const dados = await requisitar(`/ocorrencias/${encodeURIComponent(id)}/responsaveis`, { signal });
  return z.object({
    responsaveis: z.array(z.string()),
    responsavelSugerido: z.string().nullable(),
  }).parse(dados);
}

export async function registrarAcao(
  id: string,
  acao: TipoDecisao,
  nota: string,
  responsavel?: string,
  dataAgendada?: string,
) {
  await requisitar(`/ocorrencias/${encodeURIComponent(id)}/acoes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      acao,
      nota,
      responsavel: acao === "delegar" ? responsavel : undefined,
      dataAgendada: acao === "agendar" ? dataAgendada : undefined,
    }),
  });
}
