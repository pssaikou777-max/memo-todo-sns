import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ── シークレットキー ───────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

# ── データベース ───────────────────────────────────────────────
# Render/本番環境では DATABASE_URL 環境変数を使用
# ローカルでは SQLite にフォールバック
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    # postgres:// → postgresql:// に統一（Render等の旧形式対応）
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    # postgresql:// → postgresql+psycopg2:// に変換（psycopg2ドライバ指定）
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
else:
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "memo_todo_sns.db")

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    # Supabase Session Pooler はプリペアドステートメント非対応
    "connect_args": {"options": "-c statement_timeout=10000"},
}

# ── 画像アップロード ───────────────────────────────────────────
# Render/本番環境では Supabase Storage を使用
# ローカルでは static/uploads/ にフォールバック
SUPABASE_URL    = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY    = os.environ.get("SUPABASE_KEY", "")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "memo-images")

USE_SUPABASE_STORAGE = bool(SUPABASE_URL and SUPABASE_KEY)

# ローカル用フォールバック
UPLOAD_FOLDER      = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
THUMBNAIL_SIZE     = (320, 320)
