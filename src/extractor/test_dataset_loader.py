from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


_MANIFEST_NAMES = (
    "manifest.json",
    "dataset.json",
    "test_dataset.json",
)

_DOCUMENTS_NAMES = (
    "documents.json",
    "test_documents.json",
)

_GROUND_TRUTH_NAMES = (
    "ground_truth.json",
    "annotations.json",
    "extraction_ground_truth.json",
)

_CO2_REFERENCE_NAMES = (
    "co2_reference.json",
    "co2.json",
)

_IOT_NAMES = (
    "iot_readings.json",
    "iot.json",
)


@dataclass(slots=True)
class TestDocument:
    doc_id: str
    file_path: Path
    document_type: str
    expected_date: datetime | None = None
    expected_quantity: float | None = None
    expected_unit: str | None = None
    expected_supplier: str | None = None
    expected_site: str | None = None
    energy_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TestAnomaly:
    doc_id: str
    timestamp: datetime
    sensor_id: str
    anomaly_type: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TestDataset:
    root: Path
    documents: list[TestDocument]
    anomalies: list[TestAnomaly]
    co2_reference: dict[str, float]
    iot_readings: dict[str, Any]
    ground_truth: dict[str, dict[str, Any]] = field(default_factory=dict)

    def document_index(self) -> dict[str, TestDocument]:
        index: dict[str, TestDocument] = {}
        for document in self.documents:
            index[document.doc_id] = document
            index[document.file_path.name] = document
            index[document.file_path.stem] = document
        return index

    def get_document(self, doc_id: str) -> TestDocument | None:
        index = self.document_index()
        return index.get(doc_id) or index.get(Path(doc_id).stem)

    def reference_for(self, doc_id: str) -> dict[str, Any] | None:
        return self.ground_truth.get(doc_id) or self.ground_truth.get(Path(doc_id).stem)


class TestDatasetLoader:
    def __init__(self, dataset_path: str | Path):
        self.dataset_path = Path(dataset_path)

    def load(self) -> TestDataset:
        manifest = self._load_json_candidates(_MANIFEST_NAMES)
        if manifest is not None:
            return self._load_from_manifest(manifest)

        documents = self._load_documents_from_candidates()
        ground_truth = self._coerce_ground_truth(self._load_json_candidates(_GROUND_TRUTH_NAMES) or {})
        anomalies = self._coerce_anomalies(self._load_json_candidates(("anomalies.json",)) or [])
        co2_reference = self._coerce_co2_reference(self._load_json_candidates(_CO2_REFERENCE_NAMES) or {})
        iot_readings = self._coerce_iot_readings(self._load_json_candidates(_IOT_NAMES) or {})

        if not documents and not ground_truth:
            raise FileNotFoundError(
                f"No test dataset manifest or ground-truth files found in {self.dataset_path}"
            )

        if not documents and ground_truth:
            documents = self._documents_from_ground_truth(ground_truth)

        return TestDataset(
            root=self.dataset_path,
            documents=documents,
            anomalies=anomalies,
            co2_reference=co2_reference,
            iot_readings=iot_readings,
            ground_truth=ground_truth,
        )

    def _load_from_manifest(self, manifest: dict[str, Any]) -> TestDataset:
        documents = self._parse_documents(manifest.get("documents", []))
        anomalies = self._coerce_anomalies(manifest.get("anomalies", []))
        co2_reference = self._coerce_co2_reference(manifest.get("co2_reference", {}))
        iot_readings = self._coerce_iot_readings(manifest.get("iot_readings", {}) or {})
        ground_truth = self._coerce_ground_truth(manifest.get("ground_truth", {}))
        if not ground_truth and documents:
            ground_truth = {
                document.doc_id: self._document_to_ground_truth(document)
                for document in documents
            }
        return TestDataset(
            root=self.dataset_path,
            documents=documents,
            anomalies=anomalies,
            co2_reference=co2_reference,
            iot_readings=iot_readings,
            ground_truth=ground_truth,
        )

    def _load_documents_from_candidates(self) -> list[TestDocument]:
        for candidate_name in _DOCUMENTS_NAMES:
            candidate = self.dataset_path / candidate_name
            if candidate.exists():
                payload = self._read_json(candidate)
                return self._parse_documents(payload)
        return []

    def _documents_from_ground_truth(self, ground_truth: dict[str, dict[str, Any]]) -> list[TestDocument]:
        documents: list[TestDocument] = []
        for doc_id, payload in ground_truth.items():
            file_name = str(payload.get("file_path") or payload.get("file") or doc_id)
            documents.append(
                TestDocument(
                    doc_id=str(doc_id),
                    file_path=self._resolve_path(file_name),
                    document_type=str(
                        payload.get("document_type") or payload.get("type") or Path(file_name).suffix.lstrip(".") or "unknown"
                    ),
                    expected_date=self._parse_datetime(payload.get("expected_date") or payload.get("date")),
                    expected_quantity=self._parse_float(payload.get("expected_quantity") or payload.get("quantity") or payload.get("value")),
                    expected_unit=self._optional_text(payload.get("expected_unit") or payload.get("unit")),
                    expected_supplier=self._optional_text(payload.get("expected_supplier") or payload.get("supplier")),
                    expected_site=self._optional_text(payload.get("expected_site") or payload.get("site")),
                    energy_type=self._optional_text(payload.get("energy_type") or payload.get("energy")),
                    metadata={
                        k: v
                        for k, v in payload.items()
                        if k
                        not in {
                            "file_path",
                            "file",
                            "document_type",
                            "type",
                            "expected_date",
                            "date",
                            "expected_quantity",
                            "quantity",
                            "value",
                            "expected_unit",
                            "unit",
                            "expected_supplier",
                            "supplier",
                            "expected_site",
                            "site",
                            "energy_type",
                            "energy",
                        }
                    },
                )
            )
        return documents

    def _parse_documents(self, documents: list[dict[str, Any]]) -> list[TestDocument]:
        parsed: list[TestDocument] = []
        for item in documents:
            doc_id = self._require_text(item, ("id", "doc_id", "document_id"), "document")
            file_name = self._require_text(item, ("file_path", "path", "file"), f"document {doc_id}")
            parsed.append(
                TestDocument(
                    doc_id=doc_id,
                    file_path=self._resolve_path(file_name),
                    document_type=self._optional_text(
                        item.get("document_type") or item.get("type") or Path(file_name).suffix.lstrip(".") or "unknown"
                    )
                    or "unknown",
                    expected_date=self._parse_datetime(item.get("expected_date") or item.get("date")),
                    expected_quantity=self._parse_float(item.get("expected_quantity") or item.get("quantity") or item.get("value")),
                    expected_unit=self._optional_text(item.get("expected_unit") or item.get("unit")),
                    expected_supplier=self._optional_text(item.get("expected_supplier") or item.get("supplier")),
                    expected_site=self._optional_text(item.get("expected_site") or item.get("site")),
                    energy_type=self._optional_text(item.get("energy_type") or item.get("energy")),
                    metadata={
                        k: v
                        for k, v in item.items()
                        if k
                        not in {
                            "id",
                            "doc_id",
                            "document_id",
                            "file_path",
                            "path",
                            "file",
                            "document_type",
                            "type",
                            "expected_date",
                            "date",
                            "expected_quantity",
                            "quantity",
                            "value",
                            "expected_unit",
                            "unit",
                            "expected_supplier",
                            "supplier",
                            "expected_site",
                            "site",
                            "energy_type",
                            "energy",
                        }
                    },
                )
            )
        return parsed

    def _parse_anomalies(self, anomalies: list[dict[str, Any]]) -> list[TestAnomaly]:
        parsed: list[TestAnomaly] = []
        for item in anomalies:
            parsed.append(
                TestAnomaly(
                    doc_id=self._require_text(item, ("doc_id", "id", "document_id"), "anomaly"),
                    timestamp=self._parse_datetime(item.get("timestamp"), required=True),
                    sensor_id=self._require_text(item, ("sensor_id", "sensor", "source"), "anomaly"),
                    anomaly_type=self._require_text(item, ("anomaly_type", "type", "kind"), "anomaly"),
                    confidence=self._parse_float(item.get("confidence", 1.0)) or 1.0,
                    metadata={
                        k: v
                        for k, v in item.items()
                        if k
                        not in {
                            "doc_id",
                            "id",
                            "document_id",
                            "timestamp",
                            "sensor_id",
                            "sensor",
                            "source",
                            "anomaly_type",
                            "type",
                            "kind",
                            "confidence",
                        }
                    },
                )
            )
        return parsed

    def _coerce_anomalies(self, payload: Any) -> list[TestAnomaly]:
        if isinstance(payload, list):
            return self._parse_anomalies([item for item in payload if isinstance(item, dict)])
        if isinstance(payload, dict):
            anomalies: list[dict[str, Any]] = []
            for doc_id, item in payload.items():
                if isinstance(item, dict):
                    copied = dict(item)
                    copied.setdefault("doc_id", doc_id)
                    anomalies.append(copied)
            return self._parse_anomalies(anomalies)
        return []

    def _coerce_ground_truth(self, payload: Any) -> dict[str, dict[str, Any]]:
        if isinstance(payload, dict):
            return {str(key): value for key, value in payload.items() if isinstance(value, dict)}
        if isinstance(payload, list):
            result: dict[str, dict[str, Any]] = {}
            for item in payload:
                if isinstance(item, dict):
                    doc_id = self._require_text(item, ("id", "doc_id", "document_id"), "ground truth")
                    result[doc_id] = item
            return result
        return {}

    def _coerce_co2_reference(self, payload: Any) -> dict[str, float]:
        if isinstance(payload, dict):
            result: dict[str, float] = {}
            for key, value in payload.items():
                coerced = self._parse_float(value)
                if coerced is not None:
                    result[str(key)] = coerced
            return result
        if isinstance(payload, list):
            result: dict[str, float] = {}
            for item in payload:
                if isinstance(item, dict):
                    doc_id = self._require_text(item, ("doc_id", "id", "document_id"), "CO2 reference")
                    value = self._parse_float(item.get("co2_kg") or item.get("value") or item.get("reference"))
                    if value is not None:
                        result[doc_id] = value
            return result
        return {}

    def _coerce_iot_readings(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return {str(key): value for key, value in payload.items()}
        if isinstance(payload, list):
            return {str(index): value for index, value in enumerate(payload)}
        return {}

    def _load_json_candidates(self, names: tuple[str, ...]) -> dict[str, Any] | list[dict[str, Any]] | None:
        for name in names:
            candidate = self.dataset_path / name
            if candidate.exists():
                return self._read_json(candidate)
        return None

    def _read_json(self, path: Path) -> Any:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return (self.dataset_path / path).resolve()

    def _document_to_ground_truth(self, document: TestDocument) -> dict[str, Any]:
        return {
            "expected_date": document.expected_date.isoformat() if document.expected_date else None,
            "expected_quantity": document.expected_quantity,
            "expected_unit": document.expected_unit,
            "expected_supplier": document.expected_supplier,
            "expected_site": document.expected_site,
            "document_type": document.document_type,
            "energy_type": document.energy_type,
        }

    def _require_text(self, payload: dict[str, Any], keys: tuple[str, ...], label: str) -> str:
        for key in keys:
            value = payload.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        keys_text = ", ".join(keys)
        raise ValueError(f"Missing {label} field; expected one of: {keys_text}")

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _parse_float(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _parse_datetime(self, value: Any, required: bool = False) -> datetime | None:
        if value is None or value == "":
            if required:
                raise ValueError("Missing required timestamp value")
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        text = str(value).strip()
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            if required:
                raise ValueError(f"Could not parse timestamp value: {value!r}") from None
            return None
