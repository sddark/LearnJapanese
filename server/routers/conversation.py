from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from server.database import get_db

router = APIRouter(prefix="/api/conversation", tags=["conversation"])


class StartRequest(BaseModel):
    topic: str = "daily life"


@router.post("/start")
def start_session(req: StartRequest):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO conversation_sessions (topic) VALUES (?)", (req.topic,)
        )
        return {"session_id": cur.lastrowid, "topic": req.topic}


@router.get("/{session_id}")
def get_session(session_id: int):
    with get_db() as conn:
        session = conn.execute(
            "SELECT * FROM conversation_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not session:
            raise HTTPException(404, "Session not found")
        turns = conn.execute(
            "SELECT * FROM conversation_turns WHERE session_id = ? ORDER BY turn_number",
            (session_id,),
        ).fetchall()
        return {**dict(session), "turns": [dict(t) for t in turns]}
