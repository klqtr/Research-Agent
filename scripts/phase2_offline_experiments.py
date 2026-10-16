"""Real-document offline policy experiments. No model quality or human labels."""
import hashlib
import json
import sys
import time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from phase2_corpus import load_corpus

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.config import Settings
from src.retrieval import retrieve,validate_claims
from src.versions import select_versions,annotate_evidence,compare_version_facts
from src.evidence_verifier import verify_claims
from src.research_agent import ResearchAgent
from src.research_map import research_map


def main():
    stamp=datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S");folder=ROOT/"experiments"/("phase2_offline_"+stamp);folder.mkdir()
    papers=load_corpus();by_name={p["filename"]:p for p in papers}
    attention=[by_name[name] for name in ("1706.03762v1.pdf","1706.03762v7.pdf")]
    versions=[]
    for policy,explicit in (("all",None),("latest",None),("explicit",1)):
        selected,manifest=select_versions(attention,policy,explicit)
        evidence=annotate_evidence(retrieve("What hardware GPUs were used for training?",selected,k=8,facet_rerank=True),selected)
        versions.append({"policy":policy,"explicit_version":explicit,"selected_ids":manifest["selected_ids"],"retrieved_versions":[e["source_version"] for e in evidence],"evidence":evidence,
                         "interpretation":"版本过滤行为，不代表答案正确性或版本语义冲突检测准确率。"})
    changes=[]
    for names in (("1706.03762v1.pdf","1706.03762v7.pdf"),("2010.08895v1.pdf","2010.08895v3.pdf")):
        start=time.perf_counter();value=compare_version_facts(by_name[names[0]],by_name[names[1]],"")
        changes.append({"files":names,"latency_ms":(time.perf_counter()-start)*1000,"result":value})
    tasks=json.loads((ROOT/"data/phase2_qa_tasks.json").read_text(encoding="utf-8"))
    probes=[]
    for case in tasks["cases"]:
        if case["split"]!="development" or not case["targets"]:continue
        target=case["targets"][0];paper=by_name[target["paper"]]
        chunk=next(c for c in paper["chunks"] if c["id"]==target["chunk_id"])
        evidence=annotate_evidence([chunk],[paper])
        variants=[("source_verbatim",chunk["text"]),("synthetic_unrelated_assertion","This evidence proves that all vaccines are ineffective."),("synthetic_numeric_gpu_assertion","Training uses 99999 GPUs.")]
        for kind,text in variants:
            if kind=="synthetic_numeric_gpu_assertion" and "GPU" not in chunk["text"]:continue
            payload={"claims":[{"text":text,"citations":[{"chunk_id":chunk["id"],"quote":chunk["text"]}]}]}
            legacy=validate_claims(payload,evidence);guard=verify_claims(payload,evidence)
            probes.append({"case_id":case["id"],"kind":kind,"payload":payload,"evidence":evidence,"quote_only_accepted":bool(legacy["claims"]),"guard_released":bool(guard["claims"]),"audit":guard["audit"],
                           "provenance":"Synthetic assertion injected into real-source quotations; not a real model answer or independent human gold."})
    original=[paper for paper in papers if paper["filename"] not in ("2010.08895v1.pdf","2010.08895v3.pdf","1703.00564v3.pdf")]
    map_result=research_map(original)
    agent=ResearchAgent(Settings(data_dir=folder/"local_state"));agent_result=agent.run("Compare training GPUs across Attention versions",attention,use_model=False)
    state=agent.journal.load(agent_result["run_id"])
    negative=[p for p in probes if p["kind"].startswith("synthetic_")]
    summary={"kind":"offline_real_document_policy_validation_not_LLM_quality","llm_requests":0,"paid_api_calls":0,
             "synthetic_assertion_count":len(negative),"quote_only_synthetic_accepted":sum(p["quote_only_accepted"] for p in negative),"guard_synthetic_released":sum(p["guard_released"] for p in negative),
             "verbatim_count":sum(p["kind"]=="source_verbatim" for p in probes),"verbatim_released":sum(p["guard_released"] for p in probes if p["kind"]=="source_verbatim"),
             "version_policies":[{"policy":row["policy"],"retrieved_versions":row["retrieved_versions"]} for row in versions],
             "numeric_change_candidates":[{"files":row["files"],"count":len(row["result"]["changes"])} for row in changes],
             "topic_clusters":len(map_result["topics"]),"timeline_source_dated":sum(bool(row["first_submitted"]) for row in map_result["timeline"]),"timeline_unknown":sum(not row["first_submitted"] for row in map_result["timeline"]),
             "agent_mode":agent_result["mode"],"agent_tool_count":agent_result["tool_count"],
             "source_hashes":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ("src/retrieval.py","src/evidence_verifier.py","src/versions.py","src/research_agent.py")},
             "limitations":"合成断言拒绝率不是幻觉率或语义准确率；版本过滤是策略验收，数值变化候选未人工核实，主题质量未评测。"}
    for name,value in (("versions.json",versions),("version_changes.json",changes),("claim_probes.json",probes),("research_map.json",map_result),("agent_result.json",agent_result),("agent_raw_state.json",state),("summary.json",summary)):
        (folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    (ROOT/"experiments/LATEST_PHASE2_OFFLINE.txt").write_text(str(folder.relative_to(ROOT)),encoding="utf-8")
    print(json.dumps({"folder":str(folder.relative_to(ROOT)),**{k:v for k,v in summary.items() if k not in ("source_hashes","limitations","version_policies")}},ensure_ascii=True))


if __name__=="__main__":main()
