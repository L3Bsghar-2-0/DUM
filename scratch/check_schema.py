import sqlite3
import os

db_path = r"c:\Users\Adem\OneDrive\Desktop\DUM\data\db\energy.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(energy_records);")
    columns = cursor.fetchall()
    print("Schema for 'energy_records':")
    for col in columns:
        print(f"- {col[1]} ({col[2]})")
    
    print("\nSample Data (first 2 rows):")
    cursor.execute("SELECT * FROM energy_records LIMIT 2;")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    conn.close()
