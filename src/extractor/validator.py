from __future__ import annotations
import json
import os
from extractors.base import ExtractionResult

_BOUNDS: dict[str, tuple[float, float]] = {
    'voltage_v': (380.0, 440.0),
    'facteur_puissance': (0.90, 1.0),
    'gaz_debit_nm3h': (200.0, 300.0),
    'puissance_brute_kw': (800.0, 1400.0),
    'vitesse_rpm': (1400.0, 1600.0),
    'eg_temp_entree_c': (3.0, 15.0),
    'eg_temp_sortie_c': (5.0, 20.0),
    'ec_recup_temp_entree_c': (90.0, 105.0),
    'rendement_electrique_pct': (30.0, 55.0),
    'rendement_total_pct': (50.0, 90.0),
}


def _rule_validate(record: ExtractionResult) -> ExtractionResult:
    warnings = list(record.extraction_warnings)
    violations = 0
    for field, (lo, hi) in _BOUNDS.items():
        val = getattr(record, field, None)
        if val is not None and not (lo <= val <= hi):
            warnings.append(f"{field}_out_of_range: {val} not in [{lo}, {hi}]")
            violations += 1

    coverage = record.field_coverage()
    penalty = violations * 0.1
    confidence = max(coverage - penalty, 0.0)

    data = record.model_dump()
    data['confidence_score'] = confidence
    data['extraction_warnings'] = warnings
    return ExtractionResult(**data)


def _claude_validate_placeholder(records: list[ExtractionResult], api_key: str) -> list[ExtractionResult]:
    """Placeholder for Claude batch validation. Will be replaced with open-source model or actual Claude API."""
    return [_rule_validate(r) for r in records]


def validate_batch(
    records: list[ExtractionResult],
    api_key: str | None = None,
) -> list[ExtractionResult]:
    key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        return [_rule_validate(r) for r in records]

    # Use placeholder for now; replace with actual Claude API or open-source model
    BATCH = 50
    results = []
    for i in range(0, len(records), BATCH):
        batch = records[i:i + BATCH]
        results.extend(_claude_validate_placeholder(batch, key))
    return results
