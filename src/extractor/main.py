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
