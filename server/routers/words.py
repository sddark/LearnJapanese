from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from server.database import get_db

router = APIRouter(prefix="/api/words", tags=["words"])


class StatusUpdate(BaseModel):
    status: str


@router.get("")
def list_words(status: str | None = None, due: bool = False):
    from datetime import date
    with get_db() as conn:
        query = "SELECT * FROM words WHERE 1=1"
        params: list = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if due:
            today = date.today().isoformat()
            query += " AND (next_review <= ? OR next_review IS NULL)"
            params.append(today)
        query += " ORDER BY id"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.patch("/{word_id}/status")
def update_status(word_id: int, body: StatusUpdate):
    if body.status not in ("unknown", "learning", "known"):
        raise HTTPException(400, "Invalid status")
    with get_db() as conn:
        result = conn.execute(
            "UPDATE words SET status = ? WHERE id = ?", (body.status, word_id)
        )
        if result.rowcount == 0:
            raise HTTPException(404, "Word not found")
        return {"id": word_id, "status": body.status}
