import os
import io
import uuid
from datetime import datetime, timezone

from flask import (Blueprint, render_template, redirect, url_for,
                   request, flash, abort, current_app)
from flask_login import login_required, current_user
from PIL import Image

from extensions import db
from models import Memo, MemoImage, Folder, Group, Todo, VISIBILITY_PRIVATE

memos = Blueprint("memos", __name__, url_prefix="/memos")

ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def _save_image(file) -> tuple[str, str]:
    """画像を保存してサムネイルを生成。(filename, thumb_name) を返す。
    USE_SUPABASE_STORAGE=True なら Supabase Storage へ、False ならローカルへ保存。
    """
    ext      = file.filename.rsplit(".", 1)[1].lower()
    stem     = uuid.uuid4().hex
    filename = f"{stem}.{ext}"
    thumb    = f"thumb_{stem}.{ext}"

    # 元画像をメモリに読み込む
    file_bytes = file.read()

    # サムネイル生成（メモリ内）
    size = current_app.config["THUMBNAIL_SIZE"]
    with Image.open(io.BytesIO(file_bytes)) as img:
        img_thumb = img.copy()
        img_thumb.thumbnail(size)
        thumb_buf = io.BytesIO()
        fmt = "JPEG" if ext in ("jpg", "jpeg") else ext.upper()
        img_thumb.save(thumb_buf, format=fmt)
        thumb_bytes = thumb_buf.getvalue()

    if current_app.config.get("USE_SUPABASE_STORAGE"):
        _upload_to_supabase(filename, file_bytes, ext)
        _upload_to_supabase(thumb,    thumb_bytes, ext)
    else:
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_dir, exist_ok=True)
        with open(os.path.join(upload_dir, filename), "wb") as f:
            f.write(file_bytes)
        with open(os.path.join(upload_dir, thumb), "wb") as f:
            f.write(thumb_bytes)

    return filename, thumb


def _upload_to_supabase(filename: str, data: bytes, ext: str) -> None:
    from supabase import create_client
    url    = current_app.config["SUPABASE_URL"]
    key    = current_app.config["SUPABASE_KEY"]
    bucket = current_app.config["SUPABASE_BUCKET"]
    client = create_client(url, key)
    mime   = f"image/{'jpeg' if ext in ('jpg','jpeg') else ext}"
    client.storage.from_(bucket).upload(filename, data, {"content-type": mime})


def _delete_from_storage(filename: str) -> None:
    """ストレージから画像を削除"""
    if current_app.config.get("USE_SUPABASE_STORAGE"):
        try:
            from supabase import create_client
            url    = current_app.config["SUPABASE_URL"]
            key    = current_app.config["SUPABASE_KEY"]
            bucket = current_app.config["SUPABASE_BUCKET"]
            client = create_client(url, key)
            client.storage.from_(bucket).remove([filename])
        except Exception:
            pass
    else:
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        path = os.path.join(upload_dir, filename)
        if os.path.exists(path):
            os.remove(path)


def _image_url(filename: str) -> str:
    """画像の公開URLを返す"""
    if current_app.config.get("USE_SUPABASE_STORAGE"):
        url    = current_app.config["SUPABASE_URL"]
        bucket = current_app.config["SUPABASE_BUCKET"]
        return f"{url}/storage/v1/object/public/{bucket}/{filename}"
    return url_for("static", filename=f"uploads/{filename}")


# ─── 一覧 ──────────────────────────────────────────────────────────
@memos.route("/")
@login_required
def list_memos():
    folder_id = request.args.get("folder_id", type=int)
    q         = request.args.get("q", "").strip()

    query = Memo.query.filter_by(user_id=current_user.id)

    if folder_id:
        query = query.filter_by(folder_id=folder_id)

    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Memo.title.ilike(like), Memo.body.ilike(like))
        )

    memos_list = query.order_by(Memo.updated_at.desc()).all()
    folders    = Folder.query.filter_by(user_id=current_user.id).order_by(Folder.name).all()
    cur_folder = Folder.query.get(folder_id) if folder_id else None

    return render_template("memos/list.html",
                           memos=memos_list,
                           folders=folders,
                           cur_folder=cur_folder,
                           q=q,
                           image_url=_image_url)


# ─── 詳細 ──────────────────────────────────────────────────────────
@memos.route("/<int:memo_id>")
@login_required
def detail(memo_id: int):
    memo = Memo.query.get_or_404(memo_id)
    if memo.user_id != current_user.id:
        abort(403)
    memo.touch()
    db.session.commit()
    return render_template("memos/detail.html", memo=memo, image_url=_image_url)


# ─── 作成 ──────────────────────────────────────────────────────────
@memos.route("/new", methods=["GET", "POST"])
@login_required
def new():
    folders = Folder.query.filter_by(user_id=current_user.id).order_by(Folder.name).all()
    groups  = Group.query.filter_by(user_id=current_user.id).order_by(Group.name).all()

    if request.method == "POST":
        title      = request.form.get("title", "").strip()
        body       = request.form.get("body",  "").strip()
        folder_id  = request.form.get("folder_id", type=int)
        group_ids  = request.form.getlist("group_ids", type=int)
        visibility = request.form.get("visibility", VISIBILITY_PRIVATE)

        memo = Memo(
            user_id    = current_user.id,
            title      = title or None,
            body       = body  or None,
            folder_id  = folder_id or None,
            visibility = visibility,
        )
        for gid in group_ids:
            g = Group.query.get(gid)
            if g and g.user_id == current_user.id:
                memo.groups.append(g)

        db.session.add(memo)
        db.session.flush()

        images = request.files.getlist("images")
        for f in images:
            if f and f.filename and _allowed(f.filename):
                fname, thumb = _save_image(f)
                db.session.add(MemoImage(memo_id=memo.id,
                                         filename=fname,
                                         thumb_name=thumb))

        db.session.commit()
        flash("メモを保存しました。", "success")
        return redirect(url_for("memos.detail", memo_id=memo.id))

    return render_template("memos/edit.html",
                           memo=None,
                           folders=folders,
                           groups=groups,
                           image_url=_image_url)


# ─── 編集 ──────────────────────────────────────────────────────────
@memos.route("/<int:memo_id>/edit", methods=["GET", "POST"])
@login_required
def edit(memo_id: int):
    memo = Memo.query.get_or_404(memo_id)
    if memo.user_id != current_user.id:
        abort(403)

    folders = Folder.query.filter_by(user_id=current_user.id).order_by(Folder.name).all()
    groups  = Group.query.filter_by(user_id=current_user.id).order_by(Group.name).all()

    if request.method == "POST":
        memo.title      = request.form.get("title", "").strip() or None
        memo.body       = request.form.get("body",  "").strip() or None
        memo.folder_id  = request.form.get("folder_id", type=int) or None
        memo.visibility = request.form.get("visibility", VISIBILITY_PRIVATE)
        memo.updated_at = datetime.now(timezone.utc)

        group_ids = request.form.getlist("group_ids", type=int)
        memo.groups = []
        for gid in group_ids:
            g = Group.query.get(gid)
            if g and g.user_id == current_user.id:
                memo.groups.append(g)

        images = request.files.getlist("images")
        for f in images:
            if f and f.filename and _allowed(f.filename):
                fname, thumb = _save_image(f)
                db.session.add(MemoImage(memo_id=memo.id,
                                         filename=fname,
                                         thumb_name=thumb))

        db.session.commit()
        flash("メモを更新しました。", "success")
        return redirect(url_for("memos.detail", memo_id=memo.id))

    return render_template("memos/edit.html",
                           memo=memo,
                           folders=folders,
                           groups=groups,
                           image_url=_image_url)


# ─── 削除 ──────────────────────────────────────────────────────────
@memos.route("/<int:memo_id>/delete", methods=["POST"])
@login_required
def delete(memo_id: int):
    memo = Memo.query.get_or_404(memo_id)
    if memo.user_id != current_user.id:
        abort(403)

    for img in memo.images:
        for fname in (img.filename, img.thumb_name):
            if fname:
                _delete_from_storage(fname)

    db.session.delete(memo)
    db.session.commit()
    flash("メモを削除しました。", "success")
    return redirect(url_for("memos.list_memos"))


# ─── 画像個別削除 ────────────────────────────────────────────────────
@memos.route("/image/<int:image_id>/delete", methods=["POST"])
@login_required
def delete_image(image_id: int):
    img  = MemoImage.query.get_or_404(image_id)
    memo = Memo.query.get_or_404(img.memo_id)
    if memo.user_id != current_user.id:
        abort(403)

    for fname in (img.filename, img.thumb_name):
        if fname:
            _delete_from_storage(fname)

    db.session.delete(img)
    db.session.commit()
    return redirect(url_for("memos.edit", memo_id=memo.id))


# ─── 全体検索 ────────────────────────────────────────────────────────
@memos.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    memo_results = []
    todo_results = []

    if q:
        like = f"%{q}%"
        memo_results = (Memo.query
                        .filter_by(user_id=current_user.id)
                        .filter(db.or_(Memo.title.ilike(like), Memo.body.ilike(like)))
                        .order_by(Memo.updated_at.desc())
                        .limit(30).all())
        todo_results = (Todo.query
                        .filter_by(user_id=current_user.id)
                        .filter(db.or_(Todo.title.ilike(like), Todo.description.ilike(like)))
                        .order_by(Todo.created_at.desc())
                        .limit(20).all())

    return render_template("search.html",
                           q=q,
                           memo_results=memo_results,
                           todo_results=todo_results)
