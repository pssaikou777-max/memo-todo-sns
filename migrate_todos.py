"""
todos テーブルにツリー・繰り返し用カラムを追加するワンタイムマイグレーション
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "memo_todo_sns.db")
if not os.path.exists(db_path):
    print("DB not found — will be created fresh by app. Nothing to do.")
    raise SystemExit(0)

con = sqlite3.connect(db_path)
cur = con.cursor()

cols = [row[1] for row in cur.execute("PRAGMA table_info(todos)").fetchall()]
print("existing cols:", cols)

migrations = []
if "due_time" not in cols:
    migrations.append("ALTER TABLE todos ADD COLUMN due_time TEXT")
if "parent_id" not in cols:
    migrations.append("ALTER TABLE todos ADD COLUMN parent_id INTEGER REFERENCES todos(id)")
if "order_index" not in cols:
    migrations.append("ALTER TABLE todos ADD COLUMN order_index INTEGER NOT NULL DEFAULT 0")
if "repeat_type" not in cols:
    migrations.append("ALTER TABLE todos ADD COLUMN repeat_type TEXT NOT NULL DEFAULT 'none'")

for sql in migrations:
    print("Running:", sql)
    cur.execute(sql)

con.commit()
con.close()
print("Migration done.")
