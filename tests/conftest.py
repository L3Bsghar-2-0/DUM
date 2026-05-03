import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "extractor"))

DATA_DIR = Path(__file__).parent.parent / "data"
EXCEL_SAMPLE = DATA_DIR / "data tri gen" / "avril-report1_2442026.xlsx"
PDF_SAMPLE = DATA_DIR / "data factures et diverses" / "data 2.0.pdf"
IMAGE_SAMPLE = DATA_DIR / "data factures et diverses" / "WhatsApp Image 2026-04-27 at 21.39.16.jpeg"
