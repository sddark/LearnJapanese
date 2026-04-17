from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import jaconv
from server.database import get_db
from server.services.srs import sm2_update, next_review_date, status_after

router = APIRouter(prefix="/api/kana", tags=["kana"])


class AnswerRequest(BaseModel):
    kana_id: int
    transcript: str


@router.get("/next")
def get_next_kana():
    """Return the next kana due for review, then unknown, then done."""
    with get_db() as conn:
        today = date.today().isoformat()
        row = conn.execute(
            "SELECT * FROM kana WHERE next_review <= ? ORDER BY next_review ASC LIMIT 1",
            (today,),
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT * FROM kana WHERE status = 'unknown' ORDER BY id ASC LIMIT 1"
            ).fetchone()
        if not row:
            return {"done": True}
        return dict(row)


@router.get("/stats")
def get_kana_stats():
    """Return counts per kana_type and status."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT kana_type, status, COUNT(*) as cnt FROM kana GROUP BY kana_type, status"
        ).fetchall()
        stats = {"hiragana": {}, "katakana": {}}
        for row in rows:
            stats[row["kana_type"]][row["status"]] = row["cnt"]
        return stats


@router.post("/answer")
def submit_answer(req: AnswerRequest):
    """Check user's spoken transcript against the kana's romaji, update SRS."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM kana WHERE id = ?", (req.kana_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Kana not found")

        expected_romaji = row["romaji"].lower()
        transcript_clean = req.transcript.strip().lower()

        # Normalize transcript to hiragana so "カ" and "か" both match か
        transcript_hira = jaconv.kata2hira(transcript_clean)
        expected_char = jaconv.kata2hira(row["character"])

        correct = (
            transcript_clean == expected_romaji
            or transcript_hira == expected_char
            or transcript_hira == expected_romaji
        )

        grade = 4 if correct else 1
        ease, interval, reps = sm2_update(
            row["ease_factor"], row["interval_days"], row["rep_count"], grade
        )
        new_status = status_after(row["status"], interval, correct)

        conn.execute(
            """
            UPDATE kana SET
                ease_factor   = ?,
                interval_days = ?,
                rep_count     = ?,
                correct_count = correct_count + ?,
                total_count   = total_count + 1,
                status        = ?,
                next_review   = ?,
                last_reviewed = datetime('now')
            WHERE id = ?
            """,
            (ease, interval, reps, 1 if correct else 0, new_status, next_review_date(interval), req.kana_id),
        )

        return {
            "correct": correct,
            "expected": expected_romaji,
            "transcript": transcript_clean,
            "new_status": new_status,
            "interval_days": interval,
        }
