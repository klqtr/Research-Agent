"""Run and record the whole suite; partial module checks cannot replace this pointer."""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.publication_privacy import sanitize_document, sanitize_text


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    relative = f"experiments/full_tests_{stamp}.xml"
    command = [sys.executable, "-m", "pytest", "-q", f"--basetemp=tmp/pytest_full_{stamp}", f"--junitxml={relative}"]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    private = ROOT / "tmp" / "private_test_runs" / stamp
    private.mkdir(parents=True, exist_ok=True)
    (private / "original_output.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    if (ROOT / relative).exists():
        original_xml = (ROOT / relative).read_bytes()
        (private / "original_tests.xml").write_bytes(original_xml)
        (ROOT / relative).write_text(sanitize_text(original_xml.decode("utf-8")), encoding="utf-8")
    (ROOT / f"experiments/full_tests_{stamp}.log").write_text(sanitize_text(run.stdout + run.stderr), encoding="utf-8")
    metadata = {"scope": "entire_pytest_suite", "command": command, "exit_code": run.returncode, "xml": relative}
    metadata["public_copy"] = "Locations and identities redacted; results unchanged; originals retained locally."
    (ROOT / f"experiments/full_tests_{stamp}_config.json").write_text(sanitize_document(json.dumps(metadata, ensure_ascii=False, indent=2), ".json"), encoding="utf-8")
    if (ROOT / relative).exists():
        (ROOT / "experiments/LATEST_TESTS.txt").write_text(relative, encoding="utf-8")
    print(sanitize_text(run.stdout))
    if run.stderr:
        print(sanitize_text(run.stderr), file=sys.stderr)
    sys.exit(run.returncode)
