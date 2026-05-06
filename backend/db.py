import os
from typing import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./neuroadapt.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True,)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def ensure_schema() -> None:
    statements = [
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'sessions'
                  AND column_name = 'id'
                  AND data_type = 'uuid'
            ) THEN
                ALTER TABLE replay_buffer DROP CONSTRAINT IF EXISTS replay_buffer_session_id_fkey;
                ALTER TABLE preference_log DROP CONSTRAINT IF EXISTS preference_log_session_id_fkey;
                ALTER TABLE sessions ALTER COLUMN id DROP DEFAULT;
                ALTER TABLE sessions ALTER COLUMN id TYPE TEXT USING id::text;
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'replay_buffer'
                  AND column_name = 'session_id'
                  AND data_type = 'uuid'
            ) THEN
                ALTER TABLE replay_buffer ALTER COLUMN session_id TYPE TEXT USING session_id::text;
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'preference_log'
                  AND column_name = 'session_id'
                  AND data_type = 'uuid'
            ) THEN
                ALTER TABLE preference_log ALTER COLUMN session_id TYPE TEXT USING session_id::text;
            END IF;
        END $$;
        """,
        """
        CREATE TABLE IF NOT EXISTS state_snapshots (
            id BIGSERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            state JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS replay_buffer (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            state JSONB NOT NULL,
            action SMALLINT NOT NULL,
            reward FLOAT NOT NULL,
            next_state JSONB NOT NULL,
            done BOOLEAN DEFAULT false,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS preference_log (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            chosen_format TEXT NOT NULL,
            pref_delta FLOAT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_state_snapshots_session ON state_snapshots(session_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_replay_buffer_session ON replay_buffer(session_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_preference_log_session ON preference_log(session_id, created_at DESC)",
    ]
    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))
