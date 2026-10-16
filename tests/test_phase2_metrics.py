import pytest
from src.qa_metrics import summarize,wilson
from scripts.score_phase2_qa import validate_reviews


def test_no_real_model_or_human_labels_never_become_zero_accuracy():
    result=summarize([{"record_id":"a","status":"not_run"}])
    assert result["answer_correctness"]["value"] is None
    assert result["hallucination_rate"] is None and result["total_cost_usd"] is None
    assert wilson(0,0) is None


def test_declared_ai_labels_are_not_human_gold():
    records=[{"record_id":"a","status":"completed_real_endpoint","latency_ms":20,"cost_usd":None}]
    annotation={"record_id":"a","reviewer_type":"AI","reviewer_id":"model","complete":True,"answer_correct":True}
    assert summarize(records,[annotation])["human_reviewed_answers"]==0


def test_human_metrics_denominators_and_unknowns():
    records=[{"record_id":"a","status":"completed_real_endpoint","latency_ms":20,"cost_usd":0}]
    annotation={"record_id":"a","reviewer_type":"human","reviewer_id":"reviewer_1","complete":True,"answer_correct":False,"task_success":False,"version_consistent":True,
                "claims":[{"support":"fully_supported"},{"support":"evidence_conflict"},{"support":"cannot_judge"}],
                "citations":[{"relevant_and_supporting":True},{"relevant_and_supporting":False}],"required_evidence_units":[{"covered":True},{"covered":False}]}
    result=summarize(records,[annotation])
    assert result["evidence_support_rate"]==.5 and result["hallucination_rate"]==.5
    assert result["citation_precision"]==.5 and result["citation_recall"]==.5
    assert result["unknown_support_count"]==1 and result["answer_correctness"]["n"]==1
    assert 0<=result["answer_correctness"]["wilson95"][0]<=result["answer_correctness"]["wilson95"][1]<=1


@pytest.mark.parametrize("reviews",[[{"record_id":"missing"}], [{"record_id":"a","complete":"false"}], [{"record_id":"a","complete":True,"reviewer_type":"AI","reviewer_id":"model"}], [{"record_id":"a"},{"record_id":"a"}], [None]])
def test_scoring_rejects_unknown_duplicate_nonhuman_or_malformed_reviews(reviews):
    with pytest.raises(ValueError):validate_reviews([{"record_id":"a","status":"not_run"}],reviews)
