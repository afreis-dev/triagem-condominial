import { describe, expect, it } from "vitest";
import {
  mapearRegistro,
  type RegistroDecisao,
} from "./historico-api";

const base: RegistroDecisao = {
  id: 1,
  ocorrenciaId: 42,
  tipo: "entrada",
  quemDecidiu: "sistema",
  origem: null,
  prioridadeSugerida: null,
  prioridadeFinal: null,
  motivo: null,
  acao: null,
  responsavel: null,
  dataAgendada: null,
  nota: null,
  rebaixouTravada: false,
  dataHora: "2026-11-24T20:00:00+00:00",
};

describe("mapearRegistro", () => {
  it("mapeia o registro de entrada", () => {
    const evento = mapearRegistro({
      ...base,
      origem: "morador",
      prioridadeSugerida: "urgente",
    });

    expect(evento.autor).toBe("Sistema");
    expect(evento.acao).toBe("Recebida via Morador");
    expect(evento.motivo).toContain("Urgente");
    expect(evento.quando).toBe(base.dataHora);
  });

  it("mapeia a confirmação de prioridade", () => {
    const evento = mapearRegistro({
      ...base,
      tipo: "prioridade_confirmada",
      quemDecidiu: "sindico",
      prioridadeFinal: "alta",
    });

    expect(evento.autor).toBe("Síndico");
    expect(evento.acao).toBe("Prioridade confirmada");
    expect(evento.motivo).toContain("Alta");
  });

  it("exibe alteração de prioridade e justificativa", () => {
    const evento = mapearRegistro({
      ...base,
      tipo: "prioridade_alterada",
      quemDecidiu: "sindico",
      prioridadeSugerida: "urgente",
      prioridadeFinal: "normal",
      motivo: "Risco descartado",
      rebaixouTravada: true,
    });

    expect(evento.acao).toBe("Prioridade alterada");
    expect(evento.motivo).toContain("Urgente → Normal");
    expect(evento.motivo).toContain("Risco descartado");
    expect(evento.rebaixouTravada).toBe(true);
    expect(evento.motivo).not.toContain("Prioridade travada rebaixada");
  });

  it("exibe delegação, responsável e nota", () => {
    const evento = mapearRegistro({
      ...base,
      tipo: "acao",
      quemDecidiu: "sindico",
      acao: "delegar",
      responsavel: "zelador",
      nota: "Verificar vazamento",
    });

    expect(evento.acao).toBe("Delegada para Zelador");
    expect(evento.motivo).toContain("Verificar vazamento");
  });

  it("formata a data de agendamento", () => {
    const evento = mapearRegistro({
      ...base,
      tipo: "acao",
      acao: "agendar",
      dataAgendada: "2026-12-05",
    });

    expect(evento.acao).toBe("Ocorrência agendada");
    expect(evento.motivo).toContain("05/12/2026");
  });

  it("mapeia a conclusão sem campos opcionais", () => {
    const evento = mapearRegistro({
      ...base,
      tipo: "conclusao",
      quemDecidiu: "sindico",
    });

    expect(evento.acao).toBe("Ocorrência concluída");
    expect(evento.autor).toBe("Síndico");
    expect(evento.motivo).toBeUndefined();
  });

  it("mapeia a aprovação em lote", () => {
    const evento = mapearRegistro({
      ...base,
      tipo: "aprovacao_lote",
      prioridadeFinal: "normal",
      responsavel: "portaria",
    });

    expect(evento.acao).toBe("Aprovada em lote");
    expect(evento.motivo).toContain("Normal");
    expect(evento.motivo).toContain("Portaria");
  });

  it("exibe a aprovação em lote desfeita no histórico", () => {
    const evento = mapearRegistro({ ...base, tipo: "desfazer_aprovacao_lote" });
    expect(evento.acao).toBe("Aprovação em lote desfeita pelo síndico");
  });
});
