"""Run and record the whole suite; partial module checks cannot replace this pointer."""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    relative = f"experiments/full_tests_{stamp}.xml"
    command = [sys.executable, "-m", "pytest", "-q", f"--basetemp=tmp/pytest_full_{stamp}", f"--junitxml={relative}"]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (ROOT / f"experiments/full_tests_{stamp}.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    metadata = {"scope": "entire_pytest_suite", "command": command, "exit_code": run.returncode, "xml": relative}
    (ROOT / f"experiments/full_tests_{stamp}_config.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    if (ROOT / relative).exists():
        (ROOT / "experiments/LATEST_TESTS.txt").write_text(relative, encoding="utf-8")
    print(run.stdout)
    if run.stderr:
        print(run.stderr, file=sys.stderr)
    sys.exit(run.returncode)
