-- Origine des fonds : pour chaque dépôt, l'adresse qui a réellement envoyé les fonds.
CREATE TABLE wallet_funders (
    wallet   TEXT NOT NULL,
    tx_hash  TEXT NOT NULL,
    funder   TEXT,              -- NULL si introuvable dans la transaction
    ts       TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (wallet, tx_hash)
);
CREATE INDEX wallet_funders_funder_idx ON wallet_funders (funder);
