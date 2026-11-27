import { afterEach, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

it("autentica por cookie, envia CSRF na escrita e encerra a sessão", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(Response.json({ ok: true }))
    .mockResolvedValueOnce(Response.json({ id: 7, nome: "Ana", email: "ana@teste.com", csrfToken: "csrf-da-sessao" }))
    .mockResolvedValueOnce(Response.json({ ok: true }))
    .mockResolvedValueOnce(Response.json({ ok: true }));
  vi.stubGlobal("fetch", fetchMock);
  const { entrar, requisitarAutenticado, sair } = await import("./auth");

  await expect(entrar("ana@teste.com", "senha")).resolves.toEqual({
    id: 7, nome: "Ana", email: "ana@teste.com",
  });
  await requisitarAutenticado("/ocorrencias/1/prioridade", { method: "PATCH" });
  await sair();

  expect(fetchMock).toHaveBeenCalledTimes(4);
  expect(fetchMock.mock.calls[0]![1]).toMatchObject({ credentials: "include", method: "POST" });
  expect(fetchMock.mock.calls[1]![0]).toBe("http://localhost:8000/auth/me");
  const escrita = fetchMock.mock.calls[2]![1];
  expect(escrita.credentials).toBe("include");
  expect(escrita.headers.get("X-CSRF-Token")).toBe("csrf-da-sessao");
  expect(escrita.headers.has("Authorization")).toBe(false);
  expect(fetchMock.mock.calls[3]![0]).toBe("http://localhost:8000/auth/logout");
  expect(sessionStorage.getItem("triagem_token")).toBeNull();
});

it("sinaliza sessão expirada quando a API responde 401", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({}, { status: 401 })));
  const avisar = vi.fn();
  window.addEventListener("triagem-sessao-expirada", avisar, { once: true });
  const { requisitarAutenticado } = await import("./auth");

  await expect(requisitarAutenticado("/ocorrencias")).rejects.toThrow("Sessão inválida ou expirada");
  expect(avisar).toHaveBeenCalledOnce();
});
