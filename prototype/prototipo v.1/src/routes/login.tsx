import { createFileRoute } from "@tanstack/react-router";
import { Login } from "@/features/triage/login";
export const Route = createFileRoute("/login")({
  head: () => ({ meta: [
    { title: "Entrar | Triagem do Síndico" },
    { name: "description", content: "Acesso de demonstração para síndico e morador. Seus chamados, na ordem certa." },
    { property: "og:title", content: "Entrar | Triagem do Síndico" },
    { property: "og:description", content: "Entre na demonstração da Triagem do Síndico como síndico ou morador." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: Login,
});