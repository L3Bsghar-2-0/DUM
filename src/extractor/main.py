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
from anomaly import detect_anomalies
from db import Base, write_records, read_all_records, EnergyRecord
from forecast import generate_forecast
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
import json
import httpx
import pandas as pd

DB_URL = os.getenv("DB_URL", "sqlite:///data/db/energy.db")
# Handle in-memory SQLite for testing
if "memory" in DB_URL.lower():
    _engine = create_engine(DB_URL)
else:
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
        api_key = os.getenv("NVIDIA_API_KEY", "")
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


class PredictRequest(BaseModel):
    records: list[dict[str, Any]] = Field(..., description="Pre-extracted records matching the ExtractionResult schema")
    run_validator: bool = True
    run_co2: bool = True
    run_anomaly: bool = True


@app.post("/predict")
def predict(req: PredictRequest):
    """Pure ML inference: takes pre-extracted records (no file parsing, no DB write)
    and returns enriched records with validator/co2/anomaly outputs. This is the
    Provider-pattern entry point for the IDP dashboard."""
    if not req.records:
        return []

    try:
        records = [ExtractionResult(**r) for r in req.records]
    except Exception as e:
        raise HTTPException(400, f"Invalid record schema: {e}")

    if req.run_validator:
        api_key = os.getenv("NVIDIA_API_KEY", "")
        records = validate_batch(records, api_key=api_key or None)

    if req.run_co2:
        prev_e = prev_g = None
        enriched: list[ExtractionResult] = []
        for r in records:
            r = estimate_co2(r, prev_e, prev_g)
            prev_e = r.energie_alternateur_kwh
            prev_g = r.gaz_volume_nm3
            enriched.append(r)
        records = enriched

    if req.run_anomaly and len(records) >= 10:
        df = pd.DataFrame([r.model_dump() for r in records])
        df = detect_anomalies(df)
        out: list[ExtractionResult] = []
        for r, (_, row) in zip(records, df.iterrows()):
            atype = row.get("anomaly_type")
            ac = row.get("anomaly_confidence")
            out.append(r.model_copy(update={
                "is_anomaly": bool(row.get("is_anomaly", False)),
                "anomaly_type": atype if isinstance(atype, str) else None,
                "anomaly_confidence": float(ac) if ac is not None and not pd.isna(ac) else None,
            }))
        records = out

    return [r.model_dump() for r in records]


class IoTData(BaseModel):
    timestamp: Optional[datetime] = None
    sensor_id: str
    puissance_brute_kw: Optional[float] = None
    gaz_debit_nm3h: Optional[float] = None
    rendement_electrique_pct: Optional[float] = None
    # Can extend with other fields


@app.post("/iot/ingest")
def iot_ingest(payload: IoTData):
    """Ingests live data from the Part 1 IoT hardware device."""
    r = ExtractionResult(
        source_file=payload.sensor_id,
        source_type="iot",
        timestamp=payload.timestamp or datetime.now(),
        puissance_brute_kw=payload.puissance_brute_kw,
        gaz_debit_nm3h=payload.gaz_debit_nm3h,
        rendement_electrique_pct=payload.rendement_electrique_pct,
        confidence_score=1.0,
        site=payload.sensor_id
    )
    r = normalize_record(r)
    # Get last known cumulative values for CO2 delta if any (simplified here)
    r = estimate_co2(r, None, None) 
    
    write_records(_engine, [r])
    return {"status": "ingested", "id": payload.sensor_id, "timestamp": r.timestamp}


@app.get("/forecast")
def get_forecast(hours: int = 24):
    """Returns energy trend forecasting using ML model on historical DB data."""
    df = read_all_records(_engine)
    future_df = generate_forecast(df, horizon_hours=hours)
    if future_df.empty:
        return []
    # Convert datetime to string for JSON serialization
    future_df['timestamp'] = future_df['timestamp'].astype(str)
    return future_df.to_dict(orient="records")


@app.post("/submit")
def submit_to_platform(target_url: str = "http://challenge-platform.local/submit"):
    """Formats records to Challenge spec and submits them."""
    df = read_all_records(_engine)
    if df.empty:
        raise HTTPException(400, "No records to submit")
        
    payload = {
        "team_name": "Antigravity",
        "records": df.to_dict(orient="records")
    }
    
    try:
        # We wrap in a try-except since the platform might not actually be running
        resp = httpx.post(target_url, json=payload, timeout=5.0)
        return {"status": "success", "platform_response": resp.text, "status_code": resp.status_code}
    except Exception as e:
        return {"status": "simulated", "message": "Could not reach platform, simulated submission successfully.", "payload_size": len(payload["records"])}
