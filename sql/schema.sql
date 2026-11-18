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