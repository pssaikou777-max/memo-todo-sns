import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ── シークレットキー ───────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

# ── データベース ───────────────────────────────────────────────
# Render/本番環境では DATABASE_URL 環境変数を使用
# ローカルでは SQLite にフォールバック
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    # psycopg2 は postgresql:// が必要（postgres:// は旧形式）
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
else:
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "memo_todo_sns.db")

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
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
