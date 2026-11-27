export const API_URL = import.meta.env["VITE_API_URL"] || "http://localhost:8000";

export interface Sindico {
  id: number;
  nome: string;
  email: string;
}

export const CHAVE_SINDICO = ["sindico"] as const;

let csrfToken: string | null = null;

function limparSessao() {
  csrfToken = null;
}

export async function entrar(identificador: string, senha: string) {
  const resposta = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
    body: JSON.stringify({ identificador, senha }),
  });

  if (!resposta.ok) {
    throw new Error(
      resposta.status === 401
        ? "E-mail, celular ou senha incorretos"
        : "Não foi possível realizar o login.",
    );
  }
  return obterSindico();
}

export async function obterSindico(): Promise<Sindico> {
  const resposta = await fetch(`${API_URL}/auth/me`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!resposta.ok) {
    limparSessao();
    throw new Error("Sessão inválida ou expirada");
  }
  const dados: Sindico & { csrfToken: string } = await resposta.json();
  csrfToken = dados.csrfToken;
  return { id: dados.id, nome: dados.nome, email: dados.email };
}

export async function requisitarAutenticado(caminho: string, init: RequestInit = {}) {
  const metodo = (init.method || "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (!["GET", "HEAD", "OPTIONS"].includes(metodo)) {
    if (!csrfToken) await obterSindico();
    headers.set("X-CSRF-Token", csrfToken!);
  }
  const resposta = await fetch(`${API_URL}${caminho}`, {
    ...init,
    credentials: "include",
    headers,
  });
  if (resposta.status === 401) {
    limparSessao();
    if (typeof window !== "undefined") window.dispatchEvent(new Event("triagem-sessao-expirada"));
    throw new Error("Sessão inválida ou expirada");
  }
  return resposta;
}

export async function sair() {
  const resposta = await requisitarAutenticado("/auth/logout", { method: "POST" });
  if (!resposta.ok) throw new Error("Não foi possível encerrar a sessão.");
  limparSessao();
}
