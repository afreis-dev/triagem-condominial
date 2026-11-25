import { API_URL, obterToken } from "./auth";

export interface MensagemColada {
  condominioId: number;
  descricao: string;
  nome: string;
  celular: string;
}

async function requisitar(caminho: string, init: RequestInit = {}) {
  const token = obterToken();
  if (!token) throw new Error("Entre novamente para registrar uma ocorrência.");
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${API_URL}${caminho}`, { ...init, headers });
}

export async function buscarCondominiosDaCarteira(signal: AbortSignal) {
  const resposta = await requisitar("/api/condominios", { signal });
  if (!resposta.ok) throw new Error("Não foi possível carregar os condomínios.");
  return (await resposta.json()) as { id: number; nome: string }[];
}

export async function salvarMensagemColada(mensagem: MensagemColada) {
  const resposta = await requisitar("/ocorrencias/colar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...mensagem, origem: "whatsapp_sindico" }),
  });
  if (!resposta.ok) {
    const erro = (await resposta.json().catch(() => null)) as {
      detail?: string | Record<string, unknown>;
    } | null;
    const detalhe = erro?.detail;
    const motivo = typeof detalhe === "string"
      ? detalhe
      : Object.values(detalhe ?? {}).find((valor): valor is string => typeof valor === "string");
    throw new Error(motivo ?? "Não foi possível salvar a ocorrência.");
  }
}
