from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from extensions import db
from models import Group, Memo

groups_bp = Blueprint("groups", __name__, url_prefix="/groups")


@groups_bp.route("/")
@login_required
def list_groups():
    all_groups = Group.query.filter_by(user_id=current_user.id).order_by(Group.name).all()
    return render_template("groups/list.html", groups=all_groups)


@groups_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("グループ名を入力してください。", "error")
        elif Group.query.filter_by(user_id=current_user.id, name=name).first():
            flash("同じ名前のグループが既に存在します。", "error")
        else:
            db.session.add(Group(user_id=current_user.id, name=name))
            db.session.commit()
            flash(f"グループ「{name}」を作成しました。", "success")
            return redirect(url_for("groups.list_groups"))
    return render_template("groups/edit.html", group=None)


@groups_bp.route("/<int:group_id>")
@login_required
def detail(group_id: int):
    group = Group.query.get_or_404(group_id)
    if group.user_id != current_user.id:
        abort(403)
    memos = sorted(group.memos, key=lambda m: m.updated_at, reverse=True)
    return render_template("groups/detail.html", group=group, memos=memos)


@groups_bp.route("/<int:group_id>/edit", methods=["GET", "POST"])
@login_required
def edit(group_id: int):
    group = Group.query.get_or_404(group_id)
    if group.user_id != current_user.id:
        abort(403)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("グループ名を入力してください。", "error")
        else:
            group.name = name
            db.session.commit()
            flash("グループ名を更新しました。", "success")
            return redirect(url_for("groups.list_groups"))
    return render_template("groups/edit.html", group=group)


@groups_bp.route("/<int:group_id>/delete", methods=["POST"])
@login_required
def delete(group_id: int):
    group = Group.query.get_or_404(group_id)
    if group.user_id != current_user.id:
        abort(403)
    db.session.delete(group)
    db.session.commit()
    flash("グループを削除しました。", "success")
    return redirect(url_for("groups.list_groups"))
