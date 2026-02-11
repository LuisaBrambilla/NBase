ALTER TABLE norma
ADD COLUMN IF NOT EXISTS verificacao_status TEXT;

ALTER TABLE norma
ADD COLUMN IF NOT EXISTS verificacao_descricao TEXT;

ALTER TABLE norma
ADD COLUMN IF NOT EXISTS verificacao_em TIMESTAMP;

ALTER TABLE norma
ADD COLUMN IF NOT EXISTS verificacao_admin_id UUID;

CREATE INDEX IF NOT EXISTS idx_norma_verificacao_status
ON norma (verificacao_status);
