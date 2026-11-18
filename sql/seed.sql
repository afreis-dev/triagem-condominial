INSERT INTO condominios VALUES 
('aurora', 'Residencial Aurora'),
('vista-verde', 'Edifício Vista Verde'),
('palmeiras', 'Condomínio Jardim das Palmeiras')
ON CONFLICT (id) DO NOTHING;