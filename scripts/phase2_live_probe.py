"""Local live endpoints and two local model-list checks; no inference request."""
import json
import time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]


if __name__=="__main__":
    records=[]
    with httpx.Client(base_url="http://127.0.0.1:8000",timeout=15,trust_env=False) as client:
        status=client.get("/api/model/status");records.append({"path":"/api/model/status","status":status.status_code,"body":status.json()})
        for path in ("/api/health","/research.js","/api/research-map"):
            start=time.perf_counter();response=client.get(path)
            records.append({"path":path,"status":response.status_code,"latency_ms":(time.perf_counter()-start)*1000,"body":response.json() if "application/json" in response.headers.get("content-type","") else {"bytes":len(response.content)}})
        papers=client.get("/api/papers").json();attention=[p["id"] for p in papers if p.get("arxiv_id")=="1706.03762"]
        body={"question":"Compare training hardware GPUs in the latest available Attention version.","paper_ids":attention,"use_model":False}
        response=client.post("/api/research",json=body);result=response.json()
        records.append({"path":"/api/research","request":body,"status":response.status_code,"body":result})
        if response.status_code==200:
            identifier=result["run_id"]
            for path,method in ((f"/api/research/{identifier}","get"),(f"/api/research/{identifier}/resume","post")):
                response=getattr(client,method)(path);records.append({"path":path,"status":response.status_code,"body":response.json()})
        if not status.json().get("configured"):
            first=attention[0]
            response=client.post(f"/api/papers/{first}/pages/7/translation",json={"target":"Chinese"})
            records.append({"path":"translation_without_model","expected_status":503,"status":response.status_code,"body":response.json()})
    for port in (11434,1234):
        try:
            with httpx.Client(timeout=1,trust_env=False) as client:response=client.get(f"http://127.0.0.1:{port}/v1/models")
            records.append({"path":f"local_model_list_{port}","status":response.status_code,"inference_executed":False})
        except httpx.HTTPError as exc:records.append({"path":f"local_model_list_{port}","status":"unavailable","error_type":type(exc).__name__,"inference_executed":False})
    output=ROOT/"experiments"/("phase2_live_"+time.strftime("%Y%m%d_%H%M%S")+".json")
    output.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"file":str(output.relative_to(ROOT)),"statuses":[[row["path"],row["status"]] for row in records]},ensure_ascii=True))
