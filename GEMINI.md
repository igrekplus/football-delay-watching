# GEMINI.md - AI開発者向けガイド

このドキュメントは、本プロジェクトでAIアシスタント（Claude/Gemini等）と共同開発する際のガイドラインです。

## 🤖 開発環境

| 項目 | 内容 |
|------|------|
| IDE | Antigravity |
| AIアシスタント | Claude Opus 4.5 (Anthropic) |
| 開発スタイル | 会話ベースの反復開発 |

## 📂 プロジェクト構造

```
.
├── main.py              # エントリーポイント
├── config.py            # 設定管理（環境変数読み込み）
├── src/
│   ├── match_processor.py   # 試合データ取得・選定・MatchDataクラス
│   ├── facts_service.py     # スタメン・フォーメーション・国籍取得
│   ├── news_service.py      # ニュース収集・Gemini要約
│   ├── report_generator.py  # Markdownレポート生成
│   ├── email_service.py     # Gmail APIメール送信
│   ├── formation_image.py   # フォーメーション図生成（Pillow）
│   ├── nationality_flags.py # 国名→国旗絵文字マッピング
│   └── spoiler_filter.py    # ネタバレフィルター
├── docs/
│   ├── requirement.md       # 詳細要件定義書
│   └── system_design.md     # システム設計書
├── tests/                   # API検証スクリプト
└── .github/workflows/       # GitHub Actions
```

## 🔧 開発コマンド

```bash
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
| `RAPIDAPI_KEY` | API-Football | [RapidAPI](https://rapidapi.com/api-sports/api/api-football) |
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
gh secret set RAPIDAPI_KEY < <(grep "^RAPIDAPI_KEY=" .env | cut -d'=' -f2-)

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

### API-Football
- **無料枠**: 100リクエスト/日
- **確認方法**: レポート末尾の「API使用状況」または:
  ```bash
  # 直接確認
  python3 -c "
  import os, requests
  from dotenv import load_dotenv
  load_dotenv()
  resp = requests.get('https://api-football-v1.p.rapidapi.com/v3/fixtures',
    headers={'X-RapidAPI-Key': os.getenv('RAPIDAPI_KEY'),
             'X-RapidAPI-Host': 'api-football-v1.p.rapidapi.com'},
    params={'date': '2025-01-01', 'league': 39, 'season': 2024})
  print(f\"Remaining: {resp.headers.get('x-ratelimit-requests-remaining')} / {resp.headers.get('x-ratelimit-requests-limit')}\")
  "
  ```

### Google Custom Search
- **無料枠**: 100クエリ/日
- **確認**: [Cloud Console](https://console.cloud.google.com/)

### Gemini API
- **無料枠**: 1,500リクエスト/日
- 制限に余裕があるため通常は気にしなくてOK

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
3. **デフォルトで安全側**: 迷ったら `.gitignore` に追加する

```bash
# 現在の .gitignore に含まれる機密ファイル
.gmail_credentials.json
.gmail_token.json
.env
.env.local
```
