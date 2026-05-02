import pytest
from pathlib import Path
from extractors.excel import ExcelExtractor
from conftest import EXCEL_SAMPLE


def test_excel_extractor_returns_records():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    assert len(results) > 100  # monthly report has ~thousands of 10-min readings


def test_excel_extractor_has_timestamps():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    assert results[0].timestamp is not None


def test_excel_extractor_gas_flow_in_range():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    # Audit: nominal gas flow 273 Nm3/h ± 5%
    valid = [r for r in results if r.gaz_debit_nm3h is not None]
    assert len(valid) > 0
    avg = sum(r.gaz_debit_nm3h for r in valid) / len(valid)
    assert 250 < avg < 290


def test_excel_extractor_power_in_range():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    valid = [r for r in results if r.puissance_brute_kw is not None]
    avg = sum(r.puissance_brute_kw for r in valid) / len(valid)
    assert 1100 < avg < 1300  # nominal 1200 kW


def test_excel_extractor_source_type():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    assert all(r.source_type == "excel" for r in results)


def test_excel_extractor_field_coverage():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    coverages = [r.field_coverage() for r in results]
    avg_coverage = sum(coverages) / len(coverages)
    assert avg_coverage > 0.8  # should extract >80% of key fields


def test_excel_extractor_pci_from_file():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    assert results[0].pci_thermie_nm3 == pytest.approx(9.082, rel=1e-3)
