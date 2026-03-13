-- Configuração de layout por cliente (Tecbis / ARES-PCJ). Replicada no banco normas_arespcj para o site isolado.
CREATE TABLE IF NOT EXISTS site_config (
    client TEXT PRIMARY KEY,
    logo_path TEXT,
    subtitle_visible BOOLEAN NOT NULL DEFAULT TRUE,
    site_name TEXT,
    login_query TEXT,
    theme_class TEXT,
    atualizado_em TIMESTAMP DEFAULT now()
);

INSERT INTO site_config (client, logo_path, subtitle_visible, site_name, login_query, theme_class) VALUES
    ('tecbis', NULL, TRUE, 'ANA', NULL, NULL),
    ('arespcj', 'logo_arespcj.png', FALSE, 'ARES-PCJ', 'client=arespcj', 'client-arespcj')
ON CONFLICT (client) DO NOTHING;
