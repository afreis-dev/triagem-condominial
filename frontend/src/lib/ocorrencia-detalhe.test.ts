import { describe, expect, it } from "vitest";
import {
  ERRO_DATA_PASSADA,
  OCORRENCIAS,
  alertaDeRisco,
  aplicarDecisao,
  aplicarMudancaPrioridade,
  concluirOcorrencia,
  historicoOrdenado,
  podeConcluir,
  validarDecisao,
  validarMudancaPrioridade,
} from "./ocorrencias";

const byId = (id: number) => OCORRENCIAS.find((o) => o.id === id)!;
const AGORA = "2026-11-18T12:00:00.000Z";

describe("detalhe da ocorrência", () => {
  it("requires a reason to change the priority", () => {
    expect(validarMudancaPrioridade("  ")).toBe("Informe o motivo da mudança");
    expect(validarMudancaPrioridade("Já resolvido pelo morador")).toBeUndefined();
  });

  it("warns when downgrading an occurrence with a risk word", () => {
    expect(alertaDeRisco(byId(5), "normal")).toBe(
      "Esta ocorrência tem palavra de risco: gás. Explique por que não é urgente",
    );
  });

  it("does not warn when the priority goes up or there is no risk word", () => {
    expect(alertaDeRisco(byId(5), "urgente")).toBeNull();
    expect(alertaDeRisco(byId(6), "baixa")).toBeNull();
  });

  it("logs priority changes with the reason", () => {
    const o = aplicarMudancaPrioridade(byId(3), "normal", "Portão já voltou a fechar", AGORA);
    expect(o.prioridade).toBe("normal");
    expect(o.historico.at(-1)).toMatchObject({ acao: "Prioridade alterada: Alta → Normal", motivo: "Portão já voltou a fechar" });
  });

  it("blocks scheduling in the past", () => {
    expect(validarDecisao({ tipo: "agendar", data: "2026-11-17" }, "2026-11-18").data).toBe(ERRO_DATA_PASSADA);
    expect(validarDecisao({ tipo: "agendar", data: "2026-11-18" }, "2026-11-18")).toEqual({});
  });

  it("requires an assignee when delegating", () => {
    expect(validarDecisao({ tipo: "delegar" }, "2026-11-18").responsavel).toBeDefined();
    expect(validarDecisao({ tipo: "delegar", responsavel: "Portaria" }, "2026-11-18")).toEqual({});
  });

  it("confirming a decision moves the occurrence to Em andamento", () => {
    const o = aplicarDecisao(byId(1), { tipo: "delegar", responsavel: "Zelador", nota: "Fechar registro" }, AGORA);
    expect(o.status).toBe("andamento");
    expect(o.historico.at(-1)).toMatchObject({ acao: "Delegada para Zelador", motivo: "Fechar registro" });
  });

  it("only occurrences Em andamento can be concluded", () => {
    expect(podeConcluir(byId(1))).toBe(false);
    expect(concluirOcorrencia(byId(1), AGORA).status).toBe("nova");
    const concluida = concluirOcorrencia(byId(13), AGORA);
    expect(concluida).toMatchObject({ status: "concluida", concluidaEm: AGORA });
    expect(podeConcluir(concluida)).toBe(false);
    expect(concluirOcorrencia(concluida, AGORA)).toBe(concluida);
  });

  it("shows history oldest first", () => {
    const h = historicoOrdenado(aplicarDecisao(byId(2), { tipo: "eu_mesmo" }, AGORA));
    const datas = h.map((e) => e.quando);
    expect(datas).toEqual([...datas].sort());
  });
});
