import { z } from "zod";
import { API_URL, obterToken } from "./auth";
import type { TipoDecisao } from "./ocorrencias";

async function requisitar(caminho: string, init: RequestInit = {}) {
  const token = obterToken();
  if (!token) throw new Error("Entre novamente para registrar a decis?o.");
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  const resposta = await fetch(`${API_URL}${caminho}`, { ...init, headers, cache: "no-store" });
  const dados: unknown = await resposta.json();
  if (resposta.ok) return dados;
  const erro = z.object({ detail: z.string() }).safeParse(dados);
  throw new Error(erro.success ? erro.data.detail : "N?o foi poss?vel concluir a opera??o.");
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
