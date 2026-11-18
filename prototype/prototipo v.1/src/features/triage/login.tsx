import { useState, type FormEvent } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Activity, Eye, EyeOff, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { authenticateDemo, demoAccounts, formatIdentifier, LOGIN_MS } from "./demo-auth";
import { useTriage } from "./store";
type LoginErrors = { identifier?: string; password?: string; credentials?: string };

export function Login() {
  const { login } = useTriage();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<LoginErrors>({});
  const [forgot, setForgot] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const missing: LoginErrors = {};
    if (!identifier.trim()) missing.identifier = "Informe seu e-mail ou celular.";
    if (!password) missing.password = "Informe sua senha.";
    setErrors(missing);
    if (Object.keys(missing).length) return;
    setBusy(true);
    await new Promise((resolve) => setTimeout(resolve, LOGIN_MS));
    const user = authenticateDemo(identifier, password);
    setBusy(false);
    if (!user) { setErrors({ credentials: "E-mail, celular ou senha incorretos." }); return; }
    login(user);
    await navigate({ to: user.role === "manager" ? "/" : "/morador" });
  }
  return <main className="login-page">
    <div className="login-content">
      <header className="login-heading">
        <span className="brand-icon"><Activity size={23} /></span>
        <h1>Triagem <span className="brand-light">do Síndico</span></h1>
        <p className="muted">Seus chamados, na ordem certa.</p>
      </header>
      <form className="login-form" noValidate onSubmit={submit}>
        <label htmlFor="login-identifier">E-mail ou celular</label>
        <input id="login-identifier" autoComplete="username" value={identifier} disabled={busy} onChange={(e) => setIdentifier(formatIdentifier(e.target.value))} aria-invalid={Boolean(errors.identifier)} aria-describedby={errors.identifier ? "identifier-error" : undefined} />
        {errors.identifier && <span id="identifier-error" className="field-error">{errors.identifier}</span>}
        <label htmlFor="login-password">Senha</label>
        <div className="password-input">
          <input id="login-password" type={visible ? "text" : "password"} autoComplete="current-password" value={password} disabled={busy} onChange={(e) => setPassword(e.target.value)} aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? "password-error" : undefined} />
          <Button type="button" variant="ghost" size="icon" disabled={busy} onClick={() => setVisible(!visible)} aria-label={visible ? "Ocultar senha" : "Mostrar senha"} title={visible ? "Ocultar senha" : "Mostrar senha"}>{visible ? <EyeOff /> : <Eye />}</Button>
        </div>
        {errors.password && <span id="password-error" className="field-error">{errors.password}</span>}
        {errors.credentials && <p role="alert" className="field-error">{errors.credentials}</p>}
        <Button type="submit" className="w-full login-submit" disabled={busy}>{busy ? "Entrando..." : "Entrar"}{!busy && <ArrowRight />}</Button>
        <Button type="button" variant="link" className="forgot-password" onClick={() => setForgot(true)}>Esqueci minha senha</Button>
        {forgot && <p role="status" className="login-notice">Na versão final, você receberá um link para criar uma nova senha.</p>}
      </form>
      <section className="demo-access" aria-label="Acesso de demonstração">
        <h2>Acesso de demonstração</h2>
        {demoAccounts.map((account) => <Button key={account.label} type="button" variant="ghost" disabled={busy} onClick={() => { setIdentifier(account.identifier); setPassword(account.password); setErrors({}); }}>
          <span><strong>{account.label}</strong><span>{account.identifier} · senha {account.password}</span></span><ArrowRight />
        </Button>)}
      </section>
    </div>
  </main>;
}