import pytest
from co2 import estimate_co2
from extractors.base import ExtractionResult


def test_co2_electricity_only():
    r = ExtractionResult(
        source_file="f.xlsx", source_type="excel",
        energie_alternateur_kwh=1000.0,
    )
    out = estimate_co2(r, prev_energie_kwh=0.0, prev_gaz_nm3=0.0)
    assert out.co2_kg == pytest.approx(267.0)


def test_co2_gas_only():
    r = ExtractionResult(
        source_file="f.xlsx", source_type="excel",
        gaz_volume_nm3=100.0,
        pci_thermie_nm3=9.082,
    )
    out = estimate_co2(r, prev_energie_kwh=0.0, prev_gaz_nm3=0.0)
    expected = 100.0 * 9.082 * 1.163 * 0.202
    assert out.co2_kg == pytest.approx(expected, rel=1e-3)


def test_co2_combined():
    r = ExtractionResult(
        source_file="f.xlsx", source_type="excel",
        energie_alternateur_kwh=500.0,
        gaz_volume_nm3=50.0,
        pci_thermie_nm3=9.082,
    )
    out = estimate_co2(r, prev_energie_kwh=0.0, prev_gaz_nm3=0.0)
    elec_co2 = 500.0 * 0.267
    gas_co2 = 50.0 * 9.082 * 1.163 * 0.202
    assert out.co2_kg == pytest.approx(elec_co2 + gas_co2, rel=1e-3)


def test_co2_uses_delta_for_cumulative():
    r = ExtractionResult(
        source_file="f.xlsx", source_type="excel",
        energie_alternateur_kwh=1100.0,
        gaz_volume_nm3=150.0,
        pci_thermie_nm3=9.082,
    )
    out = estimate_co2(r, prev_energie_kwh=1000.0, prev_gaz_nm3=100.0)
    elec_co2 = (1100.0 - 1000.0) * 0.267
    gas_co2 = (150.0 - 100.0) * 9.082 * 1.163 * 0.202
    assert out.co2_kg == pytest.approx(elec_co2 + gas_co2, rel=1e-3)


def test_co2_none_when_no_energy_fields():
    r = ExtractionResult(source_file="f.pdf", source_type="pdf")
    out = estimate_co2(r, prev_energie_kwh=None, prev_gaz_nm3=None)
    assert out.co2_kg is None
