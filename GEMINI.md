# GEMINI.md - AI開発者向けガイド

このドキュメントは、本プロジェクトでAIアシスタントと共同開発する際のガイドラインです。

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
└── .agent/              # AIエージェント設定
    ├── workflows/       # 作業手順書（スラッシュコマンド）
    └── skills/          # ドメイン知識パッケージ
```

> [!TIP]
> **Project Structureについて**
> この構成図は概略であり、最新の構成は実際のパスを確認すること。

---

## 4. Development

### Workflows（作業手順）

プロジェクト固有の作業は、以下のワークフローを使用してください：

| コマンド | 用途 |
|---------|------|
| `/debug-run` | デバッグ実行→同期→デプロイ |
| `/deploy` | Firebase Hostingへデプロイ |
| `/resolve-issue` | Issue対応フロー（ブランチ作成→実装→検証→マージ） |
| `/tune-gemini` | Geminiプロンプトチューニング |
| `/report-check-html` | HTMLレポート内キーワード検証 |
| `/fetch-instagram` | 選手Instagram URL取得 |
| `/delete-report` | 誤生成レポート削除 |

> 主要なワークフローのみ記載。全一覧は [.agent/workflows/](.agent/workflows/) を参照

### Code Style

> [!NOTE]
> **TODO**: Black, isort, ruff等のフォーマッタ導入を検討中。
> 現状は以下の基本方針に従う：
> - 型ヒント推奨（関数シグネチャ）
> - import順序: 標準ライブラリ → サードパーティ → ローカル
> - docstring: Google形式推奨

### Naming Conventions

| 対象 | 規則 | 例 |
|------|------|-----|
| ファイル名 | スネークケース | `match_processor.py` |
| クラス名 | パスカルケース | `MatchProcessor` |
| 関数・変数 | スネークケース | `get_fixture_data()` |
| 定数 | 大文字スネーク | `MAX_RETRIES` |
| Workflow | ケバブケース | `debug-run.md` |

> [!WARNING]
> **Workflowファイル名の禁止事項**
> - `_`（アンダースコア）は使用禁止
> - 常に `-`（ハイフン）で単語を区切ること
> - ❌ `debug_run.md`, `resolve_issue.md`
> - ✅ `debug-run.md`, `resolve-issue.md`

---

## 5. Testing

### テスト実行

```bash
# 全テスト実行
python -m unittest discover tests

# 特定テスト実行
python -m unittest tests/test_datetime_util.py

# HTMLレポート検証（特定キーワード存在確認）
/report-check-html keyword="Guardiola"
```

### テスト配置

- `tests/test_*.py`: ユニットテスト（unittest使用）
- `tests/verify_*.py`: API検証スクリプト

---

## 6. Common Pitfalls

> [!CAUTION]
> **絶対に `rm -rf public/reports` を実行しないこと！**
> デプロイ時にローカルの `public/` でFirebase上が上書きされるため、同期 (`sync_firebase_reports.py`) が必須。

| 問題 | 対策 |
|------|------|
| デプロイ後にレポートが消える | `/deploy` ワークフローの手順に従うこと |
| TARGET_DATE指定ミス | `/debug-run` ワークフローの「TARGET_DATEの計算ガイド」を参照 |
| キャッシュが古い | `rm -rf .gemini/cache` でローカルキャッシュをクリア |
| モックモードで実API検証 | ログ開始直後の `Mock: False` を必ず目視確認 |

---

## 7. AI Guidelines

### AI Agent Components (Role & Usage)

作業の目的や性質に応じて、以下のコンポーネントを適切に使い分けること：

| コンポーネント | 役割 (Role) | 性質 (Nature) | 具体例 |
|---|---|---|---|
| **GEMINI.md** | メインガイド | 全体ルール・SSOT | プロジェクト全体方針、命名規則 |
| **Workflows** | 手順・プロセス | **How to perform** (固定手順) | `/deploy`, `/debug-run` |
| **Skills** | 知識・判断基準 | **How to think/know** (専門知識・判断) | `issue_resolution`, `reviewer_mode` |

> [!TIP]
> **迷った時の基準**
> 「特定のコマンドを順番に叩く作業」なら **Workflow**、「特定の観点や専門知識で判断・調査する能力」なら **Skill** として定義する。

### タスク範囲の厳守
ユーザーから依頼された特定のIssueやタスクのみに集中すること。明示的な指示がない限り、別のIssueの計画や実装を開始してはならない。

### プロンプト管理
システムから実行されるLLMプロンプト（GCPのGeminiを呼ぶ際のプロンプト）は `settings/prompts/` 以下のMarkdownファイルとして外部化する。`settings/gemini_prompts.py` でメタデータを管理し、`build_prompt` 関数を通じて呼び出す。

### 検証の徹底
以下の変更を行った場合は、必ず `/debug-run` ワークフローを完遂すること:

| 変更種別 | /debug-run必須 |
|---------|---------------|
| Geminiプロンプト (`settings/prompts/`) | ✅ 必須 |
| データ取得ロジック (`src/clients/`, `src/match_processor.py`) | ✅ 必須 |
| HTML/CSS生成 (`src/html_generator.py`, `public/`) | ✅ 必須 |
| ドキュメントのみ (`docs/`, `GEMINI.md`) | ❌ 不要 |
| テストコードのみ (`tests/`) | ❌ 不要 |

---

## 8. References

### ドキュメント体系

| ディレクトリ | 役割 | 更新タイミング |
|-------------|------|---------------|
| `01_requirements/` | WHAT: 何を作るか（要件定義） | 機能追加・変更時 |
| `02_architecture/` | HOW: 全体アーキテクチャ | 設計変更時 |
| `03_components/` | WHAT EACH: 各コンポーネント設計 | コンポーネント変更時 |
| `04_operations/` | RUN: どう動かすか（運用） | インフラ変更時 |

> 詳細は [docs/structure.md](docs/structure.md) を参照

### 環境変数・APIクォータ

詳細は [docs/04_operations/api_quota.md](docs/04_operations/api_quota.md) を参照。
各APIのヘルスチェックコマンドは同ドキュメントの「ヘルスチェックスクリプト」セクションを参照すること。

### Workflows・Skills一覧

- Workflows: [.agent/workflows/](.agent/workflows/)
  - `/check-close`: Issueクローズ前の確認
- Skills: [.agent/skills/](.agent/skills/)
  - `issue_resolution`: Issue解決のライフサイクル管理
  - `reviewer_mode`: 高度な技術レビュー
  - `research_commentary_info`: 実況・解説情報の調査
