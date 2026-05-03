import tempfile
from pathlib import Path
from pipeline import run_pipeline
from conftest import DATA_DIR


def test_pipeline_returns_positive_count():
    with tempfile.TemporaryDirectory() as tmp:
        db_url = f"sqlite:///{tmp}/test.db"
        count = run_pipeline(DATA_DIR, db_url)
        assert count > 0


def test_pipeline_processes_excel_files():
    with tempfile.TemporaryDirectory() as tmp:
        db_url = f"sqlite:///{tmp}/test.db"
        count = run_pipeline(DATA_DIR, db_url)
        assert count > 0
