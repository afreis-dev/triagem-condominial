import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "@tanstack/react-router";
import { obterSindico, sair } from "@/lib/auth";

export function AuthGuard({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [autenticado, setAutenticado] = useState(false);

  useEffect(() => {
    let ativo = true;

    obterSindico()
      .then(() => {
        if (ativo) setAutenticado(true);
      })
      .catch(() => {
        if (!ativo) return;
        sair();
        navigate({ to: "/login" });
      });

    return () => {
      ativo = false;
    };
  }, [navigate]);

  if (!autenticado) {
    return <div className="flex min-h-screen items-center justify-center">Validando sessão...</div>;
  }

  return <>{children}</>;
}
