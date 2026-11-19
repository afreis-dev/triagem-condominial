import { useSyncExternalStore } from "react";
import { OCORRENCIAS, criarDeMensagem, type Ocorrencia } from "./ocorrencias";

// In-memory mock store: starts from the seed data; pasted messages live only in this browser tab.
let estado: Ocorrencia[] = OCORRENCIAS;
const ouvintes = new Set<() => void>();

function assinar(fn: () => void) {
  ouvintes.add(fn);
  return () => ouvintes.delete(fn);
}

export function useOcorrencias(): Ocorrencia[] {
  return useSyncExternalStore(assinar, () => estado, () => OCORRENCIAS);
}

export function adicionarMensagem(condominioId: string, texto: string): Ocorrencia {
  const id = Math.max(...estado.map((o) => o.id)) + 1;
  const nova = criarDeMensagem(id, condominioId, texto);
  estado = [nova, ...estado];
  ouvintes.forEach((fn) => fn());
  return nova;
}

export function atualizarOcorrencia(id: number, fn: (o: Ocorrencia) => Ocorrencia) {
  estado = estado.map((o) => (o.id === id ? fn(o) : o));
  ouvintes.forEach((fn) => fn());
}
