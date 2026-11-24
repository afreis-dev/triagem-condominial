import { createFileRoute } from "@tanstack/react-router";
import { Queue } from "@/features/triage/queue";
export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Fila da carteira | Triagem do Síndico" },
      {
        name: "description",
        content:
          "Revise urgências e aprove chamados dos seus condomínios com decisões justificadas.",
      },
      { property: "og:title", content: "Fila da carteira | Triagem do Síndico" },
      {
        property: "og:description",
        content: "Urgências em primeiro lugar. Cada decisão registrada.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Queue,
});
