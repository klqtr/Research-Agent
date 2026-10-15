"""Central settings. Importing this module never contacts external services."""
import os
from dataclasses import dataclass
from pathlib import Path


def load_local_env():
    path = Path(".env")
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.startswith("RESEARCHTRACE_"):
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv("RESEARCHTRACE_DATA_DIR", "data/library"))
    max_upload_mb: int = int(os.getenv("RESEARCHTRACE_MAX_UPLOAD_MB", "32"))
    max_pages: int = 1200
    max_question_chars: int = 6000
    model_enabled: bool = os.getenv("RESEARCHTRACE_MODEL_ENABLED", "false").lower() == "true"
    model_base_url: str = os.getenv("RESEARCHTRACE_MODEL_BASE_URL", "http://127.0.0.1:11434/v1")
    model_name: str = os.getenv("RESEARCHTRACE_MODEL_NAME", "")
    model_key: str = os.getenv("RESEARCHTRACE_MODEL_API_KEY", "")
    model_timeout: float = float(os.getenv("RESEARCHTRACE_MODEL_TIMEOUT", "45"))
    ocr_language: str = os.getenv("RESEARCHTRACE_OCR_LANGUAGE", "eng")
    tessdata_dir: str = os.getenv("RESEARCHTRACE_TESSDATA_DIR", "data/tessdata")
