import { useQuery } from "@tanstack/react-query";
import { type EventoHistorico, type Prioridade } from "./ocorrencias";
import { API_URL, obterToken } from "./auth";

export type RegistroDecisao = {
  id: number;
  ocorrenciaId: number;
  tipo:
    | "entrada"
    | "prioridade_confirmada"
    | "prioridade_alterada"
    | "acao"
    | "conclusao"
    | "aprovacao_lote";
  quemDecidiu: "sistema" | "sindico";
  origem: string | null;
  prioridadeSugerida: Prioridade | null;
  prioridadeFinal: Prioridade | null;
  motivo: string | null;
  acao: string | null;
  responsavel: string | null;
  dataAgendada: string | null;
  nota: string | null;
  rebaixouTravada: boolean;
  dataHora: string;
};

const PRIORIDADES: Record<Prioridade, string> = {
  urgente: "Urgente",
  alta: "Alta",
  normal: "Normal",
  baixa: "Baixa",
};

const RESPONSAVEIS: Record<string, string> = {
  zelador: "Zelador",
  portaria: "Portaria",
  sindico: "Síndico",
};

const ORIGENS: Record<string, string> = {
  morador: "Morador",
  proprietario: "Proprietário",
  funcionario: "Funcionário",
  whatsapp_sindico: "WhatsApp",
};

export function mapearRegistro(registro: RegistroDecisao): EventoHistorico {
  const sugerida = registro.prioridadeSugerida ? PRIORIDADES[registro.prioridadeSugerida] : null;

  const final = registro.prioridadeFinal ? PRIORIDADES[registro.prioridadeFinal] : null;

  const responsavel = registro.responsavel
    ? (RESPONSAVEIS[registro.responsavel] ?? registro.responsavel)
    : null;

  let acao: string;
  const detalhes: string[] = [];

  switch (registro.tipo) {
    case "entrada":
      acao = registro.origem
        ? `Recebida via ${ORIGENS[registro.origem] ?? registro.origem}`
        : "Ocorrência recebida";

      if (sugerida) {
        detalhes.push(`Prioridade sugerida: ${sugerida}`);
      }
      break;

    case "prioridade_confirmada":
      acao = "Prioridade confirmada";
      if (final) detalhes.push(`Prioridade: ${final}`);
      break;

    case "prioridade_alterada":
      acao = "Prioridade alterada";
      if (sugerida && final) {
        detalhes.push(`${sugerida} → ${final}`);
      }
      break;

    case "acao":
      if (registro.acao === "delegar") {
        acao = responsavel ? `Delegada para ${responsavel}` : "Ocorrência delegada";
      } else if (registro.acao === "agendar") {
        acao = "Ocorrência agendada";

        if (registro.dataAgendada) {
          detalhes.push(`Data: ${registro.dataAgendada.split("-").reverse().join("/")}`);
        }
      } else if (registro.acao === "eu_mesmo") {
        acao = "Síndico assumiu a ocorrência";
      } else {
        acao = "Ação registrada";
      }
      break;

    case "conclusao":
      acao = "Ocorrência concluída";
      break;

    case "aprovacao_lote":
      acao = "Aprovada em lote";
      if (final) detalhes.push(`Prioridade: ${final}`);
      if (responsavel) detalhes.push(`Responsável: ${responsavel}`);
      break;
  }

  if (registro.motivo) detalhes.push(registro.motivo);
  if (registro.nota) detalhes.push(registro.nota);

  if (registro.rebaixouTravada) {
    detalhes.push("Prioridade travada rebaixada");
  }

  return {
    quando: registro.dataHora,
    autor: registro.quemDecidiu === "sistema" ? "Sistema" : "Síndico",
    acao,
    motivo: detalhes.length ? detalhes.join(" · ") : undefined,
  };
}

export function useHistoricoApi(id: number, habilitada = true) {
  const token = obterToken();
  return useQuery({
    queryKey: ["historico", id, token],
    enabled: habilitada,
    retry: false,
    queryFn: async ({ signal }) => {
      if (!token) {
        throw new Error("Entre novamente para consultar o histórico.");
      }

      const resposta = await fetch(`${API_URL}/api/ocorrencias/${id}/decisoes`, {
        signal,
        cache: "no-store",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!resposta.ok) {
        throw new Error("Não foi possível consultar o histórico.");
      }

      const registros: RegistroDecisao[] = await resposta.json();

      return registros.map(mapearRegistro);
    },
  });
}
