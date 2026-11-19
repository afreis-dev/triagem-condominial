CREATE TABLE condominios (
  id TEXT PRIMARY KEY,
  nome TEXT NOT NULL
);

CREATE TABLE ocorrencias (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  texto_original TEXT NOT NULL,
  condominio_id TEXT NOT NULL REFERENCES condominios(id),
  nome_remetente TEXT,
  celular_remetente TEXT,
  origem TEXT DEFAULT 'WhatsApp, registrada pelo síndico',
  prioridade TEXT,
  categoria TEXT,
  responsavel_sugerido TEXT,
  motivo TEXT,
  status TEXT DEFAULT 'Nova',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS palavras_risco (
  palavra TEXT PRIMARY KEY,
  categoria TEXT NOT NULL
);

-- Tabela de histórico - H14
CREATE TABLE IF NOT EXISTS registros_decisao (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ocorrencia_id UUID NOT NULL REFERENCES ocorrencias(id) ON DELETE CASCADE,
  acao TEXT NOT NULL,
  nota TEXT NOT NULL,
  criado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Gatilho que recusa UPDATE e DELETE
CREATE OR REPLACE FUNCTION recusar_alteracao_registro()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'Registros de decisão não podem ser alterados ou apagados';
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_proibir_update_registros ON registros_decisao;
DROP TRIGGER IF EXISTS trg_proibir_delete_registros ON registros_decisao;

CREATE TRIGGER trg_proibir_update_registros
BEFORE UPDATE ON registros_decisao
FOR EACH ROW EXECUTE FUNCTION recusar_alteracao_registro();

CREATE TRIGGER trg_proibir_delete_registros
BEFORE DELETE ON registros_decisao
FOR EACH ROW EXECUTE FUNCTION recusar_alteracao_registro();