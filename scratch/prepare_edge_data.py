import sqlite3
import pandas as pd
import numpy as np
import os

db_path = r"c:\Users\Adem\OneDrive\Desktop\DUM\data\db\energy.db"
output_dir = r"c:\Users\Adem\OneDrive\Desktop\DUM\data\processed"
os.makedirs(output_dir, exist_ok=True)

def prepare_data():
    print("Connecting to database...")
    conn = sqlite3.connect(db_path)
    
    # Query relevant columns, ordering by timestamp or ID
    query = "SELECT timestamp, puissance_brute_kw, gaz_debit_nm3h FROM energy_records ORDER BY id ASC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f"Loaded {len(df)} records.")
    
    # Fill missing values with forward fill then backward fill
    df[['puissance_brute_kw', 'gaz_debit_nm3h']] = df[['puissance_brute_kw', 'gaz_debit_nm3h']].ffill().bfill()
    
    # Prepare sequencing (Window size = 5)
    window = 5
    features = []
    targets = []
    
    data = df[['puissance_brute_kw', 'gaz_debit_nm3h']].values
    
    print("Sequencing data...")
    for i in range(len(data) - window):
        # Input: 5 timesteps x 2 sensors = 10 features
        window_data = data[i:i+window].flatten()
        features.append(window_data)
        
        # Target: Next timestep x 2 sensors
        targets.append(data[i+window])
        
    X = np.array(features)
    y = np.array(targets)
    
    print(f"Data ready. Input shape: {X.shape}, Target shape: {y.shape}")
    
    # Save for training
    np.save(os.path.join(output_dir, "X_train.npy"), X)
    np.save(os.path.join(output_dir, "y_train.npy"), y)
    print(f"Saved processed data to {output_dir}")

if __name__ == "__main__":
    prepare_data()
