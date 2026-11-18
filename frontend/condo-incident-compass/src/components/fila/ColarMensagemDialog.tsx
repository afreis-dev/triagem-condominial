import { useState } from "react";
import { ClipboardPaste } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { CONDOMINIOS } from "@/lib/ocorrencias";

export function ColarMensagemDialog({
  onSubmit,
}: {
  onSubmit: (condominioId: string, texto: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [condominio, setCondominio] = useState<string>("");
  const [texto, setTexto] = useState("");
  const valido = condominio !== "" && texto.trim().length > 0;

  function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (!valido) return;
    onSubmit(condominio, texto.trim());
    setOpen(false);
    setCondominio("");
    setTexto("");
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="h-10 shrink-0">
          <ClipboardPaste />
          Colar Mensagem
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-[calc(100%-2rem)] rounded-xl sm:max-w-lg">
        <form onSubmit={enviar} className="grid gap-4">
          <DialogHeader className="text-left">
            <DialogTitle>Colar mensagem do WhatsApp</DialogTitle>
            <DialogDescription>
              Escolha o condomínio e cole o texto. A ocorrência entra na fila como Nova.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="condo-msg">Condomínio</Label>
            <Select value={condominio} onValueChange={setCondominio}>
              <SelectTrigger id="condo-msg" className="h-10">
                <SelectValue placeholder="Selecione o condomínio" />
              </SelectTrigger>
              <SelectContent>
                {CONDOMINIOS.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.nome}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="texto-msg">Mensagem</Label>
            <Textarea
              id="texto-msg"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              rows={7}
              placeholder={"[09:41] Maria (apto 204): Bom dia! Está saindo água do teto da garagem..."}
              className="resize-none font-mono text-[13px]"
            />
          </div>
          <DialogFooter className="flex-row gap-2 sm:justify-end">
            <Button type="button" variant="outline" className="flex-1 sm:flex-none" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" className="flex-1 sm:flex-none" disabled={!valido}>
              Criar ocorrência
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
