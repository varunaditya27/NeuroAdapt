-- NeuroAdapt gen-engine local Postgres bootstrap
-- Safe to re-run: uses IF NOT EXISTS guards

CREATE TABLE IF NOT EXISTS learner_concept_mastery (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    learner_id TEXT,
    concept_key TEXT NOT NULL,
    mastery_score DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    confidence DOUBLE PRECISION,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, concept_key)
);

CREATE TABLE IF NOT EXISTS learner_analogy_preferences (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    selection_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, domain)
);

CREATE TABLE IF NOT EXISTS generation_events (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    action_id INTEGER NOT NULL,
    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
    fallback_used BOOLEAN NOT NULL DEFAULT FALSE,
    generation_time_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mastery_session ON learner_concept_mastery(session_id);
CREATE INDEX IF NOT EXISTS idx_generation_events_session ON generation_events(session_id);
