import pytest
from pathlib import Path
from extractors.pdf import PDFExtractor
from conftest import PDF_SAMPLE


def test_pdf_extractor_returns_list():
    ext = PDFExtractor()
    results = ext.extract(PDF_SAMPLE)
    assert isinstance(results, list)


def test_pdf_extractor_source_type():
    ext = PDFExtractor()
    results = ext.extract(PDF_SAMPLE)
    assert all(r.source_type == "pdf" for r in results)


def test_pdf_extractor_no_exception_on_all_pdfs():
    import os
    pdf_dir = Path("data/data factures et diverses")
    ext = PDFExtractor()
    for pdf_file in list(pdf_dir.glob("*.pdf"))[:3]:  # test first 3
        results = ext.extract(pdf_file)
        assert isinstance(results, list)
