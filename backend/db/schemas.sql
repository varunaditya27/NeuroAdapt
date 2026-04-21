CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS replay_buffer (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    state JSONB NOT NULL,
    action SMALLINT NOT NULL,
    reward FLOAT NOT NULL,
    next_state JSONB NOT NULL,
    done BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS preference_log (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    chosen_format TEXT NOT NULL,
    pref_delta FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);
