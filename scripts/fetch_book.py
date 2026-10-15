"""Download the exact book edition linked by the author's official website."""
import hashlib
import json
import time
import urllib.request
from pathlib import Path

if __name__ == "__main__":
    url = "https://github.com/udlbook/udlbook/releases/download/v5.0.3/UnderstandingDeepLearning_02_09_26_C.pdf"
    path = Path("data/papers/UnderstandingDeepLearning_02_09_26_C.pdf")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(url, timeout=60) as response:
            raw = response.read(80 * 1024 * 1024 + 1)
        if not raw.startswith(b"%PDF-") or len(raw) > 80 * 1024 * 1024:
            raise ValueError("Invalid or oversized book PDF")
        path.write_bytes(raw)
    raw = path.read_bytes()
    record = {"url": url, "author_site": "https://udlbook.github.io/udlbook/", "bytes": len(raw),
              "sha256": hashlib.sha256(raw).hexdigest(), "local_only": True,
              "license_note": "作者公开提供的个人阅读版本；不得据此假设可以重新公开分发PDF。"}
    Path("experiments/book_download_" + time.strftime("%Y%m%d_%H%M%S") + ".json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False), flush=True)
