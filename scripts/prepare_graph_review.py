"""All directed library-family pairs, with blank external-human review labels."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.config import Settings
from src.store import Store
from src.tools import graph,family_representatives


if __name__=="__main__":
    target=ROOT/"data/phase2_graph_review.json"
    if target.exists():raise ValueError("已有标注表，不能覆盖；请创建新版本")
    papers=family_representatives(Store(Settings().data_dir).papers());result=graph(papers)
    edges={(e["source"],e["target"]):e for e in result["edges"]}
    pairs=[]
    for source in papers:
        pages=sorted({reference.get("page") for reference in source["references"] if reference.get("page")})
        for cited in papers:
            if source["id"]==cited["id"]:continue
            edge=edges.get((source["id"],cited["id"]))
            pairs.append({"source_paper_id":source["id"],"source_title":source["title"],"target_paper_id":cited["id"],"target_title":cited["title"],
                          "target_arxiv_id":cited.get("arxiv_id"),"proposal_present":bool(edge),"algorithm_proposal_not_gold":edge,
                          "source_reference_pages_for_full_review":pages,"is_citation_human_gold":None,"reviewer_id":None,"reviewer_type":None,
                          "review_note":None,"reviewed_source_pages":[],"second_reviewer_label":None})
    target.write_text(json.dumps({"scope":"all_directed_pairs_20_families","pairs":pairs,"label_status":"no_human_annotation_performed",
                                  "instructions":"需真实审阅全部来源参考页再判断未匹配边；算法有/无匹配不是金标。只有外部人工完成后才计算精确率/召回率；记录审阅者、页码和分歧。"},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"pairs":len(pairs),"algorithm_proposals":len(edges),"human_labels":0}))
