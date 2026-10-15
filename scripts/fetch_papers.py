"""Explicit, bounded downloads of public research papers; no paid API."""
import hashlib
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data" / "papers"
PAPERS = ["1706.03762v1", "1706.03762v7", "1810.04805v2", "2005.11401v4"]


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    records = []
    identifiers = sys.argv[1:] or PAPERS
    if len(identifiers) > 8 or any(not re.fullmatch(r"\d{4}\.\d{4,5}v\d+", value) for value in identifiers):
        raise ValueError("最多8个明确版本的arXiv标识")
    for identifier in identifiers:
        url = "https://arxiv.org/pdf/" + identifier
        path = TARGET / (identifier + ".pdf")
        record = {"id": identifier, "url": url, "at": datetime.now(timezone.utc).isoformat(),
                  "license_note": "仅本地科研验证；原文版权归作者/出版方，公开分发前逐项核验许可。"}
        try:
            if not path.exists():
                req = urllib.request.Request(url, headers={"User-Agent": "ResearchTrace/0.1 (academic local evaluation)"})
                with urllib.request.urlopen(req, timeout=45) as response:
                    raw = response.read(25 * 1024 * 1024 + 1)
                if not raw.startswith(b"%PDF-") or len(raw) > 25 * 1024 * 1024:
                    raise ValueError("Not a bounded PDF response")
                path.write_bytes(raw)
            raw = path.read_bytes()
            record.update(status="downloaded", bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        except Exception as exc:
            record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
        # Polite API-independent PDF download cadence, bounded at four papers.
        time.sleep(3)
    output = ROOT / "experiments" / ("downloads_" + time.strftime("%Y%m%d_%H%M%S") + ".json")
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
