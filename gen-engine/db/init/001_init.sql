-- Phase 0 baseline schema for local development
-- Executed automatically by postgres image on first startup.

CREATE TABLE IF NOT EXISTS learners (
    learner_id UUID PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learner_mastery_scores (
    learner_id UUID NOT NULL,
    concept TEXT NOT NULL,
    mastery_score DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (mastery_score >= 0.0 AND mastery_score <= 1.0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (learner_id, concept),
    FOREIGN KEY (learner_id) REFERENCES learners(learner_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS learner_responses (
    response_id UUID PRIMARY KEY,
    learner_id UUID NOT NULL,
    concept TEXT,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (learner_id) REFERENCES learners(learner_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mastery_updated_at ON learner_mastery_scores(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_responses_created_at ON learner_responses(created_at DESC);
