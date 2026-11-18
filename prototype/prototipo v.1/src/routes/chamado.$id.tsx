import { createFileRoute } from "@tanstack/react-router";
import { Detail } from "@/features/triage/detail";
export const Route = createFileRoute("/chamado/$id")({
  head: ({ params }) => ({
    meta: [
      { title: `${params.id} | Triagem do Síndico` },
      {
        name: "description",
        content: "Consulte as justificativas, decida a ação e acompanhe o histórico do chamado.",
      },
      { property: "og:title", content: `Chamado ${params.id} | Triagem do Síndico` },
      {
        property: "og:description",
        content: "Cada decisão do chamado tem uma justificativa e um registro.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: TicketPage,
});
function TicketPage() {
  const { id } = Route.useParams();
  return <Detail id={id} />;
}
