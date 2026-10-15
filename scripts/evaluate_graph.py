"""Audit graph anchors and seven inspected repair cases; not a blind graph benchmark."""
import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.citation_graph import compact
from src.config import Settings
from src.store import Store
from src.tools import graph

# These seven quotations were inspected after the matching change. They are
# explicit regression cases and cannot estimate unbiased recall or precision.
REPAIR_CASES=[
    (None,"1810.04805",486,"Devlin"),
    (None,"1409.0473",479,"Bahdanau"),
    ("2004.04906","1810.04805",9,"Devlin"),
    ("2005.14165","1910.10683",73,"Raffel"),
    ("2002.08909","2002.08910",10,"Roberts"),
    ("1910.13461","1810.04805",9,"Devlin"),
    ("1705.03122","1701.06538",11,"Shazeer"),
]


def main():
    papers=Store(Settings().data_dir).papers()
    start=time.perf_counter();result=graph(papers);elapsed=(time.perf_counter()-start)*1000
    nodes={n["id"]:n for n in result["nodes"]};by_id={p["id"]:p for p in papers}
    baseline=json.loads((ROOT/"experiments/graph_before_matching_change.json").read_text(encoding="utf-8"))
    same_library=set(baseline["library_ids"])==set(by_id)
    if not same_library: raise ValueError("Controlled comparison requires identical library IDs")
    old_edges={(e["source"],e["target"]) for e in baseline["graph"]["edges"]}
    current_edges={(e["source"],e["target"]) for e in result["edges"]}
    audits=[]
    for edge in result["edges"]:
        source=by_id[edge["source"]]
        chunk=next((c for c in source["chunks"] if c["id"]==edge["source_chunk_id"]),None)
        audits.append({"source":edge["source"],"target":edge["target"],"page":edge["source_page"],
                       "chunk_exists_on_page":bool(chunk and chunk["page"]==edge["source_page"]),
                       "reference_quote_is_stored_source_reference":any(r["text"]==edge["reference_quote"] and r.get("page")==edge["source_page"] for r in source["references"]),
                       "limitation":"Anchor integrity is not a semantic-entailment or scholarly-quality judgment."})
    repairs=[]
    for source_id,target_id,page,author in REPAIR_CASES:
        edge=next((e for e in result["edges"] if nodes[e["source"]].get("arxiv_id")==source_id and nodes[e["target"]].get("arxiv_id")==target_id),None)
        source=by_id[edge["source"]] if edge else None
        raw_source_quote=False
        if source:
            import fitz
            with fitz.open(Settings().data_dir/(source["id"]+".pdf")) as doc:
                page_text="\n".join(block[4] for block in doc[page-1].get_text("blocks",sort=True) if len(block)>6 and block[6]==0)
                raw_source_quote=author.casefold() in page_text.casefold() and compact(nodes[edge["target"]]["title"]) in compact(page_text)
        repairs.append({"source_arxiv_id":source_id,"target_arxiv_id":target_id,"expected_page":page,"expected_author":author,
                        "matched":bool(edge and edge["source_page"]==page and author in edge["reference_quote"]),
                        "complete_title_and_author_in_original_pdf_page":raw_source_quote,
                        "pdf_check_method":"physical-page text blocks, preserving within-block reading order; not visual or semantic equivalence",
                        "was_missing_before":bool(edge and (edge["source"],edge["target"]) not in old_edges),
                        "reference_quote":edge["reference_quote"] if edge else None})
    stamp=datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    folder=ROOT/"experiments"/("graph_"+stamp);folder.mkdir()
    summary={"nodes":len(result["nodes"]),"edges":len(result["edges"]),"single_run_latency_ms":elapsed,
             "same_library_as_baseline":same_library,"old_edges":len(old_edges),"added_edges":len(current_edges-old_edges),"removed_edges":len(old_edges-current_edges),
             "anchor_checks":len(audits),"anchors_verified":sum(a["chunk_exists_on_page"] and a["reference_quote_is_stored_source_reference"] for a in audits),
             "repair_cases":repairs,"algorithm":result["algorithm"],
             "evaluation_scope":"Post-change inspection and regression, not an independent precision/recall study.",
             "source_sha256":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ("src/citation_graph.py","src/tools.py")}}
    (folder/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    (folder/"graph.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    (folder/"anchor_checks.json").write_text(json.dumps(audits,ensure_ascii=False,indent=2),encoding="utf-8")
    with (folder/"edges.csv").open("w",encoding="utf-8-sig",newline="") as output:
        writer=csv.DictWriter(output,fieldnames=["source","target","source_page","source_chunk_id","basis","reference_quote"]);writer.writeheader()
        writer.writerows({key:edge[key] for key in writer.fieldnames} for edge in result["edges"])
    (ROOT/"experiments/LATEST_GRAPH.txt").write_text(str(folder.relative_to(ROOT)),encoding="utf-8")
    print(json.dumps({"folder":str(folder.relative_to(ROOT)),"nodes":summary["nodes"],"edges":summary["edges"],"anchors_verified":summary["anchors_verified"],"repaired":sum(r["matched"] for r in repairs),"original_pdf_checks":sum(r["complete_title_and_author_in_original_pdf_page"] for r in repairs)},ensure_ascii=True))


if __name__=="__main__": main()
