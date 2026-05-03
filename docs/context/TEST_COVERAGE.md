# TEST_COVERAGE.md — Current State & Recommendations

## Overview

This document summarizes test coverage across the codebase, identifies gaps, and provides recommendations for reaching >80% coverage on critical paths.

---

## Current Test Coverage Summary

### By Module

| Module | Test File | Tests | Coverage | Status | Gaps |
|--------|-----------|-------|----------|--------|------|
| **Extractor: Excel** | test_excel.py | 7 | ~85% | ✅ Good | Edge cases (corrupted headers) |
| **Extractor: PDF** | test_pdf.py | 3 | ~60% | ⚠️ Partial | Vision fallback not tested; regex patterns |
| **Extractor: Image** | test_image.py | 2 | ~40% | ❌ Poor | Thread-safety; concurrent access |
| **Extractor: Base** | test_base.py | 4 | ~70% | ✅ Good | Edge cases |
| **Normalizer** | test_normalizer.py | 5 | ~80% | ✅ Good | Unit conversion edge cases (0 input) |
| **Validator** | test_validator.py | 3 | ~50% | ⚠️ Weak | Bounds checking; confidence scoring logic |
| **CO2 Calculator** | test_co2.py | 4 | ~60% | ⚠️ Weak | Edge cases (null inputs, division by zero) |
| **Anomaly Detector** | test_anomaly.py | 6 | ~75% | ✅ Good | Edge cases (all same value, empty data) |
| **Database** | test_db.py | 2 | ~40% | ❌ Poor | Concurrent writes; rollback scenarios |
| **Pipeline** | test_pipeline.py | 1 | ~20% | ❌ Very Poor | Multi-file extraction; error recovery |
| **API / Endpoints** | test_api.py | 2 | ~30% | ❌ Poor | /extract endpoint; error responses |
| **Dashboard** | (none) | 0 | 0% | ❌ Missing | No unit tests for Streamlit app |
| **TOTAL** | 11 files | 39 tests | ~57% | ⚠️ Moderate | See gaps below |

---

## Critical Path Modules (Target >80%)

### Priority 1: Validator (test_validator.py)

**Current Coverage**: 50% — **TOO LOW**

**Why Critical**: Validator is gate between raw extraction and database; bugs here corrupt all downstream analysis

**Current Tests**:
- `test_bounds_checking()` — validates against hard-coded bounds
- `test_confidence_score_calculation()` — checks formula
- (missing: Edge cases, violation handling)

**Test Gaps**:
1. ❌ Null fields in confidence score calculation
2. ❌ Multiple violations (should reduce score by 0.1 each)
3. ❌ Critical field coverage scoring (9-field calculation)
4. ❌ Bounds violation with edge values (380V exactly, should pass)
5. ❌ Mixed valid + invalid fields in single record

**Recommended Tests** (add 5–6):
```python
def test_validator_null_field_handling():
    """Null fields should not count toward coverage"""
    result = ExtractionResult(puissance_brute_kw=1050)
    score = calculate_coverage(result)
    assert score == 1/9  # 1 of 9 critical fields

def test_validator_multiple_violations_reduce_score():
    """Each violation reduces score by 0.1"""
    # Create record with 2 out-of-bounds values
    # Expected: confidence = (7/9 × 100) - 20 = 57.8%

def test_validator_edge_values_pass():
    """Edge values (380V, 1400 kW) should pass bounds"""
    assert validate_bounds(voltage_v=380.0) == True
    assert validate_bounds(puissance_brute_kw=1400.0) == True

def test_validator_slightly_out_of_bounds():
    """Values just outside bounds should fail"""
    assert validate_bounds(voltage_v=379.9) == False
    assert validate_bounds(puissance_brute_kw=1400.1) == False
```

**Effort to Reach 80%**: 3–4 hours (5–6 new tests)

---

### Priority 2: CO2 Calculator (test_co2.py)

**Current Coverage**: 60% — **BELOW TARGET**

**Why Critical**: CO2 is key output metric; errors here mislead stakeholders

**Current Tests**:
- `test_co2_from_electricity()` — basic electricity path
- `test_co2_from_gas()` — basic gas path
- (missing: Edge cases, null handling)

**Test Gaps**:
1. ❌ Null electricity or gas (should handle gracefully)
2. ❌ Division by zero (PCI = 0?)
3. ❌ Negative values (should error)
4. ❌ Very large values (overflow?)
5. ❌ Mixed null + valid (partial CO2 calc)

**Recommended Tests** (add 4–5):
```python
def test_co2_null_electricity():
    """If electricity null, only gas CO2 calculated"""
    result = estimate_co2(puissance_brute_kw=None, gaz_volume_nm3=100)
    assert result.co2_from_electricity_kg == 0
    assert result.co2_from_gas_kg == 100 × 0.202

def test_co2_both_null():
    """If both null, CO2 = 0"""
    result = estimate_co2(puissance_brute_kw=None, gaz_volume_nm3=None)
    assert result.co2_kg == 0

def test_co2_negative_values_error():
    """Negative power/gas should raise error"""
    with pytest.raises(ValueError):
        estimate_co2(puissance_brute_kw=-100, gaz_volume_nm3=50)

def test_co2_very_large_values():
    """Should handle 10,000+ kW without overflow"""
    result = estimate_co2(puissance_brute_kw=10000, gaz_volume_nm3=1000)
    assert result.co2_kg > 0  # Should not crash
```

**Effort to Reach 80%**: 2–3 hours (4–5 new tests)

---

### Priority 3: Database Operations (test_db.py)

**Current Coverage**: 40% — **VERY LOW**

**Why Critical**: Database is single source of truth; write errors are silent disasters

**Current Tests**:
- `test_db_insert()` — basic row insert
- (missing: Concurrent writes, rollback, constraints)

**Test Gaps**:
1. ❌ Concurrent writes (two clients writing simultaneously)
2. ❌ Transaction rollback on error
3. ❌ Duplicate record handling (unique constraints)
4. ❌ Index performance (query on (source_file, timestamp))
5. ❌ Database file corruption recovery

**Recommended Tests** (add 6–7):
```python
def test_db_concurrent_writes():
    """Two threads inserting simultaneously should not corrupt DB"""
    import threading
    results = []
    
    def write_records(records):
        write_records_to_db(records)
        results.append("OK")
    
    t1 = threading.Thread(target=write_records, args=(records_1,))
    t2 = threading.Thread(target=write_records, args=(records_2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    # Verify all records persisted
    assert count_records() == len(records_1) + len(records_2)

def test_db_transaction_rollback():
    """If insert fails midway, earlier inserts should roll back"""
    try:
        write_records([valid_record, invalid_record])  # invalid_record causes error
    except:
        pass
    
    # Count should be 0 (transaction rolled back)
    assert count_records() == 0

def test_db_query_performance():
    """Queries on indexed columns should be fast (<100ms)"""
    insert_1000_records()
    
    start = time.time()
    results = query_by_source_and_date("excel", "2026-05-01")
    elapsed = time.time() - start
    
    assert elapsed < 0.1  # 100ms threshold
```

**Effort to Reach 80%**: 4–5 hours (6–7 new tests + concurrency setup)

---

## Secondary Modules (Target >70%)

### Image Extractor (test_image.py)

**Current Coverage**: 40%

**Key Missing Tests**:
- Concurrent OCR requests (thread-safety issue; see [PROBLEMS.md#Issue-2](PROBLEMS.md#Issue-#2-ImageExtractor-Thread-Safety))
- Large image handling (>10MB)
- Corrupted image handling (invalid JPEG)

**Effort**: 3 hours (5–6 new tests + thread-safety fix)

---

### API Endpoints (test_api.py)

**Current Coverage**: 30%

**Key Missing Tests**:
- `POST /extract` with file upload (multipart form)
- Error responses (400, 500 codes)
- Concurrent requests to /extract (same issue as Image Extractor)
- Query parameters validation

**Effort**: 3 hours (5–6 new integration tests)

---

### Database Transactions (test_db.py)

**Current Coverage**: 40%

**Key Missing Tests**:
- `update_anomaly_flags()` — flag updates
- Concurrent read + write access
- SQLite WAL mode behavior

**Effort**: 2 hours (3–4 new tests)

---

## Missing Coverage Areas

### Dashboard (test_dashboard or test_streamlit.py) — 0% Coverage

**Status**: No unit tests; Streamlit testing requires `streamlit.testing.v1` (new in 1.27+)

**Recommended Approach**:
1. Extract dashboard logic into testable functions (2 hours)
2. Write tests for:
   - `load_records()` — database query
   - `filter_by_date()` — date range filtering
   - `calculate_kpis()` — KPI computation

**Effort**: 5–6 hours

---

### Pipeline Orchestration (test_pipeline.py) — 20% Coverage

**Status**: Only tests Excel count; missing integration scenarios

**Key Missing Tests**:
1. ❌ Multi-file extraction (Excel + PDF + image in one run)
2. ❌ Error recovery (skip corrupted file, continue)
3. ❌ Cold-start db-init sequence
4. ❌ Concurrent /extract requests during db-init

**Effort**: 5–6 hours (add 6–8 integration tests)

---

## Test Infrastructure Improvements

### Add pytest Coverage Reporting

```bash
# Install
pip install pytest-cov

# Run with coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html
```

**Target**: >80% on critical modules (validator, co2, db, pipeline)

---

### Add Concurrent Testing

```python
# Add pytest-asyncio for async tests
pip install pytest-asyncio

# Test concurrent requests
@pytest.mark.asyncio
async def test_concurrent_extract_requests():
    client = TestClient(app)
    tasks = [
        asyncio.create_task(client.post("/extract", files=[("file", image1)])),
        asyncio.create_task(client.post("/extract", files=[("file", image2)])),
    ]
    results = await asyncio.gather(*tasks)
    assert all(r.status_code == 200 for r in results)
```

---

### Add Mock Fixtures

```python
# tests/conftest.py
@pytest.fixture
def mock_easyocr_reader():
    """Mock EasyOCR to avoid slow model loading"""
    with patch("image.easyocr.Reader") as mock:
        yield mock

@pytest.fixture
def sample_energy_record():
    """Create valid test record"""
    return ExtractionResult(
        source_file="test.xlsx",
        puissance_brute_kw=1050.5,
        gaz_volume_nm3=125.3,
        # ... other fields
    )
```

---

## Coverage Target Timeline

### Week 1 (Hackathon Final)
- **Validator**: 50% → 80% (+4 hours)
- **CO2**: 60% → 80% (+3 hours)
- **Total**: 7 hours effort; **projected to 75% overall coverage**

### Week 2
- **Database**: 40% → 85% (+5 hours)
- **Pipeline**: 20% → 70% (+6 hours)
- **API**: 30% → 75% (+4 hours)
- **Total**: 15 hours effort; **projected to 82% overall coverage**

### Week 3
- **Dashboard**: 0% → 60% (+6 hours)
- **Image Extractor**: 40% → 80% (+3 hours)
- **Overall**: >80% coverage achieved ✅

---

## Coverage Metrics to Track

### By Module

```
validator:      50% → 80%  (Critical path priority)
co2:            60% → 80%
db:             40% → 85%
pipeline:       20% → 70%
normalizer:     80% → 85%
anomaly:        75% → 85%
api:            30% → 75%
dashboard:       0% → 60%
image_extractor:40% → 80%
total:          57% → 80%+
```

### By Category

- **Unit Tests**: >80% on all modules
- **Integration Tests**: >60% (pipeline, API)
- **Concurrency Tests**: >50% (image extraction, database)
- **Edge Cases**: >70% (null handling, bounds, division by zero)

---

## Continuous Integration Setup (Optional)

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test & Coverage

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt pytest pytest-cov
      - run: pytest tests/ --cov=src --cov-report=xml --cov-fail-under=75
      - uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

**Benefit**: Auto-run tests on every PR; blocks merge if coverage drops

---

## Summary

| Phase | Target Coverage | Effort | Timeline |
|-------|-----------------|--------|----------|
| **Week 1** | 75% (validator, co2) | 7h | Final hackathon day |
| **Week 2** | 82% (add db, pipeline) | 15h | Post-hackathon |
| **Week 3** | 85%+ (add dashboard, edge cases) | 20h | Maintenance sprint |

**Immediate Action**: Add 4 validator tests + 4 CO2 tests (7 hours) to reach 75% coverage on critical paths.

---

For identified test gaps, see [PROBLEMS.md#Issue-7](PROBLEMS.md#Issue-#7-Missing-Multi-File-Pipeline-Tests).
For testing setup instructions, see [QUICKSTART.md](QUICKSTART.md).
