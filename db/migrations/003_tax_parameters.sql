-- Paramètres des calculateurs (taux, seuils). Le LLM ne produit jamais de chiffre :
-- chaque valeur utilisée dans un calcul vient de cette table, avec l'extrait exact du
-- texte officiel qui la fonde, ce qui garde la règle "citations obligatoires".
-- Une valeur n'est utilisée que si validated_at est renseigné.
CREATE TABLE tax_parameters (
    id SERIAL PRIMARY KEY,
    calculator TEXT NOT NULL,
    key TEXT NOT NULL,
    value NUMERIC NOT NULL,
    unit TEXT NOT NULL CHECK (unit IN ('rate', 'TND')),
    valid_from DATE NOT NULL,
    valid_to DATE,
    document_id INTEGER REFERENCES documents(id),
    article TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    validated_by UUID,
    validated_at TIMESTAMPTZ,
    UNIQUE (calculator, key, valid_from)
);

-- Impôt sur la fortune, Art. 88 de la LF 2026 (applicable au 1er janvier 2026, Art. 110).
-- Lecture par tranches (0,5 % sur la part entre 3 et 5 MTND, 1 % sur la part au-delà)
-- confirmée par l'administrateur le 2026-09-25.
INSERT INTO tax_parameters
    (calculator, key, value, unit, valid_from, document_id, article, excerpt, validated_by, validated_at)
SELECT 'wealth_tax', p.key, p.value, p.unit, DATE '2026-01-01', d.id, 'Art. 88', p.excerpt,
       'bdcfa637-49bf-46f7-8653-3e94cf2b409d', now()
FROM documents d,
     (VALUES
        ('bracket_1_floor', 3000000, 'TND', '0,5% de la fortune dont la valeur varie de 3 millions de dinars à 5 millions de dinars.'),
        ('bracket_1_ceiling', 5000000, 'TND', '0,5% de la fortune dont la valeur varie de 3 millions de dinars à 5 millions de dinars.'),
        ('bracket_1_rate', 0.005, 'rate', '0,5% de la fortune dont la valeur varie de 3 millions de dinars à 5 millions de dinars.'),
        ('bracket_2_rate', 0.01, 'rate', '1% de la fortune dont la valeur est supérieure à 5 millions de dinars.')
     ) AS p(key, value, unit, excerpt)
WHERE d.source = 'Loi2025_17-1.pdf';
