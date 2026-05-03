# QUICKSTART.md — Local Development & Deployment

## Overview

This guide helps developers set up the Energy Pipeline system locally, run tests, start services, and deploy to production.

---

## Prerequisites

### System Requirements

- **OS**: macOS, Linux, or Windows (WSL2)
- **Docker**: 20.10+ (install from [docker.com](https://www.docker.com))
- **Python**: 3.9+ (for local dev without Docker)
- **Git**: For cloning repo

### Check Installation

```bash
docker --version  # Docker 20.10+
docker-compose --version  # Docker Compose 1.29+
python --version  # Python 3.13
```

---

## 1. Local Development Setup (Without Docker)

### 1a. Clone Repository & Set Up Virtual Environment

```bash
# Clone repo
git clone https://github.com/your-org/energy-pipeline.git
cd energy-pipeline

# Create virtual environment
python -m venv venv

# Activate venv
source venv/bin/activate          # macOS/Linux
# or
venv\Scripts\activate             # Windows
```

### 1b. Install Dependencies

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install dev dependencies (optional, for testing)
pip install pytest pytest-cov pytest-mock
```

### 1c. Download EasyOCR Models (One-time)

```bash
# Pre-download OCR models to avoid timeout on first use
python -c "import easyocr; reader = easyocr.Reader(['fr', 'en'])"
# This takes ~5 minutes on first run; models cached locally
```

### 1d. Create Database & Data Directories

```bash
mkdir -p data/
mkdir -p input_files/  # For test data
```

---

## 2. Running Locally Without Docker

### 2a. Run Extractor API

```bash
# Start FastAPI server (port 8000)
uvicorn src.extractor.main:app --reload --host 0.0.0.0 --port 8000
```

Output:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     API docs: http://localhost:8000/docs
```

### 2b. Run Streamlit Dashboard (in new terminal)

```bash
# Activate venv (if needed)
source venv/bin/activate

# Start Streamlit app (port 8501)
streamlit run src/dashboard/app.py
```

Output:
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

**Visit**: [http://localhost:8501](http://localhost:8501) in browser

---

## 3. Running with Docker (Recommended)

### 3a. Build & Start Services

```bash
# Build images & start services (first time: ~10 minutes)
docker-compose up --build

# Run in background
docker-compose up -d --build
```

**Waiting for startup**:
```
extractor     | INFO: Application startup complete
extractor     | INFO: Uvicorn running on http://0.0.0.0:8000
db-init       | Processing input files...
db-init       | Extracted 250 records from energy_202605.xlsx
db-init       | Inserted 240 records into database (10 skipped due to validation errors)
dashboard     | You can now view your Streamlit app in your browser.
dashboard     | Local URL: http://localhost:8501
```

### 3b. Access Services

| Service | URL | Purpose |
|---------|-----|---------|
| **Dashboard** | [http://localhost:8501](http://localhost:8501) | Interactive UI (main entry point) |
| **API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI for API testing |
| **API Health** | [http://localhost:8000/health](http://localhost:8000/health) | Service status |

### 3c. Stop Services

```bash
# Stop and remove containers
docker-compose down

# Remove all data (careful!)
docker-compose down -v
```

---

## 4. Testing

### 4a. Run All Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
# or
start htmlcov\index.html  # Windows
```

### 4b. Run Specific Test Module

```bash
# Test Excel extraction only
pytest tests/test_excel.py -v

# Test anomaly detection
pytest tests/test_anomaly.py -v

# Test with print statements
pytest tests/test_validator.py -v -s
```

### 4c. Run Concurrent Request Test (Stress Test)

```bash
# Terminal 1: Start API
python -m uvicorn src.extractor.main:app --reload

# Terminal 2: Run concurrency test
pytest tests/test_api.py::test_concurrent_extract_requests -v

# OR: Use Apache Bench (ab)
# Simulate 10 requests with concurrency of 5
ab -n 10 -c 5 http://localhost:8000/extract
```

### 4d. Check Test Coverage Target

```bash
# Generate coverage report
pytest tests/ --cov=src --cov-report=term-missing

# Filter to critical modules
pytest tests/ --cov=src/extractor --cov=src/extractor/validator --cov-report=term-missing
```

**Target**: >80% on validator, co2, anomaly, pipeline modules

---

## 5. Working with Input Data

### 5a. Prepare Input Files

```bash
# Create data directory
mkdir -p data/

# Place Excel files
cp your_energy_file.xlsx data/

# Place PDFs
cp invoice_*.pdf data/

# Place images
cp photo_*.jpg data/
```

### 5b. Trigger Extraction

**Via API** (curl):
```bash
# Upload single file
curl -X POST http://localhost:8000/extract \
  -F "file=@data/energy_202605.xlsx"

# Response:
# {
#   "records_processed": 74,
#   "records_inserted": 72,
#   "errors": ["Row 23: timestamp parse failed"]
# }
```

**Via FastAPI Docs** (interactive):
1. Go to [http://localhost:8000/docs](http://localhost:8000/docs)
2. Expand `/extract` endpoint
3. Click "Try it out"
4. Upload file
5. Click "Execute"

**Via Streamlit Dashboard**:
1. Tab 4 (Data Explorer) → shows uploaded records
2. Tab 5 (Data Quality) → shows extraction warnings

---

## 6. Database Operations

### 6a. Query Database

```bash
# Using sqlite3 CLI
sqlite3 data/energy.db

# Common queries:
> SELECT COUNT(*) FROM energy_records;
> SELECT source_type, COUNT(*) FROM energy_records GROUP BY source_type;
> SELECT * FROM energy_records WHERE is_anomaly = 1 LIMIT 5;
```

### 6b. Backup Database

```bash
# Backup SQLite DB
sqlite3 data/energy.db ".backup data/energy.backup.db"

# Restore from backup
sqlite3 data/energy.db ".restore data/energy.backup.db"
```

### 6c. Reset Database (CAREFUL!)

```bash
# Delete all records (but keep schema)
sqlite3 data/energy.db "DELETE FROM energy_records;"

# OR: Delete entire DB (will be recreated on startup)
rm data/energy.db
```

---

## 7. Debugging

### 7a. Enable Debug Logging

```bash
# Set log level to DEBUG
LOG_LEVEL=DEBUG docker-compose up

# Or: In code
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 7b. View Logs

```bash
# Watch logs in real-time
docker-compose logs -f

# Logs for specific service
docker-compose logs extractor
docker-compose logs dashboard

# Last 50 lines
docker-compose logs --tail=50 extractor
```

### 7c. Shell Into Running Container

```bash
# Access extractor container shell
docker-compose exec extractor /bin/bash

# Access dashboard container shell
docker-compose exec dashboard /bin/bash

# Run Python in extractor
docker-compose exec extractor python -c "import extractor; print(extractor.__version__)"
```

### 7d. Common Issues & Fixes

**Issue**: `docker-compose: command not found`
```bash
# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

**Issue**: `Port 8000 already in use`
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# OR: Use different port
docker-compose up -d
# Edit docker-compose.yml: extractor port 8001:8000
```

**Issue**: `easyocr.Reader() hangs on first run`
```bash
# Pre-download models (see 1c above)
python -c "import easyocr; easyocr.Reader(['fr', 'en'])"

# If still hangs, try local model caching
docker build --build-arg EASYOCR_OFFLINE=1 -t energy-extractor .
```

**Issue**: `SQLite database is locked`
```bash
# Check if multiple writers active
sqlite3 data/energy.db "PRAGMA journal_mode=WAL;"

# If stuck, restart services
docker-compose restart
```

---

## 8. Development Workflow

### 8a. Making Code Changes

```bash
# 1. Create feature branch
git checkout -b fix/issue-123-thread-safety

# 2. Make changes to src/

# 3. Run tests locally
pytest tests/ --cov=src

# 4. Run specific test
pytest tests/test_image.py -v

# 5. Commit changes
git add -A
git commit -m "Fix: Add thread-safety to ImageExtractor (Issue #2)"

# 6. Push & create PR
git push origin fix/issue-123-thread-safety
```

### 8b. Testing Changes in Docker

```bash
# Rebuild with changes
docker-compose up --build

# View logs
docker-compose logs -f extractor

# Test via API
curl -X POST http://localhost:8000/extract -F "file=@test.xlsx"
```

### 8c. Pre-commit Checks

```bash
# Before pushing, run:
pytest tests/ -v --cov=src --cov-fail-under=75  # Coverage must be >75%
python -m black src/ --check  # Code style (optional)
python -m flake8 src/ --max-line-length=120  # Linting (optional)
```

---

## 9. Configuration

### 9a. Environment Variables

**Create `.env` file**:
```bash
# .env (git-ignored)
SQLITE_PATH=/data/energy.db
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
CLAUDE_API_KEY=sk-ant-... (optional)
ELECTRICITY_MAP_KEY=... (optional)
```

**Load in docker-compose.yml**:
```yaml
services:
  extractor:
    env_file:
      - .env
```

### 9b. Validation Bounds Configuration

**Edit `config/validation_bounds.yaml`**:
```yaml
validation_bounds:
  normal_mode:
    voltage_v: [380, 440]
    puissance_brute_kw: [800, 1400]
  summer_mode:
    puissance_brute_kw: [500, 900]
```

### 9c. Logging Configuration

**Edit `src/extractor/logging_config.py`**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

---

## 10. Production Deployment

### 10a. Deploy to Cloud (AWS ECS)

```bash
# Build & push image to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

docker tag energy-extractor:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/energy-extractor:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/energy-extractor:latest

# Deploy with CloudFormation/Terraform
```

### 10b. Deploy to Kubernetes (Helm)

```bash
# Create Helm chart (see helm/ directory)
cd helm/
helm install energy-pipeline . \
  --values values.yaml \
  --namespace production

# Check deployment
kubectl get pods -n production
kubectl logs -f deployment/energy-extractor -n production
```

### 10c. Database Backup & Recovery

```bash
# Daily backup to S3
aws s3 cp data/energy.db s3://backups/energy-$(date +%Y%m%d).db

# Restore from backup
aws s3 cp s3://backups/energy-20260501.db data/energy.db
```

---

## 11. Monitoring & Alerts

### 11a. Health Checks

```bash
# API health
curl http://localhost:8000/health

# Dashboard health
curl http://localhost:8501 -I  # Should return 200 OK

# Database connectivity
curl http://localhost:8000/api/records | jq '.[] | .id' | wc -l
```

### 11b. Performance Monitoring

```bash
# Monitor API response times
curl -w "Response time: %{time_total}s\n" http://localhost:8000/records

# Monitor resource usage
docker stats energy-pipeline_extractor_1

# Expected:
# CONTAINER      CPU %   MEM USAGE / LIMIT   MEM %
# extractor_1    2.5%    450MiB / 2GiB       22%
```

### 11c. Error Monitoring

```bash
# Check error logs
docker-compose logs extractor | grep ERROR

# Extract anomaly detection results
curl http://localhost:8000/anomalies | jq '.[] | {timestamp, anomaly_type, confidence}'
```

---

## 12. Frequently Asked Questions

**Q: How do I reset everything to a clean state?**
```bash
docker-compose down -v  # Remove all data
rm data/energy.db
docker-compose up --build  # Fresh start
```

**Q: How do I use the Claude API?**
```bash
# Set API key
export CLAUDE_API_KEY=sk-ant-...

# Rebuild
docker-compose up --build

# Claude validation now active (optional fallback)
```

**Q: How do I scale to handle 1M+ records?**
See [ROADMAP.md - Phase 3: PostgreSQL Migration](ROADMAP.md#Priority-3a-Database-Migration-to-PostgreSQL)

**Q: How do I add a new extractor?**
1. Create `src/extractor/extractors/my_format.py`
2. Inherit from `BaseExtractor`
3. Implement `extract(file_path) -> List[ExtractionResult]`
4. Register in `src/extractor/main.py` extractors dict

**Q: How do I contribute to the project?**
See [CONTRIBUTING.md](../CONTRIBUTING.md) (TODO: Create this file)

---

## 13. Useful Commands Reference

```bash
# Docker
docker-compose up -d                          # Start in background
docker-compose down                           # Stop all services
docker-compose logs -f extractor              # Follow logs
docker-compose exec extractor bash            # Shell into container
docker-compose ps                             # List running services
docker-compose restart                        # Restart services

# Python
pytest tests/ -v                              # Run all tests
pytest tests/test_anomaly.py::test_spike -v   # Run specific test
python -m coverage report                     # Coverage summary
python -c "import src; print(src.__version__)" # Check imports

# Database
sqlite3 data/energy.db ".tables"              # List tables
sqlite3 data/energy.db "SELECT COUNT(*) FROM energy_records;"
sqlite3 data/energy.db ".backup backup.db"    # Backup

# API Testing
curl -X GET http://localhost:8000/records     # Query records
curl -X POST http://localhost:8000/extract -F "file=@test.xlsx"
curl http://localhost:8000/docs               # Swagger UI
```

---

## 14. Next Steps

1. **Local Setup**: Follow sections 1–3 above to get running locally
2. **Run Tests**: Follow section 4 to verify system works
3. **Explore Code**: Read [ARCHITECTURE.md](ARCHITECTURE.md) for system overview
4. **Check Issues**: See [PROBLEMS.md](PROBLEMS.md) for improvement areas
5. **Follow Roadmap**: See [ROADMAP.md](ROADMAP.md) for priorities

---

**Need Help?**

- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Design Specification: [docs/superpowers/specs/2026-05-02-energy-pipeline-design.md](../superpowers/specs/2026-05-02-energy-pipeline-design.md)
- Troubleshooting: See section 7 (Debugging) above
- File an Issue: GitHub Issues (TODO: Add link)

---

Last Updated: 2026-05-02  
For architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md).  
For identified issues, see [PROBLEMS.md](PROBLEMS.md).  
For fix priorities, see [ROADMAP.md](ROADMAP.md).
