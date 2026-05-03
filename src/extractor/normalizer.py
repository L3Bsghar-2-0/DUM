from __future__ import annotations
from extractors.base import ExtractionResult

_UNIT_TABLE: dict[str, float] = {
    'kwh': 1.0,
    'mwh': 1000.0,
    'gj': 277.78,
    'gcal': 1163.0,
    'kcal': 0.001163,
    'toe': 11630.0,
    'btu': 0.000293071,
    'thermie': 1.163,
    'th': 1.163,
}


def normalize_to_kwh(
    value: float,
    unit: str,
    pci: float = 9.082,
    delta_hours: float = 1 / 6,
) -> tuple[float, str]:
    """Convert value in given unit to kWh. Returns (converted_value, log_string)."""
    u = unit.lower().strip().replace('³', '3')
    if u in _UNIT_TABLE:
        factor = _UNIT_TABLE[u]
        return value * factor, f"{unit}->kWh*{factor}"
    if u in ('nm3', 'nm3/h'):
        factor = pci * 1.163
        return value * factor, f"Nm3->kWh*{factor:.4f}(PCI={pci})"
    if u in ('kw',):
        return value * delta_hours, f"kW->kWh*{delta_hours:.4f}h"
    return value, f"no_conversion({unit})"


def normalize_record(record: ExtractionResult) -> ExtractionResult:
    """
    For PDF/image records that may carry non-kWh units in extraction_warnings,
    re-apply unit conversions. Excel records are already in correct units.
    Returns a new ExtractionResult (does not mutate).
    """
    if record.source_type == "excel":
        return record
    data = record.model_dump()
    warnings = list(record.extraction_warnings)
    new_warnings: list[str] = []
    for w in warnings:
        new_warnings.append(w)
    data['extraction_warnings'] = new_warnings
    return ExtractionResult(**data)
