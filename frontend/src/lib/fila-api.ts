import { z } from "zod";
import { API_URL, obterToken } from "./auth";
import type { Status } from "./ocorrencias";

const respostaFila = z.object({
  ok: z.literal(true),
  ocorrencias: z.array(
    z.object({
      id: z.union([z.number(), z.string()]),
      condominioId: z.union([z.number(), z.string()]),
      condominio: z.string(),
      descricao: z.string(),
      origem: z.string(),
      status: z.enum(["nova", "em_andamento", "concluida"]),
      prioridade: z.enum(["urgente", "alta", "normal", "baixa"]).nullable(),
      motivo: z.string().nullable(),
      criadaEm: z.string().datetime({ offset: true }),
    }),
  ),
});

export async function buscarFila(signal: AbortSignal) {
  const token = obterToken();
  if (!token) throw new Error("Entre novamente para consultar a fila.");
  const resposta = await fetch(`${API_URL}/ocorrencias`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
    signal,
  });
  if (resposta.status === 401) throw new Error("Sessão expirada. Entre novamente.");
  if (!resposta.ok) throw new Error("Não foi possível buscar a fila. Tente atualizar.");

  const { ocorrencias } = respostaFila.parse(await resposta.json());
  const agora = Date.now();
  return ocorrencias.map((o) => {
    const status: Status = o.status === "em_andamento" ? "andamento" : o.status;
    return {
    id: `api-${o.id}`,
    condominioId: String(o.condominioId),
    condominio: o.condominio,
    titulo: o.descricao,
    origem: o.origem,
    status,
    prioridade: o.prioridade,
    motivo: o.motivo ?? "",
    minutosAtras: Math.max(0, Math.floor((agora - Date.parse(o.criadaEm)) / 60_000)),
    };
  });
}
