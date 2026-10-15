"""Bounded, read-only local HTTP evidence for the graph delivery."""
import json
import sys
import time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]


if __name__=="__main__":
    records=[]
    with httpx.Client(base_url="http://127.0.0.1:8000",timeout=15,trust_env=False) as client:
        for path in ("/api/health","/api/graph","/api/reference-candidates?limit=5","/graph.js","/api/watchlist"):
            start=time.perf_counter();response=client.get(path)
            records.append({"path":path,"status":response.status_code,"latency_ms":(time.perf_counter()-start)*1000,
                            "result":response.json() if "application/json" in response.headers.get("content-type","") else {"bytes":len(response.content)}})
    target=ROOT/"experiments"/("phase3_live_"+time.strftime("%Y%m%d_%H%M%S")+".json")
    target.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"file":str(target.relative_to(ROOT)),"statuses":[[r["path"],r["status"]] for r in records]},ensure_ascii=True))
    sys.exit(0 if all(r["status"]==200 for r in records) else 1)
