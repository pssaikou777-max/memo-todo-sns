from datetime import datetime, timezone, timedelta

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from extensions import db
from models import Memo, Todo, VISIBILITY_FRIENDS

timeline = Blueprint("timeline", __name__)


@timeline.route("/")
@login_required
def home():
    today      = datetime.now(timezone.utc).date()
    seven_days = datetime.now(timezone.utc) - timedelta(days=7)

    # ① 今日のTODO
    today_todos = (Todo.query
                   .filter_by(user_id=current_user.id, completed=False)
                   .filter(db.or_(Todo.due_date == today, Todo.due_date == None))
                   .order_by(Todo.due_date.asc().nullslast())
                   .limit(5).all())

    # ② 再発見（7日以上前・最終閲覧が古い順）
    rediscover = (Memo.query
                  .filter_by(user_id=current_user.id)
                  .filter(Memo.created_at <= seven_days)
                  .order_by(Memo.last_viewed_at.asc().nullsfirst(),
                            Memo.created_at.asc())
                  .limit(3).all())

    # ③ 友達の公開メモ
    from friends_bp import get_friend_ids
    friend_ids    = get_friend_ids(current_user.id)
    friends_memos = []
    if friend_ids:
        friends_memos = (Memo.query
                         .filter(Memo.user_id.in_(friend_ids))
                         .filter_by(visibility=VISIBILITY_FRIENDS)
                         .order_by(Memo.updated_at.desc())
                         .limit(5).all())

    # ④ 最近保存したメモ
    recent_memos = (Memo.query
                    .filter_by(user_id=current_user.id)
                    .order_by(Memo.updated_at.desc())
                    .limit(5).all())

    return render_template("home.html",
                           today_todos=today_todos,
                           rediscover=rediscover,
                           friends_memos=friends_memos,
                           recent_memos=recent_memos)
