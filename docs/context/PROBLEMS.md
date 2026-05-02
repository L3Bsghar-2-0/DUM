# PROBLEMS.md — Issue Catalog & Impact Analysis

## Overview

This document catalogs **10+ identified issues** across architecture, data quality, testing, and deployment. Each issue includes:
- **Severity**: HIGH (blocks critical path) | MEDIUM (degrades quality) | LOW (minor impact)
- **Location**: File path + line reference
- **Impact**: What breaks when this issue occurs
- **Fix Summary**: Recommended solution + estimated effort

---

## Critical Issues (Severity: HIGH)

### Issue #1: Placeholder Claude API Integration

**Location**: [src/extractor/validator.py](src/extractor/validator.py#L32) — `_claude_validate_placeholder()`

**Problem**: Claude API validation stubbed; returns empty dict without validation.

**Impact**:
- Batch validation claims to use "Claude for enhanced validation" but does nothing
- Invalid records pass through undetected (e.g., physically impossible power values)
- Judges will notice missing AI integration; loses innovation bonus

**Fix Summary**:
1. Implement Claude batch API for validation (estimated 4 hours)
   - Call Claude to validate if (P, V, I) are consistent
   - Return structured validation JSON
2. OR: Fall back to deterministic rule-based expansion (2 hours)
   - Add 10 more physical constraint checks

**Effort**: Medium (4 hours) | **Priority**: High (demo blocker)

---

### Issue #2: ImageExtractor Thread-Safety (Singleton _READER)

**Location**: [src/extractor/extractors/image.py](src/extractor/extractors/image.py#L29) — Global `_READER`

**Problem**: EasyOCR reader is a singleton global variable; not thread-safe.

**Impact**:
- If FastAPI processes 2 concurrent /extract requests with images, race conditions occur
- OCR model state corrupted; crashes or silent errors
- Breaks horizontal scaling of extractor service

**Reproduction**:
```python
# Concurrent requests
curl -F "file=image1.jpg" http://localhost:8000/extract &
curl -F "file=image2.jpg" http://localhost:8000/extract &
wait
# Expected: Both succeed; Actual: Random crashes
```

**Fix Summary**:
1. Move EasyOCR reader to request context (FastAPI Depends) — 1 hour
2. OR: Use thread-local storage (threading.local) — 1 hour
3. Add concurrency tests (3 requests in parallel) — 1 hour

**Effort**: Medium (3 hours) | **Priority**: High (production blocker)

---

### Issue #3: Fragile sys.path Imports

**Location**: [src/extractor/main.py](src/extractor/main.py#L1-10), [src/dashboard/app.py](src/dashboard/app.py#L8-9)

**Problem**: Code uses `sys.path.insert(0, '..')` + manual PYTHONPATH instead of proper package structure.

**Impact**:
- Breaks when code runs outside Docker (local dev, CI/CD, Jupyter)
- IDE autocomplete fails (can't resolve relative imports)
- Hard to distribute as pip package or reusable module
- Fragile: any cwd change breaks imports

**Example Failure**:
```bash
cd src/dashboard && python app.py
# Error: ModuleNotFoundError: No module named 'extractor'
# (because sys.path doesn't include parent)
```

**Fix Summary**:
1. Convert to proper Python package (5 hours):
   - Add `__init__.py` to src/, src/extractor/, src/dashboard/
   - Use relative imports: `from extractor.normalizer import normalize_record`
   - Add setup.py or pyproject.toml
2. Update docker-compose to install package: `pip install -e .` (1 hour)
3. Update tests + local dev docs (2 hours)

**Effort**: Medium (8 hours) | **Priority**: High (maintainability blocker)

---

## Medium-Severity Issues (Severity: MEDIUM)

### Issue #4: Hard-Coded Validation Bounds (No Seasonal Override)

**Location**: [src/extractor/validator.py](src/extractor/validator.py#L5-14)

**Problem**: Physical bounds fixed (voltage 380–440V, power 800–1,400 kW). No seasonal or operational mode override.

**Impact**:
- Pharmaceutical factory might have seasonal shutdowns (summer = lower power)
- Some equipment runs only during cold storage mode (chilled water 0–10°C valid; heating mode 50–80°C valid)
- System flags legitimate low-power days as anomalies
- High false positive rate in anomaly detection

**Recorded Instances**: None yet (hackathon data limited); expect in production

**Fix Summary**:
1. Load bounds from YAML config file (1 hour):
   ```yaml
   validation_bounds:
     normal_mode:
       puissance_brute_kw: [800, 1400]
     shutdown_mode:
       puissance_brute_kw: [0, 100]
   ```
2. Add operational mode field to ExtractionResult; switch bounds (1 hour)
3. OR: Make bounds 2 standard deviations from historical data (2 hours)

**Effort**: Low (2–3 hours) | **Priority**: Medium (detect after 1 week data)

---

### Issue #5: Static CO2 Factors (No Real-Time Grid Carbon Data)

**Location**: [src/extractor/co2.py](src/extractor/co2.py#L5-6)

**Problem**: CO2 factors hard-coded:
- Electricity: 0.267 kg/kWh (French average)
- Gas: 0.202 kg/kWh (fixed)

**Impact**:
- Grid carbon intensity varies by time-of-day (renewable wind ↓, coal baseload ↑)
- Report CO2 savings as "50 kg today" but actual savings might be 150 kg (if wind-heavy grid)
- Misleads sustainability officers; undervalues renewable integration
- Ignores gas source carbon intensity variation

**Example Discrepancy**:
```
Recorded: 100 kWh × 0.267 = 26.7 kg CO2
Actual (real-time grid): 100 kWh × 0.120 (wind) = 12 kg CO2
Error: +122% overestimate
```

**Fix Summary**:
1. Integrate real-time grid carbon API (2–3 hours):
   - electricitymap.org API (covers Tunisia + France)
   - Cache results (30-minute refresh)
   - Fallback to default if API unavailable
2. Add gas source carbon intensity lookup (1 hour)

**Effort**: Medium (3–4 hours) | **Priority**: Medium (sustainability feature)

---

### Issue #6: Error Recovery Lacks Structured Tracking

**Location**: [src/extractor/pipeline.py](src/extractor/pipeline.py#L30-50)

**Problem**: File extraction failures caught but only logged to console; no structured error tracking.

**Impact**:
- "Processed 1000 files" but silently skipped 50 corrupted ones
- No way to detect systematic failures (e.g., "all PDFs fail on Tuesdays")
- Debugging production issues requires manual log review
- No alerting (e.g., email if >10% of files fail)

**Current Code**:
```python
for file_path in input_files:
    try:
        results = extract(file_path)
    except Exception as e:
        print(f"Error: {e}")  # Silent skip!
```

**Fix Summary**:
1. Create structured error log (1 hour):
   ```json
   {
     "timestamp": "2026-05-02T14:30:00Z",
     "file": "energy_202605.xlsx",
     "extractor": "excel",
     "error_type": "timestamp_parse_error",
     "error_message": "Could not parse date",
     "recovery_action": "skip_row"
   }
   ```
2. Add error summary + alerting logic (2 hours)

**Effort**: Low (3 hours) | **Priority**: Medium (production visibility)

---

### Issue #7: Missing Multi-File Pipeline Tests

**Location**: [tests/](tests/) — No `test_pipeline.py`

**Problem**: Pipeline integration tests exist but only check Excel extractor count. PDFs + images not tested together.

**Test Gaps**:
- ❌ Concurrent /extract requests with image files (thread-safety)
- ❌ Multi-file extraction with mixed formats (Excel + PDF in same run)
- ❌ Error recovery (skip malformed file, continue with next)
- ❌ Database consistency after pipeline crash (partial write rollback)
- ❌ Division by zero on empty input (edge case)

**Current Coverage**:
- Excel extraction: 7 tests ✓
- Anomaly detection: 6 tests ✓
- Normalizer: 3 tests ✓
- Validator: 2 tests ✓
- **Pipeline orchestration: 0 tests** ✗

**Target**: >80% coverage on critical modules (pipeline, validator, anomaly, co2)

**Fix Summary**:
1. Write 5 integration tests (3 hours):
   - `test_pipeline_mixed_formats()` — Excel + PDF + image in one run
   - `test_concurrent_extract_requests()` — Simulate FastAPI thread pool
   - `test_error_recovery_skip_corrupted_file()` — Graceful skip
   - `test_database_rollback_on_crash()`
2. Add pytest-cov + coverage reporting (1 hour)

**Effort**: Low (4 hours) | **Priority**: Medium (reliability regression)

---

### Issue #8: Hard-Coded Validation Bounds (No Config Flexibility)

**Location**: [src/extractor/validator.py](src/extractor/validator.py) (see Issue #4)

**Problem** (duplicate of #4): Bounds not configurable; requires code change to adjust.

**Fix**: See Issue #4 for YAML config approach.

---

## Low-Medium Severity Issues (Severity: LOW-MEDIUM)

### Issue #9: No Environment Variable Validation

**Location**: Entire codebase (FastAPI routes, Streamlit config, Docker entrypoints)

**Problem**: Code assumes env vars exist; no defaults or validation.

**Impact**:
- If `SQLITE_PATH` not set, app crashes cryptically
- If `CLAUDE_API_KEY` missing, fallback behavior undefined
- Docker container fails to start without explicit env setup
- CI/CD requires manual environment configuration

**Current Code**:
```python
db_path = os.environ["SQLITE_PATH"]  # Crashes if not set!
```

**Fix Summary**:
1. Use pydantic-settings (1 hour):
   ```python
   from pydantic_settings import BaseSettings
   class Config(BaseSettings):
       sqlite_path: str = "/data/energy.db"
       claude_api_key: str = None  # Optional
       log_level: str = "INFO"
   ```
2. Add environment validation on startup (30 min)
3. Document required vars in QUICKSTART.md (30 min)

**Effort**: Low (2 hours) | **Priority**: Low (operational hygiene)

---

### Issue #10: SQLite Contention on Concurrent Writes

**Location**: [src/extractor/db.py](src/extractor/db.py), docker-compose.yml

**Problem**: FastAPI (write) + Streamlit (read) + db-init (write) all access SQLite simultaneously.

**Impact**:
- SQLite uses file-level locking; only 1 writer at a time
- If db-init writing during dashboard query → dashboard blocks 5+ seconds
- If FastAPI processing 2 /extract requests → second request blocked
- No explicit transaction isolation; risk of dirty reads

**Error Symptom**:
```
sqlite3.OperationalError: database is locked (timeout=5.0)
```

**Mitigation (Implemented)**: WAL mode enabled in docker-compose.
**Remaining Issue**: No explicit writer serialization; unpredictable contention.

**Fix Summary**:
1. Enable SQLite WAL mode (already done) ✓
2. Add connection pool with max_pool_size=1 (1 hour):
   ```python
   from sqlalchemy import create_engine
   engine = create_engine(
       "sqlite:////data/energy.db",
       connect_args={"timeout": 10, "check_same_thread": False},
       poolclass=SingletonThreadPool,  # Single connection
   )
   ```
3. Serialize writes: Use fastapi.BackgroundTasks + queue (2 hours)

**Effort**: Low (3 hours) | **Priority**: Low-Medium (only manifests under load)

---

### Issue #11: Missing Docker Resource Limits

**Location**: docker-compose.yml

**Problem**: No CPU/memory limits; EasyOCR model (500MB) + large datasets could OOM on limited systems.

**Impact**:
- On 2GB server, EasyOCR model + Streamlit + FastAPI = OOM kill
- No graceful degradation; container crashes without warning
- Difficult to debug resource exhaustion

**Current Config**:
```yaml
services:
  extractor:
    image: ...
    # No resources: limits
```

**Fix Summary**:
1. Add resource limits (30 min):
   ```yaml
   resources:
     limits:
       cpus: '2'
       memory: 2G
     reservations:
       cpus: '1'
       memory: 1G
   ```
2. Add health checks with memory monitoring (1 hour)

**Effort**: Low (1.5 hours) | **Priority**: Low (operational)

---

### Issue #12: Print-Based Logging (Not Structured)

**Location**: All Python files (src/extractor/*, src/dashboard/*)

**Problem**: Code uses `print()` for logging; no structured logging framework.

**Impact**:
- Logs mixed with application output; hard to parse
- No log levels (can't suppress DEBUG in production)
- No timestamp correlation across services
- Impossible to centralize logs (Loki, Datadog, etc.)

**Current Code**:
```python
print(f"Processing {file_path}")  # Not a structured log!
```

**Fix Summary**:
1. Add Python logging module (1 hour):
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info(f"Processing {file_path}")
   ```
2. Configure JSON logging format (1 hour)
3. Add log aggregation docs (30 min)

**Effort**: Low (2.5 hours) | **Priority**: Low (production visibility)

---

## Low-Severity Issues (Severity: LOW)

### Issue #13: Missing API Authentication

**Location**: [src/extractor/main.py](src/extractor/main.py) — FastAPI routes

**Problem**: All FastAPI endpoints (`/extract`, `/records`, `/anomalies`) are unauthenticated; anyone can upload files or query data.

**Impact**:
- Hackathon demo only; not for production
- Data not confidential; energy metrics are commercially sensitive
- No rate limiting; DOS attack possible (send 1000 large files)
- Audit trail missing (who extracted what data?)

**Fix Summary**:
1. Add OAuth2 + JWT tokens (4 hours) — production-grade
2. Or: Simple API key validation (1 hour) — MVP
   ```python
   from fastapi import Header, HTTPException
   async def verify_api_key(x_api_key: str = Header(...)):
       if x_api_key != os.environ.get("API_KEY"):
           raise HTTPException(status_code=403)
   ```

**Effort**: Medium (4 hours production) | **Priority**: Low (hackathon OK)

---

### Issue #14: No Graceful Shutdown Handling

**Location**: docker-compose.yml, src/extractor/main.py

**Problem**: If FastAPI killed during request processing, no cleanup of partial database writes or file handles.

**Impact**:
- Corrupted SQLite database on kill -9 (rare, but possible)
- Temporary uploaded files not deleted
- No graceful connection close

**Fix Summary**: Add shutdown event handler (1 hour):
```python
@app.on_event("shutdown")
async def shutdown():
    # Cleanup: close DB, delete temp files
    pass
```

**Effort**: Low (1 hour) | **Priority**: Low (operational hygiene)

---

### Issue #15: No Caching on Streamlit Dashboard

**Location**: [src/dashboard/app.py](src/dashboard/app.py)

**Problem**: Every page refresh queries entire SQLite database (no caching).

**Impact**:
- Slow dashboard with 10K+ records (5+ second load time)
- Excessive database reads
- Not scalable to production data volumes

**Current Code**:
```python
df = pd.read_sql("SELECT * FROM energy_records", conn)  # Every refresh!
```

**Fix Summary**:
1. Add @st.cache_data decorator (30 min):
   ```python
   @st.cache_data(ttl=300)  # Cache 5 minutes
   def load_records():
       return pd.read_sql(...)
   ```
2. Or: Implement Redis cache layer (3 hours) — production

**Effort**: Low (30 min to 3 hours) | **Priority**: Low (performance, not blocking)

---

## Summary Table

| Issue # | Title | Severity | Effort | Priority | Blocker? |
|---------|-------|----------|--------|----------|----------|
| 1 | Claude API Placeholder | HIGH | 4h | High | Demo |
| 2 | ImageExtractor Thread-Safety | HIGH | 3h | High | ✓ |
| 3 | Fragile sys.path Imports | HIGH | 8h | High | ✓ |
| 4 | Hard-Coded Bounds | MEDIUM | 2h | Medium | — |
| 5 | Static CO2 Factors | MEDIUM | 4h | Medium | — |
| 6 | Error Recovery Tracking | MEDIUM | 3h | Medium | — |
| 7 | Missing Pipeline Tests | MEDIUM | 4h | Medium | — |
| 9 | No Env Var Validation | LOW-MEDIUM | 2h | Low | — |
| 10 | SQLite Contention | LOW-MEDIUM | 3h | Low-Med | — |
| 11 | Missing Resource Limits | LOW-MEDIUM | 1.5h | Low | — |
| 12 | Print Logging | LOW-MEDIUM | 2.5h | Low | — |
| 13 | No API Auth | LOW | 4h | Low | — |
| 14 | No Graceful Shutdown | LOW | 1h | Low | — |
| 15 | No Dashboard Caching | LOW | 0.5h | Low | — |

---

## Recommended Fix Priority

### Week 1 (Hackathon Final Day)
1. **Issue #2** (ImageExtractor thread-safety) — 3h
2. **Issue #1** (Claude API fallback) — 2h minimal implementation
3. **Issue #6** (Error tracking) — 2h
4. **Issue #7** (Integration tests) — 2h
→ **Total: 9 hours** (improves reliability + demo impression)

### Week 2 (Post-Hackathon)
1. **Issue #3** (Package structure) — 8h
2. **Issue #4** (Bounds config) — 2h
3. **Issue #5** (Real-time CO2) — 4h
4. **Issue #9** (Env validation) — 2h
→ **Total: 16 hours** (production readiness)

### Week 3+ (Scaling)
- Issue #10 (SQLite → PostgreSQL migration)
- Issue #12 (Structured logging)
- Issue #13 (API auth)
- Issue #15 (Caching)

---

For architecture context, see [ARCHITECTURE.md](ARCHITECTURE.md).
For field validation details, see [DATA_DICTIONARY.md](DATA_DICTIONARY.md).
For fix roadmap with timelines, see [ROADMAP.md](ROADMAP.md).
