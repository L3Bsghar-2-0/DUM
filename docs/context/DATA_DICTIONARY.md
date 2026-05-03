# DATA_DICTIONARY.md — Complete Field Reference (73 Fields)

## Overview

This document describes all 73 fields in the `ExtractionResult` Pydantic model. Fields are organized by subsystem and include:
- **Unit**: Measurement unit (kWh, kW, V, %, etc.)
- **Typical Range**: Expected values during normal operation
- **Validation Bound**: Physical limit enforced by validator.py
- **Coverage**: Is this field critical for "complete" record? (9 critical fields)
- **Source**: Primary extractor (Excel, PDF, OCR, or calculated)

---

## Critical Coverage Fields (9 total)

These 9 fields determine the **Coverage Score** used for confidence estimation:

```
Coverage Score = (# non-null critical fields / 9) × 100%
Confidence Score = Coverage Score - (violations × 0.1)
```

**Critical Fields**:
1. `gaz_volume_nm3` — Gas consumption
2. `gaz_debit_nm3h` — Gas flow rate
3. `puissance_brute_kw` — Gross electrical power
4. `energie_alternateur_kwh` — Cumulative electricity production
5. `eg_puissance_kw` — Heating power
6. `ec_recup_puissance_kw` — Chilled water recovery power
7. `steg_achat_kwh` — Grid import (electricity purchased)
8. `steg_vente_kwh` — Grid export (electricity sold)
9. `production_positive_kwh` — Self-generated positive power

---

## Field Catalog

### 1. Metadata Fields (6 fields)

| Field | Type | Unit | Source | Typical Range | Notes |
|-------|------|------|--------|---------------|-------|
| `source_file` | str | — | FastAPI | "energy_202605.xlsx" | File name/type; set by extractor |
| `source_type` | str | — | FastAPI | "excel" \| "pdf" \| "image" | Extractor used |
| `timestamp` | datetime | — | Excel/PDF | 2026-05-01 to 2026-05-31 | Record time; parsed from column/invoice date |
| `confidence_score` | float | % | Validator | 0.0–100.0 | Coverage × (1 - violations) |
| `is_anomaly` | bool | — | Anomaly | True \| False | Set by detect_anomalies() |
| `anomaly_type` | str | — | Anomaly | "spike" \| "stuck_sensor" \| "dropout" \| "iqr_outlier" \| "isolation_forest" | Primary detection method triggered |

---

### 2. Gas Subsystem (2 fields) — CRITICAL ✓

| Field | Type | Unit | Bounds | Typical | Notes |
|-------|------|------|--------|---------|-------|
| `gaz_volume_nm3` | float | Nm³ | 0.0–500.0 | 100–200 | Daily gas consumption (normal cubic meters); **CRITICAL** |
| `gaz_debit_nm3h` | float | Nm³/h | 0.0–50.0 | 5–15 | Instantaneous gas flow rate; **CRITICAL** |

**Conversion**:
- Nm³ → kWh: `gaz_volume_nm3 × PCI (9.082) × conversion_factor (0.2778)`
- PCI (Pouvoir Calorifique Inférieur): Lower heating value = 9.082 thermie/Nm³

**Dependencies**:
- `gaz_debit_nm3h` calculated if missing: `gaz_volume_nm3 / interval_hours`

---

### 3. Electrical Subsystem (12 fields) — CRITICAL (2/12) ✓

#### 3a. Gross Power & Energy

| Field | Type | Unit | Bounds | Typical | Notes |
|-------|------|------|--------|---------|-------|
| `puissance_brute_kw` | float | kW | 800.0–1,400.0 | 1,050–1,150 | Gross electrical power output; **CRITICAL** |
| `energie_alternateur_kwh` | float | kWh | 0.0–∞ (cumulative) | 1,000–5,000 | Cumulative electricity produced; **CRITICAL** |

#### 3b. Voltage & Current (3-phase grid)

| Field | Type | Unit | Bounds | Typical | Notes |
|-------|------|------|--------|---------|-------|
| `voltage_v` | float | V | 380.0–440.0 | 400 | 3-phase line voltage |
| `courant_phase_1_a` | float | A | 0.0–1,000.0 | 400–600 | Phase 1 current |
| `courant_phase_2_a` | float | A | 0.0–1,000.0 | 400–600 | Phase 2 current |
| `courant_phase_3_a` | float | A | 0.0–1,000.0 | 400–600 | Phase 3 current |

#### 3c. Power Quality & Efficiency

| Field | Type | Unit | Bounds | Typical | Notes |
|-------|------|------|--------|---------|-------|
| `factor_puissance` | float | ratio | 0.8–1.0 | 0.95–0.98 | Power factor (cos φ); default 1.0 if missing |
| `puissance_reactive_kvar` | float | kVAR | 0.0–500.0 | 50–150 | Reactive power (usually calculated from P, Q, S) |
| `puissance_apparente_kva` | float | kVA | 800.0–1,500.0 | 1,100–1,200 | Apparent power (S = sqrt(P² + Q²)) |

---

### 4. Thermal Subsystem (50+ fields) — CRITICAL (2/50+) ✓

Tri-generation system produces 5 types of thermal energy. Each subsystem has ~10 fields:

#### 4a. EG (Électrogénie / Electricity-based heating) — CRITICAL (1/10) ✓

| Field | Type | Unit | Bounds | Typical | Notes |
|-------|------|------|--------|---------|-------|
| `eg_puissance_kw` | float | kW | 0.0–500.0 | 50–200 | Heat power output; **CRITICAL** |
| `eg_energie_kwh` | float | kWh | 0.0–∞ (cumulative) | 200–1,000 | Cumulative heat energy |
| `eg_temp_entree_c` | float | °C | 0.0–100.0 | 40–70 | Inlet water temperature |
| `eg_temp_sortie_c` | float | °C | 0.0–100.0 | 50–80 | Outlet water temperature |
| `eg_debit_m3h` | float | m³/h | 0.0–100.0 | 10–40 | Flow rate |
| `eg_rendement_pct` | float | % | 30.0–90.0 | 70–85 | Efficiency |
| `eg_co2_kg` | float | kg | 0.0–1,000.0 | — | Calculated: energy × 0.202 factor |

#### 4b. EC Récuperation (Chilled water recovery) — CRITICAL (1/10) ✓

| Field | Type | Unit | Bounds | Typical | Notes |
|-------|------|------|--------|---------|-------|
| `ec_recup_puissance_kw` | float | kW | 0.0–300.0 | 20–100 | Recovered chilled water power; **CRITICAL** |
| `ec_recup_energie_kwh` | float | kWh | 0.0–∞ (cumulative) | 100–500 | Cumulative recovery energy |
| `ec_recup_temp_entree_c` | float | °C | 0.0–50.0 | 5–15 | Inlet temperature |
| `ec_recup_temp_sortie_c` | float | °C | 0.0–50.0 | 2–10 | Outlet temperature |
| `ec_recup_debit_m3h` | float | m³/h | 0.0–50.0 | 5–25 | Flow rate |

#### 4c. EC Alpha Sanitary (Hot water supply)

| Field | Type | Unit | Bounds | Typical | Notes |
|-------|------|------|--------|---------|-------|
| `ec_alpha_sani_puissance_kw` | float | kW | 0.0–100.0 | 10–40 | Sanitary hot water power |
| `ec_alpha_sani_temp_entree_c` | float | °C | 0.0–100.0 | 40–60 | Inlet |
| `ec_alpha_sani_temp_sortie_c` | float | °C | 0.0–100.0 | 50–70 | Outlet |
| `ec_alpha_sani_debit_m3h` | float | m³/h | 0.0–20.0 | 2–8 | Flow rate |

#### 4d. EC Alpha (Process water heating)

| Field | Type | Unit | Bounds | Typical | Notes |
|-------|------|------|--------|---------|-------|
| `ec_alpha_puissance_kw` | float | kW | 0.0–200.0 | 30–80 | Process water heating power |
| `ec_alpha_temp_entree_c` | float | °C | 0.0–100.0 | 40–70 | Inlet |
| `ec_alpha_temp_sortie_c` | float | °C | 0.0–100.0 | 50–80 | Outlet |
| `ec_alpha_debit_m3h` | float | m³/h | 0.0–50.0 | 5–20 | Flow rate |

#### 4e. EC Gamma (Chilled water production)

| Field | Type | Unit | Bounds | Typical | Notes |
|-------|------|------|--------|---------|-------|
| `ec_gamma_puissance_kw` | float | kW | 0.0–300.0 | 50–150 | Chilled water power |
| `ec_gamma_temp_entree_c` | float | °C | 0.0–50.0 | 15–25 | Inlet (warm return) |
| `ec_gamma_temp_sortie_c` | float | °C | 0.0–50.0 | 5–15 | Outlet (cold supply) |
| `ec_gamma_debit_m3h` | float | m³/h | 0.0–100.0 | 20–60 | Flow rate |

**Note**: Each thermal subsystem follows pattern:
```
Power (kW) = debit (m³/h) × (temp_sortie - temp_entree) × specific_heat_water
Energy = cumulative(Power)
Efficiency = useful_output / heat_input
```

---

### 5. Efficiency Metrics (3 fields)

| Field | Type | Unit | Bounds | Typical | Notes |
|-------|------|------|--------|---------|-------|
| `rendement_electrique_pct` | float | % | 30.0–90.0 | 60–75 | Electrical efficiency (E_out / E_in) |
| `rendement_thermique_pct` | float | % | 30.0–90.0 | 70–85 | Thermal efficiency (Heat_out / Heat_in) |
| `rendement_total_pct` | float | % | 30.0–90.0 | 50–70 | Combined (Elec + Thermal / Total input) |

**Calculation**:
```
rendement_total_pct = (puissance_brute_kw + eg_puissance_kw + ec_gamma_puissance_kw) 
                     / (gaz_volume_nm3 × PCI × conversion_factor)
                     × 100
```

---

### 6. Grid Connection (5 fields) — CRITICAL (2/5) ✓

| Field | Type | Unit | Bounds | Typical | Notes |
|-------|------|------|--------|---------|-------|
| `steg_achat_kwh` | float | kWh | 0.0–∞ (cumulative) | 500–2,000 | Grid import (electricity purchased); **CRITICAL** |
| `steg_vente_kwh` | float | kWh | 0.0–∞ (cumulative) | 100–1,000 | Grid export (electricity sold); **CRITICAL** |
| `production_positive_kwh` | float | kWh | 0.0–∞ (cumulative) | 1,000–5,000 | Self-generated positive power; **CRITICAL** |
| `production_negative_kwh` | float | kWh | 0.0–∞ (cumulative) | 0–200 | Reverse flow (rare) |
| `net_production_kwh` | float | kWh | −∞ to +∞ | 500–4,000 | Net: production_positive - steg_achat + steg_vente |

**Note**: Cumulative counters; only differences between readings are meaningful for flow calculations.

---

### 7. Calculated Fields (4 fields)

| Field | Type | Unit | Bounds | Calculation | Notes |
|-------|------|------|--------|------------|-------|
| `co2_kg` | float | kg | 0.0–10,000.0 | `(puissance_brute_kw × 0.267) + (gaz_volume_nm3 × 0.202)` | Total CO2 emissions |
| `co2_from_electricity_kg` | float | kg | 0.0–5,000.0 | `puissance_brute_kw × 0.267` | Electricity contribution |
| `co2_from_gas_kg` | float | kg | 0.0–5,000.0 | `gaz_volume_nm3 × 0.202` | Gas contribution |
| `total_thermal_power_kw` | float | kW | 0.0–1,000.0 | `eg_puissance_kw + ec_recup_puissance_kw + ec_alpha_sani_puissance_kw + ec_alpha_puissance_kw + ec_gamma_puissance_kw` | Sum of all thermal outputs |

---

## Validation Bounds Summary

### Physical Limits (Enforced in validator.py)

```python
VALIDATION_BOUNDS = {
    "voltage_v": (380.0, 440.0),
    "puissance_brute_kw": (800.0, 1400.0),
    "gaz_volume_nm3": (0.0, 500.0),
    "gaz_debit_nm3h": (0.0, 50.0),
    "rendement_total_pct": (30.0, 90.0),
    "temperature": (0.0, 100.0),  # All temp fields
    "factor_puissance": (0.8, 1.0),
}
```

**Violation Handling**:
- Out-of-bounds value → logged as warning
- Confidence Score reduced by 0.1 per violation
- Record **NOT deleted**; flagged for manual review

---

## Unit Conversion Reference

### Energy Conversions (to kWh)

| From | To kWh | Factor | Example |
|------|--------|--------|---------|
| Nm³ (gas) | kWh | 9.082 × 0.2778 | 100 Nm³ = 252.3 kWh |
| GJ | kWh | 277.78 | 10 GJ = 2,777.8 kWh |
| Gcal | kWh | 1,163.0 | 1 Gcal = 1,163.0 kWh |
| MWh | kWh | 1,000 | 1 MWh = 1,000 kWh |
| kWh | kWh | 1.0 | — |
| J | kWh | 2.778 × 10⁻⁷ | — |
| cal | kWh | 1.163 × 10⁻⁶ | — |

**Note**: Normalizer.py applies these conversions automatically based on detected unit in header.

---

## Data Quality Scoring

### Confidence Score Calculation

```
score = (critical_fields_non_null / 9) × 100
      - (bounds_violations × 10)
      - (conversion_errors × 5)

Final Score = min(max(score, 0.0), 100.0)
```

**Examples**:
- All 9 critical fields present, no violations → **100%** confidence
- 7/9 critical fields, 1 violation → **(7/9 × 100) - 10 = 67.8%** confidence
- 5/9 critical fields, 2 violations → **(5/9 × 100) - 20 = 35.6%** confidence

### Coverage by Source

| Source | Typical Coverage | Strengths | Weaknesses |
|--------|------------------|-----------|-----------|
| **Excel** | 85–95% | All 73 fields available in structured format | Requires precise header matching; wide-format hard to parse |
| **PDF** | 40–60% | Invoice structure predictable | Text extraction variable; no thermal subsystem data |
| **OCR Image** | 20–50% | Flexible handwritten data capture | Very high error rate; low confidence |

---

## Field Dependencies

### Must Not Both Be Non-Null

Some fields are mutually exclusive or redundant:

| Field A | Field B | Reason |
|---------|---------|--------|
| `gaz_volume_nm3` | `gaz_debit_nm3h` | If both present, debit should match volume / interval |
| `temperature` fields | `puissance_kw` | If T-delta is zero, power should be zero |
| `production_positive_kwh` | `steg_achat_kwh` | Simultaneous generation + import = net export |

**Validation**: Logical consistency checks in validator.py (currently basic; could expand).

---

## Missing Data Handling

| Scenario | Behavior |
|----------|----------|
| Field completely missing from source | Set to `None` (Pydantic Optional[float]) |
| Field present but unparseable (e.g., "N/A", "—") | Set to `None`; log warning |
| Field zero but physically impossible (e.g., power = 0 kW during operation) | Flag as anomaly (stuck_sensor likely) |
| Field negative (e.g., negative temperature) | Flag as violation; log error |
| Field out-of-bounds (e.g., voltage > 500V) | Flag as violation; reduce confidence; **keep record** |

---

## Normalization Examples

### Example 1: Excel → Standard Units
```
Input (Excel column):
  Energy: 5 GJ (column header "Énergie (GJ)")
  
Normalizer detects: "GJ" unit
  
Output (ExtractionResult):
  energie_alternateur_kwh = 5 × 277.78 = 1,388.9 kWh
```

### Example 2: PDF → Coverage
```
Input (PDF invoice):
  Total consumption: 250 Nm³ (gas)
  Grid purchase: 1,500 kWh
  
Extractors populate:
  gaz_volume_nm3 = 250 ✓
  steg_achat_kwh = 1,500 ✓
  (all other fields = None)
  
Coverage = 2/9 = 22% → Low confidence (0.22)
```

### Example 3: OCR → Warnings
```
Input (OCR of handwritten sheet):
  "Puissance Brute: 1,O50 kW" (1,O50 = OCR error for 1,050)
  
OCR Confidence: 0.73
Parser attempts float("1,O50") → ValueError
  
Output:
  puissance_brute_kw = None
  extraction_warnings = ["ocr_parse_error_puissance_brute"]
  confidence_score -= 5
```

---

## Common Issues & Resolution

### Issue: Confusion between cumulative vs. instantaneous fields
**Rule**: Fields ending with `_kwh`, `_m3`, `_debit_kwh` are cumulative or rates.
Fields with `_puissance_kw` are instantaneous power.

### Issue: Temperature out-of-bounds (e.g., 150°C outlet)
**Possible Causes**:
1. Sensor fault (stuck value)
2. Extreme operating mode (rare)
3. OCR/parsing error (wrong decimal place)

**Resolution**: Check context; if puissance_kw is also abnormal, likely sensor fault (anomaly flag).

### Issue: Missing critical fields
**Impact**: Coverage score drops; confidence low; record may be unusable for trend analysis.
**Mitigation**: Ensure Excel sheets have all 73 expected columns; pre-populate PDF templates.

---

For detailed anomaly detection methods applied to these fields, see [PROBLEMS.md](PROBLEMS.md#Anomaly-Detection-Gaps).
For validation logic, see [ARCHITECTURE.md](ARCHITECTURE.md#Extractor-Modules).
For deployment & data loading, see [QUICKSTART.md](QUICKSTART.md).
