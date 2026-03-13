-- Registo de auditoria: ações na plataforma (layout, normas, perfil, login).
-- Visível apenas no centro de dados Tecbis.

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    admin_id UUID REFERENCES admins(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    details JSONB,
    ip TEXT,
    client TEXT,
    admin_email TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_admin_id ON audit_log (admin_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log (action);

COMMENT ON TABLE audit_log IS 'Log de ações na plataforma admin (Tecbis: centro de dados).';
