"""Recoverable source/results snapshot. Excludes credentials and large external PDFs."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOTS = ("src", "tests", "scripts", "docs", "reports", "experiments", "output")
SUFFIXES = {".py", ".js", ".css", ".html", ".md", ".json", ".jsonl", ".xml", ".txt", ".svg", ".png", ".jpg", ".pdf", ".ps1"}


def main():
    now = datetime.now(timezone(timedelta(hours=8)))
    folder = ROOT / "checkpoints"
    folder.mkdir(exist_ok=True)
    target = folder / ("researchtrace_" + now.strftime("%Y%m%d_%H%M%S") + ".zip")
    paths = []
    for root in ALLOWED_ROOTS:
        for path in (ROOT / root).rglob("*"):
            if path.is_file() and path.suffix in SUFFIXES and "__pycache__" not in path.parts:
                if path.parent == ROOT / "docs/sources" and path.suffix == ".js":
                    continue
                paths.append(path)
    for name in ("README.md", "NIGHT_PROGRESS.md", "NEXT_STEPS.md", "RUN_LOG.md", "MORNING_REPORT.md", "requirements.txt", "requirements-dev.txt", "requirements-lock.txt", ".env.example", ".gitignore", ".gitattributes", "pytest.ini", "Dockerfile"):
        path = ROOT / name
        if path.is_file():
            paths.append(path)
    paths.extend(path for path in (ROOT / "data").glob("*.json"))
    records = []
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as output:
        for path in sorted(set(paths)):
            raw = path.read_bytes()
            name = path.relative_to(ROOT).as_posix()
            output.writestr(name, raw)
            records.append({"path": name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        output.writestr("CHECKPOINT_MANIFEST.json", json.dumps({"at": now.isoformat(), "exclusions": [".env", "original_pdfs", "library_sqlite", "venv", "git"], "files": records}, ensure_ascii=False, indent=2))
    result = {"path": str(target.relative_to(ROOT)), "files": len(records), "bytes": target.stat().st_size, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    (folder / "LATEST.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
