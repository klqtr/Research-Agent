import json
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.publication_privacy import public_document, sanitize_document, sanitize_text


def test_public_json_preserves_metrics_and_escapes():
    raw = json.dumps({"command": [r"C:\Users\Example\private\python.exe"], "accuracy": .75, "failures": 2})
    result = json.loads(sanitize_text(raw, Path("unrelated-project")))
    assert "Example" not in result["command"][0]
    assert result["accuracy"] == .75 and result["failures"] == 2


def test_public_xml_preserves_failure_and_count():
    raw = '<testsuite tests="2" failures="1" hostname="private-machine"><testcase><failure>/home/example/work/file.py</failure></testcase></testsuite>'
    result = ET.fromstring(sanitize_text(raw, Path("unrelated-project")))
    assert result.attrib == {"tests": "2", "failures": "1", "hostname": "redacted-host"}
    assert result.find("testcase/failure") is not None
    assert "example" not in ET.tostring(result, encoding="unicode")


def test_public_copy_removes_email_and_credentials():
    address = "researcher" + "@" + "example.org"
    credential = "ghp_" + "a" * 36
    result = sanitize_text(address + " " + credential, Path("unrelated-project"))
    assert address not in result and credential not in result
    assert "[EMAIL_REDACTED]" in result and "[CREDENTIAL_REDACTED]" in result


def test_public_copy_is_idempotent_and_keeps_local_service():
    text = "http://127.0.0.1:8000/ data/phase2_qa_tasks.json 130 passed"
    assert sanitize_text(text) == text
    assert sanitize_text(sanitize_text(text)) == text


def test_json_embedded_quoted_traceback_stays_valid():
    original = {"trace": 'File "C:\\Users\\Example\\folder\\test.py", line 5', "scores": [0.75, 2, None]}
    raw = json.dumps(original)
    public = json.loads(sanitize_document(raw, ".json", Path("unrelated-project")))
    assert "Example" not in public["trace"]
    assert public["scores"] == original["scores"]


def test_clean_json_bytes_and_dataset_lock_are_preserved():
    raw = '{"question": "training GPUs", "count": 8}\r\n'
    assert sanitize_document(raw, ".json") == raw


def test_api_dump_minimization_keeps_real_status_and_latency():
    record = [{"endpoint": "/api/papers", "status": 200, "latency_ms": 12.5, "response": [{"id": "paper", "pages": [1, 2], "references": ["ref"], "title": "source title"}]}]
    name = "experiments/live_smoke_20261016_010808.json"
    result = json.loads(public_document(name, json.dumps(record)))
    assert result[0]["status"] == 200 and result[0]["latency_ms"] == 12.5
    assert result[0]["response"][0]["public_omitted_array_counts"] == {"pages": 2, "references": 1}
    assert result[0]["response"][0]["title"] == "source title"
    assert public_document(name, json.dumps(result)) == json.dumps(result)
