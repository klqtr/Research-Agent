"""Exercise the running page-analysis API and CSV exports with real stored PDFs."""
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
CASES = [("0a9bff1be3575cf9fe26", 8), ("23e3249e9a1e75418d82", 6)]


if __name__ == "__main__":
    records = []
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30, trust_env=False) as client:
        for paper_id, page in CASES:
            for attempt in range(2):
                start = time.perf_counter()
                response = client.get(f"/api/papers/{paper_id}/pages/{page}/analysis")
                response.raise_for_status()
                result = response.json()
                records.append({"paper_id": paper_id, "page": page, "attempt": attempt, "latency_ms": (time.perf_counter()-start)*1000, "response": result})
            for table in result["tables"]:
                response = client.get(f"/api/papers/{paper_id}/pages/{page}/tables/{table['id']}/csv")
                response.raise_for_status()
                records.append({"paper_id": paper_id, "page": page, "table": table["id"], "kind": "real_csv_export",
                                "status": response.status_code, "sha256": hashlib.sha256(response.content).hexdigest(),
                                "csv_utf8": response.content.decode("utf-8-sig")})
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    path = ROOT / "experiments" / ("live_structure_"+stamp+".json")
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"file":str(path.relative_to(ROOT)),"requests":len(records),"cached_requests":[{"page":r['page'],"cache_hit":r['response']['cache_hit'],"latency_ms":r['latency_ms']} for r in records if 'response' in r]},ensure_ascii=False))
