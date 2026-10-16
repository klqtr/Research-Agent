import json
from dataclasses import replace
import httpx
import pytest
from src.config import Settings
from src.research_agent import ResearchAgent,execute_tool
from src.run_state import corpus_fingerprint
from test_phase2_evidence import paper
from test_phase2_model import transport,response


def config(tmp_path):return replace(Settings(data_dir=tmp_path),model_enabled=True,model_name="explicit_mock_transport_only")
def call(identifier,name,arguments=None):return {"id":identifier,"type":"function","function":{"name":name,"arguments":json.dumps(arguments or {})}}
def tool_response(*calls):return httpx.Response(200,json={"choices":[{"message":{"content":None,"tool_calls":list(calls)}}]})
def quote_response():return response(json.dumps({"claims":[{"text":"Training uses eight GPUs.","citations":[{"chunk_id":"p1:c1","quote":"Training uses eight GPUs."}]}]}))


def test_result_driven_retrieval_then_repair_unsupported_claim(monkeypatch,tmp_path):
    seen=[]
    def handle(request):
        body=json.loads(request.content);seen.append(body)
        if len(seen)==1:return tool_response(call("search","search_library",{"query":"training"}))
        if len(seen)==2:
            assert '"p1"' in body["messages"][-1]["content"]
            return tool_response(call("evidence","retrieve",{"query":"training GPUs","paper_ids":["p1"]}))
        if len(seen)==3:
            return response(json.dumps({"claims":[{"text":"Training uses 99999 GPUs.","citations":[{"chunk_id":"p1:c1","quote":"Training uses eight GPUs."}]}]}))
        assert "Independent gate rejected" in body["messages"][-1]["content"]
        return quote_response()
    transport(monkeypatch,handle)
    agent=ResearchAgent(config(tmp_path));result=agent.run("training GPUs",[paper()],use_model=True)
    assert result["mode"]=="real_llm_native_tools" and result["rounds"]==4
    assert len(result["synthesis"]["claims"])==1
    state=agent.journal.load(result["run_id"])
    assert len(state["model_responses"])==4 and "99999" in state["model_responses"][2]["message"]["content"]


def test_tool_failure_is_returned_for_model_correction(monkeypatch,tmp_path):
    seen=[]
    def handle(request):
        body=json.loads(request.content);seen.append(body)
        if len(seen)==1:return tool_response(call("bad","retrieve",{"paper_ids":["unselected"]}))
        if len(seen)==2:
            assert "error" in json.loads(body["messages"][-1]["content"])
            return tool_response(call("fixed","retrieve"))
        return quote_response()
    transport(monkeypatch,handle);result=ResearchAgent(config(tmp_path)).run("training GPUs",[paper()],True)
    assert result["mode"]=="real_llm_native_tools"
    assert [r["status"] for r in result["trace"] if r["phase"]=="tool"]==["failed","completed"]


def test_unsupported_native_tools_explicit_compatibility(monkeypatch,tmp_path):
    def handle(request):
        return httpx.Response(400,json={"error":"tools unsupported"}) if "tools" in json.loads(request.content) else quote_response()
    transport(monkeypatch,handle);result=ResearchAgent(config(tmp_path)).run("training GPUs",[paper()],True)
    assert result["mode"]=="real_llm_rag_compatibility" and len(result["synthesis"]["claims"])==1


def test_disabled_model_fallback_is_extractive_and_resumable_without_network(monkeypatch,tmp_path):
    def forbidden(*args,**kwargs):raise AssertionError("Unexpected model request")
    monkeypatch.setattr(httpx,"Client",forbidden)
    settings=Settings(data_dir=tmp_path);agent=ResearchAgent(settings)
    result=agent.run("training GPUs",[paper()],use_model=True)
    assert result["mode"]=="extractive_fallback" and result["synthesis"]["claims"]
    again=agent.run("training GPUs",[paper()],True,run_id=result["run_id"])
    assert again["trace"]==result["trace"]
    with pytest.raises(ValueError):agent.run("training GPUs",[paper(text="Changed source")],True,run_id=result["run_id"])


def test_resume_pending_calls_does_not_repeat_completed_tool(monkeypatch,tmp_path):
    seen=[]
    def handle(request):
        seen.append(request)
        return tool_response(call("r","retrieve"),call("v","versions")) if len(seen)==1 else quote_response()
    transport(monkeypatch,handle);settings=config(tmp_path);agent=ResearchAgent(settings)
    original=agent._record_tool
    def interrupt(state,name,*args,**kwargs):
        if name=="versions":raise KeyboardInterrupt("simulated process interruption")
        return original(state,name,*args,**kwargs)
    monkeypatch.setattr(agent,"_record_tool",interrupt)
    with pytest.raises(KeyboardInterrupt):agent.run("training GPUs",[paper()],True)
    import sqlite3
    with sqlite3.connect(agent.journal.path) as connection:identifier=connection.execute("SELECT id FROM runs").fetchone()[0]
    result=ResearchAgent(settings).run("training GPUs",[paper()],True,run_id=identifier)
    assert len([r for r in result["trace"] if r.get("tool")=="retrieve"])==1
    assert result["accounting"]["attempts_reserved"]==2


def test_tool_schema_no_extra_arguments_and_network_requires_opt_in(tmp_path):
    settings=Settings(data_dir=tmp_path)
    for name,args in [("shell",{}),("retrieve",{"command":"whoami"}),("retrieve",{"k":True}),("search_arxiv",{"query":"topic"})]:
        with pytest.raises(ValueError):execute_tool(name,args,"training",[paper()],[paper()],settings)


def test_run_lease_rejects_concurrent_resume(tmp_path):
    agent=ResearchAgent(Settings(data_dir=tmp_path));state=agent.journal.create("question",[])
    with agent.journal.claim(state["run_id"]):
        with pytest.raises(ValueError):
            with agent.journal.claim(state["run_id"]):pass


def test_compatibility_does_not_add_a_model_round_beyond_limit(monkeypatch,tmp_path):
    requests=[]
    def handle(request):requests.append(request);return httpx.Response(400,json={"error":"tools rejected"})
    transport(monkeypatch,handle)
    result=ResearchAgent(replace(config(tmp_path),agent_max_rounds=1)).run("training GPUs",[paper()],True)
    assert len(requests)==1 and result["rounds"]==1 and result["mode"]=="extractive_fallback"
