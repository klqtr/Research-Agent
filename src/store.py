"""Small durable SQLite store; per-operation connections support concurrent readers."""
import json
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "library.sqlite3"
        with self.connect() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("CREATE TABLE IF NOT EXISTS papers (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            con.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, paper_id TEXT, vote INTEGER)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=20)

    def papers(self):
        with self.connect() as con:
            return [json.loads(row[0]) for row in con.execute("SELECT payload FROM papers ORDER BY rowid")]

    def get(self, paper_id):
        with self.connect() as con:
            row = con.execute("SELECT payload FROM papers WHERE id=?", (paper_id,)).fetchone()
        if row is None:
            raise KeyError("文献不存在")
        return json.loads(row[0])

    def put(self, paper):
        with self.connect() as con:
            con.execute("INSERT OR REPLACE INTO papers VALUES (?, ?)", (paper["id"], json.dumps(paper, ensure_ascii=False)))

    def delete(self, paper_id):
        # Preserve original PDF on disk to make an accidental library deletion recoverable.
        with self.connect() as con:
            con.execute("DELETE FROM papers WHERE id=?", (paper_id,))

    def feedback(self, paper_id, vote):
        self.get(paper_id)
        if vote not in (-1, 1):
            raise ValueError("反馈须为 -1 或 1")
        with self.connect() as con:
            con.execute("INSERT INTO feedback(paper_id,vote) VALUES (?,?)", (paper_id, vote))
