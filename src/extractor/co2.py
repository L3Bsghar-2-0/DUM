from __future__ import annotations
from extractors.base import ExtractionResult

ELEC_FACTOR = 0.267
GAS_FACTOR = 0.202


def estimate_co2(
    record: ExtractionResult,
    prev_energie_kwh: float | None,
    prev_gaz_nm3: float | None,
) -> ExtractionResult:
    """
    Returns a copy of record with co2_kg set.
    Uses delta of cumulative counters when prev values are provided.
    """
    data = record.model_dump()
    co2 = 0.0
    has_data = False

    if record.energie_alternateur_kwh is not None:
        prev_e = prev_energie_kwh or 0.0
        delta_e = max(record.energie_alternateur_kwh - prev_e, 0.0)
        co2 += delta_e * ELEC_FACTOR
        has_data = True

    if record.gaz_volume_nm3 is not None:
        prev_g = prev_gaz_nm3 or 0.0
        delta_g = max(record.gaz_volume_nm3 - prev_g, 0.0)
        pci = record.pci_thermie_nm3
        co2 += delta_g * pci * 1.163 * GAS_FACTOR
        has_data = True

    data['co2_kg'] = co2 if has_data else None
    return ExtractionResult(**data)
