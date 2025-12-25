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
│   ├── youtube_service.py   # YouTube動画検索
│   ├── report_generator.py  # Markdownレポート生成
│   ├── html_generator.py    # HTML変換・Firebase manifest管理
│   └── email_service.py     # Gmail APIメール送信
├── settings/            # 設定ファイル
│   └── channels.py      # YouTubeチャンネル優先度設定
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

### ⚠️ 重要: Python実行パス

> ローカルには複数のPythonバージョンが存在するため、**必ず `/usr/local/bin/python` (3.11.11) を使用すること**

```bash
# バージョン確認
/usr/local/bin/python --version  # Python 3.11.11

# 実行時は python コマンドで OK（/usr/local/bin が優先される）
python main.py
```

### 実行モード

| モード | コマンド | 用途 |
|--------|---------|------|
| **モック** | `DEBUG_MODE=True USE_MOCK_DATA=True python main.py` | API不使用・高速テスト |
| **デバッグ** | `DEBUG_MODE=True USE_MOCK_DATA=False python main.py` | 実API・1試合のみ |
| **本番** | `USE_MOCK_DATA=False python main.py` | APIフル使用 |

### デバッグ後のデプロイ

デバッグ実行後は以下でWEBに反映:
```bash
firebase deploy --only hosting
```

または `/debug-run` ワークフローを使用（実行→デプロイまで自動）

## 🔑 環境変数（Secrets）

| 変数名 | 用途 | 取得元 |
|--------|------|--------|
| `API_FOOTBALL_KEY` | API-Football | [API-Sports Dashboard](https://dashboard.api-football.com/) |
| `GOOGLE_API_KEY` | Gemini API | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `GOOGLE_SEARCH_ENGINE_ID` | Custom Search ID | [Programmable Search](https://programmablesearchengine.google.com/) |
| `GOOGLE_SEARCH_API_KEY` | Custom Search Key | [GCP Console](https://console.cloud.google.com/apis/credentials) |
| `YOUTUBE_API_KEY` | YouTube Data API | [GCP Console](https://console.cloud.google.com/apis/credentials) |
| `GMAIL_TOKEN` | Gmail OAuth Token | `tests/setup_gmail_oauth.py` で生成 |
| `GMAIL_CREDENTIALS` | Gmail OAuth Client | GCP Console → OAuth 2.0 Client |
| `NOTIFY_EMAIL` | 送信先メールアドレス | 自分のGmail |
| `GMAIL_ENABLED` | メール送信有効化 | `True` / `False` |

## 🚀 GitHub連携

### ghコマンドでの操作

```bash
# Issue一覧
gh issue list --state all

# Issue詳細
gh issue view <NUMBER>

# Issueクローズ（コメント付き）
gh issue close <NUMBER> --comment "対応内容を記載"

# Issueにコメント追加
gh issue comment <NUMBER> --body "コメント内容"

# ワークフロー手動実行
gh workflow run daily_report.yml
```

## ⚠️ API クォータ管理

> **📢 AI向け指示**: ユーザーが「クォータ確認して」「API確認して」と言った場合、以下のヘルスチェックスクリプトを順番に実行し、結果を報告すること。

```bash
python healthcheck/check_football_api.py
python healthcheck/check_google_search.py
python healthcheck/check_gemini.py
python healthcheck/check_gmail.py
```

| API | 日次上限 | 確認コマンド |
|-----|---------|-------------|
| API-Football | 7,500/日 | `python healthcheck/check_football_api.py` |
| Google Custom Search | 100/日 | `python healthcheck/check_google_search.py` |
| YouTube Data API | 10,000/日 | - |
| Gemini API | ~1,500/日 | `python healthcheck/check_gemini.py` |

## 🌐 Web開発（Firebase Hosting）

### アーキテクチャ

```
Firebase Hosting (https://football-delay-watching-a8830.web.app)
├── public/
│   ├── index.html          ← ログイン＋レポート一覧
│   └── reports/
│       ├── manifest.json   ← レポート一覧データ
│       ├── report_*.html   ← 各レポート
│       └── images/         ← フォーメーション図
```

### ⚠️ AI向け重要注意事項

> **絶対に `rm -rf public/reports` を実行しないこと！**

Firebase Hostingは**毎回デプロイ時に`public/`の内容で完全に置き換える**。
ローカルにファイルがないと、Firebase上からも削除される。

### デプロイコマンド

```bash
firebase deploy --only hosting
```

## 📝 Issue対応フロー

1. `gh issue list` でIssue確認
2. `gh issue view <NUMBER>` で詳細確認
3. コード修正
4. コミット（メッセージに `Closes #<NUMBER>` を含める）
5. `git push` でIssueが自動クローズ
6. **クローズ後、Issueにコメントで修正内容と確認結果を記載**

```bash
# コメント例
gh issue comment 30 --body "## 対応内容
- xxx を修正
## 確認結果
- デバッグモードで動作確認済み"
```

## 🔒 セキュリティ注意事項

> **⚠️ 機密ファイルは必ず `.gitignore` に追加すること**

以下のファイルは **絶対にリポジトリにコミットしてはならない**:

| ファイル種別 | 例 |
|-------------|-----|
| API認証トークン | `token.json`, `*_token.json` |
| OAuth クレデンシャル | `credentials.json`, `client_secret_*.json` |
| 環境変数ファイル | `.env`, `.env.local` |

## 💡 Tips

- **モック開発時**: `USE_MOCK_DATA=True` でAPIを消費せずテスト
- **デバッグモード**: 1試合のみ処理でクォータ節約
- **コミットメッセージ**: `Closes #N` でIssue自動クローズ
- **Issue対応後**: 必ずコメントで修正内容を記録

## 📋 開発履歴（主要な変更）

| 日付 | 内容 |
|------|------|
| 2025-12-25 | Issue #30-35対応、GEMINI.mdリファクタ |
| 2025-12-21 | API-Sports直接アクセスに移行（RapidAPI経由廃止） |
| 2025-12-14 | Gmail API経由のメール配信機能追加（Issue #5） |
| 2025-12-14 | GitHub Actions設定完了、Secrets連携 |
