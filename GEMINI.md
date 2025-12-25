# GEMINI.md - AI開発者向けガイド

このドキュメントは、本プロジェクトでAIアシスタント（Claude/Gemini等）と共同開発する際のガイドラインです。

## 🤖 開発環境

| 項目 | 内容 |
|------|------|
| IDE | Antigravity |
| AIアシスタント | Claude Opus 4.5 (Anthropic) |
| 開発スタイル | 会話ベースの反復開発 |

### GCP環境
| 項目 | 内容 |
|------|------|
| gcloud CLI | v549.0.1 (`/opt/homebrew/bin/gcloud`) |
| 設定ファイル | `.env` (gitignore済み) |

> **Note**: プロジェクトID、認証アカウント、GCSバケット名は `.env` を参照してください。

### Antigravityブラウザプロファイル

| 項目 | 内容 |
|------|------|
| プロファイルパス | `~/.gemini/antigravity-browser-profile` |
| ログインアカウント | `.env`の`BROWSER_LOGIN_EMAIL`を参照 |
| 永続化 | ✅ セッション間でログイン状態維持 |

> **Note**: Antigravityのブラウザサブエージェントは独自のChromeプロファイルを使用します。ユーザーの個人Chromeプロファイルとは別管理ですが、YouTubeなどへのログイン状態はセッションを超えて維持されます。

## 📂 プロジェクト構造

```
.
├── main.py              # エントリーポイント
├── config.py            # 設定管理（環境変数読み込み）
├── src/
│   ├── domain/          # ドメインモデル
│   │   └── models.py    # MatchDataクラス
│   ├── clients/         # 外部APIクライアント
│   │   └── cache.py     # APIキャッシュ（ローカル/GCS対応）
│   ├── utils/           # ユーティリティ
│   │   ├── formation_image.py   # フォーメーション図生成
│   │   ├── nationality_flags.py # 国名→国旗絵文字
│   │   └── spoiler_filter.py    # ネタバレフィルター
│   ├── match_processor.py   # 試合データ取得・選定
│   ├── facts_service.py     # スタメン・フォーメーション・国籍取得
│   ├── news_service.py      # ニュース収集・Gemini要約
│   ├── report_generator.py  # Markdownレポート生成
│   └── email_service.py     # Gmail APIメール送信
├── healthcheck/         # APIヘルスチェック
│   ├── check_football_api.py  # API-Football
│   ├── check_google_search.py # Google Custom Search
│   ├── check_gemini.py        # Gemini API
│   ├── check_gmail.py         # Gmail API
│   └── check_gcs_cache.py     # GCSキャッシュ状況
├── docs/
│   ├── requirement.md       # 詳細要件定義書
│   └── system_design.md     # システム設計書
├── tests/                   # API検証スクリプト
└── .github/workflows/       # GitHub Actions
```


## 🔧 開発コマンド

### 初回セットアップ（venv作成）

```bash
# Python 3.11でvenv作成（Homebrew版を使用）
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 依存パッケージ更新

```bash
source .venv/bin/activate
pip install --upgrade -r requirements.txt
```

### 実行コマンド（venv activate後）

```bash
source .venv/bin/activate

# モックモード（API不使用・高速テスト）
DEBUG_MODE=True USE_MOCK_DATA=True python main.py

# デバッグモード（実API・1試合のみ・国籍取得スキップ）
DEBUG_MODE=True USE_MOCK_DATA=False python main.py

# 本番モード（APIフル使用）
USE_MOCK_DATA=False python main.py
```


## 🔑 環境変数（Secrets）

| 変数名 | 用途 | 取得元 |
|--------|------|--------|
| `API_FOOTBALL_KEY` | API-Football | [API-Sports Dashboard](https://dashboard.api-football.com/) |
| `GOOGLE_API_KEY` | Gemini API | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `GOOGLE_SEARCH_ENGINE_ID` | Custom Search ID | [Programmable Search](https://programmablesearchengine.google.com/) |
| `GOOGLE_SEARCH_API_KEY` | Custom Search Key | [GCP Console](https://console.cloud.google.com/apis/credentials) |
| `GMAIL_TOKEN` | Gmail OAuth Token | `tests/setup_gmail_oauth.py` で生成 |
| `GMAIL_CREDENTIALS` | Gmail OAuth Client | GCP Console → OAuth 2.0 Client |
| `NOTIFY_EMAIL` | 送信先メールアドレス | 自分のGmail |
| `GMAIL_ENABLED` | メール送信有効化 | `True` / `False` |

### Gmail API セットアップ詳細

詳細は [README.md](./README.md#gmail-api-セットアップ詳細) を参照してください。

## 🚀 GitHub連携

### ghコマンドでの操作

```bash
# Secretsの設定
gh secret set API_FOOTBALL_KEY < <(grep "^API_FOOTBALL_KEY=" .env | cut -d'=' -f2-)

# ワークフロー手動実行
gh workflow run daily_report.yml

# 実行状況確認
gh run list --workflow="daily_report.yml" --limit 5

# ログ確認
gh run view <RUN_ID> --log

# Issue一覧
gh issue list --state all

# Issueクローズ
gh issue close <NUMBER> --comment "Fixed in commit xxx"
```

### リポジトリ設定

```bash
# Description設定
gh repo edit --description "説明文"

# Topics設定
gh repo edit --add-topic python --add-topic github-actions

# マージ後ブランチ自動削除
gh repo edit --delete-branch-on-merge
```

## ⚠️ API クォータ管理

> **📢 AI向け指示**: ユーザーが「クォータ確認して」「API確認して」と言った場合、以下のヘルスチェックスクリプトを順番に実行し、結果を報告すること。

```bash
# 全APIのクォータ・ステータス確認
python3 healthcheck/check_football_api.py
python3 healthcheck/check_google_search.py
python3 healthcheck/check_gemini.py
python3 healthcheck/check_gmail.py
```

### API-Football
- **有料版**: 7,500リクエスト/日（API-Sports 直接アクセス）
- **エンドポイント**: `https://v3.football.api-sports.io`
- **認証ヘッダー**: `x-apisports-key`
- **確認**: `python3 healthcheck/check_football_api.py`

### Google Custom Search
- **無料枠**: 100クエリ/日
- **確認**: `python3 healthcheck/check_google_search.py`

### Gemini API
- **無料枠の目安**: 1,500リクエスト/日（Google AI Pro は5時間ごとリフレッシュ想定）
- **確認**: `python3 healthcheck/check_gemini.py`
- 429が出たら数時間待つか軽量モデルに切替

### Gmail API
- **確認**: `python3 healthcheck/check_gmail.py`

### GCSキャッシュ
- **確認**: `python3 healthcheck/check_gcs_cache.py`
- チーム別選手キャッシュ状況を表示
- キャッシュウォーミング対象チームのカバレッジを確認可能

## 🌐 Web開発（Firebase Hosting）

### アーキテクチャ

```
┌─────────────────────────────────────────────────────┐
│                Firebase Hosting                      │
│  (https://football-delay-watching-a8830.web.app)    │
├─────────────────────────────────────────────────────┤
│  public/                                            │
│  ├── index.html          ← ログイン＋レポート一覧   │
│  └── reports/                                        │
│      ├── manifest.json   ← レポート一覧データ       │
│      ├── report_YYYY-MM-DD_HHMMSS.html ← 各レポート │
│      └── images/         ← フォーメーション図       │
└─────────────────────────────────────────────────────┘
```

### 関連ファイル

| ファイル | 役割 |
|---------|------|
| `src/html_generator.py` | Markdown→HTML変換、manifest.json更新 |
| `public/index.html` | ログイン画面＋レポート一覧表示 |
| `firebase.json` | Firebase Hosting設定 |
| `.github/workflows/daily_report.yml` | Actions→デプロイ |

### デプロイコマンド

```bash
# ローカルからデプロイ
firebase deploy --only hosting

# GitHub Actions経由（自動）
gh workflow run daily_report.yml
```

### ⚠️ AI向け重要注意事項

> **絶対に `rm -rf public/reports` を実行しないこと！**

Firebase Hostingは**毎回デプロイ時に`public/`の内容で完全に置き換える**。
ローカルにファイルがないと、Firebase上からも削除される。

**正しい開発フロー:**
1. `public/reports/` は削除せずに保持
2. 新しいHTMLは追記される
3. manifest.jsonはFirebaseから既存分をマージ

### manifest.jsonの仕組み

```json
{
  "reports": [
    {
      "datetime": "2025-12-23_071533",
      "file": "report_2025-12-23_071533.html",
      "generated": "2025-12-23 07:15:33 JST",
      "is_debug": false
    }
  ]
}
```

- `html_generator.py`がFirebase上のmanifest.jsonを取得
- 新規レポートを追加してマージ
- 重複除去して保存

### デバッグモードの識別

- `is_debug: true` → レポート一覧にDEBUGバッジ表示
- HTML本文: 「🔧 DEBUG MODE」バナー表示
- ブラウザタブ: `[DEBUG] サッカー観戦ガイド`

## 🧠 AIコーディング原則（プロSE向けガードレール）

### 1. 進め方（設計→実装の順序を徹底）
- **設計書を先に更新**: 仕様・I/Fをドキュメントに落とし、レビュー後に実装。設計変更なしのコード変更は禁止。
- **モジュール境界を意識**: 1ファイル=1責務。外部I/F（関数・クラス・APIコール）を先に固め、docstringと設計書を同期させる。
- **変更の「Why」を残す**: PR/コミットで根拠・代替案・影響範囲を簡潔に記録。プロンプトもバージョン管理（下記）。
- **小さくまとめて検証**: 変更は小さく刻み、テスト or 実行ログで裏付け。失敗時のロールバック手順を残す。
- **pushはチャット最後に**: コミットは随時行ってよいが、`git push`はチャットセッション終了時にまとめて実行する。

### 2. プロンプト設計チェックリスト（GOLDEN）
`Goal / Output / Limits / Data / Evaluation / Next` の6要素を必ず埋める。citeturn0search0  
- Goal: 目的と成功条件を1行で明示  
- Output: 形式・長さ・トーン（例: JSON / 600–1000字）  
- Limits: 禁止事項（ネタバレ・推測・スコア記述禁止）  
- Data: 最新3–5本のスニペットだけ渡す  
- Evaluation: 受入基準（禁止語・文字数・構造）  
- Next: 低信頼時の再試行や代替案

### 3. モデル別注意点
- **Gemini**: 検証・制約を短い箇条書きで明示。マルチモーダル/引用要否も書く。citeturn0search1  
- **複数モデル運用**: 出力差分を比較しログに残す（モデル差テスト推奨）。citeturn0search6

### 4. 失敗時ハンドリング
- 429/Quota: 5分間隔で最大3回リトライ。失敗時は `error_status=E3` + プレースホルダ文をセット。
- 5xx/Network: 1→2→4分バックオフ。
- モデル切替: `gemini-pro-latest` → `gemini-1.5-flash` → モック。切替はログに `model=fallback` を残す。

### 5. コンテキスト投入ルール
- スニペットは最新3–5本・各200–400字に圧縮。長文丸投げ禁止（混乱とコスト増を防ぐ）。citeturn0search2turn0search8
- 試合後疑いのある文には `[POSSIBLE SPOILER]` を付け、出力で無視させる。

### 6. プロンプト資産の管理
- プロンプトをリポジトリで版管理し、変更理由を残す（コードと同格でレビュー）。citeturn0search6
- 安定したプロンプトは `docs/prompts/` 等に置き、`AGENTS.md` から参照。

### 7. 実装ガード
- 新規APIコール前に `docs/system_design.md` / `docs/api_endpoints.md` を更新し、パラメータとレスポンス項目を確定させてから実装。
- モジュール分割: 高凝集・低結合。外部I/Fは小さく固定し、副作用のある処理（API/IO）は境界モジュールに隔離。
- 仕様未確定部分は「TODO: spec pending」と明示し、推測実装を禁止。

### 8. 評価とログ
- 生成物にはモデル名・リクエストID・リトライ回数をログ出力。
- 出力後に自動チェック: 禁止語、文字数、JSON構造、参照URL本数。NGならEステータスで表に出す。

## 📝 Issue対応フロー

1. `gh issue list` でIssue確認
2. `gh issue view <NUMBER>` で詳細確認
3. コード修正
4. コミットメッセージに `Closes #<NUMBER>` を含める
5. `git push` でIssueが自動クローズ

## 🔍 レビューモード

`guide_for_AGI/reviewer.md` に高度な技術レビュアー行動規範があります。
レビュー依頼時は「Reviewer Modeで確認して」と伝えてください。

## 📋 開発履歴（主要な変更）

| 日付 | 内容 |
|------|------|
| 2025-12-21 | API-Sports直接アクセスに移行（RapidAPI経由廃止） |
| 2025-12-14 | Gmail API経由のメール配信機能追加（Issue #5） |
| 2025-12-14 | Issue #2,#3 対応（ポジション別スタメン表示、国旗絵文字追加） |
| 2025-12-14 | GitHub Actions設定完了、Secrets連携 |
| 2025-12-14 | README作成、ドキュメント整理 |

## 💡 Tips

- **モック開発時**: `USE_MOCK_DATA=True` でAPIを消費せずテスト
- **デバッグモード**: 国籍取得をスキップしてクォータ節約
- **Issueテンプレート**: 背景→課題→対応方針→完了条件 の形式
- **コミットメッセージ**: `Closes #N` でIssue自動クローズ

## 🔒 セキュリティ注意事項（AIアシスタント向け）

> **⚠️ 機密ファイルは必ず `.gitignore` に追加すること**

以下のファイルは **絶対にリポジトリにコミットしてはならない**:

| ファイル種別 | 例 | 対応 |
|-------------|-----|------|
| API認証トークン | `token.json`, `*_token.json` | `.gitignore` に追加 |
| OAuth クレデンシャル | `credentials.json`, `client_secret_*.json` | `.gitignore` に追加 |
| 環境変数ファイル | `.env`, `.env.local` | `.gitignore` に追加（設定済み） |
| 秘密鍵・証明書 | `*.pem`, `*.key` | `.gitignore` に追加 |

### AI開発時のルール

1. **ファイル作成前に確認**: 機密情報を含むファイルを作成する前に、`.gitignore` に追加されているか確認
2. **ユーザーに確認**: 不明な場合は「このファイルを `.gitignore` に追加しますか？」と確認
3. **デフォルトで安全側**: 迷ったら# 現在の .gitignore に含まれる機密ファイル
.env
.env.local
