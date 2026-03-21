import sqlite3
import os

db_path = "newsspark_cache.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM briefings;")
    cursor.execute("DELETE FROM translations;")
    conn.commit()
    conn.close()
    print("✅ Stale briefings and translations cleared from cache.")
else:
    print("❌ newsspark_cache.db not found.")
