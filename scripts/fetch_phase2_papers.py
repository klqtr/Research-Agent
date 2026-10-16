"""Three explicit public PDFs for held-out application-domain evaluation only."""
import sys
from pathlib import Path
import fetch_papers

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.arxiv_metadata import fetch_metadata

IDENTIFIERS=["2010.08895v1","2010.08895v3","1703.00564v3"]


if __name__=="__main__":
    if len(sys.argv)>1:raise ValueError("本脚本只下载固定三份跨应用领域评测论文")
    fetch_papers.TARGET=ROOT/"data/phase2_papers"
    fetch_papers.PAPERS=IDENTIFIERS
    fetch_papers.main()
    records,raw=fetch_metadata(IDENTIFIERS)
    output=ROOT/"experiments/phase2_source_metadata";output.mkdir(exist_ok=True)
    (output/"raw.atom").write_bytes(raw)
    import json
    (output/"records.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
