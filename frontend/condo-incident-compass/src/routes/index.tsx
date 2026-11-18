import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  beforeLoad: () => {
    throw redirect({ to: "/fila", search: {} });
  },
  head: () => ({
    meta: [
      { title: "Painel do Síndico" },
      { name: "description", content: "Fila de ocorrências dos condomínios." },
      { property: "og:title", content: "Painel do Síndico" },
      { property: "og:description", content: "Fila de ocorrências dos condomínios." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
});
