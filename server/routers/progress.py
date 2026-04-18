from datetime import date, timedelta
from fastapi import APIRouter
from server.database import get_db

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/words")
def word_progress():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT jlpt_level, status, COUNT(*) as cnt FROM words GROUP BY jlpt_level, status"
        ).fetchall()
        result: dict = {}
        for row in rows:
            lvl = row["jlpt_level"]
            if lvl not in result:
                result[lvl] = {"unknown": 0, "learning": 0, "known": 0, "total": 0}
            result[lvl][row["status"]] += row["cnt"]
            result[lvl]["total"] += row["cnt"]
        return result


@router.get("/kana")
def kana_progress():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT kana_type, status, COUNT(*) as cnt FROM kana GROUP BY kana_type, status"
        ).fetchall()
        result: dict = {
            "hiragana": {"unknown": 0, "learning": 0, "known": 0, "total": 0},
            "katakana": {"unknown": 0, "learning": 0, "known": 0, "total": 0},
        }
        for row in rows:
            kt = row["kana_type"]
            result[kt][row["status"]] += row["cnt"]
            result[kt]["total"] += row["cnt"]
        return result


@router.get("/due")
def due_counts():
    today = date.today().isoformat()
    with get_db() as conn:
        words_due = conn.execute(
            "SELECT COUNT(*) FROM words WHERE next_review <= ? OR (status='unknown' AND next_review IS NULL)",
            (today,),
        ).fetchone()[0]
        kana_due = conn.execute(
            "SELECT COUNT(*) FROM kana WHERE next_review <= ? OR (status='unknown' AND next_review IS NULL)",
            (today,),
        ).fetchone()[0]
        return {"words": words_due, "kana": kana_due}


@router.get("/streak")
def streak():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT DISTINCT DATE(last_reviewed) as day
            FROM (
                SELECT last_reviewed FROM kana  WHERE last_reviewed IS NOT NULL
                UNION ALL
                SELECT last_reviewed FROM words WHERE last_reviewed IS NOT NULL
            )
            ORDER BY day DESC
        """).fetchall()

    days = [row["day"] for row in rows]
    if not days:
        return {"streak": 0}

    today = date.today()
    streak = 0
    expected = today
    for day_str in days:
        d = date.fromisoformat(day_str)
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif d == today and streak == 0:
            continue
        else:
            break

    return {"streak": streak}
