import { useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { sair } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useSindico } from "./sindico-context";

export function MenuSindico() {
  const sindico = useSindico();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  async function encerrar() {
    try {
      await sair();
      queryClient.clear();
      await navigate({ to: "/login" });
    } catch (erro) {
      toast.error(erro instanceof Error ? erro.message : "Não foi possível sair.");
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="max-w-28 shrink-0 truncate sm:max-w-44">
          {sindico?.nome ?? "Síndico"}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={() => void encerrar()}>Sair</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
