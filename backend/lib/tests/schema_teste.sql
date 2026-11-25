CREATE TABLE sindicos (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    celular TEXT,
    email TEXT,
    senha_hash TEXT
);

CREATE TABLE condominios (
    id SERIAL PRIMARY KEY,
    identificador TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    bairro TEXT,
    sindico_id INTEGER REFERENCES sindicos (id)
);

CREATE TABLE ocorrencias (
    id SERIAL PRIMARY KEY,
    protocolo TEXT NOT NULL UNIQUE,
    condominio_id INTEGER NOT NULL REFERENCES condominios (id),
    origem TEXT NOT NULL,
    nome TEXT,
    apartamento TEXT,
    celular TEXT,
    local TEXT,
    descricao TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'nova',
    prioridade TEXT,
    categoria TEXT,
    responsavel_sugerido TEXT,
    motivo TEXT,
    travada BOOLEAN NOT NULL DEFAULT FALSE,
    palavra_de_risco TEXT,
    fonte TEXT,
    criada_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    concluida_em TIMESTAMPTZ
);

CREATE TABLE registros_decisao (
    id SERIAL PRIMARY KEY,
    ocorrencia_id INTEGER NOT NULL REFERENCES ocorrencias (id),
    tipo TEXT NOT NULL,
    quem_decidiu TEXT NOT NULL,
    origem TEXT,
    prioridade_sugerida TEXT,
    prioridade_final TEXT,
    motivo TEXT,
    acao TEXT,
    responsavel TEXT,
    data_agendada DATE,
    nota TEXT,
    rebaixou_travada BOOLEAN NOT NULL DEFAULT FALSE,
    data_hora TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE FUNCTION recusar_alteracao_registro() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Registros de decisão não podem ser alterados ou apagados';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER registros_decisao_imutavel
    BEFORE UPDATE OR DELETE ON registros_decisao
    FOR EACH ROW EXECUTE FUNCTION recusar_alteracao_registro();
