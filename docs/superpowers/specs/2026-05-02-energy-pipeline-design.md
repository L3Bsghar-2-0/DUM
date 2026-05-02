# Energy Pipeline Design — Pharmaceutical Factory Tri-gen

**Date:** 2026-05-02  
**Context:** 23-hour energy hackathon. Real pharmaceutical factory data. Scoring: extraction accuracy (40pts), unit normalization (25pts), dashboard (20pts), Docker (20pts), CO2 estimation (15pts), anomaly detection bonus (+15pts), innovation bonus (+25pts).

---

## 1. Architecture — Microservices (Approach C)

Three Docker services sharing a SQLite volume:

```
docker-compose.yml
├── extractor    FastAPI :8000   POST /extract, GET /health
├── dashboard    Streamlit :8501  KPIs, CO2, anomalies, confidence badges
└── db-init      one-shot        mounts data/, runs full ingestion pipeline at startup
```

**Shared volume:** `./data/db/` → `energy.db` (SQLite). Both `extractor` and `dashboard` mount it.

**Cold-start guarantee:**
- `db-init` is built from the same image as `extractor` but runs `python pipeline.py` as its CMD — ingests all files in `data/` in-process, no HTTP calls
- `dashboard` depends on `db-init` (completed successfully)
- `extractor` service runs independently and stays up for POST /extract API calls
- `docker compose up --build` is the only command needed

---

## 2. Ground-Truth Schema

Derived from `data/rapport_audit.pdf` and `data/data tri gen/avril-report1_2442026.xlsx`.

The Excel files are wide-format: each sheet (`BILAN TOTAL`) has 74 rows × ~2877 columns. Rows are measurement fields, columns are 10-minute timestamps. PCI = 9.082 thermie/Nm3. cosφ = 1.

### Canonical `ExtractionResult` fields

| Field | Unit | Source row |
|---|---|---|
| `timestamp` | datetime | rows 10+11 (date + time) |
| `gaz_volume_nm3` | Nm3 | row 12 (cumulative) |
| `gaz_debit_nm3h` | Nm3/h | row 14 |
| `elec_auxiliaire_kwh` | kWh | row 15 (cumulative) |
| `puissance_brute_kw` | kW | row 16 |
| `heures_fonctionnement` | h | row 17 |
| `energie_alternateur_kwh` | kWh | row 18 (cumulative) |
| `energie_reactive_kvarh` | kVARh | row 19 |
| `vitesse_rpm` | rpm | row 20 |
| `facteur_puissance` | — | row 21 |
| `voltage_v` | V | row 22 |
| `courant_phase1_a` | A | row 23 |
| `courant_phase2_a` | A | row 24 |
| `courant_phase3_a` | A | row 25 |
| `eg_debit_m3h` | m3/h | row 26 |
| `eg_temp_entree_c` | °C | row 27 |
| `eg_temp_sortie_c` | °C | row 28 |
| `eg_energie_kwh` | kWh | row 29 (cumulative) |
| `eg_puissance_kw` | kW | row 30 |
| `ec_recup_debit_m3h` | m3/h | row 31 |
| `ec_recup_temp_entree_c` | °C | row 32 |
| `ec_recup_temp_sortie_c` | °C | row 33 |
| `ec_recup_energie_kwh` | kWh | row 34 (cumulative) |
| `ec_recup_puissance_kw` | kW | row 35 |
| `ec_alpha_sani_debit_m3h` | m3/h | row 36 |
| `ec_alpha_sani_temp_entree_c` | °C | row 37 |
| `ec_alpha_sani_temp_sortie_c` | °C | row 38 |
| `ec_alpha_sani_energie_kwh` | kWh | row 39 |
| `ec_alpha_sani_puissance_kw` | kW | row 40 |
| `ec_alpha_debit_m3h` | m3/h | row 43 |
| `ec_alpha_temp_entree_c` | °C | row 44 |
| `ec_alpha_temp_sortie_c` | °C | row 45 |
| `ec_alpha_energie_kwh` | kWh | row 46 |
| `ec_alpha_puissance_kw` | kW | row 47 |
| `ec_gamma_debit_m3h` | m3/h | row 50 |
| `ec_gamma_temp_entree_c` | °C | row 51 |
| `ec_gamma_temp_sortie_c` | °C | row 52 |
| `ec_gamma_energie_kwh` | kWh | row 53 |
| `ec_gamma_puissance_kw` | kW | row 54 |
| `rendement_electrique_pct` | % | row 57 |
| `rendement_thermique_pct` | % | row 58 |
| `rendement_total_pct` | % | row 59 |
| `steg_achat_kwh` | kWh | row 60 (cumulative) |
| `steg_vente_kwh` | kWh | row 61 (cumulative) |
| `production_positive_kwh` | kWh | row 62 (cumulative) |
| `production_negative_kwh` | kWh | row 63 (cumulative) |

**Metadata per record:**
- `source_file` (str)
- `source_type` (excel / pdf / image)
- `confidence_score` (float 0–1)
- `is_anomaly` (bool)
- `anomaly_type` (str or null)
- `co2_kg` (float)
- `extraction_warnings` (list[str])
- `pci_thermie_nm3` (float, default 9.082)
- `cos_phi` (float, default 1.0)

---

## 3. File Structure

```
C:\IDP-2.0\
├── src/
│   ├── extractor/
│   │   ├── main.py              FastAPI app
│   │   ├── pipeline.py          orchestrates all extractors → db
│   │   ├── extractors/
│   │   │   ├── base.py          ExtractionResult pydantic model
│   │   │   ├── excel.py         wide-format Excel parser
│   │   │   ├── pdf.py           pdfplumber + Claude vision fallback
│   │   │   └── image.py         EasyOCR for JPEG invoices
│   │   ├── normalizer.py        unit → kWh conversions with traceable factors
│   │   ├── validator.py         Claude API: plausibility + null-fill + confidence
│   │   ├── co2.py               electricity×0.267 + gas×0.202 kgCO2/kWh
│   │   ├── anomaly.py           Z-score + IQR + Isolation Forest
│   │   └── db.py                SQLAlchemy models + write_records()
│   └── dashboard/
│       └── app.py               Streamlit dashboard
├── data/
│   ├── data tri gen/            21 Excel monthly reports
│   ├── data factures et diverses/  PDFs + WhatsApp JPEGs
│   ├── rapport_audit.pdf
│   └── db/                      energy.db (created at runtime)
├── docker-compose.yml
├── Dockerfile.extractor
├── Dockerfile.dashboard
├── Dockerfile.db-init
└── requirements.txt
```

---

## 4. Component Details

### 4.1 ExcelExtractor

**Input:** `.xlsx` file with sheet `BILAN TOTAL`  
**Approach:**
1. Load with `openpyxl`, read PCI (row 7) and cosφ (row 6) from metadata rows
2. Build a `row_label_map`: col 2 cell value → canonical field name (French → schema key), using `rapidfuzz` for fuzzy matching across the 21 files which may have slight header variations
3. Collect timestamps from row 10 (date) + row 11 (time), combine into `datetime`
4. For each timestamp column, build one `ExtractionResult` from the row_label_map
5. Skip all-None columns

**French → canonical field mapping (exact + fuzzy):**
- `"Consommation du gaz naturel moteur en Nm3"` → `gaz_volume_nm3`
- `"Débit du gaz naturel moteur en Nm3/h"` → `gaz_debit_nm3h`
- `"Puissance électrique Brute en KW"` → `puissance_brute_kw`
- `"Energie éléctrique au borne de l'alternateur en KWh"` → `energie_alternateur_kwh`
- … (full map in `excel.py`)

### 4.2 PDFExtractor

**Input:** `.pdf` file  
**Approach:**
1. `pdfplumber` text extraction per page → regex search for value+unit patterns
2. If extracted field count < 5 (scanned/image PDF): render page with `pdf2image` → pass base64 image to Claude `claude-haiku-4-5` with prompt: *"Extract all energy measurement fields and values from this French factory invoice. Return JSON."*
3. Map extracted keys to canonical schema via regex + fuzzy match

### 4.3 ImageExtractor

**Input:** `.jpeg` / `.jpg` (WhatsApp invoice photos)  
**Approach:**
1. EasyOCR with `['fr', 'en']` language list
2. Concatenate text blocks → regex extraction of `value + unit` pairs
3. Map to canonical fields where possible; remaining fields go into `extraction_warnings`

### 4.4 Normalizer

Single `CONVERSION_TABLE` in `normalizer.py`. Every conversion logs the factor used.

| From | To | Factor |
|---|---|---|
| MWh | kWh | × 1000 |
| GJ | kWh | × 277.78 |
| Gcal | kWh | × 1163 |
| toe | kWh | × 11630 |
| BTU | kWh | × 0.000293 |
| thermie | kWh | × 1.163 |
| Nm3 (gas) | kWh | × PCI × 1.163 |
| kW (power) | kWh | × Δt_hours |

### 4.5 ClaudeValidator (`validator.py`)

One API call per batch of up to 50 records. Prompt includes:
- The audit-doc physical bounds (voltage 380–440V, gas flow 260–285 Nm3/h, etc.)
- The extracted records as JSON
- Instructions: flag out-of-range values, suggest null fills, return `confidence_score` per record

**Fallback:** if `ANTHROPIC_API_KEY` is not set, validator runs in rule-only mode (range checks hardcoded from audit doc). This ensures cold start always works.

### 4.6 CO2 Estimator

```python
co2_kg = (energie_alternateur_kwh_delta * 0.267) + (gaz_volume_nm3_delta * pci * 1.163 * 0.202)
```

Tunisia grid factor: 0.267 kgCO2/kWh  
Gas factor: 0.202 kgCO2/kWh_thermal

### 4.7 Anomaly Detector

Three-layer detection:
1. **Z-score** (threshold ±3σ) per field over rolling 24h window
2. **IQR** (1.5× fence) per field over full dataset
3. **Isolation Forest** (scikit-learn, contamination=0.05) on multivariate feature vector: `[puissance_brute_kw, gaz_debit_nm3h, eg_puissance_kw, ec_recup_puissance_kw]`

`anomaly_type` values: `zscore_spike`, `iqr_outlier`, `isolation_forest`, `stuck_sensor` (detected by zero-variance over 6+ consecutive readings), `dropout` (null run > 3 readings)

### 4.8 Streamlit Dashboard (`app.py`)

Tabs:
1. **KPIs** — total kWh produced, total gas consumed (kWh), efficiency %, CO2 total (tCO2), STEG bought vs sold
2. **CO2 Trend** — daily CO2 line chart, breakdown by source (electricity vs gas)
3. **Anomalies** — alert table with timestamp, field, value, anomaly_type, severity
4. **Data Table** — full unified DataFrame with confidence badges, source type icons, filter by date/source
5. **Extraction Coverage** — per-file extraction success rate, warnings list

---

## 5. FastAPI Endpoints

```
POST /extract          multipart file upload → runs extraction pipeline → returns ExtractionResult[]
GET  /health           {"status": "ok"}
GET  /records          returns all DB records as JSON (for judges)
GET  /summary          aggregated KPIs JSON
```

---

## 6. Docker Compose

```yaml
services:
  extractor:
    build: { context: ., dockerfile: Dockerfile.extractor }
    ports: ["8000:8000"]
    volumes: ["./data/db:/app/data/db"]
    environment: ["ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      retries: 5

  db-init:
    build: { context: ., dockerfile: Dockerfile.extractor }
    command: ["python", "pipeline.py"]
    volumes: ["./data:/app/data"]
    environment: ["ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}"]

  dashboard:
    build: { context: ., dockerfile: Dockerfile.dashboard }
    ports: ["8501:8501"]
    volumes: ["./data/db:/app/data/db"]
    depends_on:
      db-init:
        condition: service_completed_successfully
```

---

## 7. Error Handling

- Extractors never raise on bad files — return `ExtractionResult` with `confidence_score=0.0` and populated `extraction_warnings`
- DB writes are transactional — partial batch failure rolls back that file only
- Claude API timeout (10s) → fall back to rule-only validation silently
- EasyOCR model download happens at Docker build time (baked into image)

---

## 8. Key Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Excel files have varying row positions across months | Fuzzy header matching with `rapidfuzz` score ≥ 0.8 threshold |
| WhatsApp images are low quality / rotated | EasyOCR pre-processing: grayscale + contrast enhancement with Pillow |
| `pdf2image` requires `poppler` system dependency | Install `poppler-utils` in Dockerfile.extractor |
| EasyOCR first-run downloads models (~200MB) | Pre-download in Dockerfile with `RUN python -c "import easyocr; easyocr.Reader(['fr','en'])"` |
| SQLite concurrent write from db-init + extractor API | db-init runs before dashboard; extractor API uses connection-level locking |
