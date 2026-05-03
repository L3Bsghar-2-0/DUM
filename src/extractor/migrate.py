import sqlite3
from pathlib import Path

db_path = Path("data/db/energy.db")
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE energy_records ADD COLUMN anomaly_confidence FLOAT;")
        print("Added anomaly_confidence column successfully.")
    except sqlite3.OperationalError as e:
        print(f"Column anomaly_confidence might already exist: {e}")
        
    try:
        cursor.execute("ALTER TABLE energy_records ADD COLUMN site VARCHAR DEFAULT 'Main Factory';")
        print("Added site column successfully.")
    except sqlite3.OperationalError as e:
        print(f"Column site might already exist: {e}")
        
    conn.commit()
    conn.close()
    print("Database schema successfully upgraded!")
else:
    print(f"Database not found at {db_path.absolute()}")
