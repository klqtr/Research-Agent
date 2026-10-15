"""Offline recovery probe in an isolated temporary store; original library untouched."""
import hashlib
import json
import sys
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.arxiv_metadata import parse_metadata
from src.config import Settings
from src.parsing import parse_pdf
from src.store import Store
from src.tools import graph


def main():
    stamp=datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    folder=ROOT/"experiments"/("rebuild_"+stamp);folder.mkdir()
    settings=replace(Settings(),data_dir=ROOT/"tmp"/("rebuild_library_"+stamp))
    store=Store(settings.data_dir)
    lock=json.loads((ROOT/"data/library_sources.json").read_text(encoding="utf-8"))
    metadata=parse_metadata((ROOT/lock["metadata_atom"]).read_bytes())
    rows=[];started=time.perf_counter()
    for record in lock["files"]:
        raw=(ROOT/"data/papers"/record["filename"]).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=record["sha256"]: raise ValueError("Locked PDF hash mismatch")
        paper=parse_pdf(raw,record["filename"],settings)
        source_metadata=next((item for item in metadata if item["arxiv_id"]==paper.get("arxiv_id") and item["version"]==paper.get("version")),None)
        if source_metadata:
            paper.update(document_title=paper["title"],arxiv_metadata=source_metadata,title=source_metadata["title"],authors=source_metadata["authors"],
                         author="; ".join(a["name"] for a in source_metadata["authors"]),metadata_identity_basis="exact_arxiv_id_and_version_match")
        store.put(paper)
        rows.append({"filename":record["filename"],"expected_id":record["paper_id"],"actual_id":paper["id"],"metadata_restored":bool(source_metadata),"pages":len(paper["pages"]),"chunks":len(paper["chunks"])})
    result=graph(store.papers())
    graph_folder=ROOT/(ROOT/"experiments/LATEST_GRAPH.txt").read_text(encoding="utf-8").strip()
    expected=json.loads((graph_folder/"graph.json").read_text(encoding="utf-8"))
    edge_keys=lambda value:{(e["source"],e["target"],e["source_page"],e["source_chunk_id"]) for e in value["edges"]}
    summary={"network_calls":0,"original_library_modified":False,"elapsed_seconds":time.perf_counter()-started,"files":rows,
             "id_checks_passed":sum(r["expected_id"]==r["actual_id"] for r in rows),"metadata_restored":sum(r["metadata_restored"] for r in rows),
             "nodes":len(result["nodes"]),"edges":len(result["edges"]),"exact_edge_and_anchor_set_reproduced":edge_keys(result)==edge_keys(expected),
             "exact_node_ranks_reproduced":result["nodes"]==expected["nodes"],"scope":"Offline original-byte/parser/Atom/store/graph recovery; does not prove future source URLs will retain identical bytes."}
    (folder/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    (folder/"graph.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    (ROOT/"experiments/LATEST_REBUILD.txt").write_text(str(folder.relative_to(ROOT)),encoding="utf-8")
    print(json.dumps({key:value for key,value in summary.items() if key!="files"},ensure_ascii=True))
    return 0 if summary["id_checks_passed"]==21 and summary["exact_edge_and_anchor_set_reproduced"] and summary["exact_node_ranks_reproduced"] else 1


if __name__=="__main__": raise SystemExit(main())
