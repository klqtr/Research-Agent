"""Real-PDF end-to-end ASGI demo regression in an isolated temporary library."""
import hashlib
import json
import sys
import time
from pathlib import Path
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.app import create_app
from src.config import Settings


def run_demo(data_dir):
    records=[]
    originals={name:(ROOT/"data/papers"/name).read_bytes() for name in ("1706.03762v1.pdf","1706.03762v7.pdf","1810.04805v2.pdf")}
    with TestClient(create_app(Settings(data_dir=data_dir))) as client:
        newer=client.post("/api/papers",files={"file":("attention-latest.pdf",originals["1706.03762v7.pdf"])});assert newer.status_code==200
        preview=client.post("/api/papers",files={"file":("renamed-old.pdf",originals["1706.03762v1.pdf"])});assert preview.status_code==409
        assert preview.json()["duplicates"][0]["same_arxiv"]
        older=client.post("/api/papers?decision=keep_both",files={"file":("renamed-old.pdf",originals["1706.03762v1.pdf"])});assert older.status_code==200
        third=client.post("/api/papers",files={"file":("bert.pdf",originals["1810.04805v2.pdf"])});assert third.status_code==200
        ids=[newer.json()["paper_id"],older.json()["paper_id"]]
        for policy,explicit,expected in (("latest",None,7),("explicit",1,1)):
            request={"question":"What hardware GPUs were used for training?","paper_ids":ids,"version_policy":policy,"explicit_version":explicit,"use_model":False}
            result=client.post("/api/research",json=request);assert result.status_code==200
            body=result.json();assert body["evidence"] and all(e["source_version"]==expected for e in body["evidence"])
            assert body["mode"]=="deterministic_workflow" and body["rounds"]==0
            source=next((e for e in body["evidence"] if e["page"]==7),body["evidence"][0])
            image=client.get(f"/api/papers/{source['paper_id']}/pages/{source['page']}/image",params={"chunk_id":source["id"]})
            assert image.status_code==200 and image.content.startswith(b"\x89PNG")
            resumed=client.post("/api/research/"+body["run_id"]+"/resume");assert resumed.json()["trace"]==body["trace"]
            records.append({"action":"version_question_source_and_resume","request":request,"response":body,"source_image_bytes":len(image.content)})
        raw=client.get("/api/papers/"+ids[0]+"/pdf").content
        assert hashlib.sha256(raw).hexdigest()==hashlib.sha256(originals["1706.03762v7.pdf"]).hexdigest()
        diff=client.get("/api/diff",params={"first":ids[1],"second":ids[0]}).json();assert diff["diff"]
        graph=client.get("/api/graph").json();assert len(graph["nodes"])==2
        translation=client.post(f"/api/papers/{ids[0]}/pages/7/translation",json={"target":"Chinese"});assert translation.status_code==503
        records.extend([{"action":"duplicate_preview","response":preview.json()},{"action":"diff","response":diff},{"action":"graph","response":graph},{"action":"translation_without_model","status":translation.status_code}])
    return {"kind":"real_PDF_local_ASGI_demo_not_LLM_or_video","original_library_modified":False,"model_requests":0,"checks":"passed","records":records}


if __name__=="__main__":
    stamp=time.strftime("%Y%m%d_%H%M%S");result=run_demo(ROOT/"tmp"/("phase2_demo_"+stamp))
    output=ROOT/"experiments"/("phase2_demo_"+stamp+".json");output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"path":str(output.relative_to(ROOT)),"checks":result["checks"],"actions":len(result["records"]),"model_requests":0}))
