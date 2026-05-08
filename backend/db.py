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
    """Create database schema for SQLite (local dev) and PostgreSQL (production)."""
    statements = [
        # Sessions table - NEW (was missing!)
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # State snapshots table
        """
        CREATE TABLE IF NOT EXISTS state_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            state TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Replay buffer table
        """
        CREATE TABLE IF NOT EXISTS replay_buffer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            state TEXT NOT NULL,
            action INTEGER NOT NULL,
            reward REAL NOT NULL,
            next_state TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Preference log table
        """
        CREATE TABLE IF NOT EXISTS preference_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            chosen_format TEXT NOT NULL,
            pref_delta REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Lesson events table
        """
        CREATE TABLE IF NOT EXISTS lesson_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            subject TEXT,
            topic TEXT,
            duration_ms INTEGER,
            final_slide INTEGER,
            total_slides INTEGER,
            state TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Indices for performance
        "CREATE INDEX IF NOT EXISTS idx_state_snapshots_session ON state_snapshots(session_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_replay_buffer_session ON replay_buffer(session_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_preference_log_session ON preference_log(session_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_lesson_events_session ON lesson_events(session_id, created_at DESC)",
    ]
    async with engine.begin() as conn:
        for statement in statements:
            try:
                await conn.execute(text(statement))
            except Exception as e:
                # Log but don't fail on individual schema statements
                # (e.g., if a table already exists or if using different dialect)
                print(f"Schema statement skipped: {e}")
