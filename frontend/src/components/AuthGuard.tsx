import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { CHAVE_SINDICO, obterSindico, type Sindico } from "@/lib/auth";
import { SindicoContext } from "./sindico-context";

export function AuthGuard({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [sindico, setSindico] = useState<Sindico | null>(
    () => queryClient.getQueryData<Sindico>(CHAVE_SINDICO) ?? null,
  );

  useEffect(() => {
    let ativo = true;

    const expirar = () => {
      if (!ativo) return;
      setSindico(null);
      queryClient.clear();
      void navigate({ to: "/login" });
    };
    window.addEventListener("triagem-sessao-expirada", expirar);
    if (!queryClient.getQueryData(CHAVE_SINDICO)) {
      obterSindico()
        .then((perfil) => {
          if (ativo) {
            queryClient.setQueryData(CHAVE_SINDICO, perfil);
            setSindico(perfil);
          }
        })
        .catch(expirar);
    }

    return () => {
      ativo = false;
      window.removeEventListener("triagem-sessao-expirada", expirar);
    };
  }, [navigate, queryClient]);

  if (!sindico) {
    return <div className="flex min-h-screen items-center justify-center">Validando sessão...</div>;
  }

  return <SindicoContext.Provider value={sindico}>{children}</SindicoContext.Provider>;
}
