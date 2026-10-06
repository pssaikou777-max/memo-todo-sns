from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


# ─── 多対多中間テーブル ────────────────────────────────────────────
memo_groups = db.Table(
    "memo_groups",
    db.Column("memo_id",  db.Integer, db.ForeignKey("memos.id"),  primary_key=True),
    db.Column("group_id", db.Integer, db.ForeignKey("groups.id"), primary_key=True),
)


# ─── User ─────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64),  nullable=False, unique=True)
    email         = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # プロフィール
    display_name  = db.Column(db.String(64),  nullable=True)   # 表示名（空なら username を使用）
    bio           = db.Column(db.String(200), nullable=True)   # 一言
    avatar_color  = db.Column(db.String(16),  nullable=False, default="#4a7cf7")  # アバター背景色

    @property
    def show_name(self) -> str:
        return self.display_name or self.username

    memos   = db.relationship("Memo",   backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    folders = db.relationship("Folder", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    groups  = db.relationship("Group",  backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    todos   = db.relationship("Todo",   backref="owner", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


# ─── Folder ───────────────────────────────────────────────────────
class Folder(db.Model):
    __tablename__ = "folders"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name       = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    memos = db.relationship("Memo", backref="folder", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Folder {self.name}>"


# ─── Group ────────────────────────────────────────────────────────
class Group(db.Model):
    __tablename__ = "groups"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name       = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Group {self.name}>"


# ─── Memo ─────────────────────────────────────────────────────────
VISIBILITY_PRIVATE = "private"
VISIBILITY_FRIENDS = "friends"
VISIBILITY_PUBLIC  = "public"

class Memo(db.Model):
    __tablename__ = "memos"

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title          = db.Column(db.String(200), nullable=True)
    body           = db.Column(db.Text, nullable=True)
    folder_id      = db.Column(db.Integer, db.ForeignKey("folders.id"), nullable=True)
    visibility     = db.Column(db.String(16), nullable=False, default=VISIBILITY_PRIVATE)
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                               onupdate=lambda: datetime.now(timezone.utc))
    last_viewed_at = db.Column(db.DateTime, nullable=True)

    images = db.relationship("MemoImage", backref="memo", lazy="dynamic",
                             cascade="all, delete-orphan")
    groups = db.relationship("Group", secondary=memo_groups, backref="memos", lazy="dynamic")

    @property
    def display_title(self) -> str:
        """タイトルが空の場合は本文先頭30文字を返す"""
        if self.title:
            return self.title
        if self.body:
            return self.body[:30]
        return "（無題）"

    def touch(self) -> None:
        """最終閲覧日時を更新"""
        self.last_viewed_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<Memo {self.id}: {self.display_title[:20]}>"


# ─── MemoImage ────────────────────────────────────────────────────
class MemoImage(db.Model):
    __tablename__ = "memo_images"

    id         = db.Column(db.Integer, primary_key=True)
    memo_id    = db.Column(db.Integer, db.ForeignKey("memos.id"), nullable=False)
    filename   = db.Column(db.String(256), nullable=False)   # uploads/xxxxx.jpg
    thumb_name = db.Column(db.String(256), nullable=True)    # uploads/thumb_xxxxx.jpg
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<MemoImage {self.filename}>"


# ─── Todo ─────────────────────────────────────────────────────────
# repeat_type: none / daily / weekly / monthly
class Todo(db.Model):
    __tablename__ = "todos"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title        = db.Column(db.String(200), nullable=False)
    description  = db.Column(db.Text, nullable=True)
    due_date     = db.Column(db.Date, nullable=True)
    due_time     = db.Column(db.Time, nullable=True)           # 時間設定（任意）
    completed    = db.Column(db.Boolean, nullable=False, default=False)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    # ツリー構造
    parent_id    = db.Column(db.Integer, db.ForeignKey("todos.id"), nullable=True)
    order_index  = db.Column(db.Integer, nullable=False, default=0)
    # 繰り返し
    repeat_type  = db.Column(db.String(16), nullable=False, default="none")
    # none / daily / weekly / monthly

    children = db.relationship(
        "Todo",
        backref=db.backref("parent", remote_side="Todo.id"),
        lazy="dynamic",
        cascade="all",
        order_by="Todo.order_index",
    )

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    @property
    def all_children_done(self) -> bool:
        kids = list(self.children)
        return len(kids) == 0 or all(c.completed for c in kids)

    def __repr__(self) -> str:
        return f"<Todo {self.title}>"


# ─── Friendship ───────────────────────────────────────────────────
FRIEND_PENDING  = "pending"
FRIEND_ACCEPTED = "accepted"

class Friendship(db.Model):
    __tablename__ = "friendships"

    id           = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status       = db.Column(db.String(16), nullable=False, default=FRIEND_PENDING)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    requester = db.relationship("User", foreign_keys=[requester_id], backref="sent_requests")
    receiver  = db.relationship("User", foreign_keys=[receiver_id],  backref="received_requests")

    def __repr__(self) -> str:
        return f"<Friendship {self.requester_id}->{self.receiver_id} {self.status}>"
