"""Live local HTTP and public arXiv metadata probes. No paid inference."""
import json
import sys
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.tools import search_arxiv

if __name__ == "__main__":
    records = []
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30, trust_env=False) as client:
        for path in ("/api/health", "/api/papers", "/api/graph", "/", "/api/papers/0a9bff1be3575cf9fe26/pages/7/image"):
            start = time.perf_counter()
            response = client.get(path)
            records.append({"endpoint": path, "status": response.status_code, "latency_ms": (time.perf_counter() - start) * 1000,
                            "response": response.json() if "application/json" in response.headers.get("content-type", "") else {"bytes": len(response.content), "content_type": response.headers.get("content-type")}})
        for path, body in [("/api/ask", {"question": "What hardware GPUs were used to train the Transformer?", "paper_ids": ["0a9bff1be3575cf9fe26"]}),
                           ("/api/workflow", {"question": "graph future outline for attention research"}),
                           ("/api/csv", {"text": "method,score\nA,-2\nB,4\n"}),
                           ("/api/translate", {"text": "Training uses eight GPUs."})]:
            start = time.perf_counter()
            response = client.post(path, json=body)
            records.append({"endpoint": path, "status": response.status_code, "latency_ms": (time.perf_counter() - start)*1000, "response": response.json()})
    try:
        results = search_arxiv("retrieval augmented generation", 3)
        records.append({"endpoint": "public_arxiv_api", "status": "completed", "results": results})
    except Exception as exc:
        records.append({"endpoint": "public_arxiv_api", "status": "unavailable", "error": str(exc)})
    path = ROOT / "experiments" / ("live_smoke_" + time.strftime("%Y%m%d_%H%M%S") + ".json")
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(path), "statuses": [{"endpoint": r["endpoint"], "status": r["status"]} for r in records]}, ensure_ascii=False))
