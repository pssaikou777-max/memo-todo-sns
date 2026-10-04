from datetime import datetime, timezone, date

from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from extensions import db
from models import Todo, Memo

todos = Blueprint("todos", __name__, url_prefix="/todos")


@todos.route("/")
@login_required
def list_todos():
    today  = date.today()
    # 今日・今週・期限なし・期限切れ に分類
    q = Todo.query.filter_by(user_id=current_user.id, completed=False).order_by(Todo.due_date.asc().nullslast())
    all_todos = q.all()

    today_todos   = [t for t in all_todos if t.due_date == today]
    overdue_todos = [t for t in all_todos if t.due_date and t.due_date < today]
    week_todos    = [t for t in all_todos if t.due_date and t.due_date > today]
    nodate_todos  = [t for t in all_todos if not t.due_date]

    done_todos = Todo.query.filter_by(user_id=current_user.id, completed=True)\
                           .order_by(Todo.completed_at.desc()).limit(20).all()

    return render_template("todos/list.html",
                           today_todos=today_todos,
                           overdue_todos=overdue_todos,
                           week_todos=week_todos,
                           nodate_todos=nodate_todos,
                           done_todos=done_todos,
                           today=today)


@todos.route("/new", methods=["GET", "POST"])
@login_required
def new():
    # メモ起源の場合: ?from_memo=<id> で呼ばれる
    from_memo_id = request.args.get("from_memo", type=int)
    memo = None
    if from_memo_id:
        memo = Memo.query.get(from_memo_id)
        if memo and memo.user_id != current_user.id:
            memo = None

    if request.method == "POST":
        title        = request.form.get("title", "").strip()
        description  = request.form.get("description", "").strip()
        due_str      = request.form.get("due_date", "")
        from_memo_id = request.form.get("from_memo_id", type=int)

        if not title:
            flash("タイトルを入力してください。", "error")
            return render_template("todos/edit.html", todo=None, memo=memo)

        due_date = None
        if due_str:
            try:
                due_date = date.fromisoformat(due_str)
            except ValueError:
                pass

        todo = Todo(user_id=current_user.id,
                    title=title,
                    description=description or None,
                    due_date=due_date)
        db.session.add(todo)
        db.session.commit()
        flash("TODOを追加しました。", "success")
        # メモから来た場合はメモ詳細へ戻る
        if from_memo_id:
            return redirect(url_for("memos.detail", memo_id=from_memo_id))
        return redirect(url_for("todos.list_todos"))

    return render_template("todos/edit.html", todo=None, memo=memo)


@todos.route("/<int:todo_id>/complete", methods=["POST"])
@login_required
def complete(todo_id: int):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != current_user.id:
        abort(403)
    todo.completed    = True
    todo.completed_at = datetime.now(timezone.utc)
    db.session.commit()
    return redirect(url_for("todos.list_todos"))


@todos.route("/<int:todo_id>/uncomplete", methods=["POST"])
@login_required
def uncomplete(todo_id: int):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != current_user.id:
        abort(403)
    todo.completed    = False
    todo.completed_at = None
    db.session.commit()
    return redirect(url_for("todos.list_todos"))


@todos.route("/<int:todo_id>/delete", methods=["POST"])
@login_required
def delete(todo_id: int):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != current_user.id:
        abort(403)
    db.session.delete(todo)
    db.session.commit()
    flash("TODOを削除しました。", "success")
    return redirect(url_for("todos.list_todos"))


@todos.route("/<int:todo_id>/edit", methods=["GET", "POST"])
@login_required
def edit(todo_id: int):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != current_user.id:
        abort(403)

    if request.method == "POST":
        title       = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_str     = request.form.get("due_date", "")

        if not title:
            flash("タイトルを入力してください。", "error")
        else:
            todo.title       = title
            todo.description = description or None
            due_date = None
            if due_str:
                try:
                    due_date = date.fromisoformat(due_str)
                except ValueError:
                    pass
            todo.due_date = due_date
            db.session.commit()
            flash("TODOを更新しました。", "success")
            return redirect(url_for("todos.list_todos"))

    return render_template("todos/edit.html", todo=todo)
