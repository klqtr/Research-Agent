import csv
import io
from pathlib import Path
import fitz
import pytest
from fastapi.testclient import TestClient
from src.app import create_app
from src.config import Settings
from src.hierarchy import build_tree, heading_level
from src.page_analysis import TABLE_CAPTION, analyze_page, table_csv


def test_caption_number_not_prose_reference():
    assert TABLE_CAPTION.match("Table 2.1: Model sizes")
    assert TABLE_CAPTION.match("Table 2. Caption")
    assert not TABLE_CAPTION.match("Table 2.1 shows the model parameters.")


def test_heading_tree_hierarchy():
    titles = ["1 Introduction", "2 Methods", "2.1 Retrieval", "2.1.1 Details", "3 Results"]
    flat = [{"title": t, "level": heading_level(t), "page": 1} for t in titles]
    tree = build_tree(flat)
    assert len(tree) == 3
    assert tree[1]["children"][0]["children"][0]["title"] == "2.1.1 Details"


@pytest.mark.parametrize("filename,page,expected_cols,needle", [
    ("1706.03762v1.pdf", 8, 5, "41.0"),
    ("1706.03762v7.pdf", 8, 5, "41.8"),
    ("1810.04805v2.pdf", 6, 10, "82.1"),
    ("2005.14165v4.pdf", 8, 8, "175.0B")])
def test_real_caption_bounded_tables(filename, page, expected_cols, needle):
    path = Path("data/papers") / filename
    if not path.exists():
        pytest.skip("Real paper sample not downloaded")
    result = analyze_page(path, page)
    assert len(result["tables"]) == 1
    table = result["tables"][0]
    assert table["column_count"] == expected_cols
    assert any(needle in row for row in table["rows"])
    assert "requires_review" in table["status"]
    assert table["bbox"][3] < 250  # Body prose below the real table is excluded.
    assert needle in table_csv(table)


def test_lazy_cache_exports_and_original_unchanged(tmp_path):
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 50), "Table 1: Synthetic results")
        for y, cells in [(80, ["Method", "Score", "Cost"]), (100, ["Baseline", "0.5", "2"]), (120, ["Full", "0.8", "3"])]:
            for x, content in zip([50, 220, 360], cells):
                page.insert_text((x, y), content)
        raw = doc.tobytes()
    client = TestClient(create_app(Settings(data_dir=tmp_path)))
    pid = client.post("/api/papers", files={"file": ("test.pdf", raw)}).json()["paper_id"]
    url = f"/api/papers/{pid}/pages/1/analysis"
    first = client.get(url).json()
    second = client.get(url).json()
    assert not first["cache_hit"] and second["cache_hit"]
    csv_response = client.get(f"/api/papers/{pid}/pages/1/tables/0/csv")
    assert csv_response.status_code == 200
    rows = list(csv.reader(io.StringIO(csv_response.content.decode("utf-8-sig"))))
    assert any("0.8" in row for row in rows)
    assert client.get(f"/api/papers/{pid}/pages/1/tables/999/csv").status_code == 404
    assert client.get(f"/api/papers/{pid}/pdf").content == raw


def test_invalid_page_analysis(tmp_path):
    from src.page_analysis import cached_analysis
    with pytest.raises(ValueError):
        cached_analysis(tmp_path, "../../secret", 1)


def test_csv_export_neutralizes_formula_cells():
    rows = list(csv.reader(io.StringIO(table_csv({"rows": [["=HYPERLINK(x)", "+CMD", "-2", "@foo"]]}))))
    assert rows[0] == ["'=HYPERLINK(x)", "'+CMD", "-2", "'@foo"]


def test_native_pdf_outline_preferred(tmp_path):
    from src.parsing import parse_pdf
    with fitz.open() as doc:
        doc.new_page().insert_text((50, 50), "A real outline should supersede heuristic headings from plain text.")
        doc.set_toc([[1, "Introduction", 1], [2, "Motivation", 1], [3, "Evidence", 1]])
        raw = doc.tobytes()
    paper = parse_pdf(raw, "toc.pdf", Settings(data_dir=tmp_path))
    assert paper["headings"][0]["basis"] == "pdf_native_outline"
    assert paper["heading_tree"][0]["children"][0]["children"][0]["title"] == "Evidence"
