# ROADMAP.md — Fix Priorities & Timelines

## Overview

This roadmap prioritizes the 15 identified issues from [PROBLEMS.md](PROBLEMS.md) across 4 phases:
1. **Hackathon Final (Week 1)** — Fix blockers for demo day
2. **Production Ready (Week 2)** — Enable real-world deployment
3. **Scale & Monitor (Week 3)** — Support growth
4. **Long-term (Week 4+)** — Architecture improvements

---

## Phase 1: Hackathon Final (Week 1 — May 3-4)

**Goal**: Reliable demo that impresses judges; fix critical issues

### Priority 1a: ImageExtractor Thread-Safety (Issue #2)

**Why**: Breaks on concurrent image uploads; judges will test this

**Implementation**:
1. Move EasyOCR reader from global singleton to request context (1h)
   ```python
   from fastapi import Depends
   
   async def get_ocr_reader():
       if not hasattr(request, "ocr_reader"):
           request.ocr_reader = easyocr.Reader(['fr', 'en'])
       return request.ocr_reader
   
   async def extract_image(file: UploadFile, reader = Depends(get_ocr_reader)):
       text = reader.readtext(image)
       return parse_metrics(text)
   ```
2. Add concurrency tests (2 parallel requests) (1h)
3. Test with stress tool: `ab -n 10 -c 5 http://localhost:8000/extract` (30m)

**Effort**: 2.5 hours | **Estimated Impact**: Eliminates 90% of crashes

**Verified By**:
- [ ] 3 concurrent /extract requests succeed
- [ ] No race conditions in OCR reader
- [ ] Dashboard stays responsive

---

### Priority 1b: Claude API Fallback (Issue #1 — Minimal)

**Why**: Judges notice innovation bonus disabled

**Implementation** (MVP fallback, not full API):
1. Check if Claude API key set; skip if not (30m)
2. Implement basic validation rule engine (1h):
   ```python
   def validate_with_rules(record):
       errors = []
       if record.voltage_v and not (380 <= record.voltage_v <= 440):
           errors.append("voltage_out_of_bounds")
       if record.factor_puissance and not (0.8 <= record.factor_puissance <= 1.0):
           errors.append("power_factor_invalid")
       return errors
   ```
3. If Claude key available, augment (1h):
   ```python
   if os.environ.get("CLAUDE_API_KEY"):
       response = client.messages.create(
           model="claude-3-5-sonnet-20241022",
           messages=[{"role": "user", "content": f"Validate: {record}"}]
       )
   ```

**Effort**: 2.5 hours | **Estimated Impact**: Unlock innovation bonus; judges see AI integration

**Verified By**:
- [ ] Claude API optional (doesn't crash if missing)
- [ ] Fallback rules applied automatically
- [ ] Dashboard shows validation method used

---

### Priority 1c: Error Recovery & Logging (Issue #6)

**Why**: Pipeline silently skips files; no visibility

**Implementation**:
1. Create structured error log (1h):
   ```python
   import json
   errors = []
   try:
       extract(file)
   except Exception as e:
       errors.append({
           "timestamp": datetime.now().isoformat(),
           "file": file_path,
           "extractor": "excel",
           "error": str(e),
           "action": "skip"
       })
   
   with open("/data/extraction_errors.jsonl", "a") as f:
       f.write(json.dumps(errors) + "\n")
   ```
2. Add error summary to dashboard (1h):
   - Tab 5 → show list of extraction warnings
   - Color-code by severity (red=skip, yellow=low-confidence)

**Effort**: 2 hours | **Estimated Impact**: Judges see data quality metrics

**Verified By**:
- [ ] 10 test files processed; error log created
- [ ] Dashboard Tab 5 shows error summary
- [ ] Judges can see which files were problematic

---

### Priority 1d: Integration Tests (Issue #7 — Minimal)

**Why**: Validate pipeline works end-to-end

**Implementation**:
1. Add `test_pipeline_integration()` (2h):
   ```python
   def test_pipeline_integration():
       # Create 3 test files: 1 Excel, 1 PDF, 1 Image
       excel_file = create_test_excel()
       pdf_file = create_test_pdf()
       image_file = create_test_image()
       
       # Run pipeline
       results = run_pipeline([excel_file, pdf_file, image_file])
       
       # Verify
       assert len(results) == 3
       assert sum(1 for r in results if r.source_type == "excel") == 1
       assert all(r.confidence_score > 0 for r in results)
   ```
2. Test concurrency (30m):
   ```python
   def test_concurrent_extract_api():
       # Simulate 3 simultaneous /extract requests
       # Should not crash; all should succeed
   ```

**Effort**: 2.5 hours | **Estimated Impact**: Confidence that system works

**Verified By**:
- [ ] All 11 pytest tests pass
- [ ] Coverage report shows >70% on critical paths
- [ ] No race conditions or crashes

---

### Phase 1 Summary

| Issue | Title | Effort | Status |
|-------|-------|--------|--------|
| 2 | ImageExtractor Thread-Safety | 2.5h | ✅ |
| 1 | Claude API Fallback | 2.5h | ✅ |
| 6 | Error Recovery Logging | 2h | ✅ |
| 7 | Integration Tests | 2.5h | ✅ |
| **Total** | **Week 1** | **9.5h** | **Ready for Demo** |

**Demo Checklist**:
- [ ] Concurrent /extract requests work reliably
- [ ] No Python crashes or exceptions
- [ ] Dashboard loads <5 seconds with 100 records
- [ ] Judges see error summary + extraction success rates
- [ ] All test suites pass (11 files, 39 tests, 75%+ coverage)

---

## Phase 2: Production Ready (Week 2 — May 5-11)

**Goal**: System can run in production; maintainable code

### Priority 2a: Package Structure Fix (Issue #3)

**Why**: Current sys.path.insert() breaks outside Docker

**Implementation** (8h total):
1. Convert to proper Python package (5h):
   ```
   energy-pipeline/
   ├── setup.py
   ├── energy_pipeline/
   │   ├── __init__.py
   │   ├── extractor/
   │   │   ├── __init__.py
   │   │   ├── main.py
   │   │   ├── pipeline.py
   │   │   ├── normalizer.py
   │   │   ├── validator.py
   │   │   ├── co2.py
   │   │   ├── anomaly.py
   │   │   ├── db.py
   │   │   └── extractors/
   │   │       ├── __init__.py
   │   │       ├── base.py
   │   │       ├── excel.py
   │   │       ├── pdf.py
   │   │       └── image.py
   │   └── dashboard/
   │       ├── __init__.py
   │       └── app.py
   ```
2. Update imports everywhere (2h):
   - `from src.extractor import ...` → `from energy_pipeline.extractor import ...`
3. Update docker-compose (1h):
   - `pip install -e .` instead of sys.path hacks
4. Update tests (3h):
   - Fix all import paths
   - Verify tests run from any directory

**Effort**: 8 hours | **Estimated Impact**: Maintainable code; enables pip install

**Verified By**:
- [ ] Local development works: `cd src/dashboard && python app.py`
- [ ] `pip install -e .` succeeds
- [ ] All tests pass after import changes
- [ ] Docker build still works (no sys.path needed)

---

### Priority 2b: Validation Bounds Config (Issue #4)

**Why**: Hard-coded bounds don't account for seasonal variation

**Implementation** (2h):
1. Create `config/validation_bounds.yaml`:
   ```yaml
   validation_bounds:
     winter_mode:  # Dec-Feb, heating season
       puissance_brute_kw: [800, 1400]
       eg_puissance_kw: [50, 300]
     summer_mode:  # Jun-Aug, cooling season
       puissance_brute_kw: [500, 900]
       eg_puissance_kw: [0, 50]
       ec_gamma_puissance_kw: [100, 300]
     maintenance_mode:  # Any time
       puissance_brute_kw: [0, 1500]  # Relaxed bounds
   ```
2. Load config at startup (1h):
   ```python
   from pydantic_settings import BaseSettings
   class Config(BaseSettings):
       validation_bounds_file: str = "config/validation_bounds.yaml"
   
   def get_bounds(date):
       if date.month in [6, 7, 8]:
           return bounds["summer_mode"]
       # ...
   ```

**Effort**: 2 hours | **Estimated Impact**: Fewer false anomalies; more accurate CO2 tracking

**Verified By**:
- [ ] Summer + winter data loads correctly with seasonal bounds
- [ ] Validation tests pass with new bounds
- [ ] Anomaly false positive rate drops

---

### Priority 2c: Real-Time CO2 Grid Carbon (Issue #5)

**Why**: Static 0.267 kg/kWh underestimates renewable impact

**Implementation** (4h):
1. Integrate electricitymap.org API (2h):
   ```python
   import requests
   
   def get_carbon_intensity(country="TN"):  # Tunisia
       response = requests.get(
           f"https://api.electricitymap.org/v3/carbon-intensity/latest",
           params={"zone": country},
           headers={"auth-token": os.environ["ELECTRICITY_MAP_KEY"]}
       )
       return response.json()["carbonIntensity"] / 1000  # convert to kg/kWh
   
   # Cache for 30 minutes
   @cache(ttl=1800)
   def get_co2_factor():
       return get_carbon_intensity()
   ```
2. Update CO2 calculator (1h):
   ```python
   def estimate_co2(puissance_brute_kw, gaz_volume_nm3):
       carbon_factor = get_co2_factor()
       co2_kwh = puissance_brute_kw * carbon_factor if puissance_brute_kw else 0
       co2_gas = gaz_volume_nm3 * 0.202 if gaz_volume_nm3 else 0
       return co2_kwh + co2_gas
   ```
3. Add dashboard chart (1h):
   - Show "Grid Carbon Intensity Over Time"
   - Highlight days with renewable peaks

**Effort**: 4 hours | **Estimated Impact**: Credible carbon tracking; aligns with sustainability goals

**Verified By**:
- [ ] API integration doesn't crash if network unavailable
- [ ] Fallback to 0.267 if API fails
- [ ] Dashboard shows carbon intensity trend
- [ ] CO2 estimates match real-time data

---

### Priority 2d: Database Concurrency Testing (Issue #10)

**Why**: SQLite contention causes silent failures

**Implementation** (3h):
1. Add WAL mode + proper connection pooling (1h):
   ```python
   # Already done: WAL mode
   # Add: connection pool with serialized writes
   from sqlalchemy.pool import SingletonThreadPool
   
   engine = create_engine(
       "sqlite:////data/energy.db",
       connect_args={"timeout": 10},
       poolclass=SingletonThreadPool
   )
   ```
2. Add concurrency tests (2h):
   ```python
   def test_concurrent_db_writes():
       import threading
       threads = []
       for i in range(5):
           t = threading.Thread(target=write_records, args=(records_batch[i],))
           threads.append(t)
           t.start()
       for t in threads:
           t.join()
       assert count_records() == 5 * batch_size
   ```

**Effort**: 3 hours | **Estimated Impact**: Reliable database operations

**Verified By**:
- [ ] 5 concurrent writers don't corrupt DB
- [ ] Transaction rollback works on error
- [ ] Query latency <100ms with 10K records

---

### Priority 2e: Environment Variable Validation (Issue #9)

**Why**: App crashes cryptically if env vars missing

**Implementation** (2h):
1. Use pydantic-settings (1h):
   ```python
   from pydantic_settings import BaseSettings
   
   class AppConfig(BaseSettings):
       sqlite_path: str = "/data/energy.db"
       claude_api_key: str = None  # Optional
       log_level: str = "INFO"
       max_upload_size_mb: int = 500
       
       class Config:
           env_file = ".env"
   ```
2. Add startup validation (1h):
   ```python
   @app.on_event("startup")
   async def validate_config():
       config = AppConfig()
       assert os.path.exists(config.sqlite_path), f"DB not found: {config.sqlite_path}"
       logger.info(f"Config loaded: {config}")
   ```

**Effort**: 2 hours | **Estimated Impact**: Clearer error messages

**Verified By**:
- [ ] Missing SQLITE_PATH shows clear error
- [ ] Optional vars (CLAUDE_API_KEY) have defaults
- [ ] `.env` file loads correctly

---

### Phase 2 Summary

| Issue | Title | Effort | Status |
|-------|-------|--------|--------|
| 3 | Package Structure | 8h | ✅ |
| 4 | Bounds Config | 2h | ✅ |
| 5 | Real-Time CO2 | 4h | ✅ |
| 10 | DB Concurrency | 3h | ✅ |
| 9 | Env Validation | 2h | ✅ |
| **Total** | **Week 2** | **19h** | **Production Ready** |

**Production Checklist**:
- [ ] Code structure: proper Python package
- [ ] Configuration: YAML + environment variables
- [ ] Data Quality: seasonal bounds; real-time grid carbon
- [ ] Reliability: concurrent DB ops; env validation
- [ ] Test coverage: >80% on critical paths

---

## Phase 3: Scale & Monitor (Week 3 — May 12-18)

**Goal**: System handles 1M+ records; observable

### Priority 3a: Database Migration to PostgreSQL

**Why**: SQLite limits at ~1GB; PostgreSQL handles unlimited scale

**Implementation** (12h):
1. Create PostgreSQL schema (3h)
2. Add migration script: SQLite → PostgreSQL (3h)
3. Update ORM connection string (1h)
4. Test performance: queries <50ms with 1M records (3h)
5. Add database backups (2h)

**Effort**: 12 hours | **Estimated Impact**: 100× scale increase

---

### Priority 3b: Structured Logging (Issue #12)

**Why**: JSON logs integrate with Loki/ELK; enable alerts

**Implementation** (3h):
1. Switch from print() to Python logging (2h):
   ```python
   import logging
   import json_log_formatter
   
   logger = logging.getLogger(__name__)
   handler = logging.StreamHandler()
   formatter = json_log_formatter.JSONFormatter()
   handler.setFormatter(formatter)
   logger.addHandler(handler)
   
   logger.info("Event", extra={"source_file": "energy.xlsx", "status": "success"})
   ```
2. Add application metrics (Prometheus) (1h)

**Effort**: 3 hours | **Estimated Impact**: Observable system; enable alerting

---

### Priority 3c: Dashboard Caching (Issue #15)

**Why**: Large datasets slow dashboard

**Implementation** (2h):
1. Add Redis cache layer (2h):
   ```python
   import redis
   import pickle
   
   cache = redis.Redis()
   
   @st.cache_data(ttl=300)
   def load_records():
       cached = cache.get("energy_records")
       if cached:
           return pickle.loads(cached)
       df = pd.read_sql("SELECT * FROM energy_records", conn)
       cache.setex("energy_records", 300, pickle.dumps(df))
       return df
   ```

**Effort**: 2 hours | **Estimated Impact**: Dashboard load <2 seconds even with 1M records

---

### Priority 3d: API Authentication (Issue #13)

**Why**: Production requires access control

**Implementation** (4h):
1. Add OAuth2 + JWT (3h)
2. Add API key management UI (1h)

**Effort**: 4 hours | **Estimated Impact**: Secure data access

---

### Phase 3 Summary

| Feature | Effort | Impact |
|---------|--------|--------|
| PostgreSQL Migration | 12h | 100× scale |
| Structured Logging | 3h | Observability |
| Dashboard Caching | 2h | Performance |
| API Auth | 4h | Security |
| **Total** | **21h** | **Production Scale** |

---

## Phase 4: Long-Term (Week 4+)

### Future Improvements

1. **Real-Time Streaming** (20h)
   - Apache Kafka for event stream
   - Real-time anomaly detection dashboards

2. **ML Model Training** (30h)
   - Train custom anomaly detector on historical data
   - Replace static Isolation Forest

3. **Mobile App** (40h)
   - React Native for mobile anomaly alerts
   - Push notifications

4. **Kubernetes Deployment** (25h)
   - Helm charts
   - Auto-scaling extractors
   - Service mesh (Istio) for monitoring

---

## Timeline Summary

```
Week 1 (May 3-4):  Hackathon Final → 9.5h  → DEMO READY
                   └─ Thread-safety, Error logging, Integration tests

Week 2 (May 5-11): Production Ready → 19h   → PRODUCTION READY
                   └─ Package structure, Config, Real-time CO2, DB concurrency

Week 3 (May 12-18): Scale & Monitor → 21h   → SCALABLE SYSTEM
                   └─ PostgreSQL, Logging, Caching, API Auth

Week 4+ : Long-term → 115h  → ENTERPRISE SYSTEM
                   └─ Streaming, ML, Mobile, Kubernetes
```

**Total Effort to Production**: ~50 hours (2.5 weeks)

**Key Milestones**:
- ✅ May 4 (EOD): Hackathon submission (DEMO READY)
- ✅ May 11: Production deployment (PRODUCTION READY)
- ✅ May 18: 1M+ record capacity (SCALABLE SYSTEM)
- ✅ June 1: Enterprise-ready (LONG-TERM)

---

For detailed issue descriptions, see [PROBLEMS.md](PROBLEMS.md).
For current status, see [PROJECT.md](PROJECT.md).
For test progress, see [TEST_COVERAGE.md](TEST_COVERAGE.md).
