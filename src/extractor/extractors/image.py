from __future__ import annotations
import re
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
from extractors.base import ExtractionResult

_VALUE_RE = re.compile(
    r'([0-9]+(?:[.,][0-9]+)?)\s*'
    r'(kWh|MWh|kW|MW|Nm3|m3/h|kVARh|kVA|%|°C|A|V|rpm|th|Gcal|toe)',
    re.IGNORECASE,
)

_KEYWORD_FIELD: list[tuple[str, str]] = [
    ('gaz', 'gaz_volume_nm3'),
    ('puissance', 'puissance_brute_kw'),
    ('energie', 'energie_alternateur_kwh'),
    ('eau glacee', 'eg_energie_kwh'),
    ('eau chaude', 'ec_recup_energie_kwh'),
    ('steg', 'steg_achat_kwh'),
    ('rendement', 'rendement_electrique_pct'),
    ('voltage', 'voltage_v'),
    ('courant', 'courant_phase1_a'),
]

_READER = None


def _get_reader():
    global _READER
    if _READER is None:
        import easyocr
        _READER = easyocr.Reader(['fr', 'en'], gpu=False, verbose=False)
    return _READER


def _preprocess(path: Path) -> Image.Image:
    img = Image.open(str(path)).convert('L')
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.filter(ImageFilter.SHARPEN)
    return img


class ImageExtractor:
    def extract(self, path: Path) -> list[ExtractionResult]:
        warnings: list[str] = []
        fields: dict[str, float] = {}

        try:
            reader = _get_reader()
            img = _preprocess(path)
            import numpy as np
            ocr_results = reader.readtext(np.array(img), detail=1, paragraph=False)
            full_text = ' '.join(item[1] for item in ocr_results)

            lines = full_text.split('.')
            for line in lines:
                line_lower = line.lower()
                for keyword, field in _KEYWORD_FIELD:
                    if keyword in line_lower:
                        m = _VALUE_RE.search(line)
                        if m and field not in fields:
                            try:
                                fields[field] = float(m.group(1).replace(',', '.'))
                            except ValueError:
                                pass

            if not fields:
                warnings.append("no structured fields found in image")

        except Exception as e:
            warnings.append(f"OCR failed: {e}")

        valid_fields = {
            k: v for k, v in fields.items()
            if k in ExtractionResult.model_fields
        }

        return [ExtractionResult(
            source_file=path.name,
            source_type="image",
            confidence_score=min(len(valid_fields) / 3, 1.0),
            extraction_warnings=warnings,
            **valid_fields,
        )]
