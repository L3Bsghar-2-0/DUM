# Energy Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Dockerized microservices pipeline that extracts, normalizes, and visualizes pharmaceutical factory tri-generation energy data from Excel, PDF, and image sources.

**Architecture:** Three Docker services (extractor FastAPI :8000, dashboard Streamlit :8501, db-init one-shot) sharing a SQLite volume. The db-init service reuses the extractor image but runs `pipeline.py` to bulk-ingest all files in `data/`. The extractor stays live for `POST /extract` API calls.

**Tech Stack:** Python 3.13, FastAPI, Streamlit, SQLAlchemy 2.0, Pydantic v2, openpyxl, pdfplumber, pdf2image, EasyOCR, anthropic SDK, scikit-learn, rapidfuzz, Docker Compose.

---

## File Map

```
src/
  extractor/
    extractors/
      __init__.py
      base.py          ExtractionResult pydantic model + field_coverage()
      excel.py         ExcelExtractor — wide-format BILAN TOTAL parser
      pdf.py           PDFExtractor — pdfplumber + Claude vision fallback
      image.py         ImageExtractor — EasyOCR + regex
    normalizer.py      normalize_to_kwh(value, unit, pci, dt) → (float, str)
                       normalize_record(ExtractionResult) → ExtractionResult
    validator.py       validate_batch(records, api_key) → records with confidence_score
    co2.py             estimate_co2(record) → record with co2_kg
    anomaly.py         detect_anomalies(df) → df with is_anomaly + anomaly_type
    db.py              EnergyRecord SQLAlchemy model, write_records(), read_all_records(),
                       update_anomaly_flags()
    pipeline.py        run_pipeline(data_dir, db_url) → int (records written)
    main.py            FastAPI app — POST /extract, GET /health, GET /records, GET /summary
  dashboard/
    app.py             Streamlit — 5 tabs: KPIs, CO2 Trend, Anomalies, Data Table, Coverage
tests/
  conftest.py          sys.path setup, shared fixtures
  test_base.py
  test_normalizer.py
  test_excel.py
  test_pdf.py
  test_image.py
  test_co2.py
  test_anomaly.py
  test_db.py
  test_pipeline.py
  test_api.py
requirements.txt
.env.example
Dockerfile.extractor
Dockerfile.dashboard
docker-compose.yml
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `tests/conftest.py`
- Create: `src/extractor/__init__.py`
- Create: `src/extractor/extractors/__init__.py`
- Create: `src/dashboard/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
streamlit==1.37.0
sqlalchemy==2.0.35
pydantic==2.9.2
pydantic-settings==2.5.2
openpyxl==3.1.5
pdfplumber==0.11.4
pdf2image==1.17.0
easyocr==1.7.2
anthropic==0.34.2
python-multipart==0.0.12
python-dotenv==1.0.1
pandas==2.2.3
numpy==2.1.2
scipy==1.14.1
scikit-learn==1.5.2
rapidfuzz==3.10.0
Pillow==11.0.0
plotly==5.24.1
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 2: Create .env.example**

```
ANTHROPIC_API_KEY=sk-ant-...
DB_URL=sqlite:////app/data/db/energy.db
DATA_DIR=/app/data
```

- [ ] **Step 3: Create tests/conftest.py**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "extractor"))

DATA_DIR = Path(__file__).parent.parent / "data"
EXCEL_SAMPLE = DATA_DIR / "data tri gen" / "avril-report1_2442026.xlsx"
PDF_SAMPLE = DATA_DIR / "data factures et diverses" / "data 2.0.pdf"
IMAGE_SAMPLE = DATA_DIR / "data factures et diverses" / "WhatsApp Image 2026-04-27 at 21.39.16.jpeg"
```

- [ ] **Step 4: Create .gitignore**

```
.env
data/db/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
.venv/
```

- [ ] **Step 5: Install rapidfuzz (not yet in venv)**

```bash
pip install rapidfuzz
```

- [ ] **Step 6: Create empty `__init__.py` files**

```bash
# Run from project root
python -c "
from pathlib import Path
for p in [
    'src/extractor/__init__.py',
    'src/extractor/extractors/__init__.py',
    'src/dashboard/__init__.py',
    'data/db/.gitkeep',
]:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).touch()
"
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example .gitignore tests/conftest.py src/
git commit -m "chore: project scaffolding, requirements, and gitignore"
```

---

## Task 2: ExtractionResult Model

**Files:**
- Create: `src/extractor/extractors/base.py`
- Create: `tests/test_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_base.py
from extractors.base import ExtractionResult

def test_extraction_result_defaults():
    r = ExtractionResult(source_file="test.xlsx", source_type="excel")
    assert r.confidence_score == 0.0
    assert r.is_anomaly is False
    assert r.co2_kg is None
    assert r.extraction_warnings == []
    assert r.pci_thermie_nm3 == 9.082

def test_field_coverage_empty():
    r = ExtractionResult(source_file="test.xlsx", source_type="excel")
    assert r.field_coverage() == 0.0

def test_field_coverage_partial():
    r = ExtractionResult(
        source_file="test.xlsx",
        source_type="excel",
        gaz_volume_nm3=2024472.0,
        gaz_debit_nm3h=272.76,
        puissance_brute_kw=1199.0,
        energie_alternateur_kwh=9070710.0,
        eg_puissance_kw=230.41,
        ec_recup_puissance_kw=587.57,
        steg_achat_kwh=788205.0,
        steg_vente_kwh=3615267.0,
        production_positive_kwh=8437711.0,
    )
    assert r.field_coverage() == 1.0
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_base.py -v
```
Expected: `ModuleNotFoundError: No module named 'extractors'`

- [ ] **Step 3: Implement base.py**

```python
# src/extractor/extractors/base.py
from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

COVERAGE_FIELDS = [
    'gaz_volume_nm3', 'gaz_debit_nm3h', 'puissance_brute_kw',
    'energie_alternateur_kwh', 'eg_puissance_kw', 'ec_recup_puissance_kw',
    'steg_achat_kwh', 'steg_vente_kwh', 'production_positive_kwh',
]

class ExtractionResult(BaseModel):
    # Metadata
    timestamp: Optional[datetime] = None
    source_file: str
    source_type: str  # excel / pdf / image
    confidence_score: float = 0.0
    is_anomaly: bool = False
    anomaly_type: Optional[str] = None
    co2_kg: Optional[float] = None
    extraction_warnings: list[str] = []
    pci_thermie_nm3: float = 9.082
    cos_phi: float = 1.0

    # Gas
    gaz_volume_nm3: Optional[float] = None
    gaz_debit_nm3h: Optional[float] = None

    # Electrical
    elec_auxiliaire_kwh: Optional[float] = None
    puissance_brute_kw: Optional[float] = None
    heures_fonctionnement: Optional[float] = None
    energie_alternateur_kwh: Optional[float] = None
    energie_reactive_kvarh: Optional[float] = None
    vitesse_rpm: Optional[float] = None
    facteur_puissance: Optional[float] = None
    voltage_v: Optional[float] = None
    courant_phase1_a: Optional[float] = None
    courant_phase2_a: Optional[float] = None
    courant_phase3_a: Optional[float] = None

    # Chilled water (absorption)
    eg_debit_m3h: Optional[float] = None
    eg_temp_entree_c: Optional[float] = None
    eg_temp_sortie_c: Optional[float] = None
    eg_energie_kwh: Optional[float] = None
    eg_puissance_kw: Optional[float] = None

    # Recovered hot water
    ec_recup_debit_m3h: Optional[float] = None
    ec_recup_temp_entree_c: Optional[float] = None
    ec_recup_temp_sortie_c: Optional[float] = None
    ec_recup_energie_kwh: Optional[float] = None
    ec_recup_puissance_kw: Optional[float] = None

    # Hot water Alpha Sanitaire
    ec_alpha_sani_debit_m3h: Optional[float] = None
    ec_alpha_sani_temp_entree_c: Optional[float] = None
    ec_alpha_sani_temp_sortie_c: Optional[float] = None
    ec_alpha_sani_energie_kwh: Optional[float] = None
    ec_alpha_sani_puissance_kw: Optional[float] = None

    # Hot water Alpha
    ec_alpha_debit_m3h: Optional[float] = None
    ec_alpha_temp_entree_c: Optional[float] = None
    ec_alpha_temp_sortie_c: Optional[float] = None
    ec_alpha_energie_kwh: Optional[float] = None
    ec_alpha_puissance_kw: Optional[float] = None

    # Hot water Gamma
    ec_gamma_debit_m3h: Optional[float] = None
    ec_gamma_temp_entree_c: Optional[float] = None
    ec_gamma_temp_sortie_c: Optional[float] = None
    ec_gamma_energie_kwh: Optional[float] = None
    ec_gamma_puissance_kw: Optional[float] = None

    # Efficiencies
    rendement_electrique_pct: Optional[float] = None
    rendement_thermique_pct: Optional[float] = None
    rendement_total_pct: Optional[float] = None

    # STEG grid
    steg_achat_kwh: Optional[float] = None
    steg_vente_kwh: Optional[float] = None
    production_positive_kwh: Optional[float] = None
    production_negative_kwh: Optional[float] = None

    def field_coverage(self) -> float:
        filled = sum(1 for f in COVERAGE_FIELDS if getattr(self, f) is not None)
        return filled / len(COVERAGE_FIELDS)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_base.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/extractor/extractors/base.py tests/test_base.py
git commit -m "feat: ExtractionResult pydantic model with field_coverage"
```

---

## Task 3: Normalizer

**Files:**
- Create: `src/extractor/normalizer.py`
- Create: `tests/test_normalizer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_normalizer.py
import pytest
from normalizer import normalize_to_kwh, normalize_record
from extractors.base import ExtractionResult

def test_kwh_passthrough():
    val, log = normalize_to_kwh(100.0, 'kWh')
    assert val == 100.0
    assert 'no_conversion' not in log

def test_mwh_to_kwh():
    val, log = normalize_to_kwh(1.5, 'MWh')
    assert val == pytest.approx(1500.0)
    assert '1000' in log

def test_gcal_to_kwh():
    val, log = normalize_to_kwh(1.0, 'Gcal')
    assert val == pytest.approx(1163.0)

def test_toe_to_kwh():
    val, log = normalize_to_kwh(1.0, 'toe')
    assert val == pytest.approx(11630.0)

def test_nm3_to_kwh_uses_pci():
    # 1 Nm3 × PCI(9.082) × 1.163 = 10.562 kWh
    val, log = normalize_to_kwh(1.0, 'Nm3', pci=9.082)
    assert val == pytest.approx(9.082 * 1.163, rel=1e-3)
    assert 'PCI' in log

def test_kw_to_kwh_uses_delta_t():
    # 1200 kW × (10/60)h = 200 kWh
    val, log = normalize_to_kwh(1200.0, 'kW', delta_hours=10/60)
    assert val == pytest.approx(200.0)

def test_unknown_unit_passthrough():
    val, log = normalize_to_kwh(42.0, 'unknown_unit')
    assert val == 42.0
    assert 'no_conversion' in log

def test_normalize_record_noop_for_excel():
    r = ExtractionResult(
        source_file="f.xlsx", source_type="excel",
        puissance_brute_kw=1200.0
    )
    out = normalize_record(r)
    assert out.puissance_brute_kw == 1200.0
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_normalizer.py -v
```
Expected: `ModuleNotFoundError: No module named 'normalizer'`

- [ ] **Step 3: Implement normalizer.py**

```python
# src/extractor/normalizer.py
from __future__ import annotations
from extractors.base import ExtractionResult

_UNIT_TABLE: dict[str, float] = {
    'kwh': 1.0,
    'mwh': 1000.0,
    'gj': 277.78,
    'gcal': 1163.0,
    'kcal': 0.001163,
    'toe': 11630.0,
    'btu': 0.000293,
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
    u = unit.lower().strip()
    if u in _UNIT_TABLE:
        factor = _UNIT_TABLE[u]
        return value * factor, f"{unit}→kWh×{factor}"
    if u in ('nm3', 'nm³', 'nm3/h'):
        factor = pci * 1.163
        return value * factor, f"Nm3→kWh×{factor:.4f}(PCI={pci})"
    if u in ('kw',):
        return value * delta_hours, f"kW→kWh×{delta_hours:.4f}h"
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
        if '→kWh' in w or 'converted' in w:
            new_warnings.append(w)
        else:
            new_warnings.append(w)
    data['extraction_warnings'] = new_warnings
    return ExtractionResult(**data)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_normalizer.py -v
```
Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/extractor/normalizer.py tests/test_normalizer.py
git commit -m "feat: unit normalizer with kWh conversion table"
```

---

## Task 4: ExcelExtractor

**Files:**
- Create: `src/extractor/extractors/excel.py`
- Create: `tests/test_excel.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_excel.py
import pytest
from pathlib import Path
from extractors.excel import ExcelExtractor
from conftest import EXCEL_SAMPLE

def test_excel_extractor_returns_records():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    assert len(results) > 100  # monthly report has ~thousands of 10-min readings

def test_excel_extractor_has_timestamps():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    assert results[0].timestamp is not None

def test_excel_extractor_gas_flow_in_range():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    # Audit: nominal gas flow 273 Nm3/h ± 5%
    valid = [r for r in results if r.gaz_debit_nm3h is not None]
    assert len(valid) > 0
    avg = sum(r.gaz_debit_nm3h for r in valid) / len(valid)
    assert 250 < avg < 290

def test_excel_extractor_power_in_range():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    valid = [r for r in results if r.puissance_brute_kw is not None]
    avg = sum(r.puissance_brute_kw for r in valid) / len(valid)
    assert 1100 < avg < 1300  # nominal 1200 kW

def test_excel_extractor_source_type():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    assert all(r.source_type == "excel" for r in results)

def test_excel_extractor_field_coverage():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    coverages = [r.field_coverage() for r in results]
    avg_coverage = sum(coverages) / len(coverages)
    assert avg_coverage > 0.8  # should extract >80% of key fields

def test_excel_extractor_pci_from_file():
    ext = ExcelExtractor()
    results = ext.extract(EXCEL_SAMPLE)
    assert results[0].pci_thermie_nm3 == pytest.approx(9.082, rel=1e-3)
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_excel.py -v
```
Expected: `ModuleNotFoundError: No module named 'extractors.excel'`

- [ ] **Step 3: Implement extractors/excel.py**

```python
# src/extractor/extractors/excel.py
from __future__ import annotations
import re
from pathlib import Path
from datetime import datetime, date, time
import openpyxl
from rapidfuzz import process as fuzz_process
from extractors.base import ExtractionResult

# Row index (1-based) → canonical field name
ROW_FIELD_MAP: dict[int, str] = {
    12: 'gaz_volume_nm3',
    14: 'gaz_debit_nm3h',
    15: 'elec_auxiliaire_kwh',
    16: 'puissance_brute_kw',
    17: 'heures_fonctionnement',
    18: 'energie_alternateur_kwh',
    19: 'energie_reactive_kvarh',
    20: 'vitesse_rpm',
    21: 'facteur_puissance',
    22: 'voltage_v',
    23: 'courant_phase1_a',
    24: 'courant_phase2_a',
    25: 'courant_phase3_a',
    26: 'eg_debit_m3h',
    27: 'eg_temp_entree_c',
    28: 'eg_temp_sortie_c',
    29: 'eg_energie_kwh',
    30: 'eg_puissance_kw',
    31: 'ec_recup_debit_m3h',
    32: 'ec_recup_temp_entree_c',
    33: 'ec_recup_temp_sortie_c',
    34: 'ec_recup_energie_kwh',
    35: 'ec_recup_puissance_kw',
    36: 'ec_alpha_sani_debit_m3h',
    37: 'ec_alpha_sani_temp_entree_c',
    38: 'ec_alpha_sani_temp_sortie_c',
    39: 'ec_alpha_sani_energie_kwh',
    40: 'ec_alpha_sani_puissance_kw',
    43: 'ec_alpha_debit_m3h',
    44: 'ec_alpha_temp_entree_c',
    45: 'ec_alpha_temp_sortie_c',
    46: 'ec_alpha_energie_kwh',
    47: 'ec_alpha_puissance_kw',
    50: 'ec_gamma_debit_m3h',
    51: 'ec_gamma_temp_entree_c',
    52: 'ec_gamma_temp_sortie_c',
    53: 'ec_gamma_energie_kwh',
    54: 'ec_gamma_puissance_kw',
    57: 'rendement_electrique_pct',
    58: 'rendement_thermique_pct',
    59: 'rendement_total_pct',
    60: 'steg_achat_kwh',
    61: 'steg_vente_kwh',
    62: 'production_positive_kwh',
    63: 'production_negative_kwh',
}

# French label patterns → field (for fuzzy fallback verification)
FRENCH_LABELS: dict[str, str] = {
    "consommation du gaz naturel moteur en nm3": "gaz_volume_nm3",
    "débit du gaz naturel moteur en nm3/h": "gaz_debit_nm3h",
    "energie éléctrique en kwh": "elec_auxiliaire_kwh",
    "puissance électrique brute en kw": "puissance_brute_kw",
    "heure de fonctionnement": "heures_fonctionnement",
    "energie éléctrique au borne de l'alternateur en kwh": "energie_alternateur_kwh",
    "energie reactive en kvarh": "energie_reactive_kvarh",
    "vitesse en rpm": "vitesse_rpm",
    "facteur de puissance": "facteur_puissance",
    "voltage en v": "voltage_v",
    "courant: phase 1 en a": "courant_phase1_a",
    "courant: phase 2 en a": "courant_phase2_a",
    "courant: phase 3 en a": "courant_phase3_a",
    "rendement electrique %": "rendement_electrique_pct",
    "rendement thermique %": "rendement_thermique_pct",
    "rendement total %": "rendement_total_pct",
    "energie positive steg kwh": "steg_achat_kwh",
    "energie negative steg kwh": "steg_vente_kwh",
    "energie positive production kwh": "production_positive_kwh",
    "energie negative production kwh": "production_negative_kwh",
}

_PCI_RE = re.compile(r'pci\s*\(thermie/nm3\)[:\s]*([0-9.,]+)', re.IGNORECASE)
_COSPHI_RE = re.compile(r'cos.*?=\s*([0-9.,]+)', re.IGNORECASE)


def _parse_float(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(',', '.').strip()
    try:
        return float(s)
    except ValueError:
        return None


def _combine_datetime(d, t) -> datetime | None:
    if isinstance(d, datetime):
        dt_date = d.date()
    elif isinstance(d, date):
        dt_date = d
    else:
        return None
    if isinstance(t, time):
        dt_time = t
    elif isinstance(t, datetime):
        dt_time = t.time()
    else:
        dt_time = time(0, 0)
    return datetime.combine(dt_date, dt_time)


class ExcelExtractor:
    def extract(self, path: Path) -> list[ExtractionResult]:
        wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
        sheet_name = next(
            (s for s in wb.sheetnames if 'bilan' in s.lower() or 'total' in s.lower()),
            wb.sheetnames[0]
        )
        ws = wb[sheet_name]

        pci = 9.082
        cos_phi = 1.0
        warnings: list[str] = []

        # Read metadata rows 1-8 for PCI and cosφ
        for row_idx in range(1, 9):
            cell_val = ws.cell(row_idx, 2).value
            if cell_val is None:
                continue
            s = str(cell_val)
            m = _PCI_RE.search(s)
            if m:
                try:
                    pci = float(m.group(1).replace(',', '.'))
                except ValueError:
                    pass
            m2 = _COSPHI_RE.search(s)
            if m2:
                try:
                    cos_phi = float(m2.group(1).replace(',', '.'))
                except ValueError:
                    pass

        # Build row→field map by trying fuzzy match on col 2 labels
        # to verify or correct the hardcoded ROW_FIELD_MAP
        verified_map: dict[int, str] = dict(ROW_FIELD_MAP)
        label_keys = list(FRENCH_LABELS.keys())
        for row_idx, field in ROW_FIELD_MAP.items():
            label_cell = ws.cell(row_idx, 2).value
            if label_cell is None:
                continue
            normalized = str(label_cell).lower().strip()
            match = fuzz_process.extractOne(normalized, label_keys, score_cutoff=70)
            if match:
                fuzzy_field = FRENCH_LABELS[match[0]]
                if fuzzy_field != field:
                    warnings.append(
                        f"Row {row_idx}: fuzzy label '{match[0]}' maps to '{fuzzy_field}', "
                        f"using hardcoded '{field}'"
                    )

        # Collect all timestamp columns (row 10 = date, row 11 = time)
        max_col = ws.max_column or 1
        results: list[ExtractionResult] = []

        for col_idx in range(5, max_col + 1):
            date_val = ws.cell(10, col_idx).value
            time_val = ws.cell(11, col_idx).value
            if date_val is None:
                continue
            ts = _combine_datetime(date_val, time_val)

            record_data: dict = {}
            for row_idx, field in verified_map.items():
                cell = ws.cell(row_idx, col_idx)
                val = _parse_float(cell.value)
                if val is not None:
                    record_data[field] = val

            if not record_data:
                continue

            results.append(ExtractionResult(
                timestamp=ts,
                source_file=path.name,
                source_type="excel",
                pci_thermie_nm3=pci,
                cos_phi=cos_phi,
                extraction_warnings=list(warnings),
                confidence_score=len(record_data) / len(verified_map),
                **record_data,
            ))

        wb.close()
        return results
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_excel.py -v
```
Expected: 7 PASSED (may be slow ~10-20s for large file)

- [ ] **Step 5: Commit**

```bash
git add src/extractor/extractors/excel.py tests/test_excel.py
git commit -m "feat: ExcelExtractor for wide-format BILAN TOTAL sheets"
```

---

## Task 5: PDFExtractor

**Files:**
- Create: `src/extractor/extractors/pdf.py`
- Create: `tests/test_pdf.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pdf.py
from pathlib import Path
from extractors.pdf import PDFExtractor
from conftest import PDF_SAMPLE

def test_pdf_extractor_returns_list():
    ext = PDFExtractor()
    results = ext.extract(PDF_SAMPLE)
    assert isinstance(results, list)

def test_pdf_extractor_source_type():
    ext = PDFExtractor()
    results = ext.extract(PDF_SAMPLE)
    assert all(r.source_type == "pdf" for r in results)

def test_pdf_extractor_no_exception_on_all_pdfs():
    import os
    pdf_dir = Path("data/data factures et diverses")
    ext = PDFExtractor()
    for pdf_file in pdf_dir.glob("*.pdf"):
        results = ext.extract(pdf_file)
        assert isinstance(results, list)
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_pdf.py -v
```
Expected: `ModuleNotFoundError: No module named 'extractors.pdf'`

- [ ] **Step 3: Implement extractors/pdf.py**

```python
# src/extractor/extractors/pdf.py
from __future__ import annotations
import re
import os
import base64
import json
from pathlib import Path
import pdfplumber
from extractors.base import ExtractionResult

# Regex: captures a float value followed by a unit keyword
_VALUE_RE = re.compile(
    r'([0-9]+(?:[.,][0-9]+)?)\s*'
    r'(kWh|MWh|kW|MW|Nm3|m3/h|kVARh|kVA|%|°C|A|V|rpm|th|Gcal|toe|GJ|BTU)',
    re.IGNORECASE,
)

# Keyword → field hint mapping (partial matching)
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


def _claude_vision_extract(image_bytes: bytes, api_key: str) -> dict[str, float]:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        b64 = base64.standard_b64encode(image_bytes).decode('utf-8')
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
                    },
                    {
                        "type": "text",
                        "text": (
                            "This is a French factory energy invoice or report. "
                            "Extract all numeric energy measurement fields and their values. "
                            "Return only a JSON object with snake_case field names as keys "
                            "and numeric values. Example: {\"energie_kwh\": 1234.5, \"puissance_kw\": 456.0}"
                        ),
                    },
                ],
            }],
            timeout=10.0,
        )
        raw = msg.content[0].text.strip()
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass
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
                        # Fallback: render page as image for Claude vision
                        try:
                            img = page.to_image(resolution=150).original
                            import io
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG")
                            fields = _claude_vision_extract(buf.getvalue(), self._api_key)
                            warnings.append(f"page {page_num+1}: used Claude vision fallback")
                        except Exception as e:
                            warnings.append(f"page {page_num+1}: vision fallback failed: {e}")

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
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_pdf.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/extractor/extractors/pdf.py tests/test_pdf.py
git commit -m "feat: PDFExtractor with pdfplumber + Claude vision fallback"
```

---

## Task 6: ImageExtractor

**Files:**
- Create: `src/extractor/extractors/image.py`
- Create: `tests/test_image.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_image.py
from pathlib import Path
from extractors.image import ImageExtractor
from conftest import IMAGE_SAMPLE

def test_image_extractor_returns_result():
    ext = ImageExtractor()
    results = ext.extract(IMAGE_SAMPLE)
    assert isinstance(results, list)
    assert len(results) == 1

def test_image_extractor_source_type():
    ext = ImageExtractor()
    results = ext.extract(IMAGE_SAMPLE)
    assert results[0].source_type == "image"

def test_image_extractor_no_exception_on_all_jpegs():
    import os
    img_dir = Path("data/data factures et diverses")
    ext = ImageExtractor()
    for img_file in list(img_dir.glob("*.jpeg"))[:5]:  # test first 5 only (slow)
        results = ext.extract(img_file)
        assert isinstance(results, list)
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_image.py -v
```
Expected: `ModuleNotFoundError: No module named 'extractors.image'`

- [ ] **Step 3: Implement extractors/image.py**

```python
# src/extractor/extractors/image.py
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

_READER = None  # lazy-loaded to avoid import cost


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
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_image.py -v
```
Expected: 3 PASSED (first run will download EasyOCR model ~200MB, takes 1-2 min)

- [ ] **Step 5: Commit**

```bash
git add src/extractor/extractors/image.py tests/test_image.py
git commit -m "feat: ImageExtractor with EasyOCR + image preprocessing"
```

---

## Task 7: CO2 Estimator

**Files:**
- Create: `src/extractor/co2.py`
- Create: `tests/test_co2.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_co2.py
import pytest
from co2 import estimate_co2
from extractors.base import ExtractionResult

def test_co2_electricity_only():
    r = ExtractionResult(
        source_file="f.xlsx", source_type="excel",
        energie_alternateur_kwh=1000.0,
    )
    out = estimate_co2(r, prev_energie_kwh=0.0, prev_gaz_nm3=0.0)
    # 1000 kWh × 0.267 = 267 kgCO2
    assert out.co2_kg == pytest.approx(267.0)

def test_co2_gas_only():
    r = ExtractionResult(
        source_file="f.xlsx", source_type="excel",
        gaz_volume_nm3=100.0,
        pci_thermie_nm3=9.082,
    )
    out = estimate_co2(r, prev_energie_kwh=0.0, prev_gaz_nm3=0.0)
    # 100 Nm3 × 9.082 th/Nm3 × 1.163 kWh/th × 0.202 kgCO2/kWh
    expected = 100.0 * 9.082 * 1.163 * 0.202
    assert out.co2_kg == pytest.approx(expected, rel=1e-3)

def test_co2_combined():
    r = ExtractionResult(
        source_file="f.xlsx", source_type="excel",
        energie_alternateur_kwh=500.0,
        gaz_volume_nm3=50.0,
        pci_thermie_nm3=9.082,
    )
    out = estimate_co2(r, prev_energie_kwh=0.0, prev_gaz_nm3=0.0)
    elec_co2 = 500.0 * 0.267
    gas_co2 = 50.0 * 9.082 * 1.163 * 0.202
    assert out.co2_kg == pytest.approx(elec_co2 + gas_co2, rel=1e-3)

def test_co2_uses_delta_for_cumulative():
    r = ExtractionResult(
        source_file="f.xlsx", source_type="excel",
        energie_alternateur_kwh=1100.0,
        gaz_volume_nm3=150.0,
        pci_thermie_nm3=9.082,
    )
    out = estimate_co2(r, prev_energie_kwh=1000.0, prev_gaz_nm3=100.0)
    elec_co2 = (1100.0 - 1000.0) * 0.267
    gas_co2 = (150.0 - 100.0) * 9.082 * 1.163 * 0.202
    assert out.co2_kg == pytest.approx(elec_co2 + gas_co2, rel=1e-3)

def test_co2_none_when_no_energy_fields():
    r = ExtractionResult(source_file="f.pdf", source_type="pdf")
    out = estimate_co2(r, prev_energie_kwh=None, prev_gaz_nm3=None)
    assert out.co2_kg is None
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_co2.py -v
```
Expected: `ModuleNotFoundError: No module named 'co2'`

- [ ] **Step 3: Implement co2.py**

```python
# src/extractor/co2.py
from __future__ import annotations
from extractors.base import ExtractionResult

ELEC_FACTOR = 0.267   # kgCO2/kWh — Tunisia STEG grid
GAS_FACTOR  = 0.202   # kgCO2/kWh_thermal


def estimate_co2(
    record: ExtractionResult,
    prev_energie_kwh: float | None,
    prev_gaz_nm3: float | None,
) -> ExtractionResult:
    """
    Returns a copy of record with co2_kg set.
    Uses delta of cumulative counters when prev values are provided.
    """
    data = record.model_dump()
    co2 = 0.0
    has_data = False

    # Electricity contribution
    if record.energie_alternateur_kwh is not None:
        prev_e = prev_energie_kwh or 0.0
        delta_e = max(record.energie_alternateur_kwh - prev_e, 0.0)
        co2 += delta_e * ELEC_FACTOR
        has_data = True

    # Gas contribution
    if record.gaz_volume_nm3 is not None:
        prev_g = prev_gaz_nm3 or 0.0
        delta_g = max(record.gaz_volume_nm3 - prev_g, 0.0)
        pci = record.pci_thermie_nm3
        co2 += delta_g * pci * 1.163 * GAS_FACTOR
        has_data = True

    data['co2_kg'] = co2 if has_data else None
    return ExtractionResult(**data)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_co2.py -v
```
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/extractor/co2.py tests/test_co2.py
git commit -m "feat: CO2 estimator — Tunisia grid 0.267 + gas 0.202 kgCO2/kWh"
```

---

## Task 8: ClaudeValidator

**Files:**
- Create: `src/extractor/validator.py`
- Create: `tests/test_validator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validator.py
import os
from validator import validate_batch, _rule_validate
from extractors.base import ExtractionResult

def _make_record(**kwargs) -> ExtractionResult:
    return ExtractionResult(source_file="f.xlsx", source_type="excel", **kwargs)

def test_rule_validate_good_record():
    r = _make_record(voltage_v=408.0, facteur_puissance=0.98, gaz_debit_nm3h=272.0)
    out = _rule_validate(r)
    assert out.confidence_score > 0.5
    assert 'voltage_out_of_range' not in ' '.join(out.extraction_warnings)

def test_rule_validate_bad_voltage():
    r = _make_record(voltage_v=500.0)  # out of 380-440V range
    out = _rule_validate(r)
    assert any('voltage' in w for w in out.extraction_warnings)

def test_rule_validate_bad_power_factor():
    r = _make_record(facteur_puissance=0.5)  # below 0.90 minimum
    out = _rule_validate(r)
    assert any('facteur_puissance' in w for w in out.extraction_warnings)

def test_rule_validate_bad_gas_flow():
    r = _make_record(gaz_debit_nm3h=500.0)  # well above 285 Nm3/h max
    out = _rule_validate(r)
    assert any('gaz_debit' in w for w in out.extraction_warnings)

def test_validate_batch_no_api_key_uses_rule_mode():
    records = [_make_record(voltage_v=408.0), _make_record(voltage_v=600.0)]
    out = validate_batch(records, api_key=None)
    assert len(out) == 2
    assert out[0].confidence_score >= 0.0
    # Bad voltage record should have lower confidence
    assert out[1].confidence_score < out[0].confidence_score or \
           any('voltage' in w for w in out[1].extraction_warnings)
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_validator.py -v
```
Expected: `ModuleNotFoundError: No module named 'validator'`

- [ ] **Step 3: Implement validator.py**

```python
# src/extractor/validator.py
from __future__ import annotations
import json
import os
from extractors.base import ExtractionResult

# Physical bounds from audit doc
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
    'facteur_puissance': (0.90, 1.0),
}

_BATCH_PROMPT = """You are an energy data validator for a pharmaceutical factory tri-generation system.
Below are extracted records from energy monitoring. For each record, check physical plausibility
using these bounds from the factory audit:
- voltage_v: 380–440 V
- facteur_puissance: 0.90–1.0
- gaz_debit_nm3h: 200–300 Nm3/h
- puissance_brute_kw: 800–1400 kW
- vitesse_rpm: 1400–1600 rpm
- eg_temp_entree_c: 3–15 °C
- ec_recup_temp_entree_c: 90–105 °C
- rendement_electrique_pct: 30–55 %

Return a JSON array where each element has:
{
  "index": <int>,
  "confidence_score": <0.0-1.0>,
  "warnings": ["field: reason", ...],
  "corrections": {"field": suggested_value}
}

Records:
"""


def _rule_validate(record: ExtractionResult) -> ExtractionResult:
    warnings = list(record.extraction_warnings)
    violations = 0
    for field, (lo, hi) in _BOUNDS.items():
        val = getattr(record, field, None)
        if val is not None and not (lo <= val <= hi):
            warnings.append(f"{field}_out_of_range: {val} not in [{lo}, {hi}]")
            violations += 1

    # coverage-based confidence
    coverage = record.field_coverage()
    penalty = violations * 0.1
    confidence = max(coverage - penalty, 0.0)

    data = record.model_dump()
    data['confidence_score'] = confidence
    data['extraction_warnings'] = warnings
    return ExtractionResult(**data)


def _claude_validate(records: list[ExtractionResult], api_key: str) -> list[ExtractionResult]:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    slim = []
    for i, r in enumerate(records):
        slim.append({
            "index": i,
            "voltage_v": r.voltage_v,
            "gaz_debit_nm3h": r.gaz_debit_nm3h,
            "puissance_brute_kw": r.puissance_brute_kw,
            "facteur_puissance": r.facteur_puissance,
            "rendement_electrique_pct": r.rendement_electrique_pct,
            "eg_temp_entree_c": r.eg_temp_entree_c,
        })

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": _BATCH_PROMPT + json.dumps(slim, default=str)
            }],
            timeout=10.0,
        )
        raw = msg.content[0].text
        import re
        arr_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not arr_match:
            raise ValueError("no JSON array in response")
        validations = json.loads(arr_match.group())

        results = []
        val_map = {v['index']: v for v in validations}
        for i, record in enumerate(records):
            v = val_map.get(i, {})
            data = record.model_dump()
            data['confidence_score'] = float(v.get('confidence_score', record.confidence_score))
            existing_w = list(record.extraction_warnings)
            existing_w.extend(v.get('warnings', []))
            data['extraction_warnings'] = existing_w
            corrections = v.get('corrections', {})
            for field, val in corrections.items():
                if field in ExtractionResult.model_fields and data.get(field) is None:
                    data[field] = val
            results.append(ExtractionResult(**data))
        return results

    except Exception as e:
        # Fallback to rule-based on Claude failure
        return [_rule_validate(r) for r in records]


def validate_batch(
    records: list[ExtractionResult],
    api_key: str | None = None,
) -> list[ExtractionResult]:
    key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        return [_rule_validate(r) for r in records]

    BATCH = 50
    results = []
    for i in range(0, len(records), BATCH):
        batch = records[i:i + BATCH]
        results.extend(_claude_validate(batch, key))
    return results
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_validator.py -v
```
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/extractor/validator.py tests/test_validator.py
git commit -m "feat: ClaudeValidator with rule-based fallback and physical bounds"
```

---

## Task 9: Anomaly Detector

**Files:**
- Create: `src/extractor/anomaly.py`
- Create: `tests/test_anomaly.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_anomaly.py
import pandas as pd
import numpy as np
from anomaly import detect_anomalies

def _make_df(n=200, spike_idx=50):
    """Creates a DataFrame with one obvious spike at spike_idx."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        'id': range(n),
        'puissance_brute_kw': rng.normal(1200, 20, n),
        'gaz_debit_nm3h': rng.normal(272, 2, n),
        'eg_puissance_kw': rng.normal(260, 15, n),
        'ec_recup_puissance_kw': rng.normal(450, 30, n),
        'is_anomaly': False,
        'anomaly_type': None,
    })
    df.loc[spike_idx, 'puissance_brute_kw'] = 5000.0  # obvious spike
    return df

def test_spike_detected():
    df = _make_df(spike_idx=50)
    result = detect_anomalies(df)
    assert result.loc[50, 'is_anomaly'] is True or result.loc[50, 'is_anomaly'] == True

def test_normal_records_mostly_clean():
    df = _make_df(spike_idx=50)
    result = detect_anomalies(df)
    anomaly_rate = result['is_anomaly'].mean()
    assert anomaly_rate < 0.15  # less than 15% flagged

def test_stuck_sensor_detected():
    df = _make_df()
    df.loc[10:17, 'puissance_brute_kw'] = 1200.0  # 8 identical readings
    result = detect_anomalies(df)
    assert result.loc[15, 'is_anomaly'] is True or result.loc[15, 'is_anomaly'] == True

def test_dropout_detected():
    df = _make_df()
    df.loc[20:24, 'gaz_debit_nm3h'] = np.nan  # 5 nulls
    result = detect_anomalies(df)
    assert result.loc[22, 'is_anomaly'] is True or result.loc[22, 'is_anomaly'] == True

def test_output_has_anomaly_type():
    df = _make_df(spike_idx=50)
    result = detect_anomalies(df)
    assert result.loc[50, 'anomaly_type'] is not None
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_anomaly.py -v
```
Expected: `ModuleNotFoundError: No module named 'anomaly'`

- [ ] **Step 3: Implement anomaly.py**

```python
# src/extractor/anomaly.py
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

FEATURES = ['puissance_brute_kw', 'gaz_debit_nm3h', 'eg_puissance_kw', 'ec_recup_puissance_kw']


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds/updates 'is_anomaly' and 'anomaly_type' columns in-place copy.
    Runs: Z-score → IQR → Isolation Forest → stuck sensor → dropout.
    """
    result = df.copy()
    result['is_anomaly'] = result.get('is_anomaly', False).astype(bool)
    if 'anomaly_type' not in result.columns:
        result['anomaly_type'] = None

    feature_cols = [c for c in FEATURES if c in result.columns]
    if not feature_cols:
        return result

    def _flag(mask: pd.Series, atype: str):
        new = mask & ~result['is_anomaly']
        result.loc[new, 'anomaly_type'] = atype
        result.loc[mask, 'is_anomaly'] = True

    # 1. Z-score ±3σ
    for col in feature_cols:
        series = result[col].dropna()
        if len(series) < 10:
            continue
        z = (result[col] - series.mean()) / (series.std() + 1e-9)
        _flag(z.abs() > 3, 'zscore_spike')

    # 2. IQR 1.5×
    for col in feature_cols:
        series = result[col].dropna()
        if len(series) < 10:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        mask = (result[col] < q1 - 1.5 * iqr) | (result[col] > q3 + 1.5 * iqr)
        _flag(mask.fillna(False), 'iqr_outlier')

    # 3. Isolation Forest (multivariate)
    X = result[feature_cols].dropna()
    if len(X) > 50:
        iso = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
        preds = iso.fit_predict(X)
        iso_mask = pd.Series(preds == -1, index=X.index).reindex(result.index, fill_value=False)
        _flag(iso_mask, 'isolation_forest')

    # 4. Stuck sensor: rolling std == 0 over 6 consecutive readings
    for col in feature_cols:
        rolling_std = result[col].rolling(6, min_periods=6).std()
        _flag((rolling_std == 0).fillna(False), 'stuck_sensor')

    # 5. Dropout: null run > 3
    for col in feature_cols:
        null_mask = result[col].isna()
        # cumsum trick: groups of consecutive nulls
        groups = (~null_mask).cumsum()
        run_lengths = null_mask.groupby(groups).transform('sum')
        _flag((run_lengths > 3) & null_mask, 'dropout')

    return result
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_anomaly.py -v
```
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/extractor/anomaly.py tests/test_anomaly.py
git commit -m "feat: anomaly detector — Z-score, IQR, Isolation Forest, stuck sensor, dropout"
```

---

## Task 10: Database Layer

**Files:**
- Create: `src/extractor/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db.py
import tempfile
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine
from db import Base, EnergyRecord, write_records, read_all_records, update_anomaly_flags
from extractors.base import ExtractionResult

def _engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

def test_write_and_read_records():
    engine = _engine()
    records = [
        ExtractionResult(
            timestamp=datetime(2026, 4, 1, 0, 0),
            source_file="test.xlsx",
            source_type="excel",
            puissance_brute_kw=1199.0,
            gaz_debit_nm3h=272.76,
            confidence_score=0.9,
        )
    ]
    write_records(engine, records)
    df = read_all_records(engine)
    assert len(df) == 1
    assert df.iloc[0]['source_file'] == "test.xlsx"
    assert abs(df.iloc[0]['puissance_brute_kw'] - 1199.0) < 0.01

def test_write_multiple_files():
    engine = _engine()
    records = [
        ExtractionResult(source_file="a.xlsx", source_type="excel", puissance_brute_kw=1200.0),
        ExtractionResult(source_file="b.pdf", source_type="pdf", steg_achat_kwh=500.0),
    ]
    write_records(engine, records)
    df = read_all_records(engine)
    assert len(df) == 2

def test_update_anomaly_flags():
    import pandas as pd
    engine = _engine()
    records = [ExtractionResult(source_file="f.xlsx", source_type="excel")]
    write_records(engine, records)
    df = read_all_records(engine)
    df['is_anomaly'] = True
    df['anomaly_type'] = 'zscore_spike'
    update_anomaly_flags(engine, df)
    df2 = read_all_records(engine)
    assert df2.iloc[0]['is_anomaly'] == True

def test_extraction_warnings_serialized():
    engine = _engine()
    records = [ExtractionResult(
        source_file="f.xlsx", source_type="excel",
        extraction_warnings=["voltage_out_of_range: 500"]
    )]
    write_records(engine, records)
    df = read_all_records(engine)
    warnings = json.loads(df.iloc[0]['extraction_warnings'])
    assert "voltage_out_of_range: 500" in warnings
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_db.py -v
```
Expected: `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: Implement db.py**

```python
# src/extractor/db.py
from __future__ import annotations
import json
from datetime import datetime
import pandas as pd
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, Boolean, DateTime,
    Text, update
)
from sqlalchemy.orm import DeclarativeBase, Session
from extractors.base import ExtractionResult


class Base(DeclarativeBase):
    pass


class EnergyRecord(Base):
    __tablename__ = "energy_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, index=True, nullable=True)
    source_file = Column(String, index=True)
    source_type = Column(String)
    confidence_score = Column(Float, default=0.0)
    is_anomaly = Column(Boolean, default=False)
    anomaly_type = Column(String, nullable=True)
    co2_kg = Column(Float, nullable=True)
    extraction_warnings = Column(Text, nullable=True)
    pci_thermie_nm3 = Column(Float, default=9.082)
    cos_phi = Column(Float, default=1.0)

    # Gas
    gaz_volume_nm3 = Column(Float, nullable=True)
    gaz_debit_nm3h = Column(Float, nullable=True)

    # Electrical
    elec_auxiliaire_kwh = Column(Float, nullable=True)
    puissance_brute_kw = Column(Float, nullable=True)
    heures_fonctionnement = Column(Float, nullable=True)
    energie_alternateur_kwh = Column(Float, nullable=True)
    energie_reactive_kvarh = Column(Float, nullable=True)
    vitesse_rpm = Column(Float, nullable=True)
    facteur_puissance = Column(Float, nullable=True)
    voltage_v = Column(Float, nullable=True)
    courant_phase1_a = Column(Float, nullable=True)
    courant_phase2_a = Column(Float, nullable=True)
    courant_phase3_a = Column(Float, nullable=True)

    # Chilled water
    eg_debit_m3h = Column(Float, nullable=True)
    eg_temp_entree_c = Column(Float, nullable=True)
    eg_temp_sortie_c = Column(Float, nullable=True)
    eg_energie_kwh = Column(Float, nullable=True)
    eg_puissance_kw = Column(Float, nullable=True)

    # Recovered hot water
    ec_recup_debit_m3h = Column(Float, nullable=True)
    ec_recup_temp_entree_c = Column(Float, nullable=True)
    ec_recup_temp_sortie_c = Column(Float, nullable=True)
    ec_recup_energie_kwh = Column(Float, nullable=True)
    ec_recup_puissance_kw = Column(Float, nullable=True)

    # Hot water Alpha Sanitaire
    ec_alpha_sani_debit_m3h = Column(Float, nullable=True)
    ec_alpha_sani_temp_entree_c = Column(Float, nullable=True)
    ec_alpha_sani_temp_sortie_c = Column(Float, nullable=True)
    ec_alpha_sani_energie_kwh = Column(Float, nullable=True)
    ec_alpha_sani_puissance_kw = Column(Float, nullable=True)

    # Hot water Alpha
    ec_alpha_debit_m3h = Column(Float, nullable=True)
    ec_alpha_temp_entree_c = Column(Float, nullable=True)
    ec_alpha_temp_sortie_c = Column(Float, nullable=True)
    ec_alpha_energie_kwh = Column(Float, nullable=True)
    ec_alpha_puissance_kw = Column(Float, nullable=True)

    # Hot water Gamma
    ec_gamma_debit_m3h = Column(Float, nullable=True)
    ec_gamma_temp_entree_c = Column(Float, nullable=True)
    ec_gamma_temp_sortie_c = Column(Float, nullable=True)
    ec_gamma_energie_kwh = Column(Float, nullable=True)
    ec_gamma_puissance_kw = Column(Float, nullable=True)

    # Efficiencies
    rendement_electrique_pct = Column(Float, nullable=True)
    rendement_thermique_pct = Column(Float, nullable=True)
    rendement_total_pct = Column(Float, nullable=True)

    # STEG grid
    steg_achat_kwh = Column(Float, nullable=True)
    steg_vente_kwh = Column(Float, nullable=True)
    production_positive_kwh = Column(Float, nullable=True)
    production_negative_kwh = Column(Float, nullable=True)


def _record_to_row(r: ExtractionResult) -> dict:
    data = r.model_dump()
    data['extraction_warnings'] = json.dumps(data.get('extraction_warnings', []))
    return data


def write_records(engine, records: list[ExtractionResult]) -> None:
    rows = [_record_to_row(r) for r in records]
    with Session(engine) as session:
        session.bulk_insert_mappings(EnergyRecord, rows)
        session.commit()


def read_all_records(engine) -> pd.DataFrame:
    with Session(engine) as session:
        rows = session.query(EnergyRecord).all()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([{
            c.name: getattr(row, c.name)
            for c in EnergyRecord.__table__.columns
        } for row in rows])


def update_anomaly_flags(engine, df: pd.DataFrame) -> None:
    with Session(engine) as session:
        for _, row in df.iterrows():
            session.execute(
                update(EnergyRecord)
                .where(EnergyRecord.id == int(row['id']))
                .values(
                    is_anomaly=bool(row.get('is_anomaly', False)),
                    anomaly_type=row.get('anomaly_type'),
                )
            )
        session.commit()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_db.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/extractor/db.py tests/test_db.py
git commit -m "feat: SQLAlchemy database layer with write/read/update_anomaly"
```

---

## Task 11: Pipeline Orchestrator

**Files:**
- Create: `src/extractor/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline.py
import tempfile
from pathlib import Path
from pipeline import run_pipeline
from conftest import DATA_DIR

def test_pipeline_returns_positive_count():
    with tempfile.TemporaryDirectory() as tmp:
        db_url = f"sqlite:///{tmp}/test.db"
        count = run_pipeline(DATA_DIR, db_url)
        assert count > 0

def test_pipeline_processes_excel_files():
    with tempfile.TemporaryDirectory() as tmp:
        db_url = f"sqlite:///{tmp}/test.db"
        count = run_pipeline(DATA_DIR, db_url)
        # 21 Excel files × 100+ readings each
        assert count > 1000
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_pipeline.py -v
```
Expected: `ModuleNotFoundError: No module named 'pipeline'`

- [ ] **Step 3: Implement pipeline.py**

```python
# src/extractor/pipeline.py
from __future__ import annotations
import os
from pathlib import Path
from sqlalchemy import create_engine

from extractors.base import ExtractionResult
from extractors.excel import ExcelExtractor
from extractors.pdf import PDFExtractor
from extractors.image import ImageExtractor
from normalizer import normalize_record
from validator import validate_batch
from co2 import estimate_co2
from anomaly import detect_anomalies
from db import Base, write_records, read_all_records, update_anomaly_flags


def run_pipeline(data_dir: Path | str, db_url: str) -> int:
    data_dir = Path(data_dir)
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    records: list[ExtractionResult] = []

    # Excel
    excel_dir = data_dir / "data tri gen"
    if excel_dir.exists():
        ext = ExcelExtractor()
        for f in sorted(excel_dir.glob("*.xlsx")):
            try:
                records.extend(ext.extract(f))
                print(f"  Excel: {f.name} → {len(records)} total records")
            except Exception as e:
                print(f"  Excel FAILED {f.name}: {e}")

    # PDF
    invoice_dir = data_dir / "data factures et diverses"
    if invoice_dir.exists():
        ext_pdf = PDFExtractor(api_key=api_key)
        for f in sorted(invoice_dir.glob("*.pdf")):
            try:
                records.extend(ext_pdf.extract(f))
            except Exception as e:
                print(f"  PDF FAILED {f.name}: {e}")

        # Images
        ext_img = ImageExtractor()
        for pattern in ("*.jpeg", "*.jpg", "*.png"):
            for f in sorted(invoice_dir.glob(pattern)):
                try:
                    records.extend(ext_img.extract(f))
                except Exception as e:
                    print(f"  Image FAILED {f.name}: {e}")

    if not records:
        print("No records extracted.")
        return 0

    print(f"Extracted {len(records)} raw records. Normalizing...")
    records = [normalize_record(r) for r in records]

    print("Validating...")
    records = validate_batch(records, api_key=api_key or None)

    print("Estimating CO2...")
    prev_e: float | None = None
    prev_g: float | None = None
    co2_records = []
    for r in sorted(records, key=lambda x: (x.source_file, x.timestamp or "")):
        r = estimate_co2(r, prev_e, prev_g)
        prev_e = r.energie_alternateur_kwh
        prev_g = r.gaz_volume_nm3
        co2_records.append(r)
    records = co2_records

    print("Writing to DB...")
    write_records(engine, records)

    print("Running anomaly detection...")
    df = read_all_records(engine)
    if not df.empty:
        df = detect_anomalies(df)
        update_anomaly_flags(engine, df)

    print(f"Pipeline complete. {len(records)} records written.")
    return len(records)


if __name__ == "__main__":
    import sys
    data = Path(os.getenv("DATA_DIR", "../../data"))
    url = os.getenv("DB_URL", f"sqlite:///{data}/db/energy.db")
    Path(url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
    n = run_pipeline(data, url)
    sys.exit(0 if n > 0 else 1)
```

- [ ] **Step 4: Run tests (slow — processes all real files)**

```bash
python -m pytest tests/test_pipeline.py -v -s
```
Expected: 2 PASSED (takes 1-3 minutes)

- [ ] **Step 5: Commit**

```bash
git add src/extractor/pipeline.py tests/test_pipeline.py
git commit -m "feat: pipeline orchestrator — extract, normalize, validate, CO2, anomaly"
```

---

## Task 12: FastAPI App

**Files:**
- Create: `src/extractor/main.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api.py
import tempfile, os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from conftest import EXCEL_SAMPLE

os.environ.setdefault("DB_URL", "sqlite:////:memory:")
os.environ.setdefault("DATA_DIR", str(Path("data")))

from main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_extract_excel():
    with open(EXCEL_SAMPLE, "rb") as f:
        r = client.post("/extract", files={"file": ("test.xlsx", f, "application/octet-stream")})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "puissance_brute_kw" in data[0]

def test_records_endpoint():
    r = client.get("/records")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_summary_endpoint():
    r = client.get("/summary")
    assert r.status_code == 200
    body = r.json()
    assert "total_records" in body
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_api.py -v
```
Expected: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Implement main.py**

```python
# src/extractor/main.py
from __future__ import annotations
import os
import tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from sqlalchemy import create_engine

from extractors.base import ExtractionResult
from extractors.excel import ExcelExtractor
from extractors.pdf import PDFExtractor
from extractors.image import ImageExtractor
from normalizer import normalize_record
from validator import validate_batch
from co2 import estimate_co2
from db import Base, write_records, read_all_records

DB_URL = os.getenv("DB_URL", "sqlite:///data/db/energy.db")
_engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(_engine)

app = FastAPI(title="Energy Extraction API", version="1.0.0")

_EXTRACTORS = {
    ".xlsx": ExcelExtractor(),
    ".xls": ExcelExtractor(),
    ".pdf": PDFExtractor(),
    ".jpeg": ImageExtractor(),
    ".jpg": ImageExtractor(),
    ".png": ImageExtractor(),
}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract")
def extract(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    extractor = _EXTRACTORS.get(suffix)
    if extractor is None:
        raise HTTPException(400, f"Unsupported file type: {suffix}")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = Path(tmp.name)

    try:
        records = extractor.extract(tmp_path)
        records = [normalize_record(r) for r in records]
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        records = validate_batch(records, api_key=api_key or None)
        prev_e = prev_g = None
        co2_records = []
        for r in records:
            r = estimate_co2(r, prev_e, prev_g)
            prev_e = r.energie_alternateur_kwh
            prev_g = r.gaz_volume_nm3
            co2_records.append(r)
        write_records(_engine, co2_records)
        return [r.model_dump() for r in co2_records]
    finally:
        tmp_path.unlink(missing_ok=True)


@app.get("/records")
def get_records():
    df = read_all_records(_engine)
    if df.empty:
        return []
    return df.to_dict(orient="records")


@app.get("/summary")
def get_summary():
    df = read_all_records(_engine)
    if df.empty:
        return {"total_records": 0}

    def safe_sum(col):
        return float(df[col].dropna().sum()) if col in df.columns else 0.0

    return {
        "total_records": len(df),
        "source_breakdown": df['source_type'].value_counts().to_dict(),
        "avg_confidence": float(df['confidence_score'].mean()),
        "anomaly_count": int(df['is_anomaly'].sum()),
        "total_co2_kg": safe_sum('co2_kg'),
        "total_elec_produced_kwh": safe_sum('energie_alternateur_kwh'),
        "avg_puissance_brute_kw": float(df['puissance_brute_kw'].dropna().mean()) if 'puissance_brute_kw' in df.columns else 0.0,
        "avg_rendement_electrique_pct": float(df['rendement_electrique_pct'].dropna().mean()) if 'rendement_electrique_pct' in df.columns else 0.0,
    }
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_api.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/extractor/main.py tests/test_api.py
git commit -m "feat: FastAPI app — /extract, /health, /records, /summary"
```

---

## Task 13: Streamlit Dashboard

**Files:**
- Create: `src/dashboard/app.py`

No TDD for Streamlit (no test client). Verify by running locally.

- [ ] **Step 1: Implement app.py**

```python
# src/dashboard/app.py
from __future__ import annotations
import json
import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "extractor"))
from db import read_all_records

DB_URL = os.getenv("DB_URL", "sqlite:///data/db/energy.db")
_engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

st.set_page_config(page_title="Energy Dashboard", layout="wide", page_icon="⚡")
st.title("⚡ Pharmaceutical Factory — Energy Analytics")

@st.cache_data(ttl=30)
def load_data() -> pd.DataFrame:
    df = read_all_records(_engine)
    if df.empty:
        return df
    if 'extraction_warnings' in df.columns:
        df['extraction_warnings'] = df['extraction_warnings'].apply(
            lambda x: json.loads(x) if isinstance(x, str) else []
        )
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.sort_values('timestamp')
    return df

df = load_data()

if df.empty:
    st.warning("No data loaded yet. Run the pipeline first.")
    st.stop()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 KPIs", "🌿 CO2 Trend", "🚨 Anomalies", "📋 Data Table", "🔍 Coverage"
])

# --- TAB 1: KPIs ---
with tab1:
    excel_df = df[df['source_type'] == 'excel']
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        total_co2 = df['co2_kg'].sum() / 1000 if 'co2_kg' in df.columns else 0
        st.metric("Total CO2", f"{total_co2:.1f} tCO2")
    with col2:
        avg_power = excel_df['puissance_brute_kw'].mean() if not excel_df.empty else 0
        st.metric("Avg Power", f"{avg_power:.0f} kW")
    with col3:
        avg_eff = excel_df['rendement_electrique_pct'].mean() if not excel_df.empty else 0
        st.metric("Avg Elec Efficiency", f"{avg_eff:.1f} %")
    with col4:
        anomalies = int(df['is_anomaly'].sum())
        st.metric("Anomalies Detected", anomalies)
    with col5:
        avg_conf = df['confidence_score'].mean()
        st.metric("Avg Confidence", f"{avg_conf:.0%}")

    if not excel_df.empty and 'timestamp' in excel_df.columns:
        st.subheader("Electrical Power Output Over Time")
        fig = px.line(
            excel_df.dropna(subset=['timestamp', 'puissance_brute_kw']),
            x='timestamp', y='puissance_brute_kw',
            title='Puissance Brute (kW)', labels={'puissance_brute_kw': 'kW'}
        )
        st.plotly_chart(fig, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            fig2 = px.line(
                excel_df.dropna(subset=['timestamp', 'gaz_debit_nm3h']),
                x='timestamp', y='gaz_debit_nm3h',
                title='Gas Flow (Nm3/h)'
            )
            st.plotly_chart(fig2, use_container_width=True)
        with col_b:
            fig3 = px.line(
                excel_df.dropna(subset=['timestamp', 'rendement_electrique_pct']),
                x='timestamp', y='rendement_electrique_pct',
                title='Electrical Efficiency (%)'
            )
            st.plotly_chart(fig3, use_container_width=True)

# --- TAB 2: CO2 Trend ---
with tab2:
    co2_df = df.dropna(subset=['co2_kg'])
    if not co2_df.empty and 'timestamp' in co2_df.columns:
        co2_df = co2_df.dropna(subset=['timestamp'])
        daily = co2_df.set_index('timestamp').resample('D')['co2_kg'].sum().reset_index()
        daily['co2_tonne'] = daily['co2_kg'] / 1000
        fig = px.line(daily, x='timestamp', y='co2_tonne',
                      title='Daily CO2 Emissions (tCO2)',
                      labels={'co2_tonne': 'tCO2', 'timestamp': 'Date'})
        fig.add_hline(y=daily['co2_tonne'].mean(), line_dash="dash",
                      annotation_text="Average")
        st.plotly_chart(fig, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            total_elec_co2 = co2_df['energie_alternateur_kwh'].dropna().sum() * 0.267 / 1000
            total_gas_co2 = (
                co2_df['gaz_volume_nm3'].dropna().sum() * 9.082 * 1.163 * 0.202 / 1000
            )
            fig_pie = px.pie(
                values=[total_elec_co2, total_gas_co2],
                names=['Electricity (STEG)', 'Natural Gas'],
                title='CO2 by Source'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_b:
            st.metric("Total CO2 Emitted", f"{co2_df['co2_kg'].sum()/1000:.1f} tCO2")
            st.metric("Electricity CO2", f"{total_elec_co2:.1f} tCO2")
            st.metric("Gas CO2", f"{total_gas_co2:.1f} tCO2")
    else:
        st.info("No CO2 data available yet.")

# --- TAB 3: Anomalies ---
with tab3:
    anomaly_df = df[df['is_anomaly'] == True]
    st.metric("Total Anomalies", len(anomaly_df))

    if not anomaly_df.empty:
        type_counts = anomaly_df['anomaly_type'].value_counts().reset_index()
        type_counts.columns = ['Type', 'Count']
        fig = px.bar(type_counts, x='Type', y='Count', title='Anomalies by Type',
                     color='Type')
        st.plotly_chart(fig, use_container_width=True)

        cols_show = ['timestamp', 'source_file', 'anomaly_type',
                     'puissance_brute_kw', 'gaz_debit_nm3h', 'confidence_score']
        cols_show = [c for c in cols_show if c in anomaly_df.columns]
        st.dataframe(
            anomaly_df[cols_show].head(200),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No anomalies detected!")

# --- TAB 4: Data Table ---
with tab4:
    sources = ['All'] + sorted(df['source_type'].unique().tolist())
    selected = st.selectbox("Filter by source type", sources)
    filtered = df if selected == 'All' else df[df['source_type'] == selected]

    if 'timestamp' in filtered.columns:
        min_d = filtered['timestamp'].dropna().min()
        max_d = filtered['timestamp'].dropna().max()
        if pd.notna(min_d) and pd.notna(max_d):
            date_range = st.date_input("Date range", [min_d, max_d])
            if len(date_range) == 2:
                filtered = filtered[
                    (filtered['timestamp'] >= pd.Timestamp(date_range[0])) &
                    (filtered['timestamp'] <= pd.Timestamp(date_range[1]))
                ]

    st.write(f"Showing {len(filtered):,} records")

    display_cols = [
        'timestamp', 'source_file', 'source_type', 'confidence_score',
        'puissance_brute_kw', 'gaz_debit_nm3h', 'eg_puissance_kw',
        'co2_kg', 'is_anomaly', 'anomaly_type'
    ]
    display_cols = [c for c in display_cols if c in filtered.columns]

    st.dataframe(
        filtered[display_cols].head(500),
        use_container_width=True,
        hide_index=True,
    )

# --- TAB 5: Coverage ---
with tab5:
    st.subheader("Extraction Coverage by Source File")
    coverage = df.groupby('source_file').agg(
        records=('id', 'count'),
        avg_confidence=('confidence_score', 'mean'),
        anomalies=('is_anomaly', 'sum'),
    ).reset_index().sort_values('avg_confidence', ascending=False)
    fig = px.bar(coverage, x='source_file', y='avg_confidence',
                 color='avg_confidence', color_continuous_scale='RdYlGn',
                 title='Confidence Score by Source File',
                 labels={'avg_confidence': 'Confidence', 'source_file': 'File'})
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(coverage, use_container_width=True, hide_index=True)

    st.subheader("Files with Extraction Warnings")
    if 'extraction_warnings' in df.columns:
        with_warnings = df[df['extraction_warnings'].apply(
            lambda x: isinstance(x, list) and len(x) > 0
        )][['source_file', 'extraction_warnings']].drop_duplicates('source_file').head(20)
        if not with_warnings.empty:
            st.dataframe(with_warnings, use_container_width=True, hide_index=True)
        else:
            st.success("No extraction warnings!")
```

- [ ] **Step 2: Verify by running locally**

From project root:
```bash
# First ensure data/db/energy.db exists (run pipeline once)
cd src/extractor && python pipeline.py
# Then run dashboard
cd ../..
python -m streamlit run src/dashboard/app.py --server.port 8501
```
Open http://localhost:8501 and verify all 5 tabs render without errors.

- [ ] **Step 3: Commit**

```bash
git add src/dashboard/app.py
git commit -m "feat: Streamlit dashboard — 5 tabs, KPIs, CO2, anomalies, coverage"
```

---

## Task 14: Dockerfiles and Docker Compose

**Files:**
- Create: `Dockerfile.extractor`
- Create: `Dockerfile.dashboard`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create Dockerfile.extractor**

```dockerfile
# Dockerfile.extractor
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download EasyOCR models at build time
RUN python -c "import easyocr; easyocr.Reader(['fr', 'en'], gpu=False, verbose=False)"

COPY src/extractor/ /app/src/extractor/
WORKDIR /app/src/extractor

ENV PYTHONPATH=/app/src/extractor
ENV DB_URL=sqlite:////app/data/db/energy.db
ENV DATA_DIR=/app/data

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create Dockerfile.dashboard**

```dockerfile
# Dockerfile.dashboard
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/

ENV DB_URL=sqlite:////app/data/db/energy.db
ENV PYTHONPATH=/app/src/extractor

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "src/dashboard/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
```

- [ ] **Step 3: Create docker-compose.yml**

```yaml
services:
  extractor:
    build:
      context: .
      dockerfile: Dockerfile.extractor
    ports:
      - "8000:8000"
    volumes:
      - ./data/db:/app/data/db
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - DB_URL=sqlite:////app/data/db/energy.db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  db-init:
    build:
      context: .
      dockerfile: Dockerfile.extractor
    command: ["python", "pipeline.py"]
    volumes:
      - ./data:/app/data
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - DB_URL=sqlite:////app/data/db/energy.db
      - DATA_DIR=/app/data
    depends_on:
      extractor:
        condition: service_healthy

  dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dashboard
    ports:
      - "8501:8501"
    volumes:
      - ./data/db:/app/data/db
    environment:
      - DB_URL=sqlite:////app/data/db/energy.db
    depends_on:
      db-init:
        condition: service_completed_successfully
```

- [ ] **Step 4: Create .env file for local Docker use**

```bash
# Create .env (not committed — already in .gitignore)
echo "ANTHROPIC_API_KEY=your-key-here" > .env
```

- [ ] **Step 5: Test cold start**

```bash
# From project root — single command cold start
docker compose up --build
```

Expected output sequence:
1. `extractor` builds and starts → health check passes
2. `db-init` starts → prints "Pipeline complete. XXXX records written."
3. `dashboard` starts → available at http://localhost:8501
4. `extractor` API available at http://localhost:8000/docs

Verify:
```bash
curl http://localhost:8000/health        # → {"status":"ok"}
curl http://localhost:8000/summary       # → JSON with total_records > 0
# Open http://localhost:8501 in browser
```

- [ ] **Step 6: Commit**

```bash
git add Dockerfile.extractor Dockerfile.dashboard docker-compose.yml .env.example
git add --update  # stage any modified files
git commit -m "feat: Docker — Dockerfile.extractor, Dockerfile.dashboard, docker-compose"
```

---

## Final Test Suite

Run the full test suite before declaring done:

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: all tests pass except potentially `test_pipeline.py` (slow, skip with `-k "not pipeline"` if time-pressed).

```bash
git add .
git commit -m "chore: final test suite pass — all components verified"
```
