import sqlite3
import contextlib
from pathlib import Path
from server.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextlib.contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS kana (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                character     TEXT NOT NULL UNIQUE,
                romaji        TEXT NOT NULL,
                kana_type     TEXT NOT NULL CHECK(kana_type IN ('hiragana','katakana')),
                status        TEXT NOT NULL DEFAULT 'unknown'
                                  CHECK(status IN ('unknown','learning','known')),
                ease_factor   REAL NOT NULL DEFAULT 2.5,
                interval_days INTEGER NOT NULL DEFAULT 1,
                rep_count     INTEGER NOT NULL DEFAULT 0,
                correct_count INTEGER NOT NULL DEFAULT 0,
                total_count   INTEGER NOT NULL DEFAULT 0,
                next_review   TEXT,
                last_reviewed TEXT
            );

            CREATE TABLE IF NOT EXISTS words (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                word             TEXT NOT NULL,
                reading          TEXT NOT NULL,
                romaji           TEXT NOT NULL,
                meaning          TEXT NOT NULL,
                jlpt_level       TEXT NOT NULL DEFAULT 'N5',
                part_of_speech   TEXT,
                emoji            TEXT,
                example_sentence TEXT,
                example_meaning  TEXT,
                status           TEXT NOT NULL DEFAULT 'unknown'
                                     CHECK(status IN ('unknown','learning','known')),
                ease_factor      REAL NOT NULL DEFAULT 2.5,
                interval_days    INTEGER NOT NULL DEFAULT 1,
                rep_count        INTEGER NOT NULL DEFAULT 0,
                correct_count    INTEGER NOT NULL DEFAULT 0,
                total_count      INTEGER NOT NULL DEFAULT 0,
                next_review      TEXT,
                last_reviewed    TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_words_status ON words(status);
            CREATE INDEX IF NOT EXISTS idx_words_next_review ON words(next_review);
            CREATE INDEX IF NOT EXISTS idx_words_jlpt ON words(jlpt_level);
        """)
        _seed_kana(conn)
        _seed_words(conn)


def _seed_kana(conn: sqlite3.Connection):
    existing = conn.execute("SELECT COUNT(*) FROM kana").fetchone()[0]
    if existing > 0:
        return
    seed_file = Path(__file__).parent / "data" / "jlpt_n5_seed.sql"
    if seed_file.exists():
        conn.executescript(seed_file.read_text(encoding="utf-8"))


def _seed_words(conn: sqlite3.Connection):
    existing = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    if existing > 0:
        return
    seed_file = Path(__file__).parent / "data" / "jlpt_n5_words.sql"
    if seed_file.exists():
        conn.executescript(seed_file.read_text(encoding="utf-8"))
