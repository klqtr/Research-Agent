"""Bounded page-by-page extraction. Formula transcription is not fabricated."""
import hashlib
import re
from datetime import datetime, timezone
import fitz


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def tokens(text):
    # English words and Chinese bigrams, no downloaded model required.
    words = re.findall(r"[a-z0-9]+", text.lower())
    for part in re.findall(r"[\u4e00-\u9fff]+", text):
        words.extend(part[i:i + 2] for i in range(max(1, len(part) - 1)))
    return words


def shingles(text):
    words = tokens(text)
    return {" ".join(words[i:i + 4]) for i in range(max(0, len(words) - 3))}


def similarity(a, b):
    sa, sb = shingles(a), shingles(b)
    return len(sa & sb) / len(sa | sb) if sa and sb else 0.0


def parse_pdf(raw, filename, settings):
    if not raw.startswith(b"%PDF-"):
        raise ValueError("需要有效 PDF 文件")
    paper_id = hashlib.sha256(raw).hexdigest()[:20]
    chunks, pages, headings, references, warnings = [], [], [], [], []
    layout_title = ""
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
    except Exception as exc:
        raise ValueError("PDF 无法解析") from exc
    with doc:
        if doc.is_encrypted:
            raise ValueError("不支持加密 PDF，请先提供可读取副本")
        if not 0 < len(doc) <= settings.max_pages:
            raise ValueError("PDF 页数超出允许范围")
        in_refs = False
        for number, page in enumerate(doc, 1):
            if number == 1:
                candidates = []
                for block in page.get_text("dict")["blocks"]:
                    lines = block.get("lines", [])
                    for line in lines:
                        # arXiv's rotated side label is often larger than the paper title.
                        if abs(line.get("dir", (1, 0))[1]) > .1:
                            continue
                        spans = line.get("spans", [])
                        line_text = normalize(" ".join(s["text"] for s in spans))
                        if 8 < len(line_text) < 200 and not re.search(r"arxiv|copyright|permission|provided proper|^abstract$", line_text, re.I):
                            candidates.append((max((s["size"] for s in spans), default=0), line_text))
                if candidates:
                    largest = max(size for size, _ in candidates)
                    layout_title = " ".join(t for size, t in candidates if size >= largest - .3)[:300]
            textpage = None
            text = page.get_text()
            mode = "native"
            if len(text.strip()) < 24:
                try:
                    from pathlib import Path
                    tessdata = settings.tessdata_dir if Path(settings.tessdata_dir, settings.ocr_language + ".traineddata").exists() else None
                    textpage = page.get_textpage_ocr(language=settings.ocr_language, dpi=150, full=True, tessdata=tessdata)
                    mode = "ocr"
                except Exception:
                    warnings.append(f"第 {number} 页缺少可用文本且 OCR 不可用；不能据此回答该页事实")
                    mode = "unreadable"
            blocks = page.get_text("blocks", textpage=textpage, sort=True)
            page_chunks = []
            for block in blocks:
                if len(block) > 6 and block[6] != 0:
                    continue
                content = normalize(block[4])
                if not content:
                    continue
                for start in range(0, len(content), 1200):
                    part = content[start:start + 1200]
                    cid = f"{paper_id}:p{number}:c{len(chunks)}"
                    item = {"id": cid, "paper_id": paper_id, "page": number,
                            "bbox": list(block[:4]), "text": part, "mode": mode}
                    chunks.append(item)
                    page_chunks.append(cid)
                if re.match(r"^(\d+(?:\.\d+){0,2}\s+[A-Z]|Abstract$|References$|Appendix|Conclusion|Future Work)", content) and len(content) < 160:
                    headings.append({"title": content, "page": number, "chunk_id": chunks[-1]["id"]})
                if re.match(r"^(References|Bibliography)$", content, re.I):
                    in_refs = True
                elif in_refs:
                    references.append({"text": content, "page": number, "chunk_id": chunks[-1]["id"]})
            pages.append({"number": number, "width": page.rect.width, "height": page.rect.height,
                          "mode": mode, "chunks": page_chunks, "images": len(page.get_images())})
        metadata = doc.metadata or {}
        first = [c["text"] for c in chunks if c["page"] == 1]
        title = metadata.get("title", "").strip()
        if not title or title.lower() in ("untitled", "article"):
            title = layout_title or (first[0][:240] if first else filename)
        full = "\n".join(c["text"] for c in chunks)
        # Identity comes from document content, never the uploaded filename.
        # A citation in a late reference list must never become this document's identity.
        arxiv = re.search(r"arXiv\s*:\s*(\d{4}\.\d{4,5})(?:v(\d+))?", "\n".join(first), re.I)
        return {"id": paper_id, "filename": filename, "title": title, "author": metadata.get("author", ""),
                "arxiv_id": arxiv.group(1) if arxiv else None,
                "version": int(arxiv.group(2)) if arxiv and arxiv.group(2) else None,
                "pages": pages, "chunks": chunks, "headings": headings, "references": references,
                "warnings": warnings, "created_at": datetime.now(timezone.utc).isoformat(),
                "limitations": ["原生文本与坐标已提取；复杂公式未保证还原 LaTeX，表格未保证单元格结构。"]}


def duplicates(candidate, papers):
    text = " ".join(c["text"] for c in candidate["chunks"])[:250000]
    found = []
    for paper in papers:
        other = " ".join(c["text"] for c in paper["chunks"])[:250000]
        score = similarity(text, other)
        same_family = bool(candidate["arxiv_id"] and candidate["arxiv_id"] == paper.get("arxiv_id"))
        if candidate["id"] == paper["id"] or score >= 0.55 or same_family:
            newer = (paper.get("version") or 0) >= (candidate.get("version") or 0)
            found.append({"paper_id": paper["id"], "title": paper["title"], "similarity": round(score, 4),
                          "same_arxiv": same_family, "existing_version": paper.get("version"),
                          "recommendation": "建议保留库中现有版本" if same_family and newer else "请比较正文后决定保留或替换"})
    return found
