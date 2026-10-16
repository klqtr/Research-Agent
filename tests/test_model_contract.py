"""Mock transport tests are transport-contract checks, not real model experiments."""
from dataclasses import replace
import httpx
import pytest
from src.config import Settings
from src.model import ModelClient, ModelUnavailable


def stub_client(monkeypatch, handler):
    original = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=transport, **kwargs))


def test_real_api_contract_and_usage_parsing(monkeypatch, tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"claims":[]}'}}], "usage": {"total_tokens": 7}})
    stub_client(monkeypatch, handler)
    settings = replace(Settings(data_dir=tmp_path), model_enabled=True, model_name="transport-test-model")
    result = ModelClient(settings).complete("test")
    assert result["output"] == {"claims": []} and result["usage"]["total_tokens"] == 7
    assert len(requests) == 1 and requests[0].url.path.endswith("/chat/completions")


def test_timeout_retry_bounded(monkeypatch, tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        raise httpx.ReadTimeout("test timeout", request=request)
    stub_client(monkeypatch, handler)
    settings = replace(Settings(data_dir=tmp_path), model_enabled=True, model_name="transport-test-model")
    with pytest.raises(ModelUnavailable):
        ModelClient(settings).complete("test")
    assert len(requests) == 2


def test_malformed_json_no_fake_fallback(monkeypatch, tmp_path):
    stub_client(monkeypatch, lambda req: httpx.Response(200, json={"choices": [{"message": {"content": "not JSON"}}]}))
    with pytest.raises(ModelUnavailable):
        ModelClient(replace(Settings(data_dir=tmp_path), model_enabled=True, model_name="transport-test-model")).complete("test")


def test_no_plaintext_remote_credentials(tmp_path):
    settings = replace(Settings(data_dir=tmp_path), model_enabled=True, model_name="test", model_base_url="http://example.com/v1")
    with pytest.raises(ValueError):
        ModelClient(settings).complete("test")
