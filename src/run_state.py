"""Local durable workflow snapshots. No credentials, no automatic remote resume."""
import hashlib
import json
import re
import sqlite3
import uuid
import time
from contextlib import contextmanager
from datetime import datetime, timezone


def corpus_fingerprint(papers):
    return hashlib.sha256(json.dumps([{**{key:p.get(key) for key in ("id","title","arxiv_id","version","references","arxiv_metadata")},"chunks":[[c["id"],c["page"],c["text"]] for c in p.get("chunks",[])]} for p in sorted(papers,key=lambda p:p["id"])],ensure_ascii=False,sort_keys=True).encode()).hexdigest()


class RunJournal:
    def __init__(self,root):
        root.mkdir(parents=True,exist_ok=True);self.path=root/"research_runs.sqlite3"
        with sqlite3.connect(self.path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, updated_at TEXT, state TEXT)")
            connection.execute("CREATE TABLE IF NOT EXISTS run_leases (id TEXT PRIMARY KEY, owner TEXT, until REAL)")

    @contextmanager
    def claim(self,identifier,ttl=600):
        owner=uuid.uuid4().hex
        with sqlite3.connect(self.path,timeout=10) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row=connection.execute("SELECT until FROM run_leases WHERE id=?",(identifier,)).fetchone()
            if row and row[0]>time.time(): raise ValueError("此工作流仍在执行，不能并发恢复；崩溃租约过期后再试")
            connection.execute("INSERT OR REPLACE INTO run_leases VALUES (?,?,?)",(identifier,owner,time.time()+ttl))
        try: yield
        finally:
            with sqlite3.connect(self.path,timeout=10) as connection:
                connection.execute("DELETE FROM run_leases WHERE id=? AND owner=?",(identifier,owner))

    def save(self,state):
        state["updated_at"]=datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.path,timeout=10) as connection:
            connection.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?)",(state["run_id"],state["updated_at"],json.dumps(state,ensure_ascii=False)))

    def load(self,identifier):
        if not re.fullmatch(r"[a-f0-9]{32}",identifier): raise ValueError("运行标识无效")
        with sqlite3.connect(self.path,timeout=10) as connection:
            row=connection.execute("SELECT state FROM runs WHERE id=?",(identifier,)).fetchone()
        if row is None: raise KeyError("工作流记录不存在")
        return json.loads(row[0])

    def create(self,objective,papers,**options):
        state={"run_id":uuid.uuid4().hex,"objective":objective,"corpus_fingerprint":corpus_fingerprint(papers),"paper_ids":[p["id"] for p in papers],
               "phase":"created","rounds":0,"tool_count":0,"messages":[],"trace":[],"outputs":{},"evidence":[],"pending_calls":[],"completed_call_ids":[],**options}
        self.save(state);return state
