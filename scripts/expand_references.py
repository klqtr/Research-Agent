"""Bounded reference drill-down from actual local references; dry-run by default."""
import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import Settings
from src.parsing import parse_pdf, duplicates
from src.references import reference_candidates
from src.store import Store
from src.tools import family_representatives


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--limit", type=int, default=14)
    args = parser.parse_args()
    if not 1 <= args.limit <= 14:
        raise ValueError("每次最多14篇，不进行无界抓取")
    settings = Settings()
    store = Store(settings.data_dir)
    initial = store.papers()
    candidates = [r for r in reference_candidates(initial) if not r["already_in_library"]][:args.limit]
    at = datetime.now(timezone(timedelta(hours=8)))
    folder = ROOT / "experiments" / ("reference_expansion_" + at.strftime("%Y%m%d_%H%M%S"))
    folder.mkdir()
    (folder/"plan.json").write_text(json.dumps({"at":at.isoformat(),"download_enabled":args.download,"max_total_bytes":80*1024*1024,
                    "max_each_bytes":12*1024*1024,"minimum_gap_seconds":3,"candidates":candidates},ensure_ascii=False,indent=2),encoding="utf-8")
    records, total = [], 0
    target = ROOT / "data/papers"
    target.mkdir(exist_ok=True,parents=True)
    for candidate in candidates:
        record = {"candidate":candidate,"at":datetime.now(timezone.utc).isoformat()}
        if not args.download:
            record["status"] = "dry_run_no_network"
        else:
            identifier = candidate["arxiv_id"]
            requested = identifier + (f"v{max(candidate['explicit_versions'])}" if candidate["explicit_versions"] else "")
            url = "https://arxiv.org/pdf/" + requested
            maximum = min(12*1024*1024,80*1024*1024-total)
            if maximum <= 0:
                break
            try:
                request = urllib.request.Request(url,headers={"User-Agent":"ResearchTrace/0.2 (bounded academic local evaluation)"})
                with urllib.request.urlopen(request,timeout=40) as response:
                    resolved = response.geturl()
                    if urlsplit(resolved).hostname not in ("arxiv.org","export.arxiv.org"):
                        raise ValueError("Unexpected download origin")
                    raw = response.read(maximum+1)
                total += len(raw)
                if len(raw)>maximum or not raw.startswith(b"%PDF-"):
                    raise ValueError("Invalid or oversized PDF response")
                paper = parse_pdf(raw,requested+".pdf",settings)
                if paper.get("arxiv_id") and paper["arxiv_id"] != identifier:
                    raise ValueError("Content arXiv identity does not match requested source")
                paper.update(source_url=url,source_arxiv_id=identifier)
                if not paper.get("arxiv_id"):
                    paper.update(arxiv_id=identifier,identity_basis="verified_arxiv_download_url_not_filename")
                path = target/(requested+".pdf")
                if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()!=hashlib.sha256(raw).hexdigest():
                    path = target/(requested+"_"+paper["id"]+".pdf")
                if not path.exists():
                    path.write_bytes(raw)
                destination = store.root/(paper["id"]+".pdf")
                if not destination.exists():
                    destination.write_bytes(raw)
                matches = duplicates(paper,store.papers())
                store.put(paper)
                record.update(status="downloaded_and_imported",url=url,resolved_url=resolved,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
                              paper_id=paper["id"],title=paper["title"],pages=len(paper["pages"]),arxiv_id=paper.get("arxiv_id"),version=paper.get("version"),duplicates=matches,
                              license_note="仅本地科研验证；未重新分发PDF，公开前核验原作者/出版方许可。")
            except Exception as exc:
                record.update(status="failed",error=f"{type(exc).__name__}: {exc}")
            time.sleep(3)
        records.append(record)
        (folder/"manifest.json").write_text(json.dumps({"at":at.isoformat(),"total_received_bytes":total,"records":records},ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps({k:v for k,v in record.items() if k not in ("candidate","duplicates")},ensure_ascii=False),flush=True)
    final = {"files":len(store.papers()),"families":len(family_representatives(store.papers())),"download_enabled":args.download,
             "successful":sum(r.get("status")=="downloaded_and_imported" for r in records),"failed":sum(r.get("status")=="failed" for r in records),"received_bytes":total}
    (folder/"summary.json").write_text(json.dumps(final,ensure_ascii=False,indent=2),encoding="utf-8")
    (ROOT/"experiments/LATEST_REFERENCE_EXPANSION.txt").write_text(str(folder.relative_to(ROOT)),encoding="utf-8")
    print(json.dumps(final,ensure_ascii=False),flush=True)
