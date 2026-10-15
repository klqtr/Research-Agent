"""Record exact installed project dependencies without reading credentials."""
from importlib.metadata import distributions
from pathlib import Path

if __name__ == "__main__":
    root = Path(".venv/Lib/site-packages").resolve()
    packages = sorted({f"{d.metadata['Name']}=={d.version}" for d in distributions(path=[str(root)])})
    Path("requirements-lock.txt").write_text("\n".join(packages) + "\n", encoding="utf-8")
    print("Recorded", len(packages), "project packages")
