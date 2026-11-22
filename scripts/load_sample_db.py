import sqlite3
import os

sql_path = os.path.join("data", "event-management-sample-database-1k-en_GB-v2.sql")
db_path = os.path.join("data", "event_management.db")

if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
with open(sql_path, "r", encoding="utf-8") as f:
    sql = f.read()

conn.executescript(sql)
cursor = conn.cursor()
tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print(f"Successfully loaded {len(tables)} tables into {db_path}:")
for t in tables:
    count = cursor.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
    print(f"  - {t}: {count} rows")

conn.close()
