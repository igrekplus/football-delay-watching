# CLAUDE.md - AI開発者向けガイド（Single Source of Truth）

このドキュメントは、本プロジェクトでAIアシスタントと共同開発する際のガイドラインです。
**すべてのAIエージェント（Claude / Gemini / Codex）はこのファイルをSSOTとして参照してください。**

> [!NOTE]
> `<!-- claude-only-start -->` 〜 `<!-- claude-only-end -->` で囲まれたセクションは
> **Claude Code Remote（Webブラウザ環境）専用**です。
> Gemini（Antigravity）・Codex（IDE）での作業時はスキップしてください。

---

## 1. Overview

**プロジェクト概要**: サッカー試合のネタバレ回避型観戦ガイド生成システム。API-Football、YouTube、Google検索、Gemini LLMを統合し、試合レポート（HTML）を自動生成してFirebase Hostingで公開。

**主要技術**: Python 3.11、Google Cloud (Gemini, GCS, YouTube Data API)、Firebase Hosting、GitHub Actions

---

## 2. Quick Start

```bash
# 1. 環境構築（初回のみ）
python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# 2. 詳細な実行方法は `/debug-run` ワークフローを参照
# 3. 特定の1試合だけ確認したい場合は `TARGET_FIXTURE_ID` を併用する
#    例: TARGET_DATE="2026-02-27" TARGET_FIXTURE_ID="1379248" DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```

---

## 3. Project Structure

```
.
├── main.py              # エントリーポイント
├── config.py            # 設定管理（環境変数読み込み）
├── src/
│   ├── domain/          # ドメインモデル
│   ├── clients/         # 外部APIクライアント
│   ├── utils/           # ユーティリティ
│   ├── workflows/       # ワークフロー
│   ├── match_processor.py   # 試合データ取得・オーケストレーション
│   ├── report_generator.py  # Markdownレポート生成
│   ├── html_generator.py    # HTML変換・Firebase manifest管理
│   └── email_service.py     # Gmail APIメール送信
├── settings/            # 設定ファイル（検索仕様・プロンプト）
│   ├── search_specs.py      # YouTube/Google検索クエリテンプレート
│   └── gemini_prompts.py    # LLMプロンプトテンプレート
├── tests/               # ユニットテスト（unittest使用）
├── docs/                # 設計ドキュメント
│   ├── 01_requirements/     # 要件定義
│   ├── 02_architecture/     # 全体アーキテクチャ
│   ├── 03_components/       # コンポーネント設計
│   └── 04_operations/       # 運用・デプロイ・クォータ管理
├── .agent/              # Gemini/Codex向けエージェント設定
│   ├── workflows/       # 作業手順書（スラッシュコマンド）
│   └── skills/          # ドメイン知識パッケージ
└── .claude/             # Claude Code専用設定
    ├── hooks/           # session-start.sh など
    ├── skills/          # Claudeスキル定義
    └── settings.json    # フック・権限設定
```

> [!TIP]
> この構成図は概略であり、最新の構成は実際のパスを確認すること。

---

## 4. Development

### Workflows（作業手順）

プロジェクト固有の作業は、以下のワークフローを使用してください：

| コマンド | 用途 |
|---------|------|
| `/debug-run` | デバッグ実行→同期→デプロイ |
| `/deploy` | Firebase Hostingへデプロイ（安全な同期処理を含む） |
| `/resolve-issue` | Issue対応フロー（ブランチ作成→実装→検証→マージ） |
| `/tune-gemini` | Geminiプロンプトチューニング |
| `/report-check-html` | HTMLレポート内キーワード検証 |
| `/fetch-instagram` | 選手Instagram URL取得 |
| `/delete-report` | 誤生成レポート削除 |

> 主要なワークフローのみ記載。全一覧は [.agent/workflows/](.agent/workflows/) を参照

### Code Style

本プロジェクトでは**Ruff**を採用している。

```bash
ruff check .          # リントチェック
ruff check --fix .    # 自動修正付き
ruff format .         # フォーマット
```

**設定方針:**
- 行長: 88文字（Black互換）
- ルール: E, F, I, W, UP（pycodestyle, Pyflakes, isort, pyupgrade）
- 型ヒント推奨（関数シグネチャ）
- docstring: Google形式推奨

> [!TIP]
> コミット前に自動でRuffが実行される（pre-commitフック）。
> 初回のみ `pip install -r requirements-dev.txt && pre-commit install` が必要。

### Naming Conventions

| 対象 | 規則 | 例 |
|------|------|-----|
| ファイル名 | スネークケース | `match_processor.py` |
| クラス名 | パスカルケース | `MatchProcessor` |
| 関数・変数 | スネークケース | `get_fixture_data()` |
| 定数 | 大文字スネーク | `MAX_RETRIES` |
| Workflow | ケバブケース | `debug-run.md` |
| ブランチ名 | `feature-<issue-number>/<task-slug>` | `feature-253/fix-parser` |

> [!WARNING]
> **Workflowファイル名の禁止事項**
> - `_`（アンダースコア）は使用禁止。常に `-`（ハイフン）で区切ること。
> - ❌ `debug_run.md` ✅ `debug-run.md`

---

## 5. Testing

```bash
python -m unittest discover tests      # 全テスト
python -m unittest tests/test_foo.py   # 個別テスト
```

- `tests/test_*.py`: ユニットテスト（unittest）
- `tests/verify_*.py`: API検証スクリプト

---

## 6. Common Pitfalls

> [!CAUTION]
> **絶対に `rm -rf public/reports` を実行しないこと！**
> デプロイ時にローカルの `public/` でFirebase上が上書きされるため、同期 (`sync_firebase_reports.py`) が必須。

| 問題 | 対策 |
|------|------|
| デプロイ後にレポートが消える | `/deploy` ワークフローに従う（`scripts/safe_deploy.sh`） |
| TARGET_DATE指定ミス | `/debug-run` ワークフローの「TARGET_DATEの計算ガイド」を参照 |
| 狙った試合が選ばれない | `TARGET_FIXTURE_ID` を併用して対象fixtureを固定する |
| キャッシュが古い | `rm -rf .gemini/cache` でローカルキャッシュをクリア |
| モックモードで実API検証 | ログ開始直後の `Mock: False` を必ず目視確認 |

---

## 7. AI Guidelines

### AI Agent Components (Role & Usage)

| コンポーネント | 役割 | 性質 | 具体例 |
|---|---|---|---|
| **CLAUDE.md** | メインガイド（SSOT） | 全体ルール | プロジェクト全体方針、命名規則 |
| **Workflows** | 手順・プロセス | How to perform（固定手順） | `/deploy`, `/debug-run` |
| **Skills** | 知識・判断基準 | How to think/know（専門知識） | `issue_resolution`, `reviewer_mode` |

> [!TIP]
> 「特定コマンドを順番に叩く作業」→ **Workflow**、「専門知識で判断する能力」→ **Skill**

### タスク範囲の厳守
依頼されたIssue・タスクのみに集中する。明示的な指示がない限り、別Issueの計画・実装を開始しない。

### 設計書と実装の同期
設計書も修正しながら実装を進める。

### プロンプト管理
LLMプロンプトは `settings/prompts/` 以下のMarkdownファイルとして外部化する。`settings/gemini_prompts.py` でメタデータを管理し、`build_prompt` 関数を通じて呼び出す。

### 検証の徹底

| 変更種別 | /debug-run必須 |
|---------|---------------|
| Geminiプロンプト (`settings/prompts/`) | ✅ 必須 |
| データ取得ロジック (`src/clients/`, `src/match_processor.py`) | ✅ 必須 |
| HTML/CSS生成 (`src/html_generator.py`, `public/`) | ✅ 必須 |
| ドキュメントのみ (`docs/`, `CLAUDE.md`) | ❌ 不要 |
| テストコードのみ (`tests/`) | ❌ 不要 |

> [!IMPORTANT]
> - **「動くことの証明」の提示**: ユニットテストパスだけでなく、debug-run結果（生成ファイル・ログ）を提示すること
> - **推測の排除**: 「〜のはず」「〜と思われる」での完了報告を禁ずる
> - **URL報告**: UI変更がある場合は `/deploy` 後にURLを報告すること

---

## 8. Infrastructure（GCP・CI/CD）

### 3環境の認証・Secrets構成

| 環境 | GCP認証方法 | Secrets取得元 |
|------|------------|--------------|
| GitHub Actions | Workload Identity Federation（OIDCトークン） | GCP Secret Manager |
| ローカル（Antigravity/Codex） | ADC（`gcloud auth application-default login`） | `.env` ファイル |
| Claude Code Remote | サービスアカウントJSON（environment settings） | GCP Secret Manager（session-start自動ロード） |

### GCP Secret Manager 登録済みシークレット

| Secret名 | 用途 |
|----------|------|
| `API_FOOTBALL_KEY` | API-Football |
| `GOOGLE_API_KEY` | Gemini / Custom Search |
| `GOOGLE_SEARCH_ENGINE_ID` | Custom Search |
| `GOOGLE_SEARCH_API_KEY` | Custom Search |
| `YOUTUBE_API_KEY` | YouTube Data API |
| `NOTIFY_EMAIL` | Gmail通知先 |
| `GMAIL_TOKEN` | Gmail OAuth2 token |
| `GMAIL_CREDENTIALS` | Gmail OAuth2 credentials |
| `FIREBASE_CONFIG` | Firebase web config |
| `ALLOWED_EMAILS` | サイトアクセス制御リスト |

### GitHub Actions（WIF認証）

`google-github-actions/auth@v2` を Workload Identity Federation で使用。JSONキーは不使用。
詳細: `.github/workflows/daily_report.yml`, `.github/workflows/update-calendar.yml`

### ローカル開発（Antigravity/Codex）のGCP認証

```bash
gcloud auth application-default login   # 初回のみ
```

GCSアクセスは ADC（Application Default Credentials）が自動的に処理する。

---

<!-- claude-only-start -->
## 9. Claude Code Remote 専用セクション

> [!NOTE]
> このセクションは **Claude Code Web（ブラウザ）環境専用**です。
> Gemini（Antigravity）・Codex（IDE）での作業時はスキップしてください。

### 環境設定（Environment Settings）

Claude Code Webの environment settings に設定が必要なもの：

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `GCP_SERVICE_ACCOUNT_KEY` | ✅ | サービスアカウントJSON。これ1つだけ設定すれば他は自動ロード |
| `CLAUDE_CODE_REMOTE` | ✅ | `true` に設定（session-start hookの起動条件） |

その他のAPIキー（`GOOGLE_API_KEY` 等）は **session-start hookがSecret Managerから自動ロード**するため、environment settingsへの設定は不要。

### session-start hookの仕組み

`.claude/hooks/session-start.sh` がセッション開始時に自動実行される：

1. gcloud SDK のセットアップ
2. プロキシCA証明書の設定
3. `GCP_SERVICE_ACCOUNT_KEY` でGCP認証（`gcloud auth activate-service-account`）
4. **GCP Secret Manager から10件のシークレットを環境変数にロード**
5. PATHの設定

正常時のログ（system-reminderに表示）：
```
[session-start] GCS authentication complete.
[session-start] Loading secrets from Secret Manager...
[session-start] Secrets loaded: 10 ok, 0 failed.
```

### Claude Code Remote でのdebug-run

session-start完了後はそのまま実行可能：

```bash
# 実データで1試合生成（2日以上前の日付を指定）
TARGET_DATE="2026-01-08" DEBUG_MODE=True USE_MOCK_DATA=False python main.py

# 特定試合を指定
TARGET_DATE="2026-02-27" TARGET_FIXTURE_ID="1379248" DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```

> [!IMPORTANT]
> `.venv` は不要（systemのPythonを使用）。`pip install -r requirements.txt` は初回のみ必要。

### Claude Code専用スキル

`.claude/skills/` に定義されているスキルはClaudeセッション内でのみ利用可能（Gemini/Codexからは参照不可）。

### ブランチ命名規則（Claude Code自動生成ブランチ）

Claude Code Remoteが自動生成するブランチは `claude/<slug>` 形式になる。
通常のIssue対応ブランチは引き続き `feature-<issue-number>/<task-slug>` を使用すること。
<!-- claude-only-end -->

---

## 10. References

### ドキュメント体系

| ディレクトリ | 役割 | 更新タイミング |
|-------------|------|---------------|
| `01_requirements/` | WHAT: 要件定義 | 機能追加・変更時 |
| `02_architecture/` | HOW: 全体アーキテクチャ | 設計変更時 |
| `03_components/` | WHAT EACH: 各コンポーネント設計 | コンポーネント変更時 |
| `04_operations/` | RUN: 運用・インフラ | インフラ変更時 |

詳細は [docs/structure.md](docs/structure.md) を参照。

### 環境変数・APIクォータ

詳細は [docs/04_operations/api_quota.md](docs/04_operations/api_quota.md) を参照。

### Workflows・Skills一覧

- Workflows: [.agent/workflows/](.agent/workflows/)
- Skills (.agent): [.agent/skills/](.agent/skills/)
  - `issue_resolution`: Issue解決のライフサイクル管理
  - `reviewer_mode`: 高度な技術レビュー
  - `manage_unext_commentators`: U-NEXTの実況・解説者情報の調査からCSV更新、カレンダー反映
  - `generate_player_profiles`: 選手詳細プロフィールの作成
  - `create_codex_skill_reference`: GeminiスキルをCodexで使えるようにする
  - `regenerate_report`: レポートをCSV・manifest・キャッシュリセットして再生成
