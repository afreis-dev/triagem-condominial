import { z } from "zod";
import { requisitarAutenticado } from "./auth";
import type { TipoDecisao } from "./ocorrencias";

const papelResponsavelSchema = z.string().trim().min(1);

export const contatoResponsavelSchema = z.discriminatedUnion("temCelular", [
  z.object({ papel: papelResponsavelSchema, temCelular: z.literal(true), celular: z.string().trim().min(1) }),
  z.object({ papel: papelResponsavelSchema, temCelular: z.literal(false), celular: z.null() }),
]);

export type ContatoResponsavel = z.infer<typeof contatoResponsavelSchema>;

async function requisitar(caminho: string, init: RequestInit = {}) {
  const resposta = await requisitarAutenticado(caminho, { ...init, cache: "no-store" });
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
  const dados = await requisitar(`/ocorrencias/${encodeURIComponent(id)}/acoes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      acao,
      nota,
      responsavel: acao === "delegar" ? responsavel : undefined,
      dataAgendada: acao === "agendar" ? dataAgendada : undefined,
    }),
  });
  // Uma resposta sem contato ainda indica que a decisão foi registrada.
  const retorno = z.object({ contatoResponsavel: contatoResponsavelSchema.nullish() }).safeParse(dados);
  return retorno.success ? retorno.data.contatoResponsavel : undefined;
}
