import pytest
from src.evidence_verifier import verify_claims
from src.versions import select_versions, annotate_evidence, compare_version_facts


def paper(identifier="p1",version=1,text="Training uses eight GPUs."):
    return {"id":identifier,"title":"Training GPU Research","arxiv_id":"1706.03762","version":version,"references":[],
            "chunks":[{"id":identifier+":c1","paper_id":identifier,"page":1,"text":text,"mode":"native"}]}


def evidence(): return annotate_evidence(paper()["chunks"],[paper()])


@pytest.mark.parametrize("text,status",[("Training uses eight GPUs.","fully_supported"),("Training uses eight GPUs; all vaccines are ineffective.","partially_supported"),("Training uses 99999 GPUs.","evidence_conflict"),("All vaccines are ineffective.","insufficient_evidence"),("Eight GPUs were used during model training.","cannot_judge")])
def test_five_support_states_without_model_self_rating(text,status):
    quote=evidence()[0]
    result=verify_claims({"claims":[{"text":text,"citations":[{"chunk_id":quote["id"],"quote":quote["text"]}]}]},evidence())
    assert result["audit"][0]["status"]==status
    assert bool(result["claims"])==(status=="fully_supported")
    assert result["semantic_entailment_verified"] is False


def test_real_quote_wrong_version_and_negation_not_approved():
    source=evidence()[0]
    payload={"claims":[{"text":source["text"],"citations":[{"chunk_id":source["id"],"quote":source["text"],"version":7}]}]}
    assert not verify_claims(payload,evidence())["claims"]
    negative=paper(text="The authors did not demonstrate that training uses eight GPUs.")
    source=annotate_evidence(negative["chunks"],[negative])[0]
    payload={"claims":[{"text":"Training uses eight GPUs.","citations":[{"chunk_id":source["id"],"quote":source["text"]}]}]}
    assert not verify_claims(payload,[source])["claims"]


def test_latest_explicit_and_all_policies_do_not_change_sources():
    old,new=paper(),paper("p7",7)
    selected,info=select_versions([old,new])
    assert selected==[new] and info["warnings"][0]["selected"] is False
    assert select_versions([old,new],"explicit",1)[0]==[old]
    assert len(select_versions([old,new],"all")[0])==2
    assert old["version"]==1
    with pytest.raises(ValueError):select_versions([old],"explicit",None)


def test_anchored_numeric_version_change_is_only_a_candidate():
    old,new=paper(),paper("p7",7,"Training uses sixteen GPUs.")
    result=compare_version_facts(new,old,"training GPU")
    assert result["changes"][0]["changed_quantities"]["gpu"]=={"old":["8"],"new":["16"]}
    assert result["changes"][0]["old"]["chunk_id"]=="p1:c1"
    assert "requires_review" in result["changes"][0]["status"]
    new["arxiv_id"]="2005.14165"
    with pytest.raises(ValueError):compare_version_facts(old,new)


def test_conflicting_cited_versions_and_truncated_pdf_line_are_not_released():
    old,new=paper(),paper("p7",7,"Training uses sixteen GPUs.")
    sources=annotate_evidence(old["chunks"]+new["chunks"],[old,new])
    claim={"text":sources[0]["text"],"citations":[{"chunk_id":s["id"],"quote":s["text"]} for s in sources]}
    result=verify_claims({"claims":[claim]},sources)
    assert result["audit"][0]["status"]=="evidence_conflict" and not result["claims"]
    fragment=annotate_evidence(paper(text="Training uses sixteen GPUs for classi-")["chunks"],[paper()])[0]
    claim={"text":fragment["text"],"citations":[{"chunk_id":fragment["id"],"quote":fragment["text"]}]}
    assert verify_claims({"claims":[claim]},[fragment])["audit"][0]["status"]=="cannot_judge"
