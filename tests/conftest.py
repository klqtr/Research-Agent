"""Keep pytest temporary artifacts inside this workspace on restricted Windows hosts."""
from pathlib import Path

Path("tmp").mkdir(exist_ok=True)
