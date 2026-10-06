from datetime import datetime, timezone, date, time, timedelta
import calendar

from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Todo, Memo

todos = Blueprint("todos", __name__, url_prefix="/todos")

REPEAT_LABELS = {
    "none":    "繰り返しなし",
    "daily":   "毎日",
    "weekly":  "毎週",
    "monthly": "毎月",
}


def _get_root_todos(user_id: int):
    """ルートTODO（親なし）を order_index 順で返す"""
    return (
        Todo.query
        .filter_by(user_id=user_id, parent_id=None)
        .order_by(Todo.order_index.asc(), Todo.id.asc())
        .all()
    )


def _build_tree(root_todos):
    """ルートリストからツリー構造（各 Todo に .kids リストを付与）を返す"""
    def attach(todo):
        kids = (
            Todo.query
            .filter_by(parent_id=todo.id)
            .order_by(Todo.order_index.asc(), Todo.id.asc())
            .all()
        )
        todo.kids = kids
        for k in kids:
            attach(k)
        return todo
    return [attach(t) for t in root_todos]


def _spawn_repeat(todo: Todo) -> None:
    """繰り返し設定があれば次回分 Todo を生成して DB に追加"""
    if todo.repeat_type == "none" or not todo.due_date:
        return
    if todo.repeat_type == "daily":
        next_date = todo.due_date + timedelta(days=1)
    elif todo.repeat_type == "weekly":
        next_date = todo.due_date + timedelta(weeks=1)
    elif todo.repeat_type == "monthly":
        # 月末対応
        m = todo.due_date.month % 12 + 1
        y = todo.due_date.year + (1 if todo.due_date.month == 12 else 0)
        d = min(todo.due_date.day, calendar.monthrange(y, m)[1])
        next_date = date(y, m, d)
    else:
        return

    new_todo = Todo(
        user_id=todo.user_id,
        title=todo.title,
        description=todo.description,
        due_date=next_date,
        due_time=todo.due_time,
        parent_id=todo.parent_id,
        order_index=todo.order_index,
        repeat_type=todo.repeat_type,
    )
    db.session.add(new_todo)


# ── 一覧（ツリー＋カレンダー）─────────────────────────────────────
@todos.route("/")
@login_required
def list_todos():
    today = date.today()
    view  = request.args.get("view", "tree")   # tree / calendar

    # カレンダービュー用
    cal_year  = request.args.get("year",  today.year,  type=int)
    cal_month = request.args.get("month", today.month, type=int)
    if cal_month < 1:
        cal_month = 12; cal_year -= 1
    if cal_month > 12:
        cal_month = 1;  cal_year += 1

    # ツリービュー用
    root_todos = _get_root_todos(current_user.id)
    tree       = _build_tree(root_todos)

    # カレンダービュー用：当月の全 TODO
    first_day = date(cal_year, cal_month, 1)
    last_day  = date(cal_year, cal_month, calendar.monthrange(cal_year, cal_month)[1])
    cal_todos = (
        Todo.query
        .filter(
            Todo.user_id == current_user.id,
            Todo.due_date >= first_day,
            Todo.due_date <= last_day,
        )
        .order_by(Todo.due_date, Todo.due_time.asc().nullslast())
        .all()
    )
    # {date: [todo, ...]}
    cal_map = {}
    for t in cal_todos:
        cal_map.setdefault(t.due_date, []).append(t)

    # カレンダーグリッド（週ごとのリスト）
    cal_weeks = calendar.monthcalendar(cal_year, cal_month)

    return render_template(
        "todos/list.html",
        tree=tree,
        today=today,
        view=view,
        cal_year=cal_year,
        cal_month=cal_month,
        cal_weeks=cal_weeks,
        cal_map=cal_map,
        repeat_labels=REPEAT_LABELS,
    )


# ── 新規作成 ──────────────────────────────────────────────────────
@todos.route("/new", methods=["GET", "POST"])
@login_required
def new():
    from_memo_id = request.args.get("from_memo", type=int)
    parent_id    = request.args.get("parent_id", type=int)
    memo = None
    if from_memo_id:
        memo = Memo.query.get(from_memo_id)
        if memo and memo.user_id != current_user.id:
            memo = None

    if request.method == "POST":
        title       = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_str     = request.form.get("due_date", "")
        time_str    = request.form.get("due_time", "")
        repeat_type = request.form.get("repeat_type", "none")
        parent_id   = request.form.get("parent_id", type=int)
        from_memo_id = request.form.get("from_memo_id", type=int)

        if not title:
            flash("タイトルを入力してください。", "error")
            return render_template("todos/edit.html", todo=None, memo=memo,
                                   parent_id=parent_id, repeat_labels=REPEAT_LABELS)

        due_date = None
        if due_str:
            try:
                due_date = date.fromisoformat(due_str)
            except ValueError:
                pass

        due_time_val = None
        if time_str:
            try:
                h, m = map(int, time_str.split(":"))
                due_time_val = time(h, m)
            except (ValueError, AttributeError):
                pass

        # 同じ親の下の order_index を自動採番
        sibling_count = Todo.query.filter_by(user_id=current_user.id, parent_id=parent_id).count()

        todo = Todo(
            user_id=current_user.id,
            title=title,
            description=description or None,
            due_date=due_date,
            due_time=due_time_val,
            parent_id=parent_id,
            order_index=sibling_count,
            repeat_type=repeat_type if repeat_type in REPEAT_LABELS else "none",
        )
        db.session.add(todo)
        db.session.commit()
        flash("TODOを追加しました。", "success")
        if from_memo_id:
            return redirect(url_for("memos.detail", memo_id=from_memo_id))
        return redirect(url_for("todos.list_todos"))

    return render_template("todos/edit.html", todo=None, memo=memo,
                           parent_id=parent_id, repeat_labels=REPEAT_LABELS)


# ── 完了 ──────────────────────────────────────────────────────────
@todos.route("/<int:todo_id>/complete", methods=["POST"])
@login_required
def complete(todo_id: int):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != current_user.id:
        abort(403)
    todo.completed    = True
    todo.completed_at = datetime.now(timezone.utc)
    db.session.commit()
    _spawn_repeat(todo)
    db.session.commit()
    return redirect(url_for("todos.list_todos"))


# ── 未完了に戻す ──────────────────────────────────────────────────
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


# ── 削除 ──────────────────────────────────────────────────────────
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


# ── 編集 ──────────────────────────────────────────────────────────
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
        time_str    = request.form.get("due_time", "")
        repeat_type = request.form.get("repeat_type", "none")

        if not title:
            flash("タイトルを入力してください。", "error")
        else:
            todo.title       = title
            todo.description = description or None
            todo.repeat_type = repeat_type if repeat_type in REPEAT_LABELS else "none"

            todo.due_date = None
            if due_str:
                try:
                    todo.due_date = date.fromisoformat(due_str)
                except ValueError:
                    pass

            todo.due_time = None
            if time_str:
                try:
                    h, m = map(int, time_str.split(":"))
                    todo.due_time = time(h, m)
                except (ValueError, AttributeError):
                    pass

            db.session.commit()
            flash("TODOを更新しました。", "success")
            return redirect(url_for("todos.list_todos"))

    return render_template("todos/edit.html", todo=todo,
                           repeat_labels=REPEAT_LABELS)
