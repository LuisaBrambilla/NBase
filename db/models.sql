-- ===============================
-- EXTENSÕES NECESSÁRIAS
-- ===============================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ===============================
-- TABELA PRINCIPAL
-- ===============================

CREATE TABLE IF NOT EXISTS norma (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    orgao TEXT NOT NULL DEFAULT 'ANA',
    tipo TEXT NOT NULL DEFAULT 'Resolução',

    numero INT NOT NULL,
    ano INT NOT NULL,
    data_publicacao DATE,

    titulo TEXT,
    ementa TEXT,
    assunto TEXT,

    origem TEXT NOT NULL CHECK (origem IN ('govbr', 'ocr', 'dou', 'dodf', 'manual')),
    status TEXT NOT NULL DEFAULT 'vigente'
        CHECK (status IN ('vigente', 'nao_vigente', 'vigente_alterado')),

    consolidado BOOLEAN NOT NULL DEFAULT FALSE,
    ignorar_estatisticas BOOLEAN NOT NULL DEFAULT FALSE,

    url_oficial TEXT,

    caminho_html TEXT,
    caminho_html_bruto TEXT,
    caminho_pdf TEXT,

    texto_busca TEXT,

    criado_em TIMESTAMP DEFAULT now(),
    atualizado_em TIMESTAMP DEFAULT now(),

    CONSTRAINT norma_unica UNIQUE (orgao, tipo, ano, numero, origem)
);

-- ===============================
-- ÍNDICES
-- ===============================

CREATE INDEX IF NOT EXISTS idx_norma_numero_ano
ON norma (ano, numero);

CREATE INDEX IF NOT EXISTS idx_norma_data_publicacao
ON norma (data_publicacao);

CREATE INDEX IF NOT EXISTS idx_norma_status
ON norma (status);

CREATE INDEX IF NOT EXISTS idx_norma_assunto
ON norma (assunto);

CREATE INDEX IF NOT EXISTS idx_norma_texto_busca
ON norma
USING GIN (texto_busca gin_trgm_ops);

-- ===============================
-- TABELA DE ADMINS
-- ===============================

CREATE TABLE IF NOT EXISTS admins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome TEXT,
    email TEXT NOT NULL,
    senha_hash TEXT NOT NULL,
    mfa_secret TEXT,
    mfa_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT now(),
    atualizado_em TIMESTAMP DEFAULT now(),
    CONSTRAINT admins_email_unico UNIQUE (email)
);

CREATE INDEX IF NOT EXISTS idx_admins_email
ON admins (email);

-- ===============================
-- TRIGGER DE ATUALIZAÇÃO
-- ===============================

CREATE OR REPLACE FUNCTION atualizar_data()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_atualizar_norma
BEFORE UPDATE ON norma
FOR EACH ROW
EXECUTE FUNCTION atualizar_data();