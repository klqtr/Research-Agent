"""Reuse the original library and cache three separately sourced evaluation PDFs."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.config import Settings
from src.store import Store
from src.parsing import parse_pdf


def load_corpus():
    papers=Store(Settings().data_dir).papers()
    metadata_path=ROOT/"experiments/phase2_source_metadata/records.json"
    metadata=json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else []
    cache=ROOT/"tmp/phase2_corpus";cache.mkdir(parents=True,exist_ok=True)
    parser_hash=hashlib.sha256((ROOT/"src/parsing.py").read_bytes()).hexdigest()
    for path in sorted((ROOT/"data/phase2_papers").glob("*.pdf")):
        raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest();cached=cache/(digest+parser_hash[:10]+".json")
        if cached.exists():paper=json.loads(cached.read_text(encoding="utf-8"))
        else:
            paper=parse_pdf(raw,path.name,Settings())
            record=next((item for item in metadata if item["arxiv_id"]==paper.get("arxiv_id") and item["version"]==paper.get("version")),None)
            if record:paper.update(arxiv_metadata=record,title=record["title"],authors=record["authors"])
            cached.write_text(json.dumps(paper,ensure_ascii=False),encoding="utf-8")
        if paper["id"] not in {p["id"] for p in papers}:papers.append(paper)
    return papers


if __name__=="__main__":
    papers=load_corpus()
    selected=[p for p in papers if p["filename"] in {"2010.08895v1.pdf","2010.08895v3.pdf","1703.00564v3.pdf"}]
    rows=[{key:p.get(key) for key in ("id","filename","title","arxiv_id","version")} | {"pages":len(p["pages"]),"chunks":len(p["chunks"])} for p in selected]
    (ROOT/"data/phase2_corpus_manifest.json").write_text(json.dumps({"original_library_modified":False,"new_papers":rows,"application_domains":["scientific_computing_PDE","molecular_property_learning"],"note":"应用领域扩展仍属机器学习交叉研究，不能宣称已覆盖所有学科。"},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(rows,ensure_ascii=True))
