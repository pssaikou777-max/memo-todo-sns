"""
users テーブルに display_name・bio・avatar_color カラムを追加するマイグレーション
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "memo_todo_sns.db")
if not os.path.exists(db_path):
    print("DB not found — will be created fresh by app. Nothing to do.")
    raise SystemExit(0)

con = sqlite3.connect(db_path)
cur = con.cursor()

cols = [row[1] for row in cur.execute("PRAGMA table_info(users)").fetchall()]
print("existing cols:", cols)

migrations = []
if "display_name" not in cols:
    migrations.append("ALTER TABLE users ADD COLUMN display_name TEXT")
if "bio" not in cols:
    migrations.append("ALTER TABLE users ADD COLUMN bio TEXT")
if "avatar_color" not in cols:
    migrations.append("ALTER TABLE users ADD COLUMN avatar_color TEXT NOT NULL DEFAULT '#4a7cf7'")

for sql in migrations:
    print("Running:", sql)
    cur.execute(sql)

con.commit()
con.close()
print("Migration done.")
