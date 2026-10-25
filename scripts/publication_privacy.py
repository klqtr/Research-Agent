"""Prepare disclosed public copies; never commit, rewrite history, or contact GitHub."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".xml", ".log", ".csv", ".atom", ".svg", ".html"}
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
CREDENTIAL = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16})")
USER_PATH = re.compile(r"(?i)\b[A-Z]:[\\/]+Users[\\/]+[^\s\"'<>\r\n]+|/(?:home|Users|root)/[^\s\"'<>\r\n]+")
HOST_ATTRIBUTE = re.compile(r'(\bhostname\s*=\s*[\"\x27])[^\"\x27]*([\"\x27])', re.I)
MACHINE_NAME = re.compile(r"\b(?:LAPTOP|DESKTOP)-[A-Z0-9-]+\b", re.I)
PRIVATE_IP = re.compile(r"\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b")
PRIVATE_ONLY_PATHS = {"reports/screenshots/reader.jpg", "checkpoints/LATEST.json"}
MINIMIZED_SMOKE_FILES = {"experiments/live_smoke_20261016_010808.json", "experiments/live_smoke_20261016_012406.json"}


def sanitize_text(text, root=ROOT):
    """Preserve results; transform only private locations, identities and credentials."""
    root = Path(root)
    for original in sorted({str(root), root.as_posix(), str(root).replace("\\", "\\\\")}, key=len, reverse=True):
        text = text.replace(original, ".")
    # Bracket placeholders remain valid JSON and XML character data.
    text = USER_PATH.sub("[LOCAL_PATH]", text)
    text = HOST_ATTRIBUTE.sub(lambda match: match[1] + "redacted-host" + match[2], text)
    text = MACHINE_NAME.sub("redacted-host", text)
    text = EMAIL.sub("[EMAIL_REDACTED]", text)
    text = PRIVATE_IP.sub("[PRIVATE_IP_REDACTED]", text)
    return CREDENTIAL.sub("[CREDENTIAL_REDACTED]", text)


def tracked_files():
    raw = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT)
    return [name.decode("utf-8") for name in raw.split(b"\0") if name]


def sanitize_document(text, suffix, root=ROOT):
    """Decode structured strings first, so redaction never breaks JSON escaping."""
    def visit(value):
        if isinstance(value, str):
            return sanitize_text(value, root)
        if isinstance(value, list):
            return [visit(item) for item in value]
        if isinstance(value, dict):
            return {key: visit(item) for key, item in value.items()}
        return value
    if suffix == ".json":
        original = json.loads(text)
        redacted = visit(original)
        return text if original == redacted else json.dumps(redacted, ensure_ascii=False, indent=2) + "\n"
    if suffix == ".jsonl":
        lines = []
        changed = False
        for line in text.splitlines():
            if not line.strip():
                lines.append(line)
                continue
            original = json.loads(line)
            redacted = visit(original)
            changed |= original != redacted
            lines.append(json.dumps(redacted, ensure_ascii=False) if original != redacted else line)
        return "\n".join(lines) + ("\n" if text.endswith("\n") else "") if changed else text
    return sanitize_text(text, root)


def public_document(name, text, root=ROOT):
    """Minimize two old API dumps; keep status, latency and useful result evidence."""
    result = sanitize_document(text, Path(name).suffix.lower(), root)
    if name not in MINIMIZED_SMOKE_FILES:
        return result
    rows = json.loads(result)
    changed = False
    for record in rows:
        if record.get("endpoint") != "/api/papers" or not isinstance(record.get("response"), list):
            continue
        for paper in record["response"]:
            omitted = {}
            for field in ("pages", "headings", "references"):
                if field in paper:
                    omitted[field] = len(paper.pop(field))
            if omitted:
                paper["public_omitted_array_counts"] = omitted
                changed = True
        if changed:
            record["public_response_notice"] = "Paper content arrays omitted for public distribution; original response retained locally. Status and latency unchanged."
    return json.dumps(rows, ensure_ascii=False, indent=2) + "\n" if changed else result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="read-only scan; default")
    args = parser.parse_args()
    findings = []
    for name in tracked_files():
        path = ROOT / name
        if not path.is_file() or path.suffix.lower() in {".jpg", ".jpeg", ".png", ".pdf"}:
            continue
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            findings.append({"path": name, "reason": "encoding_requires_review"})
            continue
        needs_redaction = (public_document(name, text) != text) if path.suffix.lower() in TEXT_SUFFIXES else bool(CREDENTIAL.search(text))
        if needs_redaction:
            findings.append({"path": name, "reason": "private_pattern", "sha256": hashlib.sha256(raw).hexdigest()})
    print(json.dumps({"mode": "read_only", "findings": findings}, ensure_ascii=False, indent=2))
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(main())
