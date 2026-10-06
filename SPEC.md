# メモ×TODO×SNS アプリ 仕様書

## 概要

「思いついたことを全部入れておく場所」として使う軽量Webアプリ。  
時間が経つと過去の自分が保存したメモが再発見タイムラインに戻ってくる。  
友達の公開メモも流れてくる。TODO管理も一体化。

- **本番URL**: https://memo-todo-sns.onrender.com  
- **GitHub**: https://github.com/pssaikou777-max/memo-todo-sns  
- **DB**: Supabase PostgreSQL（東京 ap-northeast-1）  
- **画像**: Supabase Storage（バケット: memo-images）  
- **ホスティング**: Render（Free プラン）

---

## 技術スタック

| 区分 | 採用技術 |
|------|---------|
| バックエンド | Python 3.11 + Flask 3.x |
| DB（本番） | Supabase PostgreSQL 17（Session Pooler経由） |
| DB（ローカル） | SQLite（自動フォールバック） |
| ORM | SQLAlchemy 2.x |
| 認証 | Flask-Login + Werkzeug パスワードハッシュ |
| フロントエンド | Jinja2テンプレート + Vanilla CSS |
| 画像保存（本番） | Supabase Storage |
| 画像保存（ローカル） | static/uploads/ |
| Webサーバー | gunicorn（本番） / Flask開発サーバー（ローカル） |
| デプロイ | Render（render.yaml で設定） |

---

## ディレクトリ構成

```
memo_todo_sns/
├── app.py              # Flaskアプリ本体・起動エントリポイント
├── config.py           # 設定（SECRET_KEY, DB URI, Supabase等）
├── extensions.py       # db / login_manager インスタンス
├── models.py           # SQLAlchemyモデル定義
├── auth.py             # 認証Blueprint（登録・ログイン・ログアウト）
├── memos.py            # メモBlueprint（CRUD・画像・検索）
├── todos.py            # TODOBlueprint（CRUD・完了管理）
├── folders.py          # フォルダBlueprint（CRUD）
├── groups_bp.py        # グループBlueprint（CRUD）
├── friends_bp.py       # 友達Blueprint（申請・承認・削除）
├── timeline.py         # ホーム・再発見タイムラインBlueprint
├── wsgi.py             # gunicorn エントリポイント
├── render.yaml         # Render デプロイ設定
├── requirements.txt    # Python依存パッケージ
├── .env                # ローカル環境変数（Git管理外）
├── .env.example        # 環境変数サンプル（値入り・手元保存用）
├── .gitignore
├── static/
│   ├── css/style.css   # メインCSS（スマホ優先）
│   ├── js/app.js       # 最小限JS
│   ├── icons/          # PWAアイコン
│   ├── manifest.json   # PWAマニフェスト
│   └── uploads/        # ローカル画像保存先
└── templates/
    ├── base.html           # ベーステンプレート（下部ナビ・サイドナビ）
    ├── home.html           # ホーム（再発見・友達投稿・最近のメモ）
    ├── search.html         # 全体検索結果
    ├── auth/
    │   ├── login.html
    │   └── register.html
    ├── memos/
    │   ├── list.html       # メモ一覧（フォルダ絞込・検索）
    │   ├── detail.html     # メモ詳細
    │   └── edit.html       # メモ作成・編集
    ├── todos/
    │   ├── list.html       # TODO一覧（今日・今週・期限切れ・完了）
    │   └── edit.html       # TODO作成・編集
    ├── folders/
    │   ├── list.html
    │   └── edit.html
    ├── groups/
    │   ├── list.html
    │   ├── detail.html
    │   └── edit.html
    └── friends/
        ├── list.html
        └── search.html
```

---

## DBモデル一覧

| モデル | テーブル | 主要カラム |
|--------|---------|-----------|
| User | users | id, username, email, password_hash, created_at |
| Memo | memos | id, user_id, title, body, folder_id, visibility, created_at, updated_at, last_viewed_at |
| MemoImage | memo_images | id, memo_id, filename, thumb_name, created_at |
| Folder | folders | id, user_id, name, created_at |
| Group | groups | id, user_id, name, created_at |
| MemoGroup | memo_groups | memo_id, group_id（中間テーブル） |
| Todo | todos | id, user_id, title, description, due_date, completed, created_at, completed_at |
| Friendship | friendships | id, requester_id, receiver_id, status, created_at |

---

## URLルーティング一覧

| エンドポイント | メソッド | URL | 説明 |
|--------------|---------|-----|------|
| timeline.home | GET | / | ホーム（要ログイン） |
| auth.register | GET/POST | /auth/register | ユーザー登録 |
| auth.login | GET/POST | /auth/login | ログイン |
| auth.logout | GET | /auth/logout | ログアウト |
| memos.list_memos | GET | /memos/ | メモ一覧 |
| memos.new | GET/POST | /memos/new | メモ作成 |
| memos.detail | GET | /memos/<id> | メモ詳細 |
| memos.edit | GET/POST | /memos/<id>/edit | メモ編集 |
| memos.delete | POST | /memos/<id>/delete | メモ削除 |
| memos.search | GET | /memos/search | 全体検索 |
| memos.delete_image | POST | /memos/image/<id>/delete | 画像削除 |
| todos.list_todos | GET | /todos/ | TODO一覧 |
| todos.new | GET/POST | /todos/new | TODO作成 |
| todos.edit | GET/POST | /todos/<id>/edit | TODO編集 |
| todos.complete | POST | /todos/<id>/complete | TODO完了 |
| todos.uncomplete | POST | /todos/<id>/uncomplete | TODO未完了に戻す |
| todos.delete | POST | /todos/<id>/delete | TODO削除 |
| folders.list_folders | GET | /folders/ | フォルダ一覧 |
| folders.new | GET/POST | /folders/new | フォルダ作成 |
| folders.edit | GET/POST | /folders/<id>/edit | フォルダ編集 |
| folders.delete | POST | /folders/<id>/delete | フォルダ削除 |
| groups.list_groups | GET | /groups/ | グループ一覧 |
| groups.new | GET/POST | /groups/new | グループ作成 |
| groups.detail | GET | /groups/<id> | グループ詳細 |
| groups.edit | GET/POST | /groups/<id>/edit | グループ編集 |
| groups.delete | POST | /groups/<id>/delete | グループ削除 |
| friends.list_friends | GET | /friends/ | 友達一覧 |
| friends.search | GET | /friends/search | ユーザー検索 |
| friends.send_request | POST | /friends/request/<id> | 友達申請 |
| friends.accept | POST | /friends/accept/<id> | 申請承認 |
| friends.reject | POST | /friends/reject/<id> | 申請拒否 |
| friends.remove | POST | /friends/remove/<id> | 友達削除 |

---

## 公開設定

| 値 | 意味 |
|----|------|
| `private` | 自分のみ（デフォルト） |
| `friends` | 友達のタイムラインに表示 |
| `public` | 全体公開（将来対応） |

---

## 環境変数

| キー | 説明 | 必須 |
|------|------|------|
| `SECRET_KEY` | Flaskセッション暗号化キー | ✅ |
| `DATABASE_URL` | PostgreSQL接続文字列 | 本番のみ必須 |
| `SUPABASE_URL` | Supabase Project URL | 画像機能に必要 |
| `SUPABASE_KEY` | Supabase anon key | 画像機能に必要 |
| `SUPABASE_BUCKET` | Storageバケット名（memo-images） | 画像機能に必要 |

---

## ローカル起動手順

```bash
cd memo_todo_sns
pip install -r requirements.txt
# .env ファイルを作成（.env.example を参考に）
python app.py
# ブラウザ: http://localhost:5000
```

---

## 開発フェーズ

| Phase | 内容 | 状態 |
|-------|------|------|
| Phase 1 | 認証・メモCRUD・フォルダ・画像・基本UI | ✅ 完了 |
| Phase 2 | TODO・メモTODO連携・グループ・検索 | ✅ 完了 |
| Phase 3 | 再発見タイムライン強化 | 未着手 |
| Phase 4 | 友達・公開設定・友達タイムライン強化 | 未着手 |
| Phase 5 | PWA・スマホUI最適化 | 未着手 |
| Phase 6 | AI連携 | 未着手 |
| Phase 7 | 収益化（広告・サブスク） | 未着手 |
