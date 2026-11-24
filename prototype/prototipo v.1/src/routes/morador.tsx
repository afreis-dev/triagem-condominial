import { createFileRoute } from "@tanstack/react-router";
import { Resident } from "@/features/triage/resident";
export const Route = createFileRoute("/morador")({
  head: () => ({
    meta: [
      { title: "Meu chamado | Triagem do Síndico" },
      {
        name: "description",
        content: "Registre e acompanhe seu chamado no condomínio, sem login.",
      },
      { property: "og:title", content: "Meu chamado | Triagem do Síndico" },
      {
        property: "og:description",
        content: "Registro e acompanhamento de chamados do condomínio.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Resident,
});
