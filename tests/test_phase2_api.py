from fastapi.testclient import TestClient
from src.app import create_app
from src.config import Settings
from test_core import pdf_bytes


def test_research_fallback_status_and_resume_keep_source_and_zero_model_budget(tmp_path):
    client=TestClient(create_app(Settings(data_dir=tmp_path)))
    pid=client.post("/api/papers",files={"file":("paper.pdf",pdf_bytes("The model is trained with eight GPUs."))}).json()["paper_id"]
    result=client.post("/api/research",json={"question":"training GPUs","paper_ids":[pid],"use_model":True}).json()
    assert result["mode"]=="extractive_fallback" and result["rounds"]==0
    assert result["synthesis"]["claims"] and result["accounting"]["attempts_reserved"]==0
    status=client.get("/api/research/"+result["run_id"])
    resumed=client.post("/api/research/"+result["run_id"]+"/resume")
    assert status.json()["trace"]==resumed.json()["trace"]
    assert client.get("/api/model/status").json()["inference_executed"] is False
    assert client.post("/api/model/probe",json={"inference":True}).status_code==503
    assert not (tmp_path/"model_budget.sqlite3").exists()


def test_cross_paper_version_diff_does_not_become_a_fake_version_conflict(tmp_path):
    client=TestClient(create_app(Settings(data_dir=tmp_path)))
    ids=[client.post("/api/papers",files={"file":(str(i)+".pdf",pdf_bytes(f"Different research subject {i} uses GPUs."))}).json()["paper_id"] for i in range(2)]
    assert client.get("/api/version-facts",params={"first":ids[0],"second":ids[1]}).status_code==400
    assert client.get("/api/research/../../.env").status_code==404


def test_research_map_uses_known_dates_and_keeps_hypotheses_empty(tmp_path):
    client=TestClient(create_app(Settings(data_dir=tmp_path)))
    result=client.get("/api/research-map").json()
    assert result["model_hypotheses"]==[] and result["timeline"]==[]
    client.post("/api/papers",files={"file":("p.pdf",pdf_bytes("A paper without verified submission date."))})
    result=client.get("/api/research-map").json()
    assert result["timeline"][0]["first_submitted"] is None
    assert result["timeline"][0]["date_status"]=="unknown_not_inferred"
