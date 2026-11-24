import { describe, expect, it } from "vitest";
import {
  gerarProtocolo,
  mascaraCelular,
  nomeDoIdentificador,
  validarChamado,
  type ChamadoForm,
} from "./chamado";

const base: ChamadoForm = {
  perfil: "morador",
  nome: "Maria Souza",
  apartamento: "204",
  celular: "(11) 91234-5678",
  local: "",
  descricao: "Lâmpada queimada",
};

describe("formulário público do morador", () => {
  it("shows the condo name from the URL", () => {
    expect(nomeDoIdentificador("aurora")).toBe("Condomínio Aurora");
    expect(nomeDoIdentificador("residencial-jardim-aurora")).toBe("Residencial Jardim Aurora");
  });

  it("requires name, phone and description", () => {
    const e = validarChamado({ ...base, nome: " ", celular: "", descricao: "" });
    expect(Object.keys(e).sort()).toEqual(["celular", "descricao", "nome"]);
    expect(validarChamado({ ...base, descricao: "a".repeat(2000) }).descricao).toBeUndefined();
    expect(validarChamado({ ...base, descricao: "a".repeat(2001) }).descricao).toBe(
      "Máximo de 2000 caracteres",
    );
  });

  it("requires apartment for Morador and Proprietário", () => {
    expect(validarChamado({ ...base, apartamento: "" }).apartamento).toBeDefined();
    expect(validarChamado({ ...base, perfil: "proprietario", apartamento: "" }).apartamento).toBeDefined();
  });

  it("makes apartment optional for Funcionário", () => {
    expect(validarChamado({ ...base, perfil: "funcionario", apartamento: "" })).toEqual({});
  });

  it("accepts phones with 10 or 11 digits only", () => {
    expect(validarChamado({ ...base, celular: "1132345678" }).celular).toBeUndefined();
    expect(validarChamado({ ...base, celular: "11912345678" }).celular).toBeUndefined();
    expect(validarChamado({ ...base, celular: "119123456" }).celular).toBeDefined();
    expect(validarChamado({ ...base, celular: mascaraCelular("1191234567899") }).celular).toBe(
      "Informe um celular com DDD (10 ou 11 dígitos)",
    );
  });

  it("masks phone numbers", () => {
    expect(mascaraCelular("1132345678")).toBe("(11) 3234-5678");
    expect(mascaraCelular("11912345678")).toBe("(11) 91234-5678");
    expect(mascaraCelular("1191234567899")).toBe("1191234567899");
  });

  it("generates a PROT- protocol with 6 digits", () => {
    expect(gerarProtocolo(() => 0.123456)).toBe("PROT-123456");
    expect(gerarProtocolo()).toMatch(/^PROT-\d{6}$/);
  });
});
