from extractors.base import ExtractionResult

def test_extraction_result_defaults():
    r = ExtractionResult(source_file="test.xlsx", source_type="excel")
    assert r.confidence_score == 0.0
    assert r.is_anomaly is False
    assert r.co2_kg is None
    assert r.extraction_warnings == []
    assert r.pci_thermie_nm3 == 9.082

def test_field_coverage_empty():
    r = ExtractionResult(source_file="test.xlsx", source_type="excel")
    assert r.field_coverage() == 0.0

def test_field_coverage_partial():
    r = ExtractionResult(
        source_file="test.xlsx",
        source_type="excel",
        gaz_volume_nm3=2024472.0,
        gaz_debit_nm3h=272.76,
        puissance_brute_kw=1199.0,
        energie_alternateur_kwh=9070710.0,
        eg_puissance_kw=230.41,
        ec_recup_puissance_kw=587.57,
        steg_achat_kwh=788205.0,
        steg_vente_kwh=3615267.0,
        production_positive_kwh=8437711.0,
    )
    assert r.field_coverage() == 1.0
