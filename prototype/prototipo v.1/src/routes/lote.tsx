import { createFileRoute } from "@tanstack/react-router";
import { Batch } from "@/features/triage/batch";
export const Route = createFileRoute("/lote")({
  head: () => ({
    meta: [
      { title: "Aprovação em lote | Triagem do Síndico" },
      {
        name: "description",
        content: "Revise as sugestões de responsáveis para chamados não urgentes.",
      },
      { property: "og:title", content: "Aprovação em lote | Triagem do Síndico" },
      {
        property: "og:description",
        content: "Aprovação de chamados com justificativas e opção de desfazer.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Batch,
});
