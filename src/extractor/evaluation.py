from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from extractors.base import ExtractionResult


_FIELD_ALIASES = {
    "expected_date": ("expected_date", "date", "timestamp"),
    "expected_quantity": ("expected_quantity", "quantity", "value"),
    "expected_unit": ("expected_unit", "unit"),
}


@dataclass(slots=True)
class DocumentScore:
    doc_id: str
    matched: bool
    exact_match: bool
    field_matches: dict[str, bool] = field(default_factory=dict)
    source_file: str | None = None


class ExtractionEvaluator:
    def __init__(self, ground_truth: Mapping[str, Mapping[str, Any]] | None = None):
        self.ground_truth = dict(ground_truth or {})

    def evaluate(
        self,
        extracted: Sequence[ExtractionResult],
        ground_truth: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        truth = dict(ground_truth or self.ground_truth)
        normalized_truth = self._normalize_truth(truth)
        scores: list[DocumentScore] = []

        field_hits = {field: 0 for field in _FIELD_ALIASES}
        field_totals = {field: 0 for field in _FIELD_ALIASES}
        exact_matches = 0
        matched_predictions = 0

        for record in extracted:
            matched_doc_id = self._match_record(record, normalized_truth)
            matched = matched_doc_id is not None
            if matched:
                matched_predictions += 1
            truth_row = normalized_truth.get(matched_doc_id, {}) if matched_doc_id else {}
            field_matches = self._compare_record(record, truth_row)
            exact_match = bool(field_matches) and all(field_matches.values())
            if exact_match:
                exact_matches += 1
            for field_name, is_match in field_matches.items():
                if self._field_present(truth_row, _FIELD_ALIASES[field_name]):
                    field_totals[field_name] += 1
                    if is_match:
                        field_hits[field_name] += 1
            scores.append(
                DocumentScore(
                    doc_id=matched_doc_id or self._record_key(record),
                    matched=matched,
                    exact_match=exact_match,
                    field_matches=field_matches,
                    source_file=record.source_file,
                )
            )

        total_predictions = len(extracted)
        total_truth = len(normalized_truth)
        precision = exact_matches / total_predictions if total_predictions else 0.0
        recall = exact_matches / total_truth if total_truth else 0.0
        f1 = self._harmonic_mean(precision, recall)

        return {
            "extraction_precision": precision,
            "extraction_recall": recall,
            "extraction_f1": f1,
            "exact_match_count": exact_matches,
            "total_predictions": total_predictions,
            "total_ground_truth": total_truth,
            "matched_predictions": matched_predictions,
            "unmatched_predictions": total_predictions - matched_predictions,
            "field_accuracy": {
                field: (field_hits[field] / field_totals[field] if field_totals[field] else 0.0)
                for field in _FIELD_ALIASES
            },
            "documents": [asdict(score) for score in scores],
        }

    def score_dataset(
        self,
        extracted: Sequence[ExtractionResult],
        dataset: Any,
    ) -> dict[str, Any]:
        if hasattr(dataset, "ground_truth"):
            return self.evaluate(extracted, getattr(dataset, "ground_truth"))
        if isinstance(dataset, Mapping):
            return self.evaluate(extracted, dataset)
        raise TypeError("dataset must expose a ground_truth mapping or be a mapping itself")

    def _normalize_truth(self, truth: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
        normalized: dict[str, dict[str, Any]] = {}
        for key, payload in truth.items():
            if not isinstance(payload, Mapping):
                continue
            normalized[str(key)] = {
                alias: self._coerce_truth_value(payload.get(alias))
                for alias in self._all_truth_keys(payload)
            }
            normalized[str(key)]["_doc_id"] = str(key)
        return normalized

    def _all_truth_keys(self, payload: Mapping[str, Any]) -> set[str]:
        keys: set[str] = set()
        for aliases in _FIELD_ALIASES.values():
            for alias in aliases:
                if alias in payload:
                    keys.add(alias)
        return keys

    def _compare_record(self, record: ExtractionResult, truth_row: Mapping[str, Any]) -> dict[str, bool]:
        result: dict[str, bool] = {}
        for field_name, aliases in _FIELD_ALIASES.items():
            expected = self._lookup_truth_value(truth_row, aliases)
            predicted = self._predicted_value(record, field_name)
            if expected is None:
                continue
            result[field_name] = self._values_equal(predicted, expected, field_name)
        return result

    def _match_record(self, record: ExtractionResult, truth: Mapping[str, Mapping[str, Any]]) -> str | None:
        source_key = self._normalize_key(record.source_file)
        if source_key in truth:
            return source_key
        stem = self._normalize_key(Path(record.source_file).stem)
        if stem in truth:
            return stem
        for doc_id in truth:
            if source_key == self._normalize_key(doc_id) or stem == self._normalize_key(doc_id):
                return doc_id
        return None

    def _record_key(self, record: ExtractionResult) -> str:
        return self._normalize_key(record.source_file) or record.source_file

    def _predicted_value(self, record: ExtractionResult, field_name: str) -> Any:
        if field_name == "expected_date":
            return record.timestamp
        if field_name == "expected_quantity":
            return record.puissance_brute_kw or record.energie_alternateur_kwh or record.gaz_volume_nm3
        if field_name == "expected_unit":
            if record.energie_alternateur_kwh is not None:
                return "kWh"
            if record.gaz_volume_nm3 is not None:
                return "Nm3"
            return None
        return None

    def _lookup_truth_value(self, truth_row: Mapping[str, Any], aliases: Sequence[str]) -> Any:
        for alias in aliases:
            if alias in truth_row:
                return truth_row[alias]
        return None

    def _coerce_truth_value(self, value: Any) -> Any:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            parsed_datetime = self._parse_datetime(text)
            if parsed_datetime is not None:
                return parsed_datetime
            try:
                return float(text)
            except ValueError:
                return text
        return value

    def _values_equal(self, predicted: Any, expected: Any, field_name: str) -> bool:
        if expected is None:
            return predicted is None
        if field_name == "expected_date":
            predicted_dt = self._parse_datetime(predicted)
            expected_dt = self._parse_datetime(expected)
            return predicted_dt is not None and expected_dt is not None and predicted_dt.date() == expected_dt.date()
        if field_name == "expected_quantity":
            predicted_num = self._coerce_float(predicted)
            expected_num = self._coerce_float(expected)
            if predicted_num is None or expected_num is None:
                return False
            return abs(predicted_num - expected_num) <= max(1e-6, abs(expected_num) * 1e-3)
        if isinstance(predicted, str) or isinstance(expected, str):
            return self._normalize_text(predicted) == self._normalize_text(expected)
        return predicted == expected

    def _field_present(self, truth_row: Mapping[str, Any], aliases: Sequence[str]) -> bool:
        return self._lookup_truth_value(truth_row, aliases) is not None

    def _coerce_float(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _parse_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _normalize_key(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""
        return Path(text).stem

    def _normalize_text(self, value: Any) -> str:
        return str(value or "").strip().lower()

    def _harmonic_mean(self, precision: float, recall: float) -> float:
        if precision <= 0.0 or recall <= 0.0:
            return 0.0
        return 2 * precision * recall / (precision + recall)
