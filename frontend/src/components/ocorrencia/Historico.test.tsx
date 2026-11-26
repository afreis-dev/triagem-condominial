import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { mapearRegistro, type RegistroDecisao } from "@/lib/historico-api";
import { OCORRENCIAS } from "@/lib/ocorrencias";
import { Historico } from "./Historico";

const rebaixamento: RegistroDecisao = {
  id: 1,
  ocorrenciaId: 42,
  tipo: "prioridade_alterada",
  quemDecidiu: "sindico",
  origem: null,
  prioridadeSugerida: "urgente",
  prioridadeFinal: "normal",
  motivo: "Risco descartado",
  acao: null,
  responsavel: null,
  dataAgendada: null,
  nota: null,
  rebaixouTravada: true,
  dataHora: "2026-11-24T20:00:00+00:00",
};

function mostrar(registro: RegistroDecisao) {
  render(<Historico ocorrencia={{ ...OCORRENCIAS[0]!, historico: [mapearRegistro(registro)] }} />);
}

afterEach(cleanup);

it("destaca em vermelho o rebaixamento que vem da API, uma vez só", () => {
  mostrar(rebaixamento);

  const avisos = screen.getAllByText(/Prioridade travada rebaixada/);
  expect(avisos).toHaveLength(1);
  expect(avisos[0]!.className).toContain("text-urgente");
  expect(screen.getByText("Urgente → Normal · Risco descartado")).toBeTruthy();
});

it("não mostra o aviso quando a mudança não rebaixou uma travada", () => {
  mostrar({
    ...rebaixamento,
    prioridadeSugerida: "normal",
    prioridadeFinal: "alta",
    rebaixouTravada: false,
  });

  expect(screen.queryByText(/Prioridade travada rebaixada/)).toBeNull();
});
