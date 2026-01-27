import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    gmail TEXT NOT NULL,
    password TEXT NOT NULL,
    phone TEXT,
    address TEXT
)
""")

conn.commit()
conn.close()

print("Users table created successfully!")
