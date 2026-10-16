from pathlib import Path
import pytest
from scripts.phase2_demo_probe import run_demo


def test_actual_public_pdfs_version_agent_sources_and_reader_demo(tmp_path):
    needed=[Path("data/papers")/name for name in ("1706.03762v1.pdf","1706.03762v7.pdf","1810.04805v2.pdf")]
    if not all(path.exists() for path in needed):pytest.skip("公开真实演示PDF未下载，不能伪造验收")
    result=run_demo(tmp_path)
    assert result["checks"]=="passed" and result["model_requests"]==0 and not result["original_library_modified"]
