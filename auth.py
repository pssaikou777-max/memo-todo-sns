from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User

auth = Blueprint("auth", __name__, url_prefix="/auth")

AVATAR_COLORS = [
    "#4a7cf7", "#e53935", "#43a047", "#fb8c00",
    "#8e24aa", "#00897b", "#f4511e", "#1e88e5",
]


@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("timeline.home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")

        error = None
        if not username:
            error = "ユーザー名を入力してください。"
        elif not email:
            error = "メールアドレスを入力してください。"
        elif not password:
            error = "パスワードを入力してください。"
        elif password != confirm:
            error = "パスワードが一致しません。"
        elif User.query.filter_by(username=username).first():
            error = "このユーザー名はすでに使われています。"
        elif User.query.filter_by(email=email).first():
            error = "このメールアドレスはすでに登録されています。"

        if error:
            flash(error, "error")
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("timeline.home"))

    return render_template("auth/register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("timeline.home"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("timeline.home"))
        flash("メールアドレスまたはパスワードが正しくありません。", "error")

    return render_template("auth/login.html")


@auth.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip()
        bio          = request.form.get("bio", "").strip()
        avatar_color = request.form.get("avatar_color", "").strip()

        current_user.display_name = display_name or None
        current_user.bio          = bio or None
        if avatar_color in AVATAR_COLORS:
            current_user.avatar_color = avatar_color
        db.session.commit()
        flash("プロフィールを更新しました。", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html",
                           avatar_colors=AVATAR_COLORS)
