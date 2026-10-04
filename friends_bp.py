from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from extensions import db
from models import User, Friendship, FRIEND_PENDING, FRIEND_ACCEPTED

friends_bp = Blueprint("friends", __name__, url_prefix="/friends")


def get_friend_ids(user_id: int) -> list[int]:
    """承認済み友達のIDリストを返す"""
    sent = (db.session.query(Friendship.receiver_id)
            .filter_by(requester_id=user_id, status=FRIEND_ACCEPTED).all())
    received = (db.session.query(Friendship.requester_id)
                .filter_by(receiver_id=user_id, status=FRIEND_ACCEPTED).all())
    return [r[0] for r in sent] + [r[0] for r in received]


@friends_bp.route("/")
@login_required
def list_friends():
    friend_ids = get_friend_ids(current_user.id)
    friends    = User.query.filter(User.id.in_(friend_ids)).all() if friend_ids else []

    # 受信中の申請
    pending_in = (Friendship.query
                  .filter_by(receiver_id=current_user.id, status=FRIEND_PENDING).all())
    # 送信中の申請
    pending_out = (Friendship.query
                   .filter_by(requester_id=current_user.id, status=FRIEND_PENDING).all())

    return render_template("friends/list.html",
                           friends=friends,
                           pending_in=pending_in,
                           pending_out=pending_out)


@friends_bp.route("/search")
@login_required
def search():
    q       = request.args.get("q", "").strip()
    results = []
    if q:
        results = (User.query
                   .filter(User.id != current_user.id)
                   .filter(db.or_(
                       User.username.ilike(f"%{q}%"),
                       User.email.ilike(f"%{q}%")))
                   .limit(20).all())
    return render_template("friends/search.html", results=results, q=q)


@friends_bp.route("/request/<int:user_id>", methods=["POST"])
@login_required
def send_request(user_id: int):
    if user_id == current_user.id:
        flash("自分には申請できません。", "error")
        return redirect(url_for("friends.search"))

    target = User.query.get_or_404(user_id)

    # 既存チェック
    existing = Friendship.query.filter(
        db.or_(
            db.and_(Friendship.requester_id == current_user.id,
                    Friendship.receiver_id  == user_id),
            db.and_(Friendship.requester_id == user_id,
                    Friendship.receiver_id  == current_user.id),
        )
    ).first()

    if existing:
        flash("既に申請済みか友達です。", "error")
    else:
        db.session.add(Friendship(requester_id=current_user.id,
                                  receiver_id=user_id))
        db.session.commit()
        flash(f"{target.username} さんに友達申請を送りました。", "success")

    return redirect(url_for("friends.search"))


@friends_bp.route("/accept/<int:friendship_id>", methods=["POST"])
@login_required
def accept(friendship_id: int):
    f = Friendship.query.get_or_404(friendship_id)
    if f.receiver_id != current_user.id:
        abort(403)
    f.status = FRIEND_ACCEPTED
    db.session.commit()
    flash("友達申請を承認しました。", "success")
    return redirect(url_for("friends.list_friends"))


@friends_bp.route("/reject/<int:friendship_id>", methods=["POST"])
@login_required
def reject(friendship_id: int):
    f = Friendship.query.get_or_404(friendship_id)
    if f.receiver_id != current_user.id:
        abort(403)
    db.session.delete(f)
    db.session.commit()
    flash("友達申請を拒否しました。", "success")
    return redirect(url_for("friends.list_friends"))


@friends_bp.route("/remove/<int:user_id>", methods=["POST"])
@login_required
def remove(user_id: int):
    f = Friendship.query.filter(
        db.or_(
            db.and_(Friendship.requester_id == current_user.id,
                    Friendship.receiver_id  == user_id),
            db.and_(Friendship.requester_id == user_id,
                    Friendship.receiver_id  == current_user.id),
        )
    ).first()
    if f:
        db.session.delete(f)
        db.session.commit()
        flash("友達を削除しました。", "success")
    return redirect(url_for("friends.list_friends"))
