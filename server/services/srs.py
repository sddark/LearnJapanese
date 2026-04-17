from datetime import date, timedelta


def sm2_update(ease: float, interval: int, reps: int, grade: int) -> tuple[float, int, int]:
    """
    SM-2 spaced repetition update.
    grade 0-2 = fail (resets), 3-5 = pass (advances interval).
    Returns (new_ease, new_interval, new_reps).
    """
    if grade < 3:
        reps = 0
        interval = 1
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ease)
        reps += 1

    ease = max(1.3, ease + 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
    return ease, interval, reps


def next_review_date(interval: int) -> str:
    return (date.today() + timedelta(days=interval)).isoformat()


def status_after(current_status: str, interval: int, correct: bool) -> str:
    if not correct:
        return "learning" if current_status != "unknown" else "unknown"
    if current_status == "unknown":
        return "learning"
    if interval > 21:
        return "known"
    return current_status
