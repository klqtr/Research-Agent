"""One bounded public metadata batch; never replace metadata across mismatched versions."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.arxiv_metadata import fetch_metadata, parse_metadata
from src.config import Settings
from src.store import Store


if __name__ == "__main__":
    store = Store(Settings().data_dir)
    papers = [paper for paper in store.papers() if paper.get("arxiv_id")]
    ids = list(dict.fromkeys(p["arxiv_id"]+(f"v{p['version']}" if p.get("version") else "") for p in papers))
    if len(ids)>30:
        raise ValueError("本脚本只运行一个最多30条的显式元数据批次")
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    folder = ROOT/"experiments"/("metadata_"+stamp)
    folder.mkdir()
    try:
        if len(sys.argv)==3 and sys.argv[1]=="--from-atom":
            raw=Path(sys.argv[2]).read_bytes()
            records=parse_metadata(raw)
            metadata_mode="offline_replay_saved_public_atom"
        elif len(sys.argv)==1:
            records,raw = fetch_metadata(ids)
            metadata_mode="real_public_api_batch"
        else:
            raise ValueError("用法: enrich_metadata.py [--from-atom saved.atom]")
        (folder/"raw.atom").write_bytes(raw)
        changed = []
        for paper in papers:
            metadata = next((item for item in records if item["arxiv_id"]==paper["arxiv_id"] and item.get("version")==paper.get("version")),None)
            if metadata is None:
                changed.append({"paper_id":paper["id"],"status":"not_updated_version_not_matched"})
                continue
            paper.setdefault("document_title",paper["title"])
            paper.update(arxiv_metadata=metadata,title=metadata["title"],authors=metadata["authors"],author="; ".join(a["name"] for a in metadata["authors"]),
                         metadata_identity_basis="exact_arxiv_id_and_version_match")
            store.put(paper)
            changed.append({"paper_id":paper["id"],"status":"updated_from_exact_version_metadata","original_title":paper["document_title"],"title":paper["title"],
                            "author_count":len(metadata["authors"]),"arxiv_id":paper["arxiv_id"],"version":paper["version"]})
        result={"requested_identifiers":ids,"returned_metadata":len(records),"updates":changed,"paid_api_calls":"none","mode":metadata_mode}
    except Exception as exc:
        result={"requested_identifiers":ids,"status":"failed","error":f"{type(exc).__name__}: {exc}","no_synthetic_metadata":True}
    (folder/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    (ROOT/"experiments/LATEST_METADATA.txt").write_text(str(folder.relative_to(ROOT)),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False),flush=True)
