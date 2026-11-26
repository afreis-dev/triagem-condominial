INSERT INTO palavras_risco (palavra, categoria, prioridade, responsavel_sugerido, motivo, ordem) VALUES
('gás', 'seguranca_acesso', 'urgente', 'sindico', 'palavra de risco: gás', 1),
('cheiro de gás', 'seguranca_acesso', 'urgente', 'sindico', 'palavra de risco: gás', 2),
('fogo', 'seguranca_acesso', 'urgente', 'sindico', 'palavra de risco: fogo', 3),
('incêndio', 'seguranca_acesso', 'urgente', 'sindico', 'palavra de risco: incêndio', 4),
('fumaça', 'seguranca_acesso', 'urgente', 'sindico', 'palavra de risco: fumaça', 5),
('preso no elevador', 'seguranca_acesso', 'urgente', 'sindico', 'palavra de risco: preso no elevador', 6),
('alagamento', 'manutencao', 'urgente', 'sindico', 'palavra de risco: alagamento', 7),
('desabamento', 'manutencao', 'urgente', 'sindico', 'palavra de risco: desabamento', 8),
('trinca na estrutura', 'manutencao', 'urgente', 'sindico', 'palavra de risco: trinca na estrutura', 9),
('choque', 'manutencao', 'urgente', 'sindico', 'palavra de risco: choque', 10),
('fio exposto', 'manutencao', 'urgente', 'sindico', 'palavra de risco: fio exposto', 11),
('agressão', 'convivencia', 'urgente', 'sindico', 'palavra de risco: agressão', 12)
ON CONFLICT (palavra) DO NOTHING;