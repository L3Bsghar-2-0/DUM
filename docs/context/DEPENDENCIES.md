# DEPENDENCIES.md — External Systems, APIs & Integration Points

## Overview

This document maps all external dependencies: Python libraries (versions pinned), APIs (some placeholders), data formats, and infrastructure requirements.

---

## Python Package Dependencies

### Runtime Dependencies (from requirements.txt)

| Package | Version | Purpose | Status |
|---------|---------|---------|--------|
| **fastapi** | 0.115.0 | REST API framework | ✅ Implemented |
| **uvicorn** | latest | ASGI server (FastAPI) | ✅ Implemented |
| **streamlit** | 1.37.0 | Web dashboard UI | ✅ Implemented |
| **openpyxl** | 3.1.5 | Excel file parsing | ✅ Implemented |
| **pdfplumber** | 0.11.4 | PDF text extraction | ✅ Implemented |
| **pdf2image** | 1.17.0 | PDF → image conversion (fallback for OCR) | ✅ Implemented |
| **easyocr** | 1.7.2 | Optical character recognition (French + English) | ✅ Implemented |
| **rapidfuzz** | latest | Fuzzy string matching (for Excel header variants) | ✅ Implemented |
| **pandas** | 2.2.3 | DataFrames (used in Streamlit dashboard) | ✅ Implemented |
| **sqlalchemy** | 2.0.35 | ORM for SQLite database | ✅ Implemented |
| **pydantic** | 2.9.2 | Data validation (ExtractionResult model) | ✅ Implemented |
| **scikit-learn** | latest | Machine learning (Isolation Forest anomaly detection) | ✅ Implemented |
| **scipy** | latest | Statistics (Z-score, IQR calculations) | ✅ Implemented |
| **numpy** | latest | Numerical computing | ✅ Implemented |
| **plotly** | 5.24.1 | Interactive charts (Streamlit integration) | ✅ Implemented |
| **anthropic** | 0.34.2 | Claude API SDK (for validation + vision fallback) | ⚠️ Stubbed (see Issue #1) |

---

## External APIs

### Claude API (Anthropic) — PLACEHOLDER

**Status**: ⚠️ Not fully implemented (hackathon placeholder)

**Intended Use Cases**:

#### 1. Vision-Based PDF Extraction ([Issue in PROBLEMS.md](PROBLEMS.md#Issue-#3-PDF-Extractor-Vision-Fallback))

**Purpose**: Extract energy data from scanned PDF invoices (images)

**Workflow**:
```python
# Pseudo-code
if pdf_is_scanned(pdf_file):
    image = pdf2image.convert_from_path(pdf_file)[0]
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64.b64encode(image).decode()
                    }
                },
                {
                    "type": "text",
                    "text": "Extract energy metrics: electricity (kWh), gas (Nm3), date, invoice amount"
                }
            ]
        }]
    )
    return parse_extraction(response.content)
```

**API Cost**: ~$0.003 per image (Claude 3.5 Sonnet vision)

**Implementation Status**: Placeholder function returns `{}` (see [src/extractor/extractors/pdf.py](src/extractor/extractors/pdf.py#L47))

#### 2. Batch Validation API (Claude) — PLACEHOLDER

**Purpose**: Validate extracted records using Claude (optional, advanced validation)

**Intended Logic**:
```python
# If electrical power + voltage + current seem inconsistent:
# P = sqrt(3) * V * I * cos(φ)
# Ask Claude: "Are these values physically consistent?"
```

**API Cost**: Batch API (cheaper; $0.80 per 1M input tokens)

**Implementation Status**: Placeholder function returns confidence=1.0 (see [src/extractor/validator.py](src/extractor/validator.py#L32))

---

### Electricity Grid Carbon API — PLACEHOLDER

**Status**: ⏳ Recommended integration (not yet implemented)

**Purpose**: Real-time carbon intensity of electricity grid

**Intended Use**:
```python
# Replace static 0.267 kg/kWh factor
carbon_intensity = get_realtime_carbon_intensity("Tunisia")
# Returns: 0.120 kg/kWh (if 50% renewable wind)
co2_kg = electricity_kwh * carbon_intensity
```

**Recommended Service**: [electricitymap.org](https://electricitymap.org) API

**Cost**: Free tier (500 requests/month); €4.99/month for 10K requests

**Alternative**: [gridcarbon.io](https://gridcarbon.io)

---

## Data Input Formats

### Excel Input (src/extractor/extractors/excel.py)

**Expected Format**: Wide-format energy sheet (74 rows × 2,877 columns)

**Structure**:
```
Row 1:  Headers (French variant names)
        | Timestamp | Puissance Brute | Gaz Débit | EG Puissance | ... (2,877 cols)
Row 2:  | 2026-05-01 00:10 | 1050.5 | 5.2 | 45.3 | ...
Row 3:  | 2026-05-01 00:20 | 1055.2 | 5.1 | 46.1 | ...
...
Row 74: | 2026-05-02 12:20 | 1048.9 | 5.3 | 44.8 | ...
```

**Header Variants** (fuzzy matched):
- "Puissance Brute (kW)" ↔ "PuissanceBrute_kW" ↔ "puissance_brute"
- "Énergie Alternateur" ↔ "Energie Alternateur" ↔ "energy_alt"

**Timestamp Format** (French):
- Expected: "01/05/2026 14:30" or "2026-05-01 14:30"
- Fallback: ISO format "2026-05-01T14:30:00"

**Data Type**: Float (accept "1,234.56" with comma decimal)

**Error Handling**:
- Malformed rows skipped; logged as warning
- Missing columns → field set to None
- Non-numeric values → parse error; field set to None

---

### PDF Input (src/extractor/extractors/pdf.py)

**Expected Format**: Invoice PDF with energy consumption details

**Text Patterns** (regex-matched):
```
Energy: \d+(?:,\.\s)*\d+ (kWh|MWh|Nm3|GJ)
Date: \d{2}/\d{2}/\d{4}
Invoice Total: \d+(?:,\.\s)*\d+ (€|TND|USD)
```

**Example Invoice Text**:
```
INVOICE #12345
Date: 01/05/2026
---
Electricity Purchased: 1500 kWh
Gas Consumption: 250 Nm3
---
Total Amount: 5,000 TND
```

**Extraction**: Single record per PDF (aggregate values)

**Fallback**: Claude vision API for scanned PDFs (placeholder; not implemented)

---

### Image Input (src/extractor/extractors/image.py)

**Expected Format**: WhatsApp image with handwritten/printed energy data

**Supported Formats**: JPEG, PNG (up to 10MB)

**Preprocessing**:
1. Resize to 1920×1080 (if larger)
2. Enhance contrast (PIL ImageEnhance)
3. Denoise (optional; slows down)

**OCR**: EasyOCR (French + English)

**Text Patterns** (same as PDF; regex-extracted)

**Example Image Text**:
```
[Handwritten]
Puissance: 1050 kW
Gaz: 120 Nm3
Date: 02/05/2026
```

**Accuracy**: 50–80% depending on image quality (YMMV)

---

## Database

### SQLite (energy.db)

**Location**: `/data/energy.db` (shared Docker volume)

**Initialization**: Automatic on first run (SQLAlchemy creates tables)

**Schema**: [energy_records table defined in ARCHITECTURE.md](ARCHITECTURE.md#Database-Schema)

**Connection String**:
```
sqlite:////data/energy.db
?timeout=5
&check_same_thread=False
```

**Concurrency**: WAL mode enabled (allows concurrent reads + single writer)

**Backup Strategy**: None (hackathon scope); production should use:
- Daily SQLite dump (`.backup` command)
- OR: Migrate to PostgreSQL with replication

---

## Infrastructure Dependencies

### Docker Compose

**Services**:
1. **extractor**: FastAPI server (uvicorn)
   - Port: 8000
   - Health check: `/docs` endpoint
   - Volume: `/data/` (SQLite)

2. **dashboard**: Streamlit app
   - Port: 8501
   - Depends on: extractor (health check)
   - Volume: `/data/` (SQLite read-only)

3. **db-init**: One-shot pipeline runner
   - Runs at startup; exits on completion
   - Depends on: extractor (health check)
   - Volume: `/data/` (SQLite + input files)

**Shared Volume**: `energy_data` (mounts to `/data/` in all services)

**Network**: `bridge` (default; services communicate via container names)

**Environment Variables** (loaded from `.env` or docker-compose.yml):
```
SQLITE_PATH=/data/energy.db
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
CLAUDE_API_KEY=sk-ant-... (optional; for Claude fallback)
```

---

## System Requirements

### Hardware Recommendations

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 1 core | 4 cores (1 for EasyOCR model loading) |
| **RAM** | 2 GB | 4 GB (EasyOCR model = ~500 MB) |
| **Disk** | 500 MB | 1 GB (SQLite + model cache) |
| **Network** | 1 Mbps | 10 Mbps (for API calls) |

### Software Requirements

| Component | Minimum | Tested |
|-----------|---------|--------|
| **Docker** | 20.10 | 24.0+ |
| **Python** | 3.9 | 3.13 |
| **OS** | Linux | Ubuntu 22.04, macOS, Windows (WSL2) |

---

## Build Dependencies (Docker)

### Dockerfile.extractor

```dockerfile
FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    libsm6 \           # OpenCV support
    libxext6 \         # X11 libraries
    libxrender-dev \   # X11 rendering
    libopenjp2-7 \     # JPEG2000 (for PDFs)
    libtiff5 \         # TIFF support
    -qq

RUN pip install --no-cache-dir -r requirements.txt

# Pre-download EasyOCR models to avoid timeout during startup
RUN python -c "import easyocr; reader = easyocr.Reader(['fr', 'en'])"
```

**Build Time**: ~5–10 minutes (depends on internet speed; model download = 2 min)

**Image Size**: ~2 GB (Python 3.13 + EasyOCR models)

### Dockerfile.dashboard

```dockerfile
FROM python:3.13-slim

RUN pip install --no-cache-dir streamlit plotly pandas sqlalchemy

EXPOSE 8501
CMD ["streamlit", "run", "src/dashboard/app.py"]
```

**Image Size**: ~500 MB

---

## Testing Dependencies

### Pytest Plugins (for tests/)

| Package | Purpose |
|---------|---------|
| **pytest** | Test framework |
| **pytest-cov** | Code coverage reporting |
| **pytest-mock** | Mocking libraries (e.g., EasyOCR reader) |

**Run Tests**:
```bash
pytest tests/ --cov=src --cov-report=html
```

---

## Third-Party Services (Optional)

### Logging & Monitoring

**Not currently used**; recommended for production:
- **Loki**: Centralized log aggregation
- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards

### CI/CD

**Not currently used**; recommended:
- **GitHub Actions**: Automated tests on PR
- **Docker Hub**: Auto-build on push
- **Dependabot**: Dependency updates

---

## Dependency Version Pinning Strategy

**Current Approach**: `requirements.txt` with exact versions (e.g., `openpyxl==3.1.5`)

**Rationale**:
- Ensures reproducible builds (Docker + local dev)
- Avoids breaking changes in minor versions
- Hackathon: stability > cutting-edge features

**Production Recommendation**:
- Use semantic versioning ranges: `openpyxl>=3.1,<3.2`
- Regularly update with `pip-audit` to catch security patches
- Test compatibility before rolling out

---

## Known Dependency Issues

### Issue: EasyOCR Model Download Timeout

**Problem**: First run downloads 500MB+ of models; can timeout if internet slow

**Solution**: Pre-download in Docker (see Dockerfile.extractor)

**Workaround**: Use lighter OCR library (Tesseract) if bandwidth limited

---

### Issue: SQLAlchemy + SQLite Compatibility

**Problem**: SQLAlchemy 2.0 changed defaults; deprecated autocommit mode

**Solution**: Use `begin()` context manager for transactions

**Status**: ✅ Already implemented

---

### Issue: Streamlit Rerun on Every Change

**Problem**: Streamlit reruns entire script when session state changes; slow with large datasets

**Solution**: Use `@st.cache_data` decorator (see Issue #15 in PROBLEMS.md)

---

## Installation & Setup

### Local Development Setup

```bash
# Clone repo
git clone https://github.com/your-repo/energy-pipeline.git
cd energy-pipeline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock  # dev dependencies

# Run tests
pytest tests/

# Start services (Docker)
docker-compose up --build
```

**Startup Time**:
- Local (venv): ~10 seconds
- Docker: ~60 seconds (cold-start includes model download + DB init)

---

## Dependency Security

### Known Vulnerabilities

**None currently flagged** (as of 2026-05-02)

**Audit Command**:
```bash
pip-audit
# Or: python -m pip list | grep -E 'django|flask|requests'
```

### Recommended Practices

1. **Regular Updates**: Run `pip install --upgrade -r requirements.txt` monthly
2. **Security Scanning**: Enable Dependabot on GitHub
3. **Pinned Versions**: Use exact versions in requirements.txt (not `>=` ranges)
4. **Isolated Environments**: Always use virtual environments

---

For detailed API contract documentation, see [ARCHITECTURE.md](ARCHITECTURE.md#API-Contract).
For environment configuration, see [QUICKSTART.md](QUICKSTART.md).
For identified dependency issues, see [PROBLEMS.md](PROBLEMS.md).
