import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  concluirOcorrencia,
  type Ocorrencia,
  type Prioridade,
} from "./ocorrencias";

const FILA = ["fila"] as const;
const URL = "/api/ocorrencias";

type CartaoFila = {
  id: number;
  protocolo: string;
  condominioId: number;
  condominio: string;
  descricao: string;
  origem: "morador" | "proprietario" | "funcionario" | "whatsapp_sindico";
  status: "nova" | "em_andamento" | "concluida";
  prioridade: Prioridade | null;
  motivo: string | null;
  criadaEm: string;
};

function mapearCartao(cartao: CartaoFila): Ocorrencia {
  const origem = cartao.origem === "whatsapp_sindico" ? "WhatsApp" : "App";
  const prioridade = cartao.prioridade ?? "normal";
  return {
    id: cartao.id,
    protocolo: cartao.protocolo,
    condominioId: String(cartao.condominioId),
    condominioNome: cartao.condominio,
    titulo: cartao.descricao,
    descricao: cartao.descricao,
    origem,
    status: cartao.status === "em_andamento" ? "andamento" : cartao.status,
    prioridade,
    prioridadeSugerida: prioridade,
    minutosAtras: Math.max(0, Math.floor((Date.now() - Date.parse(cartao.criadaEm)) / 60_000)),
    motivo: cartao.motivo ?? "Não classificada, revisar",
    historico: [{ quando: cartao.criadaEm, autor: "Sistema", acao: `Recebida via ${origem}` }],
  };
}

export function useFilaApi(habilitada = true) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: FILA,
    enabled: habilitada,
    retry: false,
    queryFn: async ({ signal }) => {
      const resposta = await fetch(URL, { signal });
      if (!resposta.ok) throw new Error("Não foi possível consultar a fila.");
      const dados: { ok: true; ocorrencias: CartaoFila[] } = await resposta.json();
      const anteriores = new Map(
        queryClient.getQueryData<Ocorrencia[]>(FILA)?.map((o) => [o.id, o.concluidaEm]),
      );
      return dados.ocorrencias.map((cartao) => {
        const ocorrencia = mapearCartao(cartao);
        if (cartao.status !== "concluida") return ocorrencia;
        const horario = anteriores.get(cartao.id);
        return horario
          ? concluirOcorrencia({ ...ocorrencia, status: "andamento" }, horario)
          : ocorrencia;
      });
    },
  });
}

type RespostaConclusao =
  | { ok: true; ocorrenciaId: number; concluidaEm: string }
  | { ok: false; erros: { status?: string; ocorrenciaId?: string } };

export function useConclusaoApi() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const resposta = await fetch(`${URL}/${id}/concluir`, { method: "PATCH" });
      if (!resposta.ok && resposta.status !== 404 && resposta.status !== 409) {
        throw new Error("Não foi possível concluir a ocorrência.");
      }
      const resultado: RespostaConclusao = await resposta.json();
      if (!resultado.ok) throw new Error(resultado.erros.status ?? resultado.erros.ocorrenciaId);
      return resultado;
    },
    onSuccess: async ({ ocorrenciaId, concluidaEm }) => {
      await queryClient.cancelQueries({ queryKey: FILA });
      queryClient.setQueryData<Ocorrencia[]>(FILA, (lista) =>
        lista?.map((o) => (o.id === ocorrenciaId ? concluirOcorrencia(o, concluidaEm) : o)),
      );
      void queryClient.invalidateQueries({ queryKey: FILA });
      void queryClient.invalidateQueries({
        queryKey: ["historico", ocorrenciaId],
      });
    },
    onError: () => {
      void queryClient.invalidateQueries({ queryKey: FILA });
    },
  });
}
