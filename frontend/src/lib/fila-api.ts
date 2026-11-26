import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_URL, obterToken } from "./auth";
import {
  concluirOcorrencia,
  type Ocorrencia,
  type Prioridade,
} from "./ocorrencias";

const URL = `${API_URL}/ocorrencias`;

export function chaveFila() {
  return ["fila", obterToken()] as const;
}

type CartaoFila = {
  id: number;
  protocolo?: string;
  condominioId: number;
  condominio: string;
  descricao: string;
  origem: "morador" | "proprietario" | "funcionario" | "whatsapp_sindico";
  status: "nova" | "em_andamento" | "concluida";
  prioridade: Prioridade | null;
  prioridadeSugerida?: Prioridade | null;
  travada?: boolean;
  palavraDeRisco?: string | null;
  nome?: string | null;
  apartamento?: string | null;
  celular?: string | null;
  local?: string | null;
  motivo: string | null;
  criadaEm: string;
  concluidaEm?: string | null;
  marcaAcao?: string | null;
};

function mapearCartao(cartao: CartaoFila): Ocorrencia {
  const origem = cartao.origem === "whatsapp_sindico" ? "WhatsApp" : "App";
  const prioridade = cartao.prioridade ?? "normal";
  return {
    id: cartao.id,
    protocolo: cartao.protocolo ?? String(cartao.id),
    condominioId: String(cartao.condominioId),
    condominioNome: cartao.condominio,
    titulo: cartao.descricao,
    descricao: cartao.descricao,
    origem,
    status: cartao.status === "em_andamento" ? "andamento" : cartao.status,
    prioridade,
    prioridadeSugerida: cartao.prioridadeSugerida ?? prioridade,
    travada: cartao.travada ?? false,
    palavraDeRisco: cartao.palavraDeRisco ?? null,
    ...(cartao.local ? { local: cartao.local } : {}),
    ...(cartao.nome || cartao.apartamento || cartao.celular ? {
      relator: {
        nome: cartao.nome ?? "Nome não informado",
        perfil: cartao.origem === "funcionario" ? "Funcionário"
          : cartao.origem === "proprietario" ? "Proprietário" : "Morador",
        apartamento: cartao.apartamento ?? undefined,
        celular: cartao.celular ?? "",
      },
    } : {}),
    criadaEm: cartao.criadaEm,
    ...(cartao.concluidaEm ? { concluidaEm: cartao.concluidaEm } : {}),
    ...(cartao.marcaAcao ? { marcaAcao: cartao.marcaAcao } : {}),
    minutosAtras: Math.max(0, Math.floor((Date.now() - Date.parse(cartao.criadaEm)) / 60_000)),
    motivo: cartao.motivo ?? "Não classificada, revisar",
    historico: [{ quando: cartao.criadaEm, autor: "Sistema", acao: `Recebida via ${origem}` }],
  };
}

export function useOcorrenciaApi(id: string, enabled: boolean) {
  const token = obterToken();
  return useQuery({
    queryKey: ["ocorrencia", id, token],
    enabled,
    retry: false,
    queryFn: async ({ signal }) => {
      if (!token) throw new Error("Entre novamente para consultar a ocorrência.");
      const resposta = await fetch(`${URL}/${encodeURIComponent(id)}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
        signal,
      });
      if (resposta.status === 404) return null;
      if (!resposta.ok) throw new Error("Não foi possível consultar a ocorrência.");
      return mapearCartao(await resposta.json());
    },
  });
}

export function usePrioridadeApi(id: string) {
  const queryClient = useQueryClient();
  const token = obterToken();
  return useMutation({
    mutationFn: async ({ prioridade, motivo }: { prioridade: Prioridade; motivo?: string }) => {
      if (!token) throw new Error("Entre novamente para confirmar a prioridade.");
      const resposta = await fetch(`${URL}/${encodeURIComponent(id)}/prioridade`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ prioridade, motivo }),
      });
      if (!resposta.ok) {
        const dados = await resposta.json().catch(() => null);
        const detalhe = dados?.detail;
        throw new Error(typeof detalhe === "string" ? detalhe
          : detalhe?.motivo ?? "Não foi possível confirmar a prioridade.");
      }
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["ocorrencia", id, token] }),
        queryClient.invalidateQueries({ queryKey: chaveFila() }),
        queryClient.invalidateQueries({ queryKey: ["historico", Number(id), token] }),
      ]);
    },
  });
}

export function useFilaApi(habilitada = true) {
  const queryClient = useQueryClient();
  const chave = chaveFila();
  return useQuery({
    queryKey: chave,
    enabled: habilitada,
    retry: false,
    queryFn: async ({ signal }) => {
      const anteriores = new Map(
        queryClient.getQueryData<Ocorrencia[]>(chave)?.map((o) => [o.id, o.concluidaEm]),
      );
      return (await buscarFila(signal)).map((ocorrencia) => {
        if (ocorrencia.status !== "concluida") return ocorrencia;
        const horario = ocorrencia.concluidaEm ?? anteriores.get(ocorrencia.id);
        return horario
          ? concluirOcorrencia({ ...ocorrencia, status: "andamento" }, horario)
          : ocorrencia;
      });
    },
  });
}

export async function buscarFila(signal: AbortSignal): Promise<Ocorrencia[]> {
  const token = obterToken();
  if (!token) throw new Error("Entre novamente para consultar a fila.");
  const resposta = await fetch(URL, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
    signal,
  });
  if (resposta.status === 401) throw new Error("Sessão expirada. Entre novamente.");
  if (!resposta.ok) throw new Error("Não foi possível consultar a fila.");
  const dados: { ok: true; ocorrencias: CartaoFila[] } = await resposta.json();
  return dados.ocorrencias.map(mapearCartao);
}

type RespostaConclusao =
  | { ok: true; ocorrenciaId: number; concluidaEm: string }
  | { ok: false; erros: { status?: string; ocorrenciaId?: string } };

export function useConclusaoApi() {
  const queryClient = useQueryClient();
  const chave = chaveFila();
  return useMutation({
    mutationFn: async (id: number) => {
      const resposta = await fetch(`${URL}/${id}/concluir`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${obterToken()}` },
      });
      if (!resposta.ok && resposta.status !== 404 && resposta.status !== 409) {
        throw new Error("Não foi possível concluir a ocorrência.");
      }
      const resultado: RespostaConclusao = await resposta.json();
      if (!resultado.ok) throw new Error(resultado.erros.status ?? resultado.erros.ocorrenciaId);
      return resultado;
    },
    onSuccess: async ({ ocorrenciaId, concluidaEm }) => {
      await queryClient.cancelQueries({ queryKey: chave });
      queryClient.setQueryData<Ocorrencia[]>(chave, (lista) =>
        lista?.map((o) => (o.id === ocorrenciaId ? concluirOcorrencia(o, concluidaEm) : o)),
      );
      void queryClient.invalidateQueries({ queryKey: chave });
      void queryClient.invalidateQueries({
        queryKey: ["historico", ocorrenciaId],
      });
    },
    onError: () => {
      void queryClient.invalidateQueries({ queryKey: chave });
    },
  });
}
