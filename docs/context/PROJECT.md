# PROJECT.md — Energy Pipeline System Charter

## Overview

This is an **automated energy management and CO2 tracking system** built for a pharmaceutical factory's tri-generation facility (simultaneous production of electricity, heating, and chilled water). The project extracts energy metrics from multiple data sources, validates and normalizes them, calculates CO2 emissions, detects operational anomalies, and visualizes insights through an interactive dashboard.

**Development Context**: 23-hour hackathon constraint (May 2, 2026) — explains why some features are placeholders (Claude API, vision fallback).

---

## Objectives

### Primary Goals
1. **Extract** energy metrics from 3 data sources:
   - Excel monthly reports (74-row × 2,877-column wide-format sheets with 10-minute intervals)
   - PDF invoices (text + image content)
   - WhatsApp images (OCR-based text extraction)

2. **Normalize & Validate**: Convert all units to standard kWh; apply physical bounds checking (voltage 380–440V, power 800–1400 kW, efficiency 30–55%, etc.)

3. **Calculate CO2 Emissions**: Estimate carbon footprint from electricity (0.267 kg/kWh) and natural gas (0.202 kg/kWh) consumption

4. **Detect Anomalies**: Flag suspicious patterns using 5 statistical methods (Z-score, IQR, Isolation Forest, stuck sensor, dropout detection)

5. **Visualize & Explore**: 5-tab Streamlit dashboard for KPIs, trends, anomalies, raw data, and data quality coverage

---

## Scoring Rubric (Hackathon Judging)

| Criterion | Points | Status |
|-----------|--------|--------|
| Data Extraction Accuracy | 40 | ✅ Multi-format extractors (Excel, PDF, OCR) implemented |
| Unit Normalization | 25 | ✅ 13 unit types supported (Nm3, GJ, Gcal, kWh, MWh, etc.) |
| Dashboard UI/UX | 20 | ✅ 5-tab Streamlit layout with Plotly charts |
| Docker Deployment | 20 | ✅ Cold-start pipeline with docker-compose |
| CO2 Estimation | 15 | ✅ Electricity + gas paths implemented |
| Anomaly Detection Bonus | 15 | ✅ 5-method ensemble detection |
| Innovation Bonus | 25 | ⏳ Placeholder: Claude API integration (not finished) |
| **Total Possible** | **160** | ~120/160 expected (with placeholders) |

---

## Key Outputs

### Data Models
- **ExtractionResult**: Pydantic model with 73 optional float fields organized by subsystem (metadata, gas, electrical, thermal, efficiency, grid)
- **EnergyRecord**: SQLAlchemy ORM for persistent storage in SQLite
- **AnomalyFlag**: Classified anomaly types (spike, stuck_sensor, dropout, etc.)

### Artifacts Generated
1. **SQLite Database**: `energy.db` with tables for raw records, anomaly flags, extraction warnings
2. **Dashboard Visualizations**:
   - Tab 1: KPIs (total CO2, avg power, efficiency, anomaly count, confidence)
   - Tab 2: CO2 trends (daily breakdown, source comparison)
   - Tab 3: Anomaly analysis (type distribution, flagged records heatmap)
   - Tab 4: Data explorer (filterable table by source + date range)
   - Tab 5: Data quality coverage (confidence by source, extraction warnings)
3. **API Endpoints** (FastAPI):
   - `POST /extract` — Extract from uploaded file (Excel, PDF, image)
   - `GET /records` — Query historical records
   - `GET /anomalies` — List flagged anomalies with details

---

## System Constraints

### Time/Scope (Hackathon)
- **Development Window**: 23 hours (implies incomplete features acceptable)
- **Target Judges**: Energy industry professionals, cloud architects, sustainability officers
- **Infrastructure**: Docker Compose only (no Kubernetes, no cloud deployment)

### Technical Constraints
- **Data Source Format**: Pharmaceutical factory uses Excel 74×2,877 wide-format sheets (non-standard)
- **Language Support**: French + English (headers, OCR, validation messages)
- **Real-time Requirement**: None (batch processing acceptable; cold-start at container startup)
- **Persistence**: SQLite only (no backups, no replication)
- **Concurrency**: Single-threaded extraction (no multi-worker FastAPI)

### Data Constraints
- **11+ Subsystems**: Gas, electrical (gross + net), thermal recovery (5 variants), efficiency metrics, grid
- **Validation Bounds**: Hard-coded physical limits (see [DATA_DICTIONARY.md](DATA_DICTIONARY.md))
- **Coverage Scoring**: 9 critical fields required for "complete" record; missing fields lower confidence score
- **CO2 Factors**: Static (electricity 0.267 kg/kWh, gas 0.202 kg/kWh) — no real-time grid carbon data

---

## Success Criteria

### Extraction
- [ ] Excel wide-format parsing: 100% field extraction, <2% error rate on timestamps
- [ ] PDF invoice extraction: ≥80% accuracy (invoice amount, date, energy quantity)
- [ ] OCR image extraction: ≥70% accuracy on WhatsApp images

### Validation
- [ ] Physical bounds enforcement: Zero false negatives on physically impossible values (voltage >500V, power >2000 kW)
- [ ] Confidence scoring: Records with ≥5 coverage fields ≥80% confidence

### Anomalies
- [ ] Detection sensitivity: Catch 80%+ of injected spike anomalies (±50% deviation)
- [ ] False positive rate: <10% on normal operational data

### Dashboard
- [ ] Load time: <5 seconds with 1,000 records
- [ ] Interactivity: All filters respond <500ms

### Deployment
- [ ] Cold-start time: <60 seconds from `docker compose up --build` to dashboard ready
- [ ] Data integrity: SQLite consistency after FastAPI + Streamlit concurrent access

---

## Key Metrics

### Energy Metrics
- **Total Energy Produced (MWh)**: Sum of electrical + thermal outputs
- **CO2 Emissions (kg)**: Electricity × 0.267 + Gas × 0.202
- **System Efficiency (%)**: Useful output / input energy
- **Power Factor**: Reactive vs. active power on 3-phase grid

### Data Quality
- **Coverage Score**: (Count of non-null coverage fields / 9) × 100%
- **Anomaly Frequency**: % of records flagged by any detection method
- **Source Distribution**: Records by extractor type (Excel, PDF, OCR)

### Operational Insights
- **Peak Power Demand**: Maximum instantaneous power (kW)
- **Thermal Recovery Rate**: Heat recaptured vs. total waste heat
- **Grid Interaction**: Net export/import vs. self-consumption

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Excel parser fails on edge cases (non-standard formatting) | Medium | High | Implement fuzzy header matching + skip malformed rows |
| EasyOCR model download fails in Docker build | Medium | Critical | Pre-download model layers; fall back to placeholder |
| SQLite locked during concurrent FastAPI + Streamlit writes | Low | High | Use `timeout=5` + WAL mode; keep writes serialized |
| Claude API rate limit exceeded | Low | Medium | ✅ Not implemented; fallback to rule-based validation |
| 23-hour window insufficient to complete all features | High | Medium | ✅ Prioritize extraction + validation; defer innovation bonus |

---

## Deliverables

### Code
- ✅ `src/extractor/` — Python package with 4 extractors, normalizer, validator, CO2 calculator, anomaly detector
- ✅ `src/dashboard/` — Streamlit app with 5 interactive tabs
- ✅ `tests/` — 11 test files covering extraction, normalization, validation, anomalies

### Configuration
- ✅ `docker-compose.yml` — 3 services (FastAPI, db-init, Streamlit)
- ✅ `requirements.txt` — Python dependencies with pinned versions
- ✅ `Dockerfile.dashboard` & `Dockerfile.extractor` — Container images

### Documentation
- ✅ `docs/superpowers/specs/2026-05-02-energy-pipeline-design.md` — Design specification
- 🆕 `docs/context/` — Comprehensive architecture, data dictionary, issues, roadmap

---

## Glossary

| Term | Definition |
|------|-----------|
| **Tri-generation** | Simultaneous production of electricity (puissance), heating (EG), and chilled water (EC) |
| **PCI** | Pouvoir Calorifique Inférieur (lower heating value of gas; default 9.082 thermie/Nm3) |
| **Puissance Brute** | Gross electrical power before losses |
| **Rendement** | Efficiency (% of input energy converted to useful output) |
| **Steg** | Grid connection (STEG = Société Tunisienne de l'Électricité et du Gaz) |
| **Nm3** | Normal cubic meter of gas (at 0°C, 1 atm) |
| **Anomaly Flags** | spike, stuck_sensor, dropout, iqr_outlier, isolation_forest |

---

## Next Steps

See [ROADMAP.md](ROADMAP.md) for:
- Week 1 priorities (implement Claude API, fix thread-safety)
- Week 2 priorities (migrate SQLite → PostgreSQL, add structured logging)
- Week 3+ (performance optimization, real-time alerts)

For architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md).
For identified issues, see [PROBLEMS.md](PROBLEMS.md).
