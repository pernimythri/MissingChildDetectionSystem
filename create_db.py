import sqlite3


conn = sqlite3.connect("database.db")
cursor = conn.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS missing_people (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
age INTEGER,
last_seen TEXT,
description TEXT,
photo TEXT
)
""")


conn.commit()
conn.close()


print("Database created successfully")