"""Mocked native tool protocol checks; these are not LLM effect experiments."""
import json
from dataclasses import replace
import httpx
import pytest
from src.config import Settings
from src.model import ModelClient, ModelUnavailable
from src.planner import workflow


def test_native_tool_round_trip(monkeypatch, tmp_path):
    requests = []
    def handle(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests)==1:
            return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [{"id": "call_graph", "type": "function", "function": {"name": "graph", "arguments": "{}"}}]}}]})
        assert payload["messages"][-1]["role"] == "tool"
        assert payload["messages"][-1]["tool_call_id"] == "call_graph"
        assert "tools" in payload  # adaptive continuation can choose another tool
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"claims":[]}'}}]})
    original = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    result = workflow("show citation graph", [], replace(Settings(data_dir=tmp_path), model_enabled=True, model_name="mock-transport-only"), use_model=True)
    assert result["mode"] == "real_llm_native_tools" and "graph" in result["outputs"]
    assert result["synthesis"]["claims"] == [] and len(requests) == 2


@pytest.mark.parametrize("name,arguments", [("shell", "{}"), ("retrieve", '{"command":"whoami"}'), ("graph", "bad json")])
def test_native_tool_permissions(monkeypatch, name, arguments, tmp_path):
    def handle(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": None, "tool_calls": [{"id": "x", "type": "function", "function": {"name": name, "arguments": arguments}}]}}]})
    original = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    with pytest.raises(ModelUnavailable):
        ModelClient(replace(Settings(data_dir=tmp_path), model_enabled=True, model_name="mock-transport-only")).plan_native("test")
