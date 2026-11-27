import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff } from "lucide-react";
import { CHAVE_SINDICO, entrar } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [identificador, setIdentificador] = useState("");
  const [senha, setSenha] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [errosCampos, setErrosCampos] = useState<{ identificador: string | undefined; senha: string | undefined }>({ identificador: undefined, senha: undefined });
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro("");
    const erros = {
      identificador: identificador.trim() ? undefined : "Informe o e-mail ou celular.",
      senha: senha ? undefined : "Informe a senha.",
    };
    setErrosCampos(erros);
    if (erros.identificador || erros.senha) return;
    setCarregando(true);

    try {
      const sindico = await entrar(identificador.trim(), senha);
      queryClient.clear();
      queryClient.setQueryData(CHAVE_SINDICO, sindico);
      await navigate({ to: "/fila", search: {} });
    } catch (erro) {
      setErro(erro instanceof Error ? erro.message : "Erro ao realizar login.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4">
      <form
        onSubmit={enviar}
        noValidate
        className="w-full max-w-sm space-y-5 rounded-xl border bg-card p-8 shadow-sm"
      >
        <div>
          <h1 className="text-2xl font-semibold">Painel do Síndico</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Entre com suas credenciais para acessar as ocorrências.
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="identificador">E-mail ou celular</Label>
          <Input
            id="identificador"
            type="text"
            autoComplete="username"
            value={identificador}
            onChange={(e) => { setIdentificador(e.target.value); setErrosCampos((anterior) => ({ ...anterior, identificador: undefined })); }}
            aria-invalid={Boolean(errosCampos.identificador)}
            aria-describedby={errosCampos.identificador ? "identificador-erro" : undefined}
          />
          {errosCampos.identificador && <p id="identificador-erro" className="text-sm text-destructive">{errosCampos.identificador}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="senha">Senha</Label>
          <div className="relative">
            <Input
              id="senha"
              type={mostrarSenha ? "text" : "password"}
              className="pr-10"
              autoComplete="current-password"
              value={senha}
              onChange={(e) => { setSenha(e.target.value); setErrosCampos((anterior) => ({ ...anterior, senha: undefined })); }}
              aria-invalid={Boolean(errosCampos.senha)}
              aria-describedby={errosCampos.senha ? "senha-erro" : undefined}
            />
            <button
              type="button"
              onClick={() => setMostrarSenha((atual) => !atual)}
              aria-label={mostrarSenha ? "Ocultar senha" : "Mostrar senha"}
              aria-pressed={mostrarSenha}
              className="absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-r-md text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              {mostrarSenha ? <EyeOff aria-hidden="true" size={18} /> : <Eye aria-hidden="true" size={18} />}
            </button>
          </div>
          {errosCampos.senha && <p id="senha-erro" className="text-sm text-destructive">{errosCampos.senha}</p>}
        </div>

        <a href="#" onClick={(evento) => evento.preventDefault()} className="inline-block text-sm text-primary underline-offset-4 hover:underline">Esqueci minha senha</a>

        {erro && (
          <p role="alert" className="text-sm text-destructive">
            {erro}
          </p>
        )}

        <Button className="w-full" type="submit" disabled={carregando}>
          {carregando ? "Entrando..." : "Entrar"}
        </Button>
      </form>
    </main>
  );
}
