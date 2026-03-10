-- Inclui origem 'arespcj' para resoluções da ARES-PCJ (Agência Reguladora PCJ)
ALTER TABLE norma
DROP CONSTRAINT IF EXISTS norma_origem_check;

ALTER TABLE norma
ADD CONSTRAINT norma_origem_check
CHECK (origem IN ('govbr', 'ocr', 'dou', 'dodf', 'manual', 'arespcj'));
