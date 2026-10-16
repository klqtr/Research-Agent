import json
from dataclasses import replace
import httpx
import pytest
from src.config import Settings
from src.model import ModelClient, ModelUnavailable
from src.model_budget import ModelBudget


def settings(tmp_path,**options):
    return replace(Settings(data_dir=tmp_path),model_enabled=True,model_name="explicit_mock_transport_only",**options)


def transport(monkeypatch,handler):
    original=httpx.Client
    monkeypatch.setattr(httpx,"Client",lambda **kw:original(transport=httpx.MockTransport(handler),**kw))


def response(content='{"claims":[]}',**kwargs):
    return httpx.Response(200,json={"choices":[{"message":{"content":content}}],**kwargs})


def test_shared_global_call_limit_across_clients_and_no_refund_on_timeout(monkeypatch,tmp_path):
    calls=[]
    def handle(request):calls.append(request);raise httpx.ReadTimeout("mock",request=request)
    transport(monkeypatch,handle)
    config=settings(tmp_path,model_max_calls=1)
    for _ in range(2):
        with pytest.raises(ModelUnavailable):ModelClient(config).complete("question")
    assert len(calls)==1 and ModelBudget(config).snapshot()["attempts_reserved"]==1


def test_context_limit_and_cost_require_prices_before_network(monkeypatch,tmp_path):
    calls=[];transport(monkeypatch,lambda request:calls.append(request) or response())
    with pytest.raises(ModelUnavailable):ModelClient(settings(tmp_path,model_max_context_chars=512)).complete("x"*1000)
    with pytest.raises(ModelUnavailable):ModelClient(settings(tmp_path,model_max_cost_usd=.1)).complete("small")
    assert not calls


def test_known_usage_cost_and_group_scope(monkeypatch,tmp_path):
    transport(monkeypatch,lambda request:response(usage={"prompt_tokens":100,"completion_tokens":50}))
    config=settings(tmp_path,model_input_usd_per_million=1,model_output_usd_per_million=2,model_max_cost_usd=.1)
    first=ModelClient(config).complete("hello")["accounting"]
    second=ModelClient(config).complete("world")["accounting"]
    assert first["attempts_reserved"]==1 and second["attempts_reserved"]==1
    assert second["global_attempts_reserved"]==2 and second["actual_cost_usd"]==pytest.approx(.0002)


def test_health_get_does_not_claim_function_calling_or_charge_inference(monkeypatch,tmp_path):
    seen=[]
    def handle(request):seen.append(request.method);return httpx.Response(200,json={"data":[{"id":"explicit_mock_transport_only"}]})
    transport(monkeypatch,handle);client=ModelClient(settings(tmp_path))
    assert client.health()["native_tools"]=="not_probed" and seen==["GET"]
    assert not (tmp_path/"model_budget.sqlite3").exists()


def test_explicit_capability_probe_observes_json_and_tool_protocol(monkeypatch,tmp_path):
    def handle(request):
        if request.method=="GET":return httpx.Response(200,json={"data":[]})
        body=json.loads(request.content)
        if body.get("tools"):
            return httpx.Response(200,json={"choices":[{"message":{"tool_calls":[{"id":"probe","type":"function","function":{"name":"capability_echo","arguments":"{}"}}]}}]})
        return response('{"ok":true}')
    transport(monkeypatch,handle);result=ModelClient(settings(tmp_path)).probe_capabilities()
    assert result["json_output"]=="observed" and result["native_tools"]=="observed"
    assert result["accounting"]["attempts_reserved"]==2


def test_historical_costs_keep_their_original_prices(monkeypatch,tmp_path):
    transport(monkeypatch,lambda request:response(usage={"prompt_tokens":100,"completion_tokens":50}))
    old=settings(tmp_path,model_input_usd_per_million=1,model_output_usd_per_million=2)
    ModelClient(old).complete("first")
    updated=replace(old,model_input_usd_per_million=2,model_output_usd_per_million=4)
    second=ModelClient(updated).complete("second")
    assert second["accounting"]["actual_cost_usd"]==pytest.approx(.0004)
    assert ModelBudget(updated).snapshot()["actual_cost_usd"]==pytest.approx(.0006)


def test_parallel_reservations_cannot_exceed_global_limit(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from src.model_budget import BudgetExceeded
    configuration=settings(tmp_path,model_max_calls=1)
    def attempt(index):
        try:ModelBudget(configuration,str(index)).reserve({"messages":[],"max_tokens":8});return True
        except BudgetExceeded:return False
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
    assert sum(results)==1 and ModelBudget(configuration).snapshot()["attempts_reserved"]==1


def test_unknown_historical_cost_blocks_a_new_dollar_budget(monkeypatch,tmp_path):
    calls=[];transport(monkeypatch,lambda request:calls.append(request) or response())
    original=settings(tmp_path);ModelClient(original).complete("unpriced")
    priced=replace(original,model_input_usd_per_million=1,model_output_usd_per_million=2,model_max_cost_usd=.1)
    with pytest.raises(ModelUnavailable):ModelClient(priced).complete("new paid attempt")
    assert len(calls)==1


def test_capability_probe_never_exceeds_two_inference_requests_on_timeout(monkeypatch,tmp_path):
    posts=[]
    def handle(request):
        if request.method=="GET":return httpx.Response(200,json={"data":[]})
        posts.append(request);raise httpx.ReadTimeout("mock",request=request)
    transport(monkeypatch,handle)
    result=ModelClient(settings(tmp_path)).probe_capabilities()
    assert len(posts)==2 and result["accounting"]["attempts_reserved"]==2
