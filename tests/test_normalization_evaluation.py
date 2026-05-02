from __future__ import annotations

from evaluation import build_normalization_accuracy_report


def test_normalization_accuracy_report_all_passes():
    report = build_normalization_accuracy_report(
        [
            {"case_id": "kwh-1", "unit": "kWh", "value": 10.0, "expected_kwh": 10.0},
            {"case_id": "mwh-1", "unit": "MWh", "value": 1.0, "expected_kwh": 1000.0},
            {"case_id": "gj-1", "unit": "GJ", "value": 1.0, "expected_kwh": 277.78},
            {"case_id": "gcal-1", "unit": "Gcal", "value": 1.0, "expected_kwh": 1163.0},
            {"case_id": "btu-1", "unit": "BTU", "value": 1.0, "expected_kwh": 0.000293071},
            {"case_id": "toe-1", "unit": "toe", "value": 1.0, "expected_kwh": 11630.0},
            {"case_id": "nm3-1", "unit": "Nm³", "value": 1.0, "expected_kwh": 9.082 * 1.163},
        ]
    )

    assert report["overall_accuracy"] == 1.0
    assert report["average_absolute_error"] == 0.0
    assert report["by_unit"]["btu"]["accuracy"] == 1.0
    assert report["by_unit"]["nm3"]["accuracy"] == 1.0
    assert len(report["cases"]) == 7


def test_normalization_accuracy_report_detects_error():
    report = build_normalization_accuracy_report(
        [{"case_id": "bad", "unit": "toe", "value": 1.0, "expected_kwh": 12000.0}]
    )

    assert report["overall_accuracy"] == 0.0
    assert report["cases"][0]["passed"] is False
    assert report["cases"][0]["absolute_error"] == 370.0