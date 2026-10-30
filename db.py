import sqlite3
import time
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
conn.executescript(
    """
CREATE TABLE IF NOT EXISTS vacancies(
  rid INTEGER PRIMARY KEY AUTOINCREMENT,
  uid TEXT UNIQUE,
  source TEXT, title TEXT, company TEXT, url TEXT, text TEXT,
  score INTEGER, reason TEXT, letter TEXT,
  status TEXT DEFAULT 'new',
  created_at INTEGER, updated_at INTEGER
);
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);
"""
)
conn.commit()


def exists(uid: str) -> bool:
    return conn.execute("SELECT 1 FROM vacancies WHERE uid=?", (uid,)).fetchone() is not None


def add(v: dict, score: int, reason: str, status: str) -> int:
    now = int(time.time())
    cur = conn.execute(
        "INSERT OR IGNORE INTO vacancies(uid,source,title,company,url,text,score,reason,status,created_at,updated_at)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (v["uid"], v["source"], v["title"], v["company"], v["url"], v["text"], score, reason, status, now, now),
    )
    conn.commit()
    return cur.lastrowid


def get(rid: int):
    return conn.execute("SELECT * FROM vacancies WHERE rid=?", (rid,)).fetchone()


def set_status(rid: int, status: str):
    conn.execute("UPDATE vacancies SET status=?, updated_at=? WHERE rid=?", (status, int(time.time()), rid))
    conn.commit()


def set_letter(rid: int, letter: str):
    conn.execute("UPDATE vacancies SET letter=?, updated_at=? WHERE rid=?", (letter, int(time.time()), rid))
    conn.commit()


def count_today(status: str) -> int:
    since = int(time.time()) - 86400
    return conn.execute(
        "SELECT COUNT(*) FROM vacancies WHERE status=? AND updated_at>?", (status, since)
    ).fetchone()[0]


def stats() -> dict:
    rows = conn.execute("SELECT status, COUNT(*) c FROM vacancies GROUP BY status").fetchall()
    return {r["status"]: r["c"] for r in rows}


def kv_get(k: str, default=None):
    r = conn.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return r["v"] if r else default


def kv_set(k: str, v: str):
    conn.execute("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
    conn.commit()
