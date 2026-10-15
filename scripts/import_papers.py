"""Import downloaded real PDFs into the local library, keeping all versions."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import Settings
from src.parsing import duplicates, parse_pdf
from src.store import Store


def main():
    settings = Settings()
    store = Store(settings.data_dir)
    results = []
    for path in sorted((ROOT / "data" / "papers").glob("*.pdf")):
        raw = path.read_bytes()
        paper = parse_pdf(raw, path.name, settings)
        matches = duplicates(paper, store.papers())
        target = store.root / (paper["id"] + ".pdf")
        if not target.exists():
            target.write_bytes(raw)
        store.put(paper)
        result = {"filename": path.name, "id": paper["id"], "title": paper["title"], "pages": len(paper["pages"]),
                  "chunks": len(paper["chunks"]), "warnings": paper["warnings"], "duplicates": matches,
                  "decision": "keep_both_for_version_evaluation"}
        print(json.dumps(result, ensure_ascii=False), flush=True)
        results.append(result)
    (ROOT / "experiments" / "import_manifest.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
