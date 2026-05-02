from __future__ import annotations
import re
import os
import json
from pathlib import Path
import pdfplumber
from extractors.base import ExtractionResult

_VALUE_RE = re.compile(
    r'([0-9]+(?:[.,][0-9]+)?)\s*'
    r'(kWh|MWh|kW|MW|Nm3|m3/h|kVARh|kVA|%|°C|A|V|rpm|th|Gcal|toe|GJ|BTU)',
    re.IGNORECASE,
)

_KEYWORD_FIELD: list[tuple[str, str]] = [
    ('gaz naturel', 'gaz_volume_nm3'),
    ('débit gaz', 'gaz_debit_nm3h'),
    ('puissance électrique', 'puissance_brute_kw'),
    ('énergie active', 'energie_alternateur_kwh'),
    ('énergie réactive', 'energie_reactive_kvarh'),
    ('facteur de puissance', 'facteur_puissance'),
    ('eau glacée', 'eg_energie_kwh'),
    ('eau chaude', 'ec_recup_energie_kwh'),
    ('steg', 'steg_achat_kwh'),
    ('rendement', 'rendement_electrique_pct'),
]


def _extract_text_fields(text: str) -> dict[str, float]:
    fields: dict[str, float] = {}
    lines = text.splitlines()
    for line in lines:
        line_lower = line.lower()
        for keyword, field in _KEYWORD_FIELD:
            if keyword.lower() in line_lower:
                m = _VALUE_RE.search(line)
                if m and field not in fields:
                    try:
                        fields[field] = float(m.group(1).replace(',', '.'))
                    except ValueError:
                        pass
    return fields


def _vision_extract_placeholder(image_bytes: bytes, api_key: str) -> dict[str, float]:
    """Placeholder for Claude vision extraction. Replace with actual implementation or open-source model."""
    return {}


class PDFExtractor:
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    def extract(self, path: Path) -> list[ExtractionResult]:
        results: list[ExtractionResult] = []
        warnings: list[str] = []

        try:
            with pdfplumber.open(str(path)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    fields = _extract_text_fields(text)

                    if len(fields) < 3 and self._api_key:
                        # Fallback: render page as image for vision extraction
                        try:
                            img = page.to_image(resolution=150).original
                            import io
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG")
                            fields = _vision_extract_placeholder(buf.getvalue(), self._api_key)
                            warnings.append(f"page {page_num + 1}: used vision fallback")
                        except Exception as e:
                            warnings.append(f"page {page_num + 1}: vision fallback failed: {e}")

                    if not fields:
                        continue

                    results.append(ExtractionResult(
                        source_file=path.name,
                        source_type="pdf",
                        extraction_warnings=list(warnings),
                        confidence_score=min(len(fields) / 5, 1.0),
                        **{k: v for k, v in fields.items()
                           if k in ExtractionResult.model_fields},
                    ))
        except Exception as e:
            results.append(ExtractionResult(
                source_file=path.name,
                source_type="pdf",
                confidence_score=0.0,
                extraction_warnings=[f"PDF extraction failed: {e}"],
            ))

        return results
