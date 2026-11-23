import { z } from "zod";

// Public resident form (/c/$identificador). Kept independent from the manager dashboard modules.

export type Perfil = "morador" | "proprietario" | "funcionario";

export const PERFIS: { id: Perfil; label: string }[] = [
  { id: "morador", label: "Morador" },
  { id: "proprietario", label: "Proprietário" },
  { id: "funcionario", label: "Funcionário" },
];

export interface ChamadoForm {
  perfil: Perfil;
  nome: string;
  apartamento: string;
  celular: string;
  local: string;
  descricao: string;
}

export type CampoObrigatorio = "nome" | "apartamento" | "celular" | "descricao";
export type ErrosChamado = Partial<Record<CampoObrigatorio | "local", string>>;

export function apartamentoObrigatorio(perfil: Perfil): boolean {
  return perfil !== "funcionario";
}

export function somenteDigitos(v: string): string {
  return v.replace(/\D/g, "").slice(0, 11);
}

/** Brazilian phone mask: (11) 1234-5678 for 10 digits, (11) 91234-5678 for 11. */
export function mascaraCelular(v: string): string {
  const d = somenteDigitos(v);
  if (d.length === 0) return "";
  if (d.length <= 2) return `(${d}`;
  const ddd = d.slice(0, 2);
  const resto = d.slice(2);
  if (d.length <= 6) return `(${ddd}) ${resto}`;
  const corte = d.length === 11 ? 7 : 6;
  return `(${ddd}) ${d.slice(2, corte)}-${d.slice(corte)}`;
}

const schema = z.object({
  nome: z.string().trim().min(1, "Informe seu nome").max(100, "Máximo de 100 caracteres"),
  apartamento: z.string().trim().max(20, "Máximo de 20 caracteres"),
  celular: z
    .string()
    .transform(somenteDigitos)
    .refine((d) => d.length === 10 || d.length === 11, "Informe um celular com DDD (10 ou 11 dígitos)"),
  local: z.string().trim().max(120, "Máximo de 120 caracteres"),
  descricao: z
    .string()
    .trim()
    .min(1, "Descreva o problema")
    .max(1000, "Máximo de 1000 caracteres"),
});

export function validarChamado(form: ChamadoForm): ErrosChamado {
  const erros: ErrosChamado = {};
  const r = schema.safeParse(form);
  if (!r.success) {
    for (const issue of r.error.issues) {
      const campo = issue.path[0] as keyof ErrosChamado;
      if (!erros[campo]) erros[campo] = issue.message;
    }
  }
  if (apartamentoObrigatorio(form.perfil) && form.apartamento.trim() === "") {
    erros.apartamento = "Informe o apartamento";
  }
  return erros;
}

/** Protocol shown to the resident after submitting, e.g. PROT-123456. */
export function gerarProtocolo(aleatorio: () => number = Math.random): string {
  return `PROT-${String(Math.floor(aleatorio() * 1_000_000)).padStart(6, "0")}`;
}

const PREFIXOS = /^(condom[ií]nio|residencial|edif[ií]cio|ed|cond)\b/i;

/** Builds a readable condo name from the URL identifier: "aurora" -> "Condomínio Aurora". */
export function nomeDoIdentificador(identificador: string): string {
  let texto = identificador;
  try {
    texto = decodeURIComponent(identificador);
  } catch {
    // keep raw value
  }
  const palavras = texto
    .replace(/[-_+]+/g, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((p) =>
      ["de", "da", "do", "das", "dos", "e"].includes(p.toLowerCase())
        ? p.toLowerCase()
        : p.charAt(0).toUpperCase() + p.slice(1).toLowerCase(),
    );
  const nome = palavras.join(" ").slice(0, 80);
  if (!nome) return "Condomínio";
  return PREFIXOS.test(nome) ? nome : `Condomínio ${nome}`;
}
