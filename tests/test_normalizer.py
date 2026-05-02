import pytest
from normalizer import normalize_to_kwh, normalize_record
from extractors.base import ExtractionResult


def test_kwh_passthrough():
    val, log = normalize_to_kwh(100.0, 'kWh')
    assert val == 100.0
    assert 'no_conversion' not in log


def test_mwh_to_kwh():
    val, log = normalize_to_kwh(1.5, 'MWh')
    assert val == pytest.approx(1500.0)
    assert '1000' in log


def test_gcal_to_kwh():
    val, log = normalize_to_kwh(1.0, 'Gcal')
    assert val == pytest.approx(1163.0)


def test_toe_to_kwh():
    val, log = normalize_to_kwh(1.0, 'toe')
    assert val == pytest.approx(11630.0)


def test_nm3_to_kwh_uses_pci():
    # 1 Nm3 × PCI(9.082) × 1.163 = 10.562 kWh
    val, log = normalize_to_kwh(1.0, 'Nm3', pci=9.082)
    assert val == pytest.approx(9.082 * 1.163, rel=1e-3)
    assert 'PCI' in log


def test_kw_to_kwh_uses_delta_t():
    # 1200 kW × (10/60)h = 200 kWh
    val, log = normalize_to_kwh(1200.0, 'kW', delta_hours=10 / 60)
    assert val == pytest.approx(200.0)


def test_unknown_unit_passthrough():
    val, log = normalize_to_kwh(42.0, 'unknown_unit')
    assert val == 42.0
    assert 'no_conversion' in log


def test_normalize_record_noop_for_excel():
    r = ExtractionResult(
        source_file="f.xlsx", source_type="excel",
        puissance_brute_kw=1200.0
    )
    out = normalize_record(r)
    assert out.puissance_brute_kw == 1200.0
