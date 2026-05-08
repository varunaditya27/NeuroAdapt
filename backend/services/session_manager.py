"""Session management service - creates and tracks learning sessions."""

import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, text
from fastapi import HTTPException


async def create_session(db: AsyncSession, student_id: str) -> dict:
    """Create a new session for a student."""
    try:
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        # Insert into sessions table
        stmt = text("""
            INSERT INTO sessions (id, student_id, created_at)
            VALUES (:id, :student_id, :created_at)
        """)
        
        await db.execute(stmt, {
            'id': session_id,
            'student_id': student_id,
            'created_at': created_at
        })
        await db.commit()
        
        return {
            'session_id': session_id,
            'student_id': student_id,
            'created_at': created_at
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to initialize session: {str(e)}")


async def get_session(db: AsyncSession, session_id: str) -> dict | None:
    """Retrieve session metadata."""
    try:
        stmt = text("SELECT id, student_id, created_at FROM sessions WHERE id = :session_id")
        result = await db.execute(stmt, {'session_id': session_id})
        row = result.fetchone()
        
        if row:
            return {
                'session_id': row[0],
                'student_id': row[1],
                'created_at': row[2]
            }
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session: {str(e)}")
