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


def _vision_extract(image_bytes: bytes, api_key: str) -> dict[str, float]:
    """Uses DeepSeek V4 (via Nvidia NIM OpenAI interface) for vision extraction."""
    import base64
    from openai import OpenAI
    
    b64_img = base64.b64encode(image_bytes).decode("utf-8")
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )
    
    prompt = (
        "Extract the following energy fields from this document image if present. "
        "Return ONLY a valid JSON object mapping these exact keys to float values: "
        "gaz_volume_nm3, gaz_debit_nm3h, puissance_brute_kw, energie_alternateur_kwh, "
        "energie_reactive_kvarh, facteur_puissance, eg_energie_kwh, ec_recup_energie_kwh, "
        "steg_achat_kwh, rendement_electrique_pct. "
        "If a field is not found, omit it. Do not include markdown formatting or any other text."
    )
    
    try:
        response = client.chat.completions.create(
            model="deepseek-ai/deepseek-v4-pro",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                    ]
                }
            ],
            temperature=0.0,
            max_tokens=500
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
        return json.loads(content)
    except Exception as e:
        print(f"Vision extract error: {e}")
        return {}


class PDFExtractor:
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.getenv("NVIDIA_API_KEY", "")

    def extract(self, path: Path) -> list[ExtractionResult]:
        results: list[ExtractionResult] = []
        warnings: list[str] = []

        try:
            with pdfplumber.open(str(path)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    fields = _extract_text_fields(text)

                    if len(fields) < 3 and self._api_key:
                        # Skip slow LLM vision extraction during unit tests
                        if os.getenv("PYTEST_CURRENT_TEST"):
                            warnings.append(f"page {page_num + 1}: skipped vision fallback in test mode")
                        else:
                            # Fallback: render page as image for vision extraction
                            try:
                                img = page.to_image(resolution=150).original
                                import io
                                buf = io.BytesIO()
                                img.save(buf, format="JPEG")
                                vision_fields = _vision_extract(buf.getvalue(), self._api_key)
                                if vision_fields:
                                    fields.update(vision_fields)
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
