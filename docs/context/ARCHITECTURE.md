# ARCHITECTURE.md — System Design & Data Flows

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Energy Pipeline System                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  FastAPI Extractor Service (:8000)                              │
│  ├── POST /extract — Process uploaded files                     │
│  ├── GET /records — Query historical records                    │
│  └── GET /anomalies — List flagged anomalies                    │
│         ↓↓↓ (Shared SQLite Volume)                              │
│  SQLite Database (energy.db)                                     │
│  ├── energy_records — 71 columns (all 73 fields)               │
│  ├── anomaly_flags — Detection results                          │
│  └── extraction_warnings — Error tracking                       │
│         ↑↑↑ (Shared SQLite Volume)                              │
│  Streamlit Dashboard Service (:8501)                             │
│  ├── Tab 1: KPIs (totals, avg, efficiency, anomaly count)      │
│  ├── Tab 2: CO2 Trends (daily/source breakdown)                 │
│  ├── Tab 3: Anomalies (type distribution, flagged records)      │
│  ├── Tab 4: Data Explorer (filterable table)                    │
│  └── Tab 5: Data Quality (coverage by source)                   │
│                                                                   │
│  db-init Service (one-shot, cold-start)                         │
│  ├── Runs at container startup                                  │
│  ├── Triggers full pipeline on input data files                 │
│  └── Blocks dashboard until completion                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

### Docker Compose Services

| Service | Image | Port | Purpose | Dependencies |
|---------|-------|------|---------|--------------|
| **extractor** | Dockerfile.extractor | 8000 | FastAPI server for file extraction; API endpoints | SQLite volume |
| **dashboard** | Dockerfile.dashboard | 8501 | Streamlit UI for visualization & exploration | SQLite volume, extractor health check |
| **db-init** | Dockerfile.extractor | N/A | One-shot pipeline runner; processes input data | SQLite volume, extractor health check |

**Shared Volume**: `energy_data` (SQLite database + input files)

**Network**: `bridge` (services communicate via container names)

**Cold-Start Guarantee**: 
1. `docker compose up --build` starts extractor + db-init services
2. db-init waits for extractor API health check
3. db-init runs full pipeline on input data files
4. db-init exits (one-shot)
5. dashboard waits for db-init completion (health check)
6. dashboard reads from SQLite and displays results
7. **All data prepared before user sees UI** ✅

---

## Data Pipeline Flow

### Orchestration (src/extractor/pipeline.py)

```
Input Data Files (Excel, PDF, Images)
        ↓
        ├─→ [ExcelExtractor] → ExtractionResult (73 fields)
        ├─→ [PDFExtractor] → ExtractionResult (73 fields)
        └─→ [ImageExtractor] → ExtractionResult (73 fields)
                ↓
        ┌───────────────────────────┐
        │ normalize_record()         │ ← Batch operation
        │ ├─ Unit conversion (×13)  │   (gaz_volume_nm3 → kWh,
        │ ├─ PCI factor (9.082)     │    GJ → kWh, etc.)
        │ └─ Handle nulls           │
        └───────────────────────────┘
                ↓
        ┌───────────────────────────┐
        │ validate_batch()          │ ← Batch operation
        │ ├─ Bounds checking (10)   │   (voltage, power, efficiency, etc.)
        │ ├─ Confidence scoring     │   Placeholder: Claude validation
        │ └─ Extract warnings       │
        └───────────────────────────┘
                ↓
        ┌───────────────────────────┐
        │ estimate_co2()            │ ← Per-record
        │ ├─ Electricity path       │   (puissance_brute_kw × 0.267)
        │ ├─ Gas path (PCI factor)  │   (gaz_volume_nm3 × PCI × 0.202)
        │ └─ Total CO2 (kg)         │
        └───────────────────────────┘
                ↓
        ┌───────────────────────────┐
        │ detect_anomalies()        │ ← Per-record sequence
        │ ├─ Z-score (±3σ)         │   Applied to 4 features:
        │ ├─ IQR (1.5× bounds)     │   • puissance_brute_kw
        │ ├─ Isolation Forest (5%)  │   • gaz_debit_nm3h
        │ ├─ Stuck sensor          │   • eg_puissance_kw
        │ └─ Dropout detection     │   • ec_recup_puissance_kw
        └───────────────────────────┘
                ↓
        ┌───────────────────────────┐
        │ write_records()           │ ← Bulk insert
        │ ├─ SQLAlchemy ORM         │   (SQLite + indexes)
        │ ├─ Transaction commit     │
        │ └─ Logging + error track  │
        └───────────────────────────┘
                ↓
        SQLite Database (energy.db)
```

---

## Extractor Modules

### 1. Base Extractor (src/extractor/extractors/base.py)

**Abstract Base Class**: `BaseExtractor`

```python
class BaseExtractor:
    def extract(self, file_path: str) -> List[ExtractionResult]:
        """Parse file and return list of records (73-field Pydantic models)"""
        raise NotImplementedError()
```

**ExtractionResult Fields** (73 total):
- **Metadata** (6 fields): source_file, source_type, timestamp, confidence_score, is_anomaly, anomaly_type
- **Gas** (2 fields): gaz_volume_nm3, gaz_debit_nm3h
- **Electrical** (12 fields): puissance_brute_kw, energie_alternateur_kwh, voltage_v, courant_phase_1/2/3_a, etc.
- **Thermal Systems** (50+ fields): 5 subsystems × 10+ fields each (EG, EC recovery, Alpha Sanitary, Alpha, Gamma)
- **Efficiency** (3 fields): rendement_electrique_pct, rendement_thermique_pct, rendement_total_pct
- **Grid** (5 fields): steg_achat_kwh, steg_vente_kwh, production_positive_kwh, production_negative_kwh, factor_puissance

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for complete field listing with units and validation bounds.

---

### 2. Excel Extractor (src/extractor/extractors/excel.py)

**Input Format**: 74-row × 2,877-column wide-format sheets (10-minute interval data)

**Processing Steps**:
1. **Load Workbook**: openpyxl with `data_only=True` (values, not formulas)
2. **Header Matching**: Fuzzy matching (rapidfuzz) for French variant headers (e.g., "Puissance Brute (kW)" vs. "PuissanceBrute_kW")
3. **Row Extraction**: Iterate rows 2–74 (skip header + metadata rows)
4. **Timestamp Parsing**: Column 0 → datetime (handle French date formats: "01/05/2026 14:30")
5. **Data Conversion**: Columns 1–2876 → float (convert "1,234.56" French decimal to float)
6. **Build ExtractionResult**: Map column indices to 73 fields; null unmapped columns
7. **Batch Return**: List[ExtractionResult] with validation warnings captured

**Error Handling**: Malformed rows logged but not halted; missing columns set to None

---

### 3. PDF Extractor (src/extractor/extractors/pdf.py)

**Input Format**: Invoice PDFs with energy consumption data (text + images)

**Processing Steps**:
1. **Text Extraction**: pdfplumber (text-based PDFs, optimized for invoices)
2. **Placeholder Vision Fallback**: `_vision_extract_placeholder()` (stubbed; would use Claude vision API for scanned PDFs)
3. **Regex Parsing**: Extract energy quantities, dates, invoice amounts using patterns like:
   - `(?:Énergie|Energy)[:=]\s*([\d,.\s]+)\s*(kWh|MWh|Nm3|GJ)`
   - `Date[:=]\s*(\d{2}/\d{2}/\d{4})`
4. **Single Record Return**: One ExtractionResult per PDF (aggregate amounts)

**Current Limitation**: Text-based PDFs only; scanned images fall back to placeholder (no Claude API in hackathon)

---

### 4. Image Extractor (src/extractor/extractors/image.py)

**Input Format**: WhatsApp images with handwritten or printed energy data

**Processing Steps**:
1. **Image Preprocessing**: Pillow (resize to 1920×1080, enhance contrast, denoise)
2. **OCR Recognition**: EasyOCR (French + English, GPU-optimized)
3. **Text Parsing**: Regex extraction of energy metrics from OCR output
4. **Global Reader State**: ⚠️ Singleton `_READER` (thread-safety issue; see [PROBLEMS.md](PROBLEMS.md))
5. **Confidence Score**: EasyOCR confidence × regex match confidence

**Current Limitation**: Highly variable image quality; accuracy 50–80% depending on photo

---

## Database Schema

### energy_records Table (SQLAlchemy)

| Column | Type | Nullable | Index | Notes |
|--------|------|----------|-------|-------|
| id | INTEGER | No | PRIMARY | Auto-increment |
| source_file | VARCHAR | No | Yes | Extractor type + filename |
| source_type | VARCHAR | No | No | 'excel' \| 'pdf' \| 'image' |
| timestamp | DATETIME | Yes | Yes | Record time; null if not available |
| confidence_score | FLOAT | Yes | No | 0.0–1.0; based on field coverage |
| is_anomaly | BOOLEAN | Yes | No | Flag set by detect_anomalies() |
| anomaly_type | VARCHAR | Yes | No | 'spike' \| 'stuck_sensor' \| 'dropout' \| 'iqr_outlier' \| 'isolation_forest' |
| co2_kg | FLOAT | Yes | No | Calculated by estimate_co2() |
| extraction_warnings | JSON | Yes | No | {"field": ["error1", "error2"]} |
| (All 73 fields as separate columns) | FLOAT | Yes | No | gaz_volume_nm3, puissance_brute_kw, etc. |
| created_at | DATETIME | Yes | No | Insert timestamp |

**Indexes**: `(source_file, timestamp)` for efficient dashboard queries

---

## Dashboard Layout

### Streamlit App (src/dashboard/app.py)

**5-Tab Interface**:

#### Tab 1: Key Performance Indicators
- **Total CO2 Emissions (kg)**: Sum of all co2_kg values
- **Average Power (kW)**: Mean of puissance_brute_kw
- **System Efficiency (%)**: Mean of rendement_total_pct
- **Anomaly Count**: Count WHERE is_anomaly = True
- **Data Coverage**: Mean confidence_score
- **Records Processed**: Total row count

#### Tab 2: CO2 Emissions Trends
- **Daily CO2 Breakdown (line chart)**: Date → CO2 (kg), colored by source_type
- **Source Comparison (pie chart)**: excel vs. pdf vs. image contributions
- **Cumulative CO2 (area chart)**: Running sum over time
- **Filter**: Date range picker; source type multiselect

#### Tab 3: Anomaly Analysis
- **Anomaly Type Distribution (bar chart)**: spike, stuck_sensor, dropout, iqr_outlier, isolation_forest counts
- **Anomalies by Source (stacked bar)**: source_type × anomaly_type
- **Timeline Heatmap**: Date × Hour → anomaly density
- **Filter**: Date range; severity threshold

#### Tab 4: Data Explorer
- **Filterable Table**: All 73 fields, sortable, paginated (50 rows/page)
- **Filter Sidebar**: source_type multiselect; date range slider; confidence threshold
- **Export**: Download filtered data as CSV

#### Tab 5: Data Quality & Coverage
- **Coverage by Source (bar chart)**: source_type → mean confidence_score
- **Field Completeness (heatmap)**: Field name × source_type → % non-null values
- **Extraction Warnings (text list)**: Unique warnings across all records
- **Statistics**: Records per source, coverage threshold, data freshness (newest/oldest timestamp)

---

## Error Handling & Logging

### Pipeline-Level

**Log Levels**:
- `INFO`: File processing started/completed, record counts
- `WARNING`: Malformed rows skipped, bounds violations, low confidence
- `ERROR`: File not found, OCR failure, database connection lost
- `DEBUG`: Field-by-field extraction details, fuzzy match scores

**Error Recovery**:
- File extraction failures → log + continue (skip file, don't halt pipeline)
- Database writes → transaction rollback on constraint violation
- API health checks → 3-second timeout with retry

### Per-Record

**Extraction Warnings** (JSON):
```json
{
  "timestamp_parse_error": "Could not parse '14:30' in French format",
  "missing_field_coverage": "Only 5/9 critical fields populated",
  "bounds_violation_voltage": "380 V (expected 380–440 V)"
}
```

---

## Technology Stack

| Layer | Library | Version | Purpose |
|-------|---------|---------|---------|
| **API Framework** | FastAPI | 0.115.0 | REST endpoints, async I/O |
| **ASGI Server** | uvicorn | Latest | Production ASGI server |
| **Web Framework** | Streamlit | 1.37.0 | Dashboard UI + interactivity |
| **Excel** | openpyxl | 3.1.5 | XLSX parsing (values only) |
| **PDF** | pdfplumber | 0.11.4 | Text extraction from PDFs |
| **PDF Images** | pdf2image | 1.17.0 | Fallback for scanned PDFs |
| **OCR** | easyocr | 1.7.2 | Text recognition (French + English) |
| **String Matching** | rapidfuzz | Latest | Fuzzy header matching |
| **Data Handling** | pandas | 2.2.3 | DataFrames (not heavily used; Pydantic preferred) |
| **ORM** | SQLAlchemy | 2.0.35 | SQLite object mapping |
| **Data Validation** | Pydantic | 2.9.2 | ExtractionResult validation |
| **Anomaly Detection** | scikit-learn | Latest | Isolation Forest, Z-score, IQR |
| **Statistics** | scipy, numpy | Latest | Statistical calculations |
| **Visualization** | Plotly | 5.24.1 | Interactive charts (Streamlit integration) |
| **AI Fallback** | anthropic | 0.34.2 | Claude API (not implemented in hackathon) |
| **Infrastructure** | Docker | Latest | Containerization + cold-start |
| **Runtime** | Python | 3.13-slim | Base image for all containers |

---

## Scalability Considerations

### Current Limitations (Hackathon)
- **Single-threaded**: No worker pool for concurrent /extract requests
- **SQLite only**: No replication, no distributed locking, max ~5 concurrent readers
- **In-memory anomaly detection**: Full dataset loaded to RAM for Isolation Forest
- **No caching**: Queries hit SQLite every time

### Production Roadmap (see [ROADMAP.md](ROADMAP.md))
1. **Week 1**: Add thread-safety to ImageExtractor + implement Claude API
2. **Week 2**: Migrate SQLite → PostgreSQL; add read replicas for dashboard
3. **Week 3**: Implement Redis cache layer; add streaming anomaly detection
4. **Week 4+**: Kubernetes deployment; horizontal scaling of extractor services

---

## API Contract

### FastAPI Endpoints

**POST /extract** — Extract from uploaded file
```
Request:
  - file: UploadFile (Excel, PDF, or Image)
  
Response (200):
  {
    "records_processed": 74,
    "records_inserted": 72,
    "errors": ["Row 23: timestamp parse failed", "Row 45: power out of bounds"],
    "extraction_warnings": {
      "row_23": ["timestamp_parse_error"],
      "row_45": ["bounds_violation_power"]
    }
  }
```

**GET /records** — Query historical records
```
Request:
  - source_type: Optional[str] ("excel" | "pdf" | "image")
  - start_date: Optional[datetime]
  - end_date: Optional[datetime]
  - limit: Optional[int] (default 100)
  
Response (200):
  [
    {
      "id": 1,
      "source_file": "excel_energy_202605.xlsx",
      "timestamp": "2026-05-02T14:30:00",
      "puissance_brute_kw": 1050.5,
      "gaz_volume_nm3": 125.3,
      "co2_kg": 345.2,
      "is_anomaly": false,
      ... (all 73 fields)
    }
  ]
```

**GET /anomalies** — List flagged anomalies
```
Response (200):
  [
    {
      "id": 42,
      "timestamp": "2026-05-02T15:00:00",
      "anomaly_type": "spike",
      "confidence": 0.92,
      "flagged_fields": ["puissance_brute_kw"]
    }
  ]
```

---

## Security Considerations

⚠️ **Not implemented** (hackathon scope):
- Authentication/authorization on FastAPI endpoints
- Rate limiting
- Input sanitization (assume uploaded files are trusted)
- Database encryption
- Environment variable validation

See [PROBLEMS.md](PROBLEMS.md) for security backlog.

---

For detailed field documentation, see [DATA_DICTIONARY.md](DATA_DICTIONARY.md).
For identified issues, see [PROBLEMS.md](PROBLEMS.md).
For setup & deployment, see [QUICKSTART.md](QUICKSTART.md).
