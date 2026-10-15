from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from src.app import create_app
from src.config import Settings
from src.tools import csv_analysis, download_arxiv_pdf


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(Settings(data_dir=tmp_path)))


@pytest.mark.parametrize("identifier", ["http://localhost/secret", "../file", "file:///etc/passwd", "arxiv.org/1", "1706.03762/../x"])
def test_download_does_not_accept_arbitrary_urls(identifier):
    with pytest.raises(ValueError):
        download_arxiv_pdf(identifier, 100)


def test_search_invalid_limits(client):
    assert client.get("/api/search?q=test&limit=-1").status_code == 422
    assert client.get("/api/search?q=test&limit=999999").status_code == 422


def test_model_workflow_without_model(client):
    response = client.post("/api/workflow", json={"question": "make an outline", "use_model": True})
    assert response.status_code == 503


def test_csv_row_and_size_limits():
    with pytest.raises(ValueError):
        csv_analysis("a,b\n" + "x,1\n" * 10001)
    with pytest.raises(ValueError):
        csv_analysis("x" * 2_000_001)


def test_exact_local_files_still_served(client):
    assert client.get("/").status_code == 200
    assert "研证" in client.get("/").text
    assert client.get("/app.js").status_code == 200
    assert client.get("/.env").status_code == 404
