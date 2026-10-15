import pytest
from src.planner import validate_plan, workflow
from src.config import Settings


@pytest.mark.parametrize("payload", [None, {}, {"steps": []}, {"steps": [{"tool": "shell"}]}, {"steps": [{"tool": "retrieve", "command": "whoami"}]}, {"steps": [{"tool": "graph"}] * 5}])
def test_invalid_plan(payload):
    with pytest.raises(ValueError):
        validate_plan(payload)


def test_deterministic_workflow_disclosed():
    result = workflow("graph future outline", [], Settings())
    assert result["mode"] == "deterministic_workflow"
    assert set(result["outputs"]) == {"retrieve", "graph", "future_work", "outline"}


def test_plan_deduplicates_tools():
    assert validate_plan({"steps": [{"tool": "graph"}, {"tool": "graph"}]}) == ["graph"]
