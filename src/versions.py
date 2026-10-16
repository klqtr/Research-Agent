"""Version policy, evidence annotation and anchored candidate fact changes."""
from difflib import SequenceMatcher
from .evidence_verifier import normalized, quantities
from .retrieval import terms


def family(paper):
    return paper.get("arxiv_id") or paper["id"]


def select_versions(papers, policy="latest", explicit_version=None):
    if policy not in ("latest","all","explicit"): raise ValueError("未知版本策略")
    if policy=="explicit" and (not isinstance(explicit_version,int) or explicit_version<1): raise ValueError("显式版本须为正整数")
    latest={}
    for paper in papers:
        key=family(paper)
        if key not in latest or (paper.get("version") or 0)>(latest[key].get("version") or 0): latest[key]=paper
    selected=[paper for paper in papers if policy=="all" or (policy=="latest" and latest[family(paper)]["id"]==paper["id"]) or (policy=="explicit" and paper.get("version")==explicit_version)]
    warnings=[{"paper_id":paper["id"],"family":family(paper),"version":paper.get("version"),"latest_available_version":latest[family(paper)].get("version"),
               "status":"older_available_source","selected":any(p["id"]==paper["id"] for p in selected)}
              for paper in papers if (paper.get("version") or 0)<(latest[family(paper)].get("version") or 0)]
    return selected,{"policy":policy,"explicit_version":explicit_version,"selected_ids":[p["id"] for p in selected],"warnings":warnings,
                     "scope":"仅依据本次提供的文献集合，不声称已查询全网最新修订；最新版本不等于事实正确。"}


def annotate_evidence(evidence,papers):
    by_id={paper["id"]:paper for paper in papers}
    return [{**chunk,"source_version":by_id[chunk["paper_id"]].get("version"),"source_family":family(by_id[chunk["paper_id"]]),
             "source_url":(f"https://arxiv.org/abs/{by_id[chunk['paper_id']]['arxiv_id']}v{by_id[chunk['paper_id']]['version']}" if by_id[chunk["paper_id"]].get("arxiv_id") and by_id[chunk["paper_id"]].get("version") else "local_document")} for chunk in evidence]


def compare_version_facts(first,second,query="",limit=30):
    if family(first)!=family(second): raise ValueError("关键事实比较要求相同文献家族，不比较近题不同论文")
    if first["id"]==second["id"]: return {"changes":[],"method":"same_document"}
    old,new=sorted([first,second],key=lambda paper:paper.get("version") or 0)
    query_terms=set(terms(query));used=set();changes=[]
    def body(paper):
        refs=min((ref.get("page",10**6) for ref in paper.get("references",[])),default=10**6)
        return [c for c in paper["chunks"] if c["page"]<refs and c.get("mode")!="unreadable"][:1500]
    newer=body(new)
    newer_terms={chunk["id"]:set(terms(chunk["text"])) for chunk in newer}
    for source in body(old):
        source_terms=set(terms(source["text"]))
        if query_terms and not query_terms & source_terms: continue
        candidates=[(len(source_terms&newer_terms[target["id"]])/max(1,len(source_terms|newer_terms[target["id"]])),target) for target in newer if target["id"] not in used]
        if not candidates: continue
        overlap,target=max(candidates,key=lambda pair:pair[0])
        if overlap<.35: continue
        used.add(target["id"])
        if normalized(source["text"])==normalized(target["text"]): continue
        old_values,new_values=quantities(source["text"]),quantities(target["text"])
        numeric={key:{"old":old_values[key],"new":new_values[key]} for key in old_values.keys()&new_values.keys() if old_values[key]!=new_values[key]}
        if not numeric: continue
        changes.append({"old":{"paper_id":old["id"],"version":old.get("version"),"page":source["page"],"chunk_id":source["id"],"quote":source["text"]},
                        "new":{"paper_id":new["id"],"version":new.get("version"),"page":target["page"],"chunk_id":target["id"],"quote":target["text"]},
                        "changed_quantities":numeric,"lexical_alignment":round(overlap,4),"status":"candidate_fact_change_requires_review"})
        if len(changes)>=limit: break
    return {"from":old["id"],"to":new["id"],"changes":changes,"method":"lexical_paragraph_alignment_and_scoped_quantity_candidates",
            "limitations":"字词对齐/设备层数批次数值候选，不是语义矛盾证明；可能为不同实验配置、排版或OCR差异。没有候选不表示结论未变，新增/删除/跨页变化可能漏检。"}
