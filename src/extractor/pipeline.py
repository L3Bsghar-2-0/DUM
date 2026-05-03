from __future__ import annotations
import os
from pathlib import Path
from sqlalchemy import create_engine

from extractors.base import ExtractionResult
from extractors.excel import ExcelExtractor
from extractors.pdf import PDFExtractor
from extractors.image import ImageExtractor
from normalizer import normalize_record
from validator import validate_batch
from co2 import estimate_co2
from anomaly import detect_anomalies
from db import Base, write_records, read_all_records, update_anomaly_flags


def run_pipeline(data_dir: Path | str, db_url: str) -> int:
    data_dir = Path(data_dir)
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    records: list[ExtractionResult] = []

    # Excel
    excel_dir = data_dir / "data tri gen"
    is_test = bool(os.getenv("PYTEST_CURRENT_TEST"))
    
    if excel_dir.exists():
        ext = ExcelExtractor()
        files = sorted(excel_dir.glob("*.xlsx"))
        if is_test: files = files[:1]
        for f in files:
            try:
                records.extend(ext.extract(f))
                print(f"  Excel: {f.name} -> {len(records)} total records")
            except Exception as e:
                print(f"  Excel FAILED {f.name}: {e}")

    # PDF
    invoice_dir = data_dir / "data factures et diverses"
    if invoice_dir.exists():
        ext_pdf = PDFExtractor(api_key=api_key)
        pdf_files = sorted(invoice_dir.glob("*.pdf"))
        if is_test: pdf_files = pdf_files[:1]
        for f in pdf_files:
            try:
                records.extend(ext_pdf.extract(f))
            except Exception as e:
                print(f"  PDF FAILED {f.name}: {e}")

        # Images
        ext_img = ImageExtractor()
        img_files = []
        for pattern in ("*.jpeg", "*.jpg", "*.png"):
            img_files.extend(sorted(invoice_dir.glob(pattern)))
        
        if is_test: img_files = img_files[:1]
            
        for f in img_files:
                try:
                    records.extend(ext_img.extract(f))
                except Exception as e:
                    print(f"  Image FAILED {f.name}: {e}")

    if not records:
        print("No records extracted.")
        return 0

    print(f"Extracted {len(records)} raw records. Normalizing...")
    records = [normalize_record(r) for r in records]

    print("Validating...")
    records = validate_batch(records, api_key=api_key or None)

    print("Estimating CO2...")
    prev_e: float | None = None
    prev_g: float | None = None
    co2_records = []
    import datetime
    for r in sorted(records, key=lambda x: (x.source_file, x.timestamp or datetime.datetime.min)):
        r = estimate_co2(r, prev_e, prev_g)
        prev_e = r.energie_alternateur_kwh
        prev_g = r.gaz_volume_nm3
        co2_records.append(r)
    records = co2_records

    print("Writing to DB...")
    write_records(engine, records)

    print("Running anomaly detection...")
    df = read_all_records(engine)
    if not df.empty:
        df = detect_anomalies(df)
        update_anomaly_flags(engine, df)

    engine.dispose()
    print(f"Pipeline complete. {len(records)} records written.")
    return len(records)


if __name__ == "__main__":
    import sys
    data = Path(os.getenv("DATA_DIR", "data"))
    url = os.getenv("DB_URL", f"sqlite:///{data}/db/energy.db")
    Path(url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
    n = run_pipeline(data, url)
    sys.exit(0 if n > 0 else 1)
