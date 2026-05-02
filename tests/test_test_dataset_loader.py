from __future__ import annotations

import json
from pathlib import Path

from extractor.test_dataset_loader import TestDatasetLoader


def test_test_dataset_loader_parses_manifest(tmp_path: Path):
    doc_a = tmp_path / "doc-a.pdf"
    doc_a.write_text("placeholder", encoding="utf-8")
    doc_b = tmp_path / "doc-b.xlsx"
    doc_b.write_text("placeholder", encoding="utf-8")

    manifest = {
        "documents": [
            {
                "id": "doc-a",
                "file_path": "doc-a.pdf",
                "type": "pdf",
                "expected_date": "2026-05-01T00:00:00",
                "expected_quantity": 1250.5,
                "expected_unit": "kWh",
                "expected_supplier": "STEG",
                "expected_site": "Site A",
                "energy_type": "electricity",
            },
            {
                "id": "doc-b",
                "file_path": "doc-b.xlsx",
                "type": "excel",
                "expected_date": "2026-05-02",
                "expected_quantity": 42,
                "expected_unit": "Nm3",
                "expected_supplier": "Supplier B",
                "expected_site": "Site B",
                "energy_type": "gas",
            },
        ],
        "anomalies": [
            {
                "doc_id": "doc-a",
                "timestamp": "2026-05-01T10:00:00",
                "sensor_id": "sensor-1",
                "type": "spike",
                "confidence": 0.9,
            }
        ],
        "co2_reference": {"doc-a": 12.5},
        "iot_readings": {"sensor-1": [1, 2, 3]},
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    dataset = TestDatasetLoader(tmp_path).load()

    assert len(dataset.documents) == 2
    assert len(dataset.anomalies) == 1
    assert dataset.co2_reference["doc-a"] == 12.5
    assert dataset.iot_readings["sensor-1"] == [1, 2, 3]
    assert dataset.get_document("doc-a").expected_unit == "kWh"
    assert dataset.reference_for("doc-b")["expected_site"] == "Site B"


def test_test_dataset_loader_falls_back_to_ground_truth(tmp_path: Path):
    ground_truth = {
        "doc-c": {
            "file_path": "doc-c.pdf",
            "expected_date": "2026-05-03T00:00:00",
            "expected_quantity": 88,
            "expected_unit": "GJ",
            "expected_supplier": "Supplier C",
            "expected_site": "Site C",
        }
    }
    (tmp_path / "ground_truth.json").write_text(json.dumps(ground_truth), encoding="utf-8")

    dataset = TestDatasetLoader(tmp_path).load()

    assert len(dataset.documents) == 1
    assert dataset.documents[0].doc_id == "doc-c"
    assert dataset.documents[0].expected_unit == "GJ"
