import random
from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import jaconv
from server.database import get_db
from server.services.srs import sm2_update, next_review_date, status_after

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


class AnswerRequest(BaseModel):
    word_id: int
    correct: bool
    transcript: str = ""


def _pick_distractors(conn, exclude_id: int, count: int = 3) -> list[dict]:
    rows = conn.execute(
        "SELECT id, word FROM words WHERE id != ? ORDER BY RANDOM() LIMIT ?",
        (exclude_id, count),
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/next")
def get_next_word():
    today = date.today().isoformat()
    with get_db() as conn:
        # Priority 1: due for review
        row = conn.execute(
            "SELECT * FROM words WHERE next_review <= ? ORDER BY next_review ASC LIMIT 1",
            (today,),
        ).fetchone()
        # Priority 2: unseen unknown
        if not row:
            row = conn.execute(
                "SELECT * FROM words WHERE status = 'unknown' AND next_review IS NULL ORDER BY id ASC LIMIT 1"
            ).fetchone()
        if not row:
            return {"done": True}

        word = dict(row)
        mode = "choice" if word["status"] == "unknown" else "speak"

        if mode == "choice":
            distractors = _pick_distractors(conn, word["id"])
            choices = [{"id": word["id"], "word": word["word"]}] + distractors
            random.shuffle(choices)
            word["choices"] = choices

        word["mode"] = mode
        return word


@router.post("/answer")
def submit_answer(req: AnswerRequest):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM words WHERE id = ?", (req.word_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Word not found")

        correct = req.correct
        if req.transcript:
            expected_romaji = row["romaji"].lower()
            transcript_clean = req.transcript.strip().lower()
            transcript_hira = jaconv.kata2hira(transcript_clean)
            expected_hira = jaconv.kata2hira(row["reading"])
            correct = (
                transcript_clean == expected_romaji
                or transcript_hira == expected_hira
                or transcript_hira == expected_romaji
            )

        grade = 4 if correct else 1
        ease, interval, reps = sm2_update(
            row["ease_factor"], row["interval_days"], row["rep_count"], grade
        )
        new_status = status_after(row["status"], interval, correct)

        conn.execute(
            """
            UPDATE words SET
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
            (ease, interval, reps, 1 if correct else 0, new_status, next_review_date(interval), req.word_id),
        )

        return {
            "correct": correct,
            "word": row["word"],
            "reading": row["reading"],
            "new_status": new_status,
            "interval_days": interval,
        }
