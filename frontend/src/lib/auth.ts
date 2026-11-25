export const API_URL = import.meta.env["VITE_API_URL"] || "http://127.0.0.1:8000";
const CHAVE_TOKEN = "triagem_token";

export interface Sindico {
  id: number;
  nome: string;
  email: string;
}

export function obterToken() {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(CHAVE_TOKEN);
}

export function sair() {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(CHAVE_TOKEN);
  }
}

export async function entrar(email: string, senha: string) {
  const resposta = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, senha }),
  });

  if (!resposta.ok) {
    throw new Error(
      resposta.status === 401 ? "E-mail ou senha inválidos." : "Não foi possível realizar o login.",
    );
  }

  const dados: { access_token: string } = await resposta.json();
  sessionStorage.setItem(CHAVE_TOKEN, dados.access_token);
}

export async function obterSindico(): Promise<Sindico> {
  const token = obterToken();
  if (!token) throw new Error("Sessão não encontrada");

  const resposta = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!resposta.ok) {
    sair();
    throw new Error("Sessão inválida ou expirada");
  }

  return resposta.json();
}
