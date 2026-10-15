"""Real execution on synthetic stress fixtures, explicitly not official test PDFs."""
import json
import sys
import time
import tracemalloc
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import Settings
from src.parsing import parse_pdf


def main():
    fixtures = ROOT / "tmp" / "pdfs"
    fixtures.mkdir(parents=True, exist_ok=True)
    longpath = fixtures / "synthetic_541_pages.pdf"
    if not longpath.exists():
        with fitz.open() as doc:
            for number in range(541):
                page = doc.new_page()
                page.insert_text((50, 60), f"Synthetic stress fixture - Page {number + 1}\nThis is generated test data, not Understanding Deep Learning.\nTraining batch size 256; hardware 8 GPUs.\n" + ("Evidence chunking bounded memory reproducibility.\n" * 20), fontsize=11)
            doc.save(longpath)
    scanpath = fixtures / "synthetic_scan.pdf"
    if not scanpath.exists():
        with fitz.open() as source:
            page = source.new_page()
            page.insert_text((50, 60), "Synthetic scanned research fixture\nTraining uses eight NVIDIA P100 GPUs.\nBatch size is 256 sequences.\nThis is generated test data, not an official competition file.", fontsize=16)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            with fitz.open() as scan:
                target = scan.new_page(width=page.rect.width, height=page.rect.height)
                target.insert_image(target.rect, pixmap=pix)
                scan.save(scanpath)
    records = []
    sources = [longpath, scanpath]
    book = ROOT / "data/papers/UnderstandingDeepLearning_02_09_26_C.pdf"
    if book.exists():
        sources.append(book)
    for path in sources:
        tracemalloc.start()
        start = time.perf_counter()
        paper = parse_pdf(path.read_bytes(), path.name, Settings())
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        record = {"file": path.name, "fixture": "synthetic_not_official" if path in (longpath, scanpath) else "real_author_release_matching_official_filename_not_pack_hash_verified", "pages": len(paper["pages"]),
                  "chunks": len(paper["chunks"]), "latency_seconds": elapsed,
                  "python_peak_tracemalloc_mb": peak / 1024 / 1024,
                  "memory_limitations": "tracemalloc only tracks Python allocations, not native PDF/OCR engine memory",
                  "page_modes": dict((mode, sum(p["mode"] == mode for p in paper["pages"])) for mode in {p["mode"] for p in paper["pages"]}),
                  "warnings": paper["warnings"], "ocr_text": " ".join(c["text"] for c in paper["chunks"])[:1000] if "scan" in path.name else None}
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    output = ROOT / "experiments" / ("robustness_" + time.strftime("%Y%m%d_%H%M%S") + ".json")
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
