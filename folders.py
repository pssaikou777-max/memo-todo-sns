from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from extensions import db
from models import Folder, Memo

folders = Blueprint("folders", __name__, url_prefix="/folders")


@folders.route("/")
@login_required
def list_folders():
    all_folders = Folder.query.filter_by(user_id=current_user.id).order_by(Folder.name).all()
    return render_template("folders/list.html", folders=all_folders)


@folders.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("フォルダ名を入力してください。", "error")
        elif Folder.query.filter_by(user_id=current_user.id, name=name).first():
            flash("同じ名前のフォルダが既に存在します。", "error")
        else:
            db.session.add(Folder(user_id=current_user.id, name=name))
            db.session.commit()
            flash(f"フォルダ「{name}」を作成しました。", "success")
            return redirect(url_for("folders.list_folders"))
    return render_template("folders/edit.html", folder=None)


@folders.route("/<int:folder_id>/edit", methods=["GET", "POST"])
@login_required
def edit(folder_id: int):
    folder = Folder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id:
        abort(403)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("フォルダ名を入力してください。", "error")
        else:
            folder.name = name
            db.session.commit()
            flash("フォルダ名を更新しました。", "success")
            return redirect(url_for("folders.list_folders"))
    return render_template("folders/edit.html", folder=folder)


@folders.route("/<int:folder_id>/delete", methods=["POST"])
@login_required
def delete(folder_id: int):
    folder = Folder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id:
        abort(403)
    # フォルダ内メモのfolder_idをNullに
    Memo.query.filter_by(folder_id=folder_id).update({"folder_id": None})
    db.session.delete(folder)
    db.session.commit()
    flash("フォルダを削除しました。", "success")
    return redirect(url_for("folders.list_folders"))
