import { useState, type FormEvent } from "react";
import { Check, ChevronRight, Paperclip, Building2, ArrowLeft, LockKeyhole, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTriage } from "./store";
import { condos, stamp, statusDescriptions, type Status } from "./domain";
import { residentTickets } from "./demo-auth";
export function Resident() {
  const { tickets, user, addTicket } = useTriage();
  const [screen, setScreen] = useState<"list" | "form" | "receipt" | "track">("list");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const condo = user?.condo ?? 0;
  const [role, setRole] = useState("Morador");
  const [name, setName] = useState(user?.name ?? "");
  const [apartment, setApartment] = useState("");
  const [phone, setPhone] = useState("(11) 98765-4321");
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState<string>();
  const [photoName, setPhotoName] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const mine = user ? residentTickets(tickets, user) : [];
  const ticket = mine.find((t) => t.id === selectedId);
  function openForm() {
    setDescription(""); setLocation(""); setPhoto(undefined); setPhotoName(""); setErrors({}); setScreen("form");
  }
  function submit(e: FormEvent) {
    e.preventDefault();
    const missing: Record<string, string> = {};
    if (!phone.trim()) missing["phone"] = "Informe seu celular.";
    else if (phone.replace(/\D/g, "").length < 10) missing["phone"] = "Informe um celular com DDD.";
    if (!description.trim()) missing["description"] = "Descreva o problema.";
    setErrors(missing);
    if (Object.keys(missing).length) return;
    const id = addTicket(
      {
        title: description,
        condo,
        name,
        apartment,
        phone: user?.phone ?? phone,
        location,
        origin: "Link do condomínio",
        role,
        photo,
      },
      true,
    );
    setSelectedId(id);
    setScreen("receipt");
  }
  return (
    <main className="page resident-page">
      <div className="resident-condo">
        <Building2 size={22} />
        <div>
          <span className="eyebrow">CANAL DO CONDOMÍNIO</span>
          <h2>{ticket && screen !== "form" ? condos[ticket.condo] : condos[condo]}</h2>
        </div>
      </div>
      {screen === "list" ? (
        <section className="resident-list">
          <div className="page-heading"><div><h1>Meus chamados</h1><p className="muted">{mine.length} chamados registrados</p></div></div>
          <Button className="w-full" onClick={openForm}><Plus />Abrir novo chamado</Button>
          <div className="resident-ticket-list">
            {[...mine].sort((a, b) => b.arrived - a.arrived).map((item) => (
              <Button variant="outline" className="resident-ticket" key={item.id} onClick={() => { setSelectedId(item.id); setScreen("track"); }}>
                <span className="resident-ticket-content"><span className="resident-ticket-meta"><span className="mono">{item.id}</span><span className="status-badge">{item.status}</span></span><strong>{item.title}</strong><time className="mono muted">{stamp(item.arrived)}</time></span><ChevronRight />
              </Button>
            ))}
            {!mine.length && <p className="empty">Nenhum chamado registrado.</p>}
          </div>
        </section>
      ) : screen === "form" ? (
        <>
          <div className="page-heading">
            <div>
              <h1>Registrar chamado</h1>
              <p className="muted">O que precisa de atenção no condomínio?</p>
            </div>
          </div>
          <form onSubmit={submit} noValidate className="resident-form">
            <Button type="button" variant="ghost" className="back-link" onClick={() => setScreen("list")}><ArrowLeft />Voltar aos meus chamados</Button>
            <label>
              Condomínio
              <input value={condos[condo]} readOnly />
            </label>
            <fieldset>
              <legend>Quem está registrando?</legend>
              <div className="role-options">
                {["Morador", "Proprietário", "Funcionário"].map((r) => (
                  <Button
                    type="button"
                    variant="outline"
                    className={role === r ? "active" : ""}
                    onClick={() => setRole(r)}
                    key={r}
                  >
                    {r}
                  </Button>
                ))}
              </div>
            </fieldset>
            <div className="form-two">
              <label>
                Nome
                <input
                  placeholder="Seu nome"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
              <label>
                Apartamento {role === "Funcionário" && <span className="optional">(opcional)</span>}
                <input
                  placeholder="Ex.: 302"
                  value={apartment}
                  onChange={(e) => setApartment(e.target.value)}
                />
              </label>
            </div>
            <label>
              Celular <span className="required">*</span>
              <input
                type="tel"
                placeholder="(11) 99999-9999"
                aria-invalid={Boolean(errors["phone"])}
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                readOnly
              />
              {errors["phone"] && <span className="field-error">{errors["phone"]}</span>}
            </label>
            <label>
              Onde fica o problema? <span className="optional">(opcional)</span>
              <input
                placeholder="Ex.: garagem, bloco B, 2º andar"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </label>
            <label>
              Descrição <span className="required">*</span>
              <textarea
                rows={5}
                placeholder="Conte o que aconteceu e há quanto tempo."
                aria-invalid={Boolean(errors["description"])}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              {errors["description"] && (
                <span className="field-error">{errors["description"]}</span>
              )}
            </label>
            <label className="photo-upload">
              <Paperclip size={18} />
              {photoName || "Adicionar foto"}
              <span className="optional">(opcional)</span>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    if (photo) URL.revokeObjectURL(photo);
                    setPhoto(URL.createObjectURL(file));
                    setPhotoName(file.name);
                  }
                }}
              />
            </label>
            <p className="privacy">
              <LockKeyhole size={15} />
              Seu nome e celular serão usados apenas para atender este chamado.
            </p>
            <Button type="submit" className="w-full">
              Enviar chamado
              <ChevronRight />
            </Button>
          </form>
        </>
      ) : screen === "receipt" && ticket ? (
        <section className="receipt">
          <span className="receipt-check">
            <Check size={30} />
          </span>
          <h1>Chamado recebido</h1>
          <p className="muted">Seu registro foi enviado ao síndico.</p>
          <div className="receipt-protocol">
            <span>PROTOCOLO</span>
            <strong className="mono">{ticket.id}</strong>
            <time className="mono">{stamp(ticket.arrived)}</time>
          </div>
          <Button className="w-full" onClick={() => setScreen("track")}>
            Acompanhar meu chamado
            <ChevronRight />
          </Button>
          <Button
            variant="ghost"
            className="w-full mt-3"
            onClick={() => setScreen("list")}
          >
            Voltar aos meus chamados
          </Button>
        </section>
      ) : ticket ? (
        <section className="tracking">
          <Button variant="ghost" onClick={() => setScreen("list")} className="back-link">
            <ArrowLeft />
            Voltar aos meus chamados
          </Button>
          <div className="eyebrow">ACOMPANHAMENTO</div>
          <h1>Meu chamado</h1>
          <span className="mono tracking-protocol">{ticket.id}</span>
          <div className="tracking-current">
            <span className="status-badge">{ticket.status}</span>
            <p>{statusDescriptions[ticket.status]}</p>
          </div>
          <h2>{ticket.title}</h2>
          <p className="muted">
            {ticket.location || "Local não informado"} ·{" "}
            {ticket.apartment ? `Apto. ${ticket.apartment}` : ticket.role}
          </p>
          {ticket.photo && <img className="attachment" src={ticket.photo} alt="Foto do chamado" />}
          <section className="history">
            <h2>Atualizações do chamado</h2>
            <ol>
              {ticket.history
                .filter((e) => e.status)
                .map((e, i) => (
                  <li key={i}>
                    <span className="timeline-dot" />
                    <time className="mono">{stamp(e.at)}</time>
                    <h3>{e.status}</h3>
                    <p>{statusDescriptions[e.status as Status]}</p>
                  </li>
                ))}
            </ol>
          </section>
        </section>
      ) : null}
    </main>
  );
}
