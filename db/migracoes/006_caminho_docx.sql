-- Coluna para armazenar caminho do arquivo Word (PDF convertido para .docx)
ALTER TABLE norma ADD COLUMN IF NOT EXISTS caminho_docx TEXT;
