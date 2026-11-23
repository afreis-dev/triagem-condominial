-- Aplicar depois do schema.sql e, em ambiente de teste, depois do seed.sql.
BEGIN;

CREATE TABLE IF NOT EXISTS responsaveis (
  condominio_id TEXT NOT NULL REFERENCES condominios(id),
  papel TEXT NOT NULL,
  PRIMARY KEY (condominio_id, papel)
);

-- Papéis usados pelo classificador nos condomínios do seed.
INSERT INTO responsaveis (condominio_id, papel)
SELECT c.id, p.papel
FROM condominios c
CROSS JOIN (VALUES ('zelador'), ('portaria'), ('sindico')) AS p(papel)
WHERE c.id IN ('aurora', 'vista-verde', 'palmeiras')
ON CONFLICT DO NOTHING;

ALTER TABLE registros_decisao
  ADD COLUMN IF NOT EXISTS tipo TEXT,
  ADD COLUMN IF NOT EXISTS responsavel TEXT,
  ADD COLUMN IF NOT EXISTS data_agendada DATE,
  ADD COLUMN IF NOT EXISTS marca_acao TEXT;

COMMIT;
