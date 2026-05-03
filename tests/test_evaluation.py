from __future__ import annotations

from datetime import datetime

from evaluation import ExtractionEvaluator
from extractors.base import ExtractionResult


def test_extraction_evaluator_scores_exact_matches():
    records = [
        ExtractionResult(
            source_file="doc-a.pdf",
            source_type="pdf",
            timestamp=datetime(2026, 5, 1, 0, 0),
            energie_alternateur_kwh=1200.0,
        ),
        ExtractionResult(
            source_file="doc-b.xlsx",
            source_type="excel",
            timestamp=datetime(2026, 5, 2, 0, 0),
            gaz_volume_nm3=800.0,
        ),
    ]
    ground_truth = {
        "doc-a": {
            "expected_date": "2026-05-01T00:00:00",
            "expected_quantity": 1200.0,
            "expected_unit": "kWh",
            "expected_supplier": None,
            "expected_site": None,
        },
        "doc-b": {
            "expected_date": "2026-05-02T00:00:00",
            "expected_quantity": 750.0,
            "expected_unit": "Nm3",
            "expected_supplier": None,
            "expected_site": None,
        },
    }

    metrics = ExtractionEvaluator().evaluate(records, ground_truth)

    assert metrics["total_predictions"] == 2
    assert metrics["total_ground_truth"] == 2
    assert metrics["exact_match_count"] == 1
    assert metrics["extraction_precision"] == 0.5
    assert metrics["extraction_recall"] == 0.5
    assert metrics["extraction_f1"] == 0.5
    assert metrics["field_accuracy"]["expected_date"] == 1.0
    assert metrics["field_accuracy"]["expected_quantity"] == 0.5
    assert metrics["field_accuracy"]["expected_unit"] == 1.0


def test_extraction_evaluator_matches_source_file_stem():
    record = ExtractionResult(
        source_file="nested/path/doc-c.pdf",
        source_type="pdf",
        timestamp=datetime(2026, 5, 3, 12, 0),
        energie_alternateur_kwh=75.0,
    )
    ground_truth = {
        "doc-c": {
            "expected_date": "2026-05-03T08:00:00",
            "expected_quantity": 75.0,
            "expected_unit": "kWh",
        }
    }

    metrics = ExtractionEvaluator().evaluate([record], ground_truth)

    assert metrics["matched_predictions"] == 1
    assert metrics["unmatched_predictions"] == 0
    assert metrics["exact_match_count"] == 1