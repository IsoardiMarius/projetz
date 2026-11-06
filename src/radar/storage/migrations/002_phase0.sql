-- Appartenance des marchés aux jeux de données de la Phase 0.
CREATE TABLE phase0_markets (
    condition_id TEXT PRIMARY KEY REFERENCES markets (condition_id) ON DELETE CASCADE,
    grp          TEXT NOT NULL CHECK (grp IN ('case', 'sample')),
    case_key     TEXT,
    CHECK ((grp = 'case') = (case_key IS NOT NULL))
);
