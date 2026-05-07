CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS state_snapshots (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS replay_buffer (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    state JSONB NOT NULL,
    action SMALLINT NOT NULL,
    reward FLOAT NOT NULL,
    next_state JSONB NOT NULL,
    done BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS preference_log (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    chosen_format TEXT NOT NULL,
    pref_delta FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_state_snapshots_session ON state_snapshots(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_replay_buffer_session ON replay_buffer(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_preference_log_session ON preference_log(session_id, created_at DESC);
