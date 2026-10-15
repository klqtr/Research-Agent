"""Explicit optional download of official Tesseract English language data."""
import hashlib
import json
import urllib.request
from pathlib import Path


if __name__ == "__main__":
    root = Path("data/tessdata")
    root.mkdir(parents=True, exist_ok=True)
    url = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/eng.traineddata"
    raw = urllib.request.urlopen(url, timeout=40).read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise ValueError("OCR language data too large")
    (root / "eng.traineddata").write_bytes(raw)
    (root / "SOURCE.json").write_text(json.dumps({"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "license": "Apache-2.0; upstream tesseract-ocr/tessdata_fast"}, indent=2), encoding="utf-8")
    print("OCR English language data ready:", len(raw), "bytes")
