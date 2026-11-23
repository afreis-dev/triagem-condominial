import { Link, useNavigate } from "@tanstack/react-router";
import { Activity, ArrowRight, ChevronDown, LogOut, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { useTriage } from "./store";
export function AppHeader() {
  const { user, logout } = useTriage();
  const navigate = useNavigate();
  if (!user) return null;
  return (
    <>
      <header className="app-header">
        <Link to={user.role === "manager" ? "/" : "/morador"} className="brand">
          <span className="brand-icon">
            <Activity size={23} />
          </span>
          <span>
            Triagem <span className="brand-light">do Síndico</span>
          </span>
        </Link>
        <DropdownMenu>
          <DropdownMenuTrigger asChild><Button variant="ghost" className="user-menu">{user.name}<ChevronDown /></Button></DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="shadow-none"><DropdownMenuItem className="min-h-11" onSelect={() => { logout(); void navigate({ to: "/login", replace: true }); }}><LogOut />Sair</DropdownMenuItem></DropdownMenuContent>
        </DropdownMenu>
      </header>
    </>
  );
}
export function UndoNotice() {
  const { undoInfo, undo, now } = useTriage();
  if (!undoInfo) return null;
  return (
    <div className="undo-notice" role="status">
      <div>
        <span>{undoInfo.count} chamados delegados</span>
        <Button variant="ghost" onClick={undo}>
          <RotateCcw />
          Desfazer
        </Button>
      </div>
      <progress
        max={10000}
        value={Math.max(0, undoInfo.expires - now)}
        aria-label="Tempo para desfazer"
      />
    </div>
  );
}
export function PageBack({ label = "Voltar à fila" }: { label?: string }) {
  return (
    <Button variant="ghost" asChild className="back-link">
      <Link to="/">
        <ArrowRight className="rotate-180" />
        {label}
      </Link>
    </Button>
  );
}
