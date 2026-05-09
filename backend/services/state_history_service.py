"""State history service - queries and manages state snapshots for analytics."""

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException


async def get_state_history(db: AsyncSession, session_id: str, limit: int = 100) -> dict:
    """Retrieve state history snapshots for a session."""
    try:
        # Clamp limit to reasonable range
        limit = max(1, min(limit, 1000))
        
        stmt = text("""
            SELECT id, session_id, state, created_at
            FROM state_snapshots
            WHERE session_id = :session_id
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        
        result = await db.execute(stmt, {
            'session_id': session_id,
            'limit': limit
        })
        
        rows = result.fetchall()
        snapshots = []
        
        for row in rows:
            state_data = row[2]
            # Parse JSON if stored as string
            if isinstance(state_data, str):
                try:
                    state_data = json.loads(state_data)
                except json.JSONDecodeError:
                    pass
            
            snapshots.append({
                'id': row[0],
                'session_id': row[1],
                'state': state_data,
                'created_at': row[3]
            })
        
        return {
            'session_id': session_id,
            'snapshots': snapshots,
            'total_count': len(snapshots),
            'limit': limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve state history: {str(e)}")
