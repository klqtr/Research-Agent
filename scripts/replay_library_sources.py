"""Verify the exact library by default; opt in to bounded public source downloads."""
import argparse
import hashlib
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BOOK_URL="https://github.com/udlbook/udlbook/releases/download/v5.0.3/UnderstandingDeepLearning_02_09_26_C.pdf"


def validate_record(record):
    filename=record["filename"]
    if Path(filename).name!=filename or not re.fullmatch(r"[A-Za-z0-9_.-]+\.pdf",filename) or "/" in filename or "\\" in filename:
        raise ValueError("Source filename must be a single PDF basename")
    if record["url"]!=BOOK_URL and not re.fullmatch(r"https://arxiv\.org/pdf/\d{4}\.\d{4,5}v\d+",record["url"]):
        raise ValueError("Only exact-version arXiv PDFs and the fixed author release are allowed")
    if not re.fullmatch(r"[a-f0-9]{64}",record["sha256"]): raise ValueError("Invalid SHA256")
    if not 0<record["bytes"]<=80*1024*1024: raise ValueError("Invalid source size")


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--download-missing",action="store_true");args=parser.parse_args()
    lock=json.loads((ROOT/"data/library_sources.json").read_text(encoding="utf-8"))
    if not 1<=len(lock["files"])<=30: raise ValueError("Source count outside replay bound")
    for record in lock["files"]: validate_record(record)
    target=ROOT/"data/papers";target.mkdir(parents=True,exist_ok=True)
    rows=[];received=0
    for record in lock["files"]:
        path=target/record["filename"]
        item={"filename":record["filename"],"url":record["url"],"expected_sha256":record["sha256"]}
        try:
            if path.exists():
                raw=path.read_bytes();item["operation"]="existing_file_read_only"
            elif args.download_missing:
                if received+record["bytes"]>150*1024*1024: raise ValueError("150MiB total download budget reached")
                request=urllib.request.Request(record["url"],headers={"User-Agent":"ResearchTrace/0.2 bounded reproduction"})
                with urllib.request.urlopen(request,timeout=45) as response:
                    raw=response.read(record["bytes"]+1)
                received+=len(raw);item["operation"]="public_source_download"
                if len(raw)!=record["bytes"] or hashlib.sha256(raw).hexdigest()!=record["sha256"]:
                    raise ValueError("Source content differs from locked bytes; nothing was written or overwritten")
                if not raw.startswith(b"%PDF-"): raise ValueError("Not a PDF")
                path.write_bytes(raw)
                time.sleep(3)
            else:
                item["status"]="missing_not_downloaded";rows.append(item);continue
            item["actual_sha256"]=hashlib.sha256(raw).hexdigest()
            item["status"]="verified" if len(raw)==record["bytes"] and item["actual_sha256"]==record["sha256"] else "mismatch_original_preserved"
        except Exception as exc:
            item.update(status="failed",error=f"{type(exc).__name__}: {exc}")
        rows.append(item)
    result={"at":datetime.now(timezone.utc).isoformat(),"download_enabled":args.download_missing,"received_bytes":received,"records":rows,
            "verified":sum(r["status"]=="verified" for r in rows),"expected":len(rows),"scope":"Exact source-byte verification, not a network reproduction unless download_enabled and files were missing."}
    output=ROOT/"experiments"/("source_replay_"+time.strftime("%Y%m%d_%H%M%S")+".json")
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"file":str(output.relative_to(ROOT)),"verified":result["verified"],"expected":len(rows),"received_bytes":received}))
    return 0 if result["verified"]==len(rows) else 1


if __name__=="__main__": raise SystemExit(main())
