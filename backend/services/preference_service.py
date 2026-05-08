"""Preference history service - queries and manages preference logs."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException


async def get_preference_history(db: AsyncSession, session_id: str, limit: int = 100) -> dict:
    """Retrieve preference history for a session."""
    try:
        # Clamp limit to reasonable range
        limit = max(1, min(limit, 1000))
        
        stmt = text("""
            SELECT id, session_id, chosen_format, pref_delta, created_at
            FROM preference_log
            WHERE session_id = :session_id
            ORDER BY created_at ASC
            LIMIT :limit
        """)
        
        result = await db.execute(stmt, {
            'session_id': session_id,
            'limit': limit
        })
        
        rows = result.fetchall()
        preferences = [
            {
                'id': row[0],
                'session_id': row[1],
                'chosen_format': row[2],
                'pref_delta': row[3],
                'created_at': row[4]
            }
            for row in rows
        ]
        
        return {
            'session_id': session_id,
            'preferences': preferences,
            'count': len(preferences)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve preference history: {str(e)}")
