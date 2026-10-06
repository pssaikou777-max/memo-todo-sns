"""
Supabase PostgreSQL に対してカラム追加マイグレーションを実行
"""
import os
from dotenv import load_dotenv
load_dotenv()

import psycopg2

url = os.environ.get("DATABASE_URL", "")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)

con = psycopg2.connect(url)
cur = con.cursor()

# 現在のカラムを確認
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
user_cols = [r[0] for r in cur.fetchall()]
print("users cols:", user_cols)

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='todos'")
todo_cols = [r[0] for r in cur.fetchall()]
print("todos cols:", todo_cols)

# users マイグレーション
user_migrations = []
if "display_name" not in user_cols:
    user_migrations.append("ALTER TABLE users ADD COLUMN display_name VARCHAR(64)")
if "bio" not in user_cols:
    user_migrations.append("ALTER TABLE users ADD COLUMN bio VARCHAR(200)")
if "avatar_color" not in user_cols:
    user_migrations.append("ALTER TABLE users ADD COLUMN avatar_color VARCHAR(16) NOT NULL DEFAULT '#4a7cf7'")

# todos マイグレーション
todo_migrations = []
if "due_time" not in todo_cols:
    todo_migrations.append("ALTER TABLE todos ADD COLUMN due_time TIME")
if "parent_id" not in todo_cols:
    todo_migrations.append("ALTER TABLE todos ADD COLUMN parent_id INTEGER REFERENCES todos(id)")
if "order_index" not in todo_cols:
    todo_migrations.append("ALTER TABLE todos ADD COLUMN order_index INTEGER NOT NULL DEFAULT 0")
if "repeat_type" not in todo_cols:
    todo_migrations.append("ALTER TABLE todos ADD COLUMN repeat_type VARCHAR(16) NOT NULL DEFAULT 'none'")

all_migrations = user_migrations + todo_migrations
if not all_migrations:
    print("Nothing to migrate.")
else:
    for sql in all_migrations:
        print("Running:", sql)
        cur.execute(sql)

con.commit()
con.close()
print("Migration done.")
