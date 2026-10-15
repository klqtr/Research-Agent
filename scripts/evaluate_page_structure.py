"""Save source-anchored layout baseline and selected-cell probes, no invented metrics."""
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.page_analysis import analyze_page, ANALYZER_VERSION


def compact(text):
    return "".join(str(text).split()).lower()


if __name__ == "__main__":
    dataset = ROOT / "data/page_structure_cases.json"
    cases = json.loads(dataset.read_text(encoding="utf-8"))["cases"]
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    folder = ROOT / "experiments" / ("page_structure_" + stamp)
    folder.mkdir()
    pages = {}
    for case in cases:
        key = (case["file"], case["page"])
        if key in pages:
            continue
        file = ROOT / "data/papers" / case["file"]
        ours = analyze_page(file, case["page"])
        with fitz.open(file) as doc:
            page = doc[case["page"]-1]
            native = {}
            for strategy in ("lines", "text"):
                start = time.perf_counter()
                finder = page.find_tables(strategy=strategy)
                native[strategy] = {"latency_ms": (time.perf_counter()-start)*1000,
                                    "tables": [{"bbox": list(t.bbox), "row_count": t.row_count, "column_count": t.col_count, "rows": t.extract()} for t in finder.tables]}
        pages[key] = {"file": case["file"], "page": case["page"], "source_sha256": hashlib.sha256(file.read_bytes()).hexdigest(), "ours": ours, "native_baselines": native}
    checks = []
    for case in cases:
        result = pages[(case["file"],case["page"])]["ours"]
        table = next((t for t in result["tables"] if t["caption"].startswith(case["caption"])), None)
        row = next((r for r in table["rows"] if any(compact(c) == compact(case["row_label"]) for c in r)), []) if table else []
        hits = {col: bool(len(row)>int(col) and compact(row[int(col)]) == compact(value)) for col,value in case["cells"].items()}
        checks.append({"case": case, "table_found": bool(table), "column_count_correct": bool(table and table["column_count"]==case["columns"]), "actual_columns": table["column_count"] if table else None,
                       "selected_row": row, "cell_hits": hits})
    summary = {"analyzer_version": ANALYZER_VERSION, "table_cases": len(checks), "correct_column_cases": sum(c["column_count_correct"] for c in checks),
               "selected_cells": sum(len(c["cell_hits"]) for c in checks), "matched_selected_cells": sum(sum(c["cell_hits"].values()) for c in checks),
               "limitations": "少量开发/回归页，非独立表格测试集；只评指定关键单元格和列数，合并表头、其他值、缺失格、公式及扫描表格质量未通过该指标证明。"}
    (folder/"raw.json").write_text(json.dumps(list(pages.values()),ensure_ascii=False,indent=2),encoding="utf-8")
    (folder/"checks.json").write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding="utf-8")
    (folder/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    (folder/"config.json").write_text(json.dumps({"dataset_sha256":hashlib.sha256(dataset.read_bytes()).hexdigest(),"code_sha256":hashlib.sha256((ROOT/'src/page_analysis.py').read_bytes()).hexdigest(),"fitz_version":fitz.VersionBind,"at":stamp},indent=2),encoding="utf-8")
    (ROOT/'experiments/LATEST_PAGE_STRUCTURE.txt').write_text(str(folder.relative_to(ROOT)),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False));print(folder)
