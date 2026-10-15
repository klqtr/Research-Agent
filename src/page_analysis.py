"""Lazy, source-anchored page structure extraction with explicit heuristic limits."""
import csv
import hashlib
import io
import json
import os
import re
import statistics
import time
import tempfile
from pathlib import Path
import fitz
from .parsing import normalize

ANALYZER_VERSION = "caption-layout-v4-neighbour-scope"
TABLE_CAPTION = re.compile(r"^Table\s+\d+(?:\.\d+)*\s*(?:[:：]|\.(?!\d))", re.I)
FIGURE_CAPTION = re.compile(r"^(?:Figure|Fig\.)\s*\d+(?:\.\d+)*\s*(?:[:：]|\.(?!\d))", re.I)


def text_lines(block):
    result = []
    for line in block.get("lines", []):
        spans = line.get("spans", [])
        content = normalize(" ".join(span["text"] for span in spans))
        if content:
            result.append({"text": content, "bbox": list(line["bbox"]),
                           "size": max((span["size"] for span in spans), default=10),
                           "fonts": sorted({span["font"] for span in spans})})
    return result


def cell_like(block):
    lines = text_lines(block)
    if len(lines) < 3 or statistics.median(len(line["text"]) for line in lines) > 38:
        return False
    numeric = sum(bool(re.search(r"\d", line["text"])) for line in lines)
    # Prose lines are normally stacked; table cells have multiple x positions at
    # near-identical y coordinates. A numeric column also gives useful support.
    aligned = max((sum(abs(other["bbox"][1] - line["bbox"][1]) < 4 for other in lines) for line in lines), default=0)
    return aligned >= 2 or numeric / len(lines) >= .35


def table_neighbours(caption, blocks):
    # A PDF text block can contain cells from two side-by-side tables. Scope the
    # actual lines horizontally to this caption before finding neighbouring rows.
    left, right = float("-inf"), float("inf")
    for other in blocks:
        if other is caption:
            continue
        text = normalize(" ".join(line["text"] for line in text_lines(other)))
        if not TABLE_CAPTION.match(text):
            continue
        # Scope only when another table caption actually shares this horizontal
        # band. A short standalone caption must not crop a wider table's columns.
        overlap = min(caption["bbox"][3], other["bbox"][3]) - max(caption["bbox"][1], other["bbox"][1])
        if overlap <= 0:
            continue
        if other["bbox"][0] >= caption["bbox"][2]:
            right = min(right, (other["bbox"][0] + caption["bbox"][2]) / 2)
        elif other["bbox"][2] <= caption["bbox"][0]:
            left = max(left, (other["bbox"][2] + caption["bbox"][0]) / 2)
    scoped = []
    for block in blocks:
        lines = [line for line in block.get("lines", []) if left <= (line["bbox"][0] + line["bbox"][2]) / 2 <= right]
        if lines:
            bbox = fitz.Rect(lines[0]["bbox"])
            for line in lines[1:]:
                bbox |= fitz.Rect(line["bbox"])
            scoped.append({**block, "bbox": list(bbox), "lines": lines})
    eligible = [block for block in scoped if cell_like(block)]
    top, bottom = caption["bbox"][1], caption["bbox"][3]
    above = sorted((b for b in eligible if b["bbox"][3] <= top + 2), key=lambda b: b["bbox"][3], reverse=True)
    below = sorted((b for b in eligible if b["bbox"][1] >= bottom - 2), key=lambda b: b["bbox"][1])
    groups = []
    for sequence, direction, edge in [(above, -1, top), (below, 1, bottom)]:
        group = []
        for block in sequence:
            gap = edge - block["bbox"][3] if direction < 0 else block["bbox"][1] - edge
            if gap > (35 if not group else 24):
                break
            group.append(block)
            edge = block["bbox"][1] if direction < 0 else block["bbox"][3]
        if group:
            groups.append(group)
    return max(groups, key=lambda group: sum(len(text_lines(b)) for b in group), default=[])


def layout_rows(blocks):
    lines = [line for block in blocks for line in text_lines(block)]
    groups = []
    for line in sorted(lines, key=lambda line: ((line["bbox"][1] + line["bbox"][3]) / 2, line["bbox"][0])):
        center = (line["bbox"][1] + line["bbox"][3]) / 2
        group = next((g for g in reversed(groups[-3:]) if abs(g["center"] - center) <= 4), None)
        if group is None:
            groups.append({"center": center, "lines": [line]})
        else:
            group["lines"].append(line)
    if not groups:
        return [], [], []
    # Use the row with the largest number of distinct cells as an anchor. Empty
    # cells remain empty; missing values are never inferred from neighbouring rows.
    anchor = max(groups, key=lambda group: len(group["lines"]))
    anchors = sorted((l["bbox"][0] + l["bbox"][2]) / 2 for l in anchor["lines"])
    if len(anchors) > 30 or len(anchors) < 2:
        return [], [], lines
    rows, source_cells = [], []
    for group in groups:
        cells = [""] * len(anchors)
        for line in sorted(group["lines"], key=lambda line: line["bbox"][0]):
            center = (line["bbox"][0] + line["bbox"][2]) / 2
            column = min(range(len(anchors)), key=lambda col: abs(anchors[col] - center))
            cells[column] = (cells[column] + " " + line["text"]).strip()
            source_cells.append({**line, "row": len(rows), "column": column})
        rows.append(cells)
    return rows, anchors, source_cells


def analyze_page(pdf_path: Path, page_number: int):
    start = time.perf_counter()
    with fitz.open(pdf_path) as doc:
        if not 1 <= page_number <= len(doc):
            raise ValueError("页码不存在")
        page = doc[page_number - 1]
        blocks = [b for b in page.get_text("dict")["blocks"] if b.get("type") == 0]
        tables, captions, formulas = [], [], []
        for block in blocks:
            text = normalize(" ".join(l["text"] for l in text_lines(block)))
            if TABLE_CAPTION.match(text):
                neighbours = table_neighbours(block, blocks)
                rows, columns, source_cells = layout_rows(neighbours)
                bbox = list(fitz.Rect(neighbours[0]["bbox"])) if neighbours else list(block["bbox"])
                for other in neighbours[1:]:
                    bbox = list(fitz.Rect(bbox) | fitz.Rect(other["bbox"]))
                tables.append({"id": len(tables), "caption": text, "caption_bbox": list(block["bbox"]),
                               "bbox": bbox, "rows": rows, "column_centers": columns, "source_cells": source_cells,
                               "row_count": len(rows), "column_count": len(columns),
                               "method": "caption_bounded_layout_rows", "status": "heuristic_candidate_requires_review"})
            if FIGURE_CAPTION.match(text):
                captions.append({"text": text, "bbox": list(block["bbox"]), "kind": "figure_caption"})
            for line in text_lines(block):
                math_font = any(re.search(r"CMMI|CMSY|CMEX|Math|Symbol", font, re.I) for font in line["fonts"])
                if math_font and ("=" in line["text"] or len(line["text"]) < 180):
                    formulas.append({**line, "kind": "math_glyph_candidate", "latex": None,
                                     "status": "source_glyphs_only_not_latex_transcription"})
        # Ruled tables without captions can still be detected; never run unbounded
        # full-page text strategy, which turned entire academic pages into grids.
        if not tables:
            finder = page.find_tables(strategy="lines")
            for native in finder.tables[:10]:
                rows = native.extract()
                tables.append({"id": len(tables), "caption": "", "bbox": list(native.bbox),
                               "caption_bbox": None, "rows": rows, "source_cells": [],
                               "row_count": native.row_count, "column_count": native.col_count,
                               "method": "native_ruled_lines", "status": "heuristic_candidate_requires_review"})
        images = [{"index": index, "bbox": list(info["bbox"]), "width": info["width"], "height": info["height"],
                   "xref": info.get("xref", 0), "kind": "embedded_image_not_necessarily_figure"}
                  for index, info in enumerate(page.get_image_info(xrefs=True)[:40])]
        return {"page": page_number, "width": page.rect.width, "height": page.rect.height,
                "tables": tables, "figure_captions": captions, "embedded_images": images,
                "formula_candidates": formulas[:100], "analyzer_version": ANALYZER_VERSION,
                "latency_ms": round((time.perf_counter() - start) * 1000, 3),
                "limitations": ["行列由版式启发式恢复，合并表头/缺失单元格可能错位，必须对照页图。",
                                "图注与嵌入图片分别提取，未断言配对关系；矢量图不一定有嵌入图片。",
                                "数学字体仅生成原文glyph候选，不宣称已还原LaTeX；扫描页表格结构尚不支持。"]}


def cached_analysis(root, paper_id, page_number, refresh=False):
    root = Path(root)
    # paper_id must originate in Store.get, never an arbitrary filesystem path.
    if not re.fullmatch(r"[a-f0-9]{20}", paper_id):
        raise ValueError("文献标识无效")
    folder = root / "page_analysis"
    folder.mkdir(exist_ok=True)
    path = folder / f"{paper_id}_{page_number}_{ANALYZER_VERSION}.json"
    if path.exists() and not refresh:
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
            return {**result, "cache_hit": True}
        except (OSError, ValueError):
            pass  # Rebuild an interrupted cache; the original PDF is untouched.
    result = analyze_page(root / (paper_id + ".pdf"), page_number)
    # Include source hash so the cache can be audited independently of its name.
    with (root / (paper_id + ".pdf")).open("rb") as source:
        result["source_sha256"] = hashlib.file_digest(source, "sha256").hexdigest()
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder, suffix=".tmp", delete=False) as output:
        json.dump(result, output, ensure_ascii=False)
        temporary = output.name
    os.replace(temporary, path)
    return {**result, "cache_hit": False}


def table_csv(table):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    def safe_cell(value):
        value = "" if value is None else str(value)
        if value.lstrip().startswith(("=", "+", "-", "@")):
            try:
                float(value)
            except ValueError:
                return "'" + value
        return value
    writer.writerows([[safe_cell(value) for value in row] for row in table["rows"]])
    return output.getvalue()
