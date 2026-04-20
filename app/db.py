import sqlite3
from datetime import datetime, timezone


def _conn(db_path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def init_db(db_path):
    with _conn(db_path) as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                rkey       TEXT UNIQUE NOT NULL,
                text       TEXT NOT NULL,
                service    TEXT DEFAULT 'claude-code',
                tags       TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_created_at ON notes(created_at DESC);
        """)


def insert_note(db_path, rkey, text, service="claude-code", tags="", created_at=None):
    if created_at is None:
        created_at = datetime.now(timezone.utc).isoformat()
    with _conn(db_path) as con:
        cur = con.execute(
            "INSERT OR IGNORE INTO notes (rkey, text, service, tags, created_at) VALUES (?,?,?,?,?)",
            (rkey, text, service, tags, created_at),
        )
        return cur.lastrowid


def fetch_notes(db_path):
    with _conn(db_path) as con:
        rows = con.execute(
            "SELECT rkey, text, service, tags, created_at FROM notes ORDER BY created_at DESC"
        ).fetchall()

    notes = []
    for r in rows:
        tags_list = [t.strip() for t in r["tags"].split(",") if t.strip()]
        notes.append({
            "rkey":      r["rkey"],
            "text":      r["text"],
            "service":   r["service"],
            "tags":      tags_list,
            "createdAt": r["created_at"],
        })
    return notes
