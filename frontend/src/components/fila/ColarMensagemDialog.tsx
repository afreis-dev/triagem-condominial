import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
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
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { mascaraCelular } from "@/lib/chamado";
import { buscarCondominiosDaCarteira, salvarMensagemColada } from "@/lib/colar-mensagem-api";

export function ColarMensagemDialog({
  aoSalvar,
}: {
  aoSalvar: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [condominio, setCondominio] = useState<string>("");
  const [texto, setTexto] = useState("");
  const [nome, setNome] = useState("");
  const [celular, setCelular] = useState("");
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const condominios = useQuery({
    queryKey: ["condominios-da-carteira"],
    queryFn: ({ signal }) => buscarCondominiosDaCarteira(signal),
    enabled: open,
    retry: false,
  });

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (salvando) return;
    if (!condominio) return setErro("Escolha o condomínio");
    if (!texto.trim()) return setErro("Descreva a ocorrência");
    if (Array.from(texto).length > 2000) return setErro("A descrição deve ter no máximo 2000 caracteres");
    setErro("");
    setSalvando(true);
    try {
      await salvarMensagemColada({ condominioId: Number(condominio), descricao: texto, nome, celular });
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível salvar a ocorrência.");
      return;
    } finally {
      setSalvando(false);
    }
    setOpen(false);
    setCondominio("");
    setTexto("");
    setNome("");
    setCelular("");
    aoSalvar();
  }

  return (
    <Dialog open={open} onOpenChange={(aberto) => {
      if (salvando) return;
      setErro("");
      setOpen(aberto);
    }}>
      <DialogTrigger asChild>
        <Button className="h-10 shrink-0">
          <ClipboardPaste />
          Colar mensagem
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[calc(100dvh-2rem)] max-w-[calc(100%-2rem)] overflow-y-auto rounded-xl sm:max-w-lg">
        <form onSubmit={enviar} className="grid gap-4">
          <DialogHeader className="text-left">
            <DialogTitle>Colar mensagem do WhatsApp</DialogTitle>
            <DialogDescription>
              Escolha o condomínio e cole o texto. A ocorrência entra na fila como Nova.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="condo-msg">Condomínio <span aria-hidden="true" className="text-destructive">*</span></Label>
            <select
              id="condo-msg"
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={condominio}
              onChange={(e) => { setCondominio(e.target.value); setErro(""); }}
              disabled={salvando || condominios.isFetching}
              aria-required="true"
            >
              <option value="">{condominios.isFetching ? "Carregando condomínios…" : "Selecione o condomínio"}</option>
              {condominios.data?.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
            {condominios.isError && <p role="alert">{condominios.error.message}</p>}
            {condominios.data?.length === 0 && <p className="text-sm">Nenhum condomínio na carteira.</p>}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="texto-msg">Mensagem <span aria-hidden="true" className="text-destructive">*</span></Label>
            <Textarea
              id="texto-msg"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              disabled={salvando}
              aria-required="true"
              rows={7}
              placeholder={"[09:41] Maria (apto 204): Bom dia! Está saindo água do teto da garagem..."}
              className="resize-none font-mono text-[13px]"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="nome-msg">Nome (opcional)</Label>
            <Input id="nome-msg" value={nome} onChange={(e) => setNome(e.target.value)} disabled={salvando} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="celular-msg">Celular (opcional)</Label>
            <Input
              id="celular-msg"
              type="tel"
              autoComplete="tel-national"
              placeholder="(11) 91234-5678"
              value={celular}
              onChange={(e) => setCelular(mascaraCelular(e.target.value))}
              disabled={salvando}
            />
          </div>
          {erro && <p role="alert" className="text-sm text-destructive">{erro}</p>}
          <DialogFooter className="flex-row gap-2 sm:justify-end">
            <Button type="button" variant="outline" className="flex-1 sm:flex-none" disabled={salvando} onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" className="flex-1 sm:flex-none" disabled={salvando}>
              {salvando ? "Salvando…" : "Salvar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
