# Pythonアプリ 一般公開ロードマップ
## 〜ゼロから他の人が触れる状態までの完全手順〜

このドキュメントは「メモ×TODO×SNS」アプリの開発・公開を通じて確立した  
**Pythonアプリを一般公開するまでの汎用ロードマップ**です。  
次のアプリでも同じ流れで進められます。

---

## 全体の流れ

```
① アプリ設計・技術スタック決定
    ↓
② ローカル開発（コーディング・動作確認）
    ↓
③ GitHub push
    ↓
④ Supabase セットアップ（DB・Storage）
    ↓
⑤ Render デプロイ
    ↓
⑥ 本番動作確認
    ↓
⑦ 一般公開・ユーザーテスト
    ↓
⑧ Issue管理・改善サイクル
```

---

## STEP 1：アプリ設計

### 決めること
- アプリの目的・ターゲットユーザー
- 技術スタック（後述の推奨構成を参照）
- DBモデル（テーブル・カラム設計）
- URLルーティング一覧
- 公開設定・認証が必要かどうか

### 推奨技術スタック（Python Webアプリ）

| 区分 | 採用技術 | 理由 |
|------|---------|------|
| バックエンド | Python + Flask | シンプル・軽量 |
| DB（本番） | Supabase PostgreSQL | 無料・信頼性高 |
| DB（ローカル） | SQLite（自動フォールバック） | 設定不要 |
| ORM | SQLAlchemy 2.x | 安全・可読性高 |
| 認証 | Flask-Login + Werkzeug | 実績あり |
| 画像保存 | Supabase Storage | 無料1GB |
| ホスティング | Render（Free プラン） | GitHub連携・無料 |

---

## STEP 2：ローカル開発

### 必須ファイル構成

```
myapp/
├── app.py              # create_app() で Flask アプリを生成
├── config.py           # 環境変数読み込み・設定
├── extensions.py       # db = SQLAlchemy() など拡張インスタンス
├── models.py           # DBモデル定義
├── wsgi.py             # gunicorn用エントリポイント
├── render.yaml         # Renderデプロイ設定
├── requirements.txt    # 依存パッケージ
├── .env                # ローカル環境変数（Git管理外）
├── .env.example        # 環境変数テンプレート（値入りで手元保存）
├── .gitignore          # .env / *.db / __pycache__ 等を除外
├── static/
└── templates/
```

### config.py のポイント

```python
import os
from dotenv import load_dotenv
load_dotenv()

# DB: 本番はSUPABASE、ローカルはSQLiteに自動切替
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
else:
    SQLALCHEMY_DATABASE_URI = "sqlite:///myapp.db"
```

### requirements.txt の最低構成

```
Flask>=3.0
Flask-Login>=0.6
Flask-SQLAlchemy>=3.0
Werkzeug>=3.0
Pillow>=10.0
psycopg2-binary>=2.9
gunicorn>=21.2
supabase>=2.0
python-dotenv>=1.0
```

### wsgi.py

```python
from app import app

if __name__ == "__main__":
    app.run()
```

### .gitignore の最低構成

```
__pycache__/
*.pyc
*.db
*.sqlite3
.env
.venv/
venv/
static/uploads/*
!static/uploads/.gitkeep
```

### ローカル動作確認コマンド

```bash
pip install -r requirements.txt
python app.py
# http://localhost:5000 で確認
```

---

## STEP 3：GitHub push

### 初回（リポジトリ新規作成時）

```bash
# GitHub でリポジトリを作成してから
git init
git add -A
git commit -m "initial commit"
git remote add origin https://github.com/ユーザー名/リポジトリ名.git
git push -u origin main
```

### 2回目以降（変更を push するとき）

```bash
git add -A
git commit -m "変更内容の説明"
git push origin main
```

### ⚠ 注意
- `.env` は絶対に push しない（.gitignore に入れること）
- `*.db` も push しない（本番DBはSupabaseを使う）

---

## STEP 4：Supabase セットアップ

### 4-1. プロジェクト作成

1. https://supabase.com にアクセス → GitHub でサインイン
2. 「New project」→ プロジェクト名・DBパスワード・リージョン（Tokyo: ap-northeast-1）を設定
3. 作成完了まで約1分待つ

### 4-2. 接続情報の取得

| 項目 | 取得場所 |
|------|---------|
| `SUPABASE_URL` | Settings → API → Project URL |
| `SUPABASE_KEY` | Settings → API → anon public キー（`sb_publishable_...`） |
| `DATABASE_URL` | 上部「Connect」ボタン → **Session pooler** → URI |

### ⚠ 接続方法の選択

| 方式 | ホスト | 用途 |
|------|--------|------|
| Direct | `db.xxxx.supabase.co:5432` | IPv6環境のみ |
| **Session pooler** | `aws-0-ap-northeast-1.pooler.supabase.com:5432` | **IPv4環境はこちら（Render含む）** |
| Transaction pooler | 同上:6543 | サーバーレス向け |

**RenderはIPv4なので必ずSession poolerを使うこと。**

### DATABASE_URL の形式

```
# Session Pooler の場合（ユーザー名に .プロジェクトID が付く）
postgresql://postgres.プロジェクトID:パスワード@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres

# config.py で postgresql+psycopg2:// に自動変換される
```

### 4-3. Storage バケット作成（画像機能がある場合）

1. 左メニュー「Storage」→「New bucket」
2. バケット名: `memo-images`（任意）
3. **「Public bucket」にチェック**
4. Save

---

## STEP 5：Render デプロイ

### render.yaml の基本構成

```yaml
services:
  - type: web
    name: myapp
    env: python
    region: oregon
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn wsgi:app --workers 2 --bind 0.0.0.0:$PORT
    envVars:
      - key: SECRET_KEY
        generateValue: true
      - key: PYTHON_VERSION
        value: "3.11.0"
      - key: DATABASE_URL
        sync: false
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_KEY
        sync: false
      - key: SUPABASE_BUCKET
        value: "memo-images"
```

### デプロイ手順

1. https://render.com → GitHub でサインイン
2. 「New +」→「Web Service」
3. GitHubリポジトリを選択 → Connect
4. 設定を確認：
   - Start Command: `gunicorn wsgi:app --workers 2 --bind 0.0.0.0:$PORT`
   - Plan: **Free（$0/month）**
5. 「Environment Variables」に以下を追加：
   - `DATABASE_URL`: Supabase Session Pooler の接続文字列
   - `SUPABASE_URL`: Supabase Project URL
   - `SUPABASE_KEY`: Supabase anon key
   - `SECRET_KEY`: 任意の長いランダム文字列
   - `SUPABASE_BUCKET`: `memo-images`
6. 「Deploy web service」をクリック
7. ログに `Your service is live 🎉` が出ればOK

### デプロイ後のURL形式

```
https://アプリ名.onrender.com
```

---

## STEP 6：本番動作確認チェックリスト

- [ ] URLにアクセスしてログイン画面が表示される
- [ ] ユーザー登録ができる
- [ ] ログイン・ログアウトができる
- [ ] 主要機能（CRUD）が動作する
- [ ] 画像アップロードが動作する（Supabase Storageに保存されるか）
- [ ] DBにデータが保存されている（Supabase → Table Editor で確認）

---

## STEP 7：一般公開・ユーザーテスト

- URLを共有するだけで誰でも登録・使用可能
- スマホからも動作確認する
- 自分＋数人で1〜2週間使ってみる

---

## STEP 8：Issue管理・改善サイクル

### GitHub Issueの使い方

1. GitHubリポジトリ → 「Issues」タブ → 「New issue」
2. タイトル: `[バグ] ○○が動かない` / `[改善] ○○を追加したい`
3. 内容: 再現手順・期待動作・実際の動作を記載
4. BOBにIssue内容を渡す → 修正 → `git push` → 自動デプロイ

### 自動デプロイの仕組み

```
コード修正 → git push → GitHubにコード反映
                ↓
           Render が変更を検知（自動）
                ↓
           自動ビルド・デプロイ（約2〜3分）
                ↓
           本番に反映
```

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| DB接続エラー（IPv6） | Direct接続 + IPv4環境 | Session poolerに切り替え |
| `ModuleNotFoundError` | requirements.txt に未記載 | 追加して再push |
| ページが遅い（初回） | Renderスリープ | Free→有料プランで解消 |
| 画像が表示されない | Storageバケット非公開 | Public bucketに変更 |
| ログイン後データがない | ローカルDBと本番DBは別 | 本番で再登録（正常動作） |
| `AppenderQuery has no len()` | lazy="dynamic"リレーション | `.all()` か `.count()` を使う |

---

## 所要時間の目安

| ステップ | 所要時間 |
|---------|---------|
| アプリ設計 | 1〜2時間 |
| ローカル開発（Phase1） | 4〜8時間 |
| ローカル開発（Phase2以降） | 2〜4時間/Phase |
| GitHub push | 5分 |
| Supabase セットアップ | 15〜30分 |
| Render デプロイ | 10〜20分 |
| 動作確認 | 30分 |
| **合計（最小MVP）** | **約1日** |
