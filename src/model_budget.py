"""Persistent conservative reservations shared across clients and worker processes.

The char-based token reservation is an upper-bound heuristic, not a tokenizer.
Failed requests still consume reservations because providers may have charged them.
"""
import json
import math
import sqlite3
from datetime import datetime, timezone


class BudgetExceeded(RuntimeError):
    pass


class ModelBudget:
    def __init__(self, settings, group_id=None):
        self.settings=settings
        self.group_id=group_id
        for rate in (settings.model_input_usd_per_million,settings.model_output_usd_per_million):
            if rate is not None and (not math.isfinite(rate) or rate<0):raise ValueError("模型单价须为有限非负数")
        settings.data_dir.mkdir(parents=True,exist_ok=True)
        self.path=settings.data_dir/"model_budget.sqlite3"
        with self.connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS model_calls (id INTEGER PRIMARY KEY, at TEXT, reserved_tokens INTEGER, reserved_cost REAL, status TEXT, usage TEXT, group_id TEXT, pricing TEXT)")
            for column in ("group_id","pricing"):
                if column not in {row[1] for row in connection.execute("PRAGMA table_info(model_calls)")}:
                    try:connection.execute(f"ALTER TABLE model_calls ADD COLUMN {column} TEXT")
                    except sqlite3.OperationalError:
                        if column not in {row[1] for row in connection.execute("PRAGMA table_info(model_calls)")}:raise

    def connect(self):
        return sqlite3.connect(self.path,timeout=10)

    def reserve(self, body):
        settings=self.settings
        # UTF-8 bytes overestimate common BPE tokenization; not a formal bound
        # for every remote tokenizer. Actual usage remains a separate field.
        units=len(json.dumps(body.get("messages",[]),ensure_ascii=False).encode("utf-8"))+len(json.dumps(body.get("tools",[])).encode("utf-8"))+128
        output=body.get("max_tokens",settings.model_max_output_tokens)
        tokens=units+output
        rates=(settings.model_input_usd_per_million,settings.model_output_usd_per_million)
        if any(rate is not None and (not math.isfinite(rate) or rate<0) for rate in rates):
            raise ValueError("模型单价须为有限非负数")
        cost=None if None in rates else (units*rates[0]+output*rates[1])/1_000_000
        if settings.model_max_cost_usd>0 and cost is None:
            raise BudgetExceeded("设置美元预算时必须同时提供输入/输出单价；没有猜测价格")
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            count,total,spent,unknown=connection.execute("SELECT COUNT(*),COALESCE(SUM(reserved_tokens),0),COALESCE(SUM(reserved_cost),0),COALESCE(SUM(CASE WHEN reserved_cost IS NULL THEN 1 ELSE 0 END),0) FROM model_calls").fetchone()
            if count>=settings.model_max_calls or total+tokens>settings.model_max_reserved_tokens:
                raise BudgetExceeded("累计调用次数或保守Token预留达到上限；未发送请求")
            if settings.model_max_cost_usd>0 and unknown:
                raise BudgetExceeded("历史尝试费用未知，无法确认美元剩余额度；未发送请求，不自动把未知费用当0")
            if settings.model_max_cost_usd>0 and spent+(cost or 0)>settings.model_max_cost_usd:
                raise BudgetExceeded("累计美元预留达到预算；未发送请求")
            pricing=json.dumps({"input_per_million":rates[0],"output_per_million":rates[1],"requested_model":body.get("model")})
            cursor=connection.execute("INSERT INTO model_calls(at,reserved_tokens,reserved_cost,status,group_id,pricing) VALUES (?,?,?,?,?,?)",(datetime.now(timezone.utc).isoformat(),tokens,cost,"reserved",self.group_id,pricing))
            return cursor.lastrowid

    def finish(self, identifier, status, usage=None):
        with self.connect() as connection:
            connection.execute("UPDATE model_calls SET status=?,usage=? WHERE id=?",(status,json.dumps(usage) if usage else None,identifier))

    def snapshot(self):
        with self.connect() as connection:
            global_count,global_tokens=connection.execute("SELECT COUNT(*),COALESCE(SUM(reserved_tokens),0) FROM model_calls").fetchone()
            rows=connection.execute("SELECT reserved_tokens,reserved_cost,status,usage,pricing FROM model_calls"+(" WHERE group_id=?" if self.group_id else ""),((self.group_id,) if self.group_id else ())).fetchall()
        usage=[json.loads(row[3]) for row in rows if row[3]]
        complete=all(isinstance(item,dict) and all(type(item.get(key)) is int and item[key]>=0 for key in ("prompt_tokens","completion_tokens")) for item in usage) and len(usage)==len(rows) and bool(rows)
        prices=[json.loads(row[4]) if row[4] else {} for row in rows]
        known_prices=all(item.get("input_per_million") is not None and item.get("output_per_million") is not None for item in prices)
        actual_cost=sum((item["prompt_tokens"]*price["input_per_million"]+item["completion_tokens"]*price["output_per_million"])/1_000_000 for item,price in zip(usage,prices)) if complete and known_prices else None
        return {"scope":"workflow_call_group" if self.group_id else "global_persistent_ledger","group_id":self.group_id,"global_attempts_reserved":global_count,"global_reserved_token_units":global_tokens,
                "attempts_reserved":len(rows),"reserved_token_units":sum(row[0] for row in rows),
                "reserved_cost_usd":sum(row[1] for row in rows) if rows and all(row[1] is not None for row in rows) else None,
                "reported_usage":usage,"actual_cost_usd":actual_cost,"actual_usage_complete":complete,
                "reported_prompt_tokens":sum(item["prompt_tokens"] for item in usage) if complete else None,
                "reported_completion_tokens":sum(item["completion_tokens"] for item in usage) if complete else None,
                "reservation_note":"保守UTF-8字节预留，不是模型Tokenizer或实际费用；失败/重试也计入，缺usage/单价时实际费用为null。"}
