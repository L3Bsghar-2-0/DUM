import tempfile
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from conftest import EXCEL_SAMPLE

# Create temp db directory for tests
_tmpdir = tempfile.mkdtemp()
_db_path = Path(_tmpdir) / "energy.db"
os.environ["DB_URL"] = f"sqlite:///{_db_path}"
os.environ.setdefault("DATA_DIR", str(Path("data")))

from main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_extract_excel():
    with open(EXCEL_SAMPLE, "rb") as f:
        r = client.post("/extract", files={"file": ("test.xlsx", f, "application/octet-stream")})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "puissance_brute_kw" in data[0]


def test_records_endpoint():
    r = client.get("/records")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_summary_endpoint():
    r = client.get("/summary")
    assert r.status_code == 200
    body = r.json()
    assert "total_records" in body
