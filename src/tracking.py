"""Opt-in, bounded arXiv tracking with persistent leases and real snapshot history."""
import asyncio
import contextlib
import logging
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from .tools import recommend_results, search_arxiv


def utcnow():
    return datetime.now(timezone.utc)


def stamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


class WatchRepository:
    def __init__(self, store):
        self.store = store
        with self.connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS watches (
                id INTEGER PRIMARY KEY, query TEXT NOT NULL UNIQUE, interval_minutes INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 0, refresh_limit INTEGER NOT NULL, runs_count INTEGER NOT NULL DEFAULT 0,
                next_due_at TEXT NOT NULL, lease_until TEXT, last_started_at TEXT, last_success_at TEXT,
                last_error TEXT, disabled_reason TEXT, created_at TEXT NOT NULL)""")
            con.execute("""CREATE TABLE IF NOT EXISTS watch_runs (
                id INTEGER PRIMARY KEY, watch_id INTEGER NOT NULL, started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL, status TEXT NOT NULL, new_count INTEGER NOT NULL,
                results TEXT NOT NULL, error TEXT)""")
            if "trigger_kind" not in {row["name"] for row in con.execute("PRAGMA table_info(watch_runs)")}:
                con.execute("ALTER TABLE watch_runs ADD COLUMN trigger_kind TEXT NOT NULL DEFAULT 'unspecified'")
            con.execute("CREATE TABLE IF NOT EXISTS watch_seen(watch_id INTEGER NOT NULL, source_key TEXT NOT NULL, PRIMARY KEY(watch_id, source_key))")

    def connect(self):
        con = self.store.connect()
        con.row_factory = sqlite3.Row
        return con

    def get(self, watch_id):
        with self.connect() as con:
            row = con.execute("SELECT * FROM watches WHERE id=?", (watch_id,)).fetchone()
        if row is None:
            raise KeyError("追踪条目不存在")
        return dict(row)

    def list(self):
        with self.connect() as con:
            return [dict(row) for row in con.execute("SELECT * FROM watches ORDER BY id")]

    def create(self, query, interval_minutes=60, enabled=False, refresh_limit=48, now=None):
        query = query.strip()
        if not 1 <= len(query) <= 300 or not 30 <= interval_minutes <= 1440 or not 1 <= refresh_limit <= 48:
            raise ValueError("追踪词1–300字符，间隔30–1440分钟，最多1–48次刷新")
        at = stamp(now or utcnow())
        with self.connect() as con:
            if con.execute("SELECT COUNT(*) FROM watches").fetchone()[0] >= 10:
                raise ValueError("本地追踪最多10个主题并保留历史，暂不支持增加更多主题")
            try:
                cursor = con.execute("INSERT INTO watches(query,interval_minutes,enabled,refresh_limit,next_due_at,created_at) VALUES (?,?,?,?,?,?)",
                                     (query, interval_minutes, int(enabled), refresh_limit, at, at))
            except sqlite3.IntegrityError as exc:
                raise ValueError("此检索主题已存在，请修改现有追踪") from exc
            identifier = cursor.lastrowid
        return self.get(identifier)

    def update(self, watch_id, enabled, interval_minutes=None, refresh_limit=None, now=None):
        current = self.get(watch_id)
        interval = interval_minutes if interval_minutes is not None else current["interval_minutes"]
        limit = refresh_limit if refresh_limit is not None else current["refresh_limit"]
        if not 30 <= interval <= 1440 or not max(1, current["runs_count"]) <= limit <= 48:
            raise ValueError("间隔或刷新上限无效；上限不得小于已执行次数")
        if enabled and current["runs_count"] >= limit:
            raise ValueError("刷新额度已用完，请显式提高上限（最多48次）")
        with self.connect() as con:
            con.execute("UPDATE watches SET enabled=?,interval_minutes=?,refresh_limit=?,next_due_at=?,disabled_reason=NULL WHERE id=?",
                        (int(enabled), interval, limit, stamp(now or utcnow()), watch_id))
        return self.get(watch_id)

    def claim(self, watch_id, now, force=False):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM watches WHERE id=?", (watch_id,)).fetchone()
            if row is None:
                raise KeyError("追踪条目不存在")
            row = dict(row)
            if row["lease_until"] and row["lease_until"] > stamp(now):
                raise ValueError("此条目正在刷新，未重复调用")
            if row["runs_count"] >= row["refresh_limit"]:
                raise ValueError("此条目已到显式刷新上限")
            if row["last_started_at"] and row["last_started_at"] > stamp(now - timedelta(seconds=60)):
                raise ValueError("刷新间隔过短，请至少等待60秒")
            if not force and (not row["enabled"] or row["next_due_at"] > stamp(now)):
                raise ValueError("条目未启用或尚未到刷新时间")
            con.execute("UPDATE watches SET lease_until=?,last_started_at=? WHERE id=?",
                        (stamp(now + timedelta(minutes=2)), stamp(now), watch_id))
        return row

    def finish(self, watch, started, finished, results, error=None, trigger_kind="unspecified"):
        new = []
        with self.connect() as con:
            if error is None:
                for result in results:
                    # Versions remain distinct, so a new arXiv revision can be surfaced.
                    identity = re.sub(r"^https?://", "", result.get("url", "")) or hashlib.sha256(result["title"].encode()).hexdigest()
                    cursor = con.execute("INSERT OR IGNORE INTO watch_seen VALUES (?,?)", (watch["id"], identity))
                    result["is_new_to_watch"] = bool(cursor.rowcount)
                    if cursor.rowcount:
                        new.append(identity)
            con.execute("INSERT INTO watch_runs(watch_id,started_at,finished_at,status,new_count,results,error,trigger_kind) VALUES (?,?,?,?,?,?,?,?)",
                        (watch["id"], stamp(started), stamp(finished), "failed" if error else "completed", len(new), json.dumps(results, ensure_ascii=False), error, trigger_kind))
            con.execute("""UPDATE watches SET lease_until=NULL,runs_count=runs_count+1,next_due_at=?,
                last_success_at=CASE WHEN ? IS NULL THEN ? ELSE last_success_at END,last_error=?,
                enabled=CASE WHEN runs_count+1>=refresh_limit THEN 0 ELSE enabled END,
                disabled_reason=CASE WHEN runs_count+1>=refresh_limit THEN 'refresh_limit_reached' ELSE disabled_reason END
                WHERE id=?""", (stamp(finished + timedelta(minutes=watch["interval_minutes"])), error, stamp(finished), error, watch["id"]))
        return {"watch_id": watch["id"], "status": "failed" if error else "completed", "new_count": len(new),
                "results": results, "error": error, "finished_at": stamp(finished)}

    def runs(self, watch_id, limit=10):
        self.get(watch_id)
        with self.connect() as con:
            rows = con.execute("SELECT * FROM watch_runs WHERE watch_id=? ORDER BY id DESC LIMIT ?", (watch_id, min(max(limit, 1), 30))).fetchall()
        return [{**dict(row), "results": json.loads(row["results"])} for row in rows]


class WatchService:
    def __init__(self, store, search=None, clock=None):
        self.store = store
        self.repo = WatchRepository(store)
        self.search = search or search_arxiv
        self.clock = clock or utcnow

    def refresh(self, watch_id, force=False):
        start = self.clock()
        watch = self.repo.claim(watch_id, start, force)
        try:
            result = recommend_results(watch["query"], self.search(watch["query"], 5), self.store.papers(), self.store.preference_profile())
            error = None
        except Exception as exc:
            result, error = [], f"{type(exc).__name__}: refresh failed; see source service availability"
        return self.repo.finish(watch, start, self.clock(), result, error, "manual" if force else "scheduled")

    def tick(self):
        now = self.clock()
        due = [row for row in self.repo.list() if row["enabled"] and row["next_due_at"] <= stamp(now)
               and (not row["lease_until"] or row["lease_until"] <= stamp(now))]
        results = []
        for row in due[:2]:
            try:
                results.append(self.refresh(row["id"]))
            except ValueError:
                continue  # Another worker/manual request may already hold the lease.
        return results


async def watch_loop(service):
    # No watches are created or enabled on startup. An empty/disabled list never
    # causes a network call. Each activation has an explicit <=48 refresh budget.
    while True:
        try:
            await asyncio.to_thread(service.tick)
        except Exception as exc:
            logging.warning("Tracking scheduler iteration failed: %s", type(exc).__name__)
        await asyncio.sleep(60)
