import json
import pytest
from src.translation import protect,restore,translate_segments
from test_phase2_model import settings,transport,response


def test_protected_formula_citations_numbers_and_glossary():
    text="Attention uses 8 GPUs, α=0.1, $x^2$ and [12]. ν=1e−4, 64×64, d_model [1–2]."
    masked,mapping=protect(text,{"Attention":"注意力"})
    restored=restore(masked,mapping)
    assert restored==text.replace("Attention","注意力")
    for key in mapping:
        with pytest.raises(ValueError):restore(masked.replace(key,"",1),mapping)


def test_paragraph_alignment_reorders_model_segments_without_losing_ids(monkeypatch,tmp_path):
    def handle(request):
        body=json.loads(request.content)
        segments=json.loads(body["messages"][-1]["content"])["segments"]
        return response(json.dumps({"segments":[{"id":s["id"],"translation":"译文 "+s["text"]} for s in reversed(segments)]}))
    transport(monkeypatch,handle)
    result=translate_segments([{"id":"a","text":"Uses 8 GPUs [1]."},{"id":"b","text":"Uses $x^2$."}],settings(tmp_path))
    assert [s["id"] for s in result["segments"]]==["a","b"]
    assert "8 GPUs [1]" in result["segments"][0]["translation"]
    assert "不是翻译正确性" in result["validation_scope"]


def test_incomplete_translation_rejected_not_filled_with_fake_text(monkeypatch,tmp_path):
    transport(monkeypatch,lambda request:response('{"segments":[]}'))
    with pytest.raises(ValueError):translate_segments([{"id":"a","text":"a paragraph"}],settings(tmp_path))
