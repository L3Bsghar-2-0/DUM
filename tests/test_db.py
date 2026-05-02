import tempfile
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine
from db import Base, EnergyRecord, write_records, read_all_records, update_anomaly_flags
from extractors.base import ExtractionResult


def _engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_write_and_read_records():
    engine = _engine()
    records = [
        ExtractionResult(
            timestamp=datetime(2026, 4, 1, 0, 0),
            source_file="test.xlsx",
            source_type="excel",
            puissance_brute_kw=1199.0,
            gaz_debit_nm3h=272.76,
            confidence_score=0.9,
        )
    ]
    write_records(engine, records)
    df = read_all_records(engine)
    assert len(df) == 1
    assert df.iloc[0]['source_file'] == "test.xlsx"
    assert abs(df.iloc[0]['puissance_brute_kw'] - 1199.0) < 0.01


def test_write_multiple_files():
    engine = _engine()
    records = [
        ExtractionResult(source_file="a.xlsx", source_type="excel", puissance_brute_kw=1200.0),
        ExtractionResult(source_file="b.pdf", source_type="pdf", steg_achat_kwh=500.0),
    ]
    write_records(engine, records)
    df = read_all_records(engine)
    assert len(df) == 2


def test_update_anomaly_flags():
    import pandas as pd
    engine = _engine()
    records = [ExtractionResult(source_file="f.xlsx", source_type="excel")]
    write_records(engine, records)
    df = read_all_records(engine)
    df['is_anomaly'] = True
    df['anomaly_type'] = 'zscore_spike'
    update_anomaly_flags(engine, df)
    df2 = read_all_records(engine)
    assert df2.iloc[0]['is_anomaly'] == True


def test_extraction_warnings_serialized():
    engine = _engine()
    records = [ExtractionResult(
        source_file="f.xlsx", source_type="excel",
        extraction_warnings=["voltage_out_of_range: 500"]
    )]
    write_records(engine, records)
    df = read_all_records(engine)
    warnings = json.loads(df.iloc[0]['extraction_warnings'])
    assert "voltage_out_of_range: 500" in warnings
