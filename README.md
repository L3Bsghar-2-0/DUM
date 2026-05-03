# ReTeqFusion: Intelligent Energy Pipeline & Edge Intelligence

ReTeqFusion is a state-of-the-art energy management platform designed for industrial tri-generation facilities. The system automates the entire data lifecycle—from extracting unstructured reports to real-time cloud monitoring and local edge intelligence.

## 🌟 Core Superpowers

### 1. Multi-Source Extraction (The Pipeline)
Automated extraction and normalization of data from:
*   **Excel**: Complex 74x2,877 wide-format monthly reports.
*   **PDF**: Structured invoices and technical logs.
*   **Images (OCR)**: Scanned reports and WhatsApp photos.
*   **Unit Normalization**: Standardizes 13+ unit types (Nm3, GJ, kWh, etc.) into a unified data model.

### 2. Live Cloud Integration (MQTT)
*   **Real-Time Sync**: Connects to **HiveMQ Cloud** via TLS.
*   **IoT Ready**: Automatically ingests and stores live telemetry from ESP32 sensors (DHT22, MQ2) directly into the system database.

### 3. Edge Intelligence (Track 3A Excellence)
*   **Next-Value Prediction**: A lightweight (46 KB) multi-sensor Random Forest model runs locally.
*   **Resilience Mode**: Continues detecting anomalies even during network outages.
*   **High Performance**: Inference latency of **< 20ms**, optimized for constrained hardware.

### 4. Interactive Analytics Dashboard
A 7-tab Streamlit suite providing:
*   **KPIs & CO2 Trends**: Real-time carbon footprint tracking.
*   **Anomaly Detection**: 5-method statistical ensemble (Z-Score, Isolation Forest, etc.).
*   **Edge Monitoring**: Live visualization of on-device intelligence and "Digital Twin" simulations.

---

## 🛠 Technical Architecture

*   **Backend**: Python, FastAPI
*   **Frontend**: Streamlit + Plotly
*   **Intelligence**: Scikit-Learn (Anomalies, Forecasting, Edge Model)
*   **Connectivity**: Paho MQTT (TLS Secured)
*   **Database**: SQLite (SQLAlchemy ORM)
*   **Infrastructure**: Docker & Docker Compose

## 📂 Project Structure

```text
DUM/
├── src/
│   ├── extractor/      # Backend, ML Pipeline, and Models
│   ├── dashboard/      # Streamlit UI
│   └── edge_emulator_live.py # Edge Intelligence Service
├── reteqfusion-server/ # MQTT Subscriber (Cloud Sync)
├── data/
│   └── db/             # Persistence Layer (energy.db)
└── README.md           # You are here
```

## 🚀 Quick Start for Judges

### 1. Launch the Backend & Dashboard
```powershell
# Set path (required for module discovery)
$env:PYTHONPATH = "src/extractor"

# Start the API
python -m uvicorn src.extractor.main:app --reload

# Start the Dashboard (separate terminal)
python -m streamlit run src/dashboard/app.py
```

### 2. Start the Live Cloud Sync
```powershell
cd reteqfusion-server
python subscriber.py
```

### 3. Demonstrate Edge Intelligence
Navigate to the **"🌐 Edge Intelligence"** tab on the dashboard to see the live 20ms inference and local anomaly detection in action.

---
*Developed for the ReTeqFusion Energy Challenge — May 2026*
