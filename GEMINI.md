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
| 設定ファイル | `.gcp_config.md` (gitignore済み) |

> **Note**: プロジェクトID、認証アカウント、GCSバケット名は `.gcp_config.md` を参照してください。

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
- **無料枠の目安**: 1,500リクエスト/日（Google AI Pro は5時間ごとリフレッシュ想定）
- 429が出たら数時間待つか軽量モデルに切替

## 🧠 AIコーディング原則（プロSE向けガードレール）

### 1. 進め方（設計→実装の順序を徹底）
- **設計書を先に更新**: 仕様・I/Fをドキュメントに落とし、レビュー後に実装。設計変更なしのコード変更は禁止。
- **モジュール境界を意識**: 1ファイル=1責務。外部I/F（関数・クラス・APIコール）を先に固め、docstringと設計書を同期させる。
- **変更の「Why」を残す**: PR/コミットで根拠・代替案・影響範囲を簡潔に記録。プロンプトもバージョン管理（下記）。
- **小さくまとめて検証**: 変更は小さく刻み、テスト or 実行ログで裏付け。失敗時のロールバック手順を残す。

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
