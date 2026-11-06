-- Schéma initial : marchés, trades, profils de wallets.
-- Aucune donnée d'identité : uniquement des adresses pseudonymes et des transactions publiques.

CREATE TABLE markets (
    condition_id      TEXT PRIMARY KEY,
    market_id         TEXT NOT NULL,
    question          TEXT NOT NULL,
    slug              TEXT,
    group_item_title  TEXT,
    event_id          TEXT,
    event_slug        TEXT,
    tags              TEXT[] NOT NULL DEFAULT '{}',
    fee_type          TEXT,
    neg_risk          BOOLEAN NOT NULL DEFAULT FALSE,
    start_date        TIMESTAMPTZ,
    end_date          TIMESTAMPTZ,
    closed_time       TIMESTAMPTZ,
    closed            BOOLEAN NOT NULL,
    volume            DOUBLE PRECISION,
    resolution_status TEXT,
    outcomes          JSONB NOT NULL,   -- [{"token_id", "label", "final_price"}]
    winning_token_id  TEXT,
    fetched_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX markets_event_idx ON markets (event_id);

-- Toutes les exécutions d'un marché, vues de chaque côté (taker et makers).
-- Un marché est toujours collecté en entier puis remplacé : l'ingestion est idempotente.
CREATE TABLE trades (
    condition_id  TEXT NOT NULL REFERENCES markets (condition_id) ON DELETE CASCADE,
    seq           INTEGER NOT NULL,          -- rang chronologique dans le marché (0 = plus ancien)
    ts            TIMESTAMPTZ NOT NULL,      -- horodatage du bloc
    wallet        TEXT NOT NULL,
    token_id      TEXT NOT NULL,
    outcome_index SMALLINT,
    side          TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    size          DOUBLE PRECISION NOT NULL CHECK (size >= 0),
    price         DOUBLE PRECISION NOT NULL CHECK (price >= 0 AND price <= 1),
    is_taker      BOOLEAN NOT NULL,
    tx_hash       TEXT NOT NULL,
    PRIMARY KEY (condition_id, seq)
);
CREATE INDEX trades_wallet_ts_idx ON trades (wallet, ts);
CREATE INDEX trades_token_ts_idx ON trades (token_id, ts);

CREATE TABLE market_collections (
    condition_id  TEXT PRIMARY KEY REFERENCES markets (condition_id) ON DELETE CASCADE,
    collected_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    n_rows        INTEGER NOT NULL,
    n_taker_rows  INTEGER NOT NULL,
    n_unmatched_taker_rows INTEGER NOT NULL  -- lignes taker introuvables dans le flux complet (contrôle qualité)
);

-- Profil minimal d'un wallet : âge et dépôts, pour les signaux « compte neuf » et « financé juste avant ».
CREATE TABLE wallet_profiles (
    wallet             TEXT PRIMARY KEY,
    first_activity_ts  TIMESTAMPTZ,
    fetched_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE wallet_deposits (
    wallet    TEXT NOT NULL REFERENCES wallet_profiles (wallet) ON DELETE CASCADE,
    ts        TIMESTAMPTZ NOT NULL,
    usdc      DOUBLE PRECISION,
    tx_hash   TEXT NOT NULL,
    PRIMARY KEY (wallet, tx_hash, ts)
);
CREATE INDEX wallet_deposits_tx_idx ON wallet_deposits (tx_hash);
