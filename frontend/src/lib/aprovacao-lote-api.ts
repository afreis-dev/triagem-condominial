import { requisitarAutenticado } from "./auth";
import type { Prioridade, Responsavel } from "./ocorrencias";

export interface OcorrenciaParaAprovacao {
  id: number;
  descricao: string;
  condominio: string;
  status: string;
  prioridade: Prioridade;
  responsavel_sugerido: "zelador" | "portaria" | "sindico" | null;
  motivo: string | null;
}

const RESPONSAVEIS: Record<NonNullable<OcorrenciaParaAprovacao["responsavel_sugerido"]>, Responsavel> = {
  zelador: "Zelador",
  portaria: "Portaria",
  sindico: "Síndico",
};

export function responsavelDoLote(ocorrencia: OcorrenciaParaAprovacao) {
  return RESPONSAVEIS[ocorrencia.responsavel_sugerido ?? "sindico"];
}

export async function buscarParaAprovacao(signal: AbortSignal) {
  const resposta = await requisitarAutenticado("/ocorrencias/para-aprovacao", {
    signal,
    cache: "no-store",
  });
  if (!resposta.ok) throw new Error("Não foi possível carregar a aprovação em lote.");
  const dados: { ocorrencias: OcorrenciaParaAprovacao[] } = await resposta.json();
  return dados.ocorrencias.filter(
    (o) => o.status === "nova" && ["alta", "normal", "baixa"].includes(o.prioridade),
  );
}

async function enviarLote(rota: string, ids: number[], mensagem: string) {
  const resposta = await requisitarAutenticado(`/ocorrencias/${rota}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  if (!resposta.ok) {
    const dados = await resposta.json().catch(() => null);
    throw new Error(typeof dados?.detail === "string" ? dados.detail : mensagem);
  }
  return resposta;
}

export async function aprovarLote(ids: number[]): Promise<number[]> {
  const resposta = await enviarLote("aprovar-lote", ids, "Não foi possível aprovar o lote.");
  const dados: { aprovados: number[] } = await resposta.json();
  return dados.aprovados;
}

export async function desfazerLote(ids: number[]) {
  await enviarLote("desfazer-lote", ids, "Não foi possível desfazer a aprovação.");
}
