import os
from flask import Flask
from extensions import db, login_manager
from models import User
import config as cfg


def create_app() -> Flask:
    app = Flask(__name__)

    # ── 設定読み込み ───────────────────────────────────
    app.config.from_object(cfg)

    # ── 拡張初期化 ─────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    # ── Blueprint 登録 ────────────────────────────────
    from auth       import auth
    from memos      import memos
    from folders    import folders
    from todos      import todos
    from friends_bp import friends_bp
    from groups_bp  import groups_bp
    from timeline   import timeline

    app.register_blueprint(auth)
    app.register_blueprint(memos)
    app.register_blueprint(folders)
    app.register_blueprint(todos)
    app.register_blueprint(friends_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(timeline)

    # ── DB初期化 ──────────────────────────────────────
    with app.app_context():
        db.create_all()
        # アップロードフォルダ作成
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
