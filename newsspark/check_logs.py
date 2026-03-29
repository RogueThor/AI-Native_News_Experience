import sqlite3
import os
import json

db_path = "newsspark_cache.db"
if not os.path.exists(db_path):
    print(f"Error: {db_path} does not exist.")
else:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM agent_logs ORDER BY timestamp DESC LIMIT 5;")
        rows = cursor.fetchall()
        for row in rows:
            print(f"--- [{row['timestamp']}] {row['agent_name']} ---")
            print(f"Action: {row['action']}")
            print(f"Input: {row['input_summary']}")
            print(f"Output: {row['output_summary']}")
            print("-" * 40)
    except Exception as e:
        print(f"Error: {e}")
    conn.close()
