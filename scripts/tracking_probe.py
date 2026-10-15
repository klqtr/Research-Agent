"""Bounded live scheduler probe. Creation requires the explicit --create flag.

The test topic is public and the watch automatically stops after two attempts.
No LLM, credentials, external messaging, or paid resources are involved.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    now = datetime.now(timezone(timedelta(hours=8)))
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=35, trust_env=False) as client:
        response = client.get("/api/watchlist")
        response.raise_for_status()
        watches = response.json()["watches"]
        watch = next((w for w in watches if w["query"] == "retrieval augmented generation"), None)
        created = False
        if watch is None and "--create" in sys.argv:
            response = client.post("/api/watchlist", json={"query": "retrieval augmented generation", "interval_minutes": 30, "enabled": True, "refresh_limit": 2})
            response.raise_for_status()
            watch, created = response.json(), True
        runs = []
        if watch:
            response = client.get(f"/api/watchlist/{watch['id']}/runs")
            response.raise_for_status()
            runs = response.json()["runs"]
    record = {"observed_at": now.isoformat(), "created_this_probe": created, "watch": watch, "runs": runs,
              "kind": "real_local_service_and_public_arxiv_scheduler_probe", "expected_stop": "disabled after at most two attempts", "llm_calls": "none"}
    path = ROOT / "experiments" / ("tracking_probe_" + now.strftime("%Y%m%d_%H%M%S") + ".json")
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "experiments/LATEST_TRACKING_PROBE.txt").write_text(str(path.relative_to(ROOT)), encoding="utf-8")
    print(json.dumps({"file": str(path.relative_to(ROOT)), "created": created, "watch_id": watch["id"] if watch else None,
                      "enabled": bool(watch["enabled"]) if watch else False, "runs_count": len(runs), "statuses": [r["status"] for r in runs]}, ensure_ascii=False))
