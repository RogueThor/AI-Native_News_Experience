import sqlite3
import os

db_path = "newsspark_cache.db"
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
curr = conn.cursor()
try:
    curr.execute("SELECT * FROM agent_logs WHERE agent_name = 'story_arc' ORDER BY timestamp DESC LIMIT 10")
    rows = curr.fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print(f"Error: {e}")
conn.close()
