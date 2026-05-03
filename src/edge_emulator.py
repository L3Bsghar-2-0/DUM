import joblib
import numpy as np
import time
import os
import json
from datetime import datetime

# Paths
MODEL_PATH = r"c:\Users\Adem\OneDrive\Desktop\DUM\src\extractor\models\edge_model.pkl"
THRESH_PATH = r"c:\Users\Adem\OneDrive\Desktop\DUM\src\extractor\models\error_thresholds.npy"
LOG_PATH = r"c:\Users\Adem\OneDrive\Desktop\DUM\edge_inference.log"

class EdgeDevice:
    def __init__(self):
        print("--- Initializing Edge Intelligence Engine ---")
        self.model = joblib.load(MODEL_PATH)
        self.thresholds = np.load(THRESH_PATH)
        self.network_connected = True
        self.history = [] # Last 5 readings
        
    def simulate_reading(self, power, gas):
        """Simulates a sensor reading and local processing."""
        start_time = time.time()
        
        # Add to history
        self.history.append([power, gas])
        if len(self.history) > 5:
            self.history.pop(0)
            
        # Inference (if we have enough history)
        inference_time = 0
        prediction = None
        is_anomaly = False
        anomaly_type = None
        
        if len(self.history) == 5:
            inf_start = time.time()
            # Prepare input
            X_input = np.array(self.history).flatten().reshape(1, -1)
            # Predict
            prediction = self.model.predict(X_input)[0]
            inf_end = time.time()
            inference_time = (inf_end - inf_start) * 1000 # ms
            
            # Local Anomaly Detection (Compare previous prediction with current reading)
            # For simplicity, we compare current reading with prediction from previous step
            # but since this is a simulation, we'll just check if current reading is far from "expected"
            # if we had a stored prediction from the previous step.
            
        latency = (time.time() - start_time) * 1000 # total processing latency
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "mode": "ONLINE" if self.network_connected else "OFFLINE (EDGE MODE)",
            "sensors": {"power": power, "gas": gas},
            "inference_latency_ms": round(inference_time, 2),
            "total_latency_ms": round(latency, 2),
            "prediction": prediction.tolist() if prediction is not None else None
        }
        
        # Anomaly detection if offline
        if not self.network_connected and prediction is not None:
            # We compare current value with the prediction we just made (self-consistency check)
            # In a real system, you compare reading(t) with prediction(t) made at t-1.
            diff_power = abs(power - prediction[0])
            diff_gas = abs(gas - prediction[1])
            
            if diff_power > self.thresholds[0] * 3 or diff_gas > self.thresholds[1] * 3:
                log_entry["local_anomaly_detected"] = True
                log_entry["anomaly_details"] = "Deviation from predicted trend exceeded 3-sigma"
        
        self.log(log_entry)
        return log_entry

    def log(self, entry):
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")

def run_demo():
    device = EdgeDevice()
    
    # 1. Normal Operation (Online)
    print("\n[Phase 1] Normal Operation (Network Online)")
    for i in range(5):
        device.simulate_reading(1000 + i*10, 280 + i*2)
        print(f"Reading {i+1} processed.")
        
    # 2. Network Failure Simulation
    print("\n[Phase 2] NETWORK FAILURE - Switching to Edge Intelligence Mode")
    device.network_connected = False
    
    # Normal data while offline
    print("Reading sensors while offline...")
    for i in range(3):
        res = device.simulate_reading(1050 + i*5, 290 + i)
        print(f"Offline Reading {i+1}: Latency {res['inference_latency_ms']}ms")

    # 3. Anomaly detection while offline
    print("\n[Phase 3] INJECTING ANOMALY (Offline)")
    # Sudden drop in power
    res = device.simulate_reading(500, 295) 
    if res.get("local_anomaly_detected"):
        print(f"!!! SUCCESS: Local Anomaly Detected at the Edge !!!")
        print(f"!!! Message: {res['anomaly_details']}")

    print(f"\n✅ Demo complete. Logs saved to {LOG_PATH}")

if __name__ == "__main__":
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)
    run_demo()
