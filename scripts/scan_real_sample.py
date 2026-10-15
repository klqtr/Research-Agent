"""Evaluate OCR on rasterized pages of a real paper, not the official scan file."""
import json
import re
import sys
import time
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import Settings
from src.parsing import parse_pdf


def words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


if __name__ == "__main__":
    target = ROOT / "tmp/pdfs/attention_derived_scan_pages1_7.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)
    original_text = []
    with fitz.open(ROOT / "data/papers/1706.03762v1.pdf") as source, fitz.open() as output:
        for index in (0, 6):
            page = source[index]
            original_text.append(page.get_text())
            image = page.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY)
            generated = output.new_page(width=page.rect.width, height=page.rect.height)
            generated.insert_image(generated.rect, pixmap=image)
        if not target.exists():
            output.save(target)
    start = time.perf_counter()
    parsed = parse_pdf(target.read_bytes(), target.name, Settings())
    results = []
    for idx, original in enumerate(original_text, 1):
        recognized = " ".join(c["text"] for c in parsed["chunks"] if c["page"] == idx)
        gold, pred = words(original), words(recognized)
        results.append({"scan_page": idx, "original_page": (1, 7)[idx - 1],
                        "unique_word_recall": len(gold & pred) / max(1, len(gold)),
                        "unique_word_precision": len(gold & pred) / max(1, len(pred)),
                        "reference_text": original, "recognized_text": recognized})
    record = {"source": "arxiv:1706.03762v1", "kind": "derived_raster_scan_not_official_img_pdf", "raster_scale": 2,
              "latency_seconds": time.perf_counter() - start, "pages": parsed["pages"], "results": results,
              "metric_limitations": "去重词集合指标，不是字符准确率、WER、公式识别或版式还原准确率。"}
    path = ROOT / "experiments" / ("real_scan_" + time.strftime("%Y%m%d_%H%M%S") + ".json")
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(path), "latency_seconds": record["latency_seconds"], "metrics": [{k: v for k, v in r.items() if k not in ("reference_text", "recognized_text")} for r in results]}, ensure_ascii=False))
