INSERT INTO condominios VALUES 
('aurora', 'Residencial Aurora'),
('vista-verde', 'Edifício Vista Verde'),
('palmeiras', 'Condomínio Jardim das Palmeiras')
ON CONFLICT (id) DO NOTHING;

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