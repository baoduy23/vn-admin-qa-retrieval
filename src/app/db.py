"""SQLite lưu lịch sử truy vấn và đánh giá của người dùng (Quân).

Các bảng (theo lộ trình, thêm vài cột để làm thống kê):
    queries(id, time, question, refused, top_chunk_id, top_score, reason, n_parts, pipeline)
    feedback(query_id, rating, comment, time)      rating: 1 = hữu ích, -1 = chưa đúng

File mặc định là artifacts/app.db (thư mục artifacts không commit), muốn đổi thì đặt biến môi trường APP_DB.
Trên Streamlit Community Cloud ổ đĩa bị xoá mỗi lần app khởi động lại, nên lịch sử chỉ còn trong lần deploy đó.
"""
from __future__ import annotations

import datetime as dt
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src.data.split import ROOT

DB_PATH = Path(os.environ.get("APP_DB", ROOT / "artifacts/app.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS queries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    time         TEXT NOT NULL,
    question     TEXT NOT NULL,
    refused      INTEGER NOT NULL,
    top_chunk_id TEXT,
    top_score    REAL,
    reason       TEXT,
    n_parts      INTEGER DEFAULT 1,
    pipeline     TEXT
);
CREATE TABLE IF NOT EXISTS feedback (
    query_id INTEGER NOT NULL REFERENCES queries(id),
    rating   INTEGER NOT NULL CHECK (rating IN (-1, 1)),
    comment  TEXT,
    time     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feedback_query ON feedback(query_id);
"""


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


@contextmanager
def session(path=None):
    """Mở kết nối, xong thì commit rồi đóng luôn (Streamlit chạy lại script liên tục nên không giữ kết nối)."""
    con = connect(path)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def log_query(result: dict, path=None) -> int:
    """Ghi một lượt hỏi từ kết quả answer(), trả về id để gắn đánh giá."""
    top = next((p["chunk_id"] for p in result.get("parts", []) if p.get("chunk_id")), None)
    if top is None and result.get("sources"):
        top = result["sources"][0]["chunk_id"]          # câu bị từ chối vẫn ghi đoạn gần nhất để làm thống kê
    with session(path) as con:
        cur = con.execute(
            "INSERT INTO queries(time, question, refused, top_chunk_id, top_score, reason, n_parts, pipeline) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (now(), result["question"], int(result["refused"]), top, result.get("scores", {}).get("top1"),
             result.get("reason"), len(result.get("parts", [])) or 1, result.get("pipeline")))
        return cur.lastrowid


def save_feedback(query_id: int, rating: int, comment: str = "", path=None) -> None:
    """Mỗi câu hỏi chỉ giữ đánh giá mới nhất, bấm lại thì ghi đè."""
    with session(path) as con:
        con.execute("DELETE FROM feedback WHERE query_id = ?", (query_id,))
        con.execute("INSERT INTO feedback(query_id, rating, comment, time) VALUES (?, ?, ?, ?)",
                    (query_id, rating, comment.strip() or None, now()))


def history(limit: int = 500, path=None) -> list[dict]:
    with session(path) as con:
        rows = con.execute(
            "SELECT q.*, f.rating, f.comment FROM queries q LEFT JOIN feedback f ON f.query_id = q.id "
            "ORDER BY q.id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def summary(path=None) -> dict:
    with session(path) as con:
        r = con.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(refused), 0) refused, "
            "(SELECT COUNT(*) FROM feedback WHERE rating = 1) up, "
            "(SELECT COUNT(*) FROM feedback WHERE rating = -1) down FROM queries").fetchone()
    return dict(r)
