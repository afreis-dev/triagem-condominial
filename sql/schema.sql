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

INSERT INTO palavras_risco (palavra, categoria) VALUES
('gás', 'manutencao'),
('cheiro de gás', 'manutencao'),
('fogo', 'seguranca_acesso'),
('incêndio', 'seguranca_acesso'),
('fumaça', 'seguranca_acesso'),
('preso no elevador', 'manutencao'),
('alagamento', 'manutencao'),
('desabamento', 'manutencao'),
('trinca na estrutura', 'manutencao'),
('choque', 'manutencao'),
('fio exposto', 'manutencao'),
('agressão', 'seguranca_acesso')
ON CONFLICT (palavra) DO NOTHING;