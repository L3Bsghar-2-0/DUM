import joblib
import numpy as np
import time
import os
import json
import random
from datetime import datetime

# Paths
MODEL_PATH = r"c:\Users\Adem\OneDrive\Desktop\DUM\src\extractor\models\edge_model.pkl"
THRESH_PATH = r"c:\Users\Adem\OneDrive\Desktop\DUM\src\extractor\models\error_thresholds.npy"
LOG_PATH = r"c:\Users\Adem\OneDrive\Desktop\DUM\edge_inference.log"

class EdgeDevice:
    def __init__(self):
        print("--- Initializing Real-Time Edge Intelligence Engine ---")
        self.model = joblib.load(MODEL_PATH)
        self.thresholds = np.load(THRESH_PATH)
        self.network_connected = True
        self.history = [] 
        
        # Initial state for simulation
        self.curr_power = 1000.0
        self.curr_gas = 280.0
        
    def get_next_reading(self):
        """Simulates real-time sensor fetching with drift and occasional noise."""
        # Add some random walk/drift
        self.curr_power += random.uniform(-10, 10)
        self.curr_gas += random.uniform(-1, 1)
        
        # Ensure values stay in physical bounds
        self.curr_power = max(800, min(1400, self.curr_power))
        self.curr_gas = max(100, min(500, self.curr_gas))
        
        # Inject an anomaly every 30 seconds
        if int(time.time()) % 30 == 0:
            return self.curr_power * 0.5, self.curr_gas * 1.5 # Huge drop in power, spike in gas
            
        return self.curr_power, self.curr_gas

    def process_step(self):
        start_time = time.time()
        power, gas = self.get_next_reading()
        
        # Add to history
        self.history.append([power, gas])
        if len(self.history) > 5:
            self.history.pop(0)
            
        inference_time = 0
        prediction = None
        
        if len(self.history) == 5:
            inf_start = time.time()
            X_input = np.array(self.history).flatten().reshape(1, -1)
            prediction = self.model.predict(X_input)[0]
            inference_time = (time.time() - inf_start) * 1000
            
        latency = (time.time() - start_time) * 1000
        
        # Simulate network toggling (Offline every 20 seconds for 10 seconds)
        self.network_connected = not (15 < int(time.time()) % 30 < 25)
        
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "mode": "ONLINE" if self.network_connected else "OFFLINE (EDGE MODE)",
            "sensors": {"power": round(power, 2), "gas": round(gas, 2)},
            "inference_latency_ms": round(inference_time, 2),
            "total_latency_ms": round(latency, 2),
            "prediction": [round(p, 2) for p in prediction.tolist()] if prediction is not None else None
        }
        
        # Local Anomaly Detection logic
        if prediction is not None:
            # Simple 3-sigma check
            # For demonstration, we compare current reading with prediction made from history
            diff_power = abs(power - prediction[0])
            if diff_power > self.thresholds[0] * 2.5:
                log_entry["local_anomaly_detected"] = True
                log_entry["anomaly_details"] = "Sudden Power Drop (Edge Flagged)"
        
        self.log(log_entry)
        return log_entry

    def log(self, entry):
        # Keep only the last 50 entries in the log file to keep it "real-time" and small
        lines = []
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, "r") as f:
                lines = f.readlines()
        
        lines.append(json.dumps(entry) + "\n")
        if len(lines) > 50:
            lines = lines[-50:]
            
        with open(LOG_PATH, "w") as f:
            f.writelines(lines)

def start_live_service():
    device = EdgeDevice()
    print("Edge Intelligence Service is now LIVE. Updating edge_inference.log every 2 seconds.")
    try:
        while True:
            device.process_step()
            time.sleep(2)
    except KeyboardInterrupt:
        print("Service stopped.")

if __name__ == "__main__":
    start_live_service()
