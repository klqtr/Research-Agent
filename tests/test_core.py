import json
from dataclasses import replace
import fitz
import pytest
from fastapi.testclient import TestClient
from src.app import create_app
from src.config import Settings
from src.model import ModelClient, ModelUnavailable
from src.parsing import duplicates, parse_pdf
from src.retrieval import retrieve, validate_claims
from src.tools import csv_analysis, graph


def pdf_bytes(text, title="Test Research Paper"):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 540, 790), title + "\n" + text, fontsize=11)
    doc.set_metadata({"title": title})
    raw = doc.tobytes()
    doc.close()
    return raw


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "library")


@pytest.fixture
def client(settings):
    return TestClient(create_app(settings))


def test_invalid_pdf(client):
    response = client.post("/api/papers", files={"file": ("evil.pdf", b"not a pdf", "application/pdf")})
    assert response.status_code == 400
    assert not client.get("/api/papers").json()


def test_real_parse_and_source_anchor(settings):
    paper = parse_pdf(pdf_bytes("The model uses 8 GPUs and a batch size of 4096."), "random.pdf", settings)
    assert paper["pages"][0]["mode"] == "native"
    assert any("8 GPUs" in chunk["text"] and chunk["page"] == 1 and len(chunk["bbox"]) == 4 for chunk in paper["chunks"])


def test_renamed_duplicate_and_no_silent_replace(client):
    raw = pdf_bytes("A sufficiently long shared paper explains attention models and training algorithms in detail.")
    first = client.post("/api/papers", files={"file": ("one.pdf", raw)}).json()
    second = client.post("/api/papers", files={"file": ("completely-unrelated-name.pdf", raw)})
    assert second.status_code == 409
    assert len(client.get("/api/papers").json()) == 1
    assert client.get(f"/api/papers/{first['paper_id']}/pdf").content == raw


def test_content_version_not_filename(settings):
    existing = parse_pdf(pdf_bytes("arXiv:1706.03762v7\nThe transformer uses self attention and parallel training."), "v1.pdf", settings)
    older = parse_pdf(pdf_bytes("arXiv:1706.03762v1\nThe transformer uses self attention and parallel training."), "v7.pdf", settings)
    match = duplicates(older, [existing])[0]
    assert match["same_arxiv"] and match["existing_version"] == 7
    assert "保留" in match["recommendation"]


def test_cross_paper_coverage(settings):
    papers = [parse_pdf(pdf_bytes(f"Training GPU hardware batch size attention model {i}"), f"{i}.pdf", settings) for i in range(3)]
    result = retrieve("GPU batch size", papers, k=3)
    assert len({x["paper_id"] for x in result}) == 3


def test_citation_integrity(settings):
    p = parse_pdf(pdf_bytes("Training uses eight GPUs for the base model."), "one.pdf", settings)
    e = p["chunks"][-1]
    payload = {"claims": [{"text": "valid", "citations": [{"chunk_id": e["id"], "quote": e["text"]}]},
                          {"text": "invalid", "citations": [{"chunk_id": "invented", "quote": "not a source"}]},
                          {"text": "invalid quote", "citations": [{"chunk_id": e["id"], "quote": "9999 GPUs"}]}]}
    checked = validate_claims(payload, [e])
    assert len(checked["claims"]) == 1 and len(checked["rejected"]) == 2
    assert not checked["semantic_entailment_verified"]


@pytest.mark.parametrize("payload", [{}, [], {"claims": "bad"}])
def test_invalid_model_structure(payload):
    with pytest.raises(ValueError):
        validate_claims(payload, [])


@pytest.mark.parametrize("text", ["", "one\n1", "name,value\nx,nan", "name,value\nx,inf"])
def test_invalid_csv(text):
    with pytest.raises(ValueError):
        csv_analysis(text)


def test_csv_no_causal_claim():
    r = csv_analysis("method,score\nA,-2\nB,4\n")
    assert r["series"]["score"]["mean"] == 1
    assert "未执行显著性检验" in r["caption"]


def test_missing_model_no_mock(client):
    r = client.post("/api/ask", json={"question": "What is the GPU?", "use_model": True}).json()
    assert r["mode"] == "model_unavailable" and r["abstained"]
    assert client.post("/api/translate", json={"text": "hello"}).status_code == 503


@pytest.mark.parametrize("question", ["", " " * 10, "a" * 6001], ids=["empty", "spaces", "too_long"])
def test_invalid_question(client, question):
    assert client.post("/api/ask", json={"question": question}).status_code in (400, 422)


def test_graph_pagerank_known_topology():
    ps = [{"id": str(i), "title": "Distinct reference paper title " + str(i), "references": [], "version": None} for i in range(3)]
    ps[1]["references"] = [{"text": ps[0]["title"]}]
    ps[2]["references"] = [{"text": ps[0]["title"]}]
    result = graph(ps)
    assert len(result["edges"]) == 2 and result["nodes"][0]["id"] == "0"
    assert abs(sum(n["pagerank"] for n in result["nodes"]) - 1) < .00001


def test_delete_preserves_source(client):
    raw = pdf_bytes("An original paper must be preserved when removed from the index.")
    paper_id = client.post("/api/papers", files={"file": ("p.pdf", raw)}).json()["paper_id"]
    assert client.delete("/api/papers/" + paper_id).status_code == 200
    assert (client.app.state.store.root / (paper_id + ".pdf")).read_bytes() == raw
    assert client.get("/api/papers/" + paper_id).status_code == 404


def test_model_unavailable_does_not_contact_network(settings, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected network")
    monkeypatch.setattr("httpx.Client", forbidden)
    with pytest.raises(ModelUnavailable):
        ModelClient(settings).complete("hello")


def test_graph_collapses_versions():
    papers = [{"id": "v1", "arxiv_id": "1706.03762", "version": 1, "title": "Attention Is All You Need", "references": []},
              {"id": "v7", "arxiv_id": "1706.03762", "version": 7, "title": "Attention Is All You Need", "references": []}]
    result = graph(papers)
    assert len(result["nodes"]) == 1 and result["nodes"][0]["id"] == "v7"
    assert len(result["nodes"][0]["versions"]) == 2
    from src.tools import writing_outline
    refs = writing_outline("version aware research", papers)["references"]
    assert len(refs) == 1 and refs[0]["source"].endswith("1706.03762v7")


def test_random_query_does_not_get_char_evidence(settings):
    paper = parse_pdf(pdf_bytes("The attention model is trained with eight GPUs."), "p.pdf", settings)
    assert not retrieve("zzzxqv unobtainiumxx florbknight", [paper])


def test_private_and_absent_year_abstention(client):
    client.post("/api/papers", files={"file": ("p.pdf", pdf_bytes("The authors trained an attention model in 2017."))})
    for question in ["What is the authors private bank account number?", "What was the revenue in 2030?"]:
        result = client.post("/api/ask", json={"question": question}).json()
        assert result["abstained"] and not result["claims"] and result["refusal_reason"]


def test_real_attention_title_if_sample_available(settings):
    from pathlib import Path
    path = Path("data/papers/1706.03762v7.pdf")
    if not path.exists():
        pytest.skip("Public real PDF sample not downloaded")
    paper = parse_pdf(path.read_bytes(), "random.pdf", settings)
    assert paper["title"] == "Attention Is All You Need"


def test_reference_arxiv_not_document_identity(settings):
    with fitz.open() as doc:
        doc.new_page().insert_text((50, 50), "A local paper without an arXiv identity. This is a complete first page.")
        doc.new_page().insert_text((50, 50), "References\narXiv:1606.06565 cited research paper, not our identifier.")
        raw = doc.tobytes()
    assert parse_pdf(raw, "not_identity.pdf", settings)["arxiv_id"] is None


def test_pdf_page_image_and_exact_highlight(client):
    raw = pdf_bytes("The original source evidence must remain available and unchanged.")
    pid = client.post("/api/papers", files={"file": ("p.pdf", raw)}).json()["paper_id"]
    paper = client.get("/api/papers/" + pid).json()
    chunk = paper["chunks"][0]["id"]
    path = f"/api/papers/{pid}/pages/1/image"
    response = client.get(path, params={"chunk_id": chunk})
    assert response.status_code == 200 and response.content.startswith(b"\x89PNG")
    assert client.get(f"/api/papers/{pid}/pages/0/image").status_code == 404
    assert client.get(path, params={"chunk_id": "invented"}).status_code == 400
    assert client.get(f"/api/papers/{pid}/pdf").content == raw
