from src.tools import recommend_results
from src.store import Store


def test_reproducible_code_signal_and_feedback():
    results = [{"title": "Attention research", "abstract": "attention methods", "code_available": False},
               {"title": "Attention research with code", "abstract": "attention methods github.com/test/test", "code_available": True}]
    ranked = recommend_results("attention", results, [], [{"title": "Attention research", "weight": 1}])
    assert ranked[0]["code_available"]
    assert ranked[0]["recommendation_components"]["code_link_signal"] == .1
    assert "不是训练" in ranked[0]["recommendation_note"]


def test_feedback_persistence_and_clamp(tmp_path):
    store = Store(tmp_path)
    store.put({"id": "one", "title": "Attention study"})
    for _ in range(5):
        store.feedback("one", 1)
    profile = Store(tmp_path).preference_profile()
    assert profile == [{"title": "Attention study", "weight": 3}]
