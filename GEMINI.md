# GEMINI.md - AI開発者向けガイド

このドキュメントは、本プロジェクトでAIアシスタントと共同開発する際のガイドラインです。

---

## 1. Overview

**プロジェクト概要**: サッカー試合のネタバレ回避型観戦ガイド生成システム。API-Football、YouTube、Google検索、Gemini LLMを統合し、試合レポート（HTML）を自動生成してFirebase Hostingで公開。

**主要技術**: Python 3.11、Google Cloud (Gemini, GCS, YouTube Data API)、Firebase Hosting、GitHub Actions

---

## 2. Quick Start

```bash
# 1. 環境構築
python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# 2. 初回実行（モックモード・UIレイアウト確認）
DEBUG_MODE=True USE_MOCK_DATA=True python main.py

# 3. 詳細な実行方法
# → `/debug-run` ワークフローを参照
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

> 詳細は [.agent/workflows/](.agent/workflows/) を参照

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
| デプロイ後にレポートが消える | デプロイ前に必ず `python scripts/sync_firebase_reports.py` を実行 |
| TARGET_DATE指定ミス | 必ず「今日より2日以上前」の日付を指定（当日や前日はスタメン情報未取得） |
| キャッシュが古い | `rm -rf .gemini/cache` でローカルキャッシュをクリア |
| モックモードで実API検証 | ログ開始直後の `Mock: False` を必ず目視確認 |

---

## 7. AI Guidelines

### タスク範囲の厳守
ユーザーから依頼された特定のIssueやタスクのみに集中すること。明示的な指示がない限り、別のIssueの計画や実装を開始してはならない。

### プロンプト管理
システムから実行されるLLMプロンプト(GCPのGeminiを呼ぶ際のプロンプトは `settings/prompts/` 以下のMarkdownファイルとして外部化する。`settings/gemini_prompts.py` でメタデータを管理し、`build_prompt` 関数を通じて呼び出す。

### 検証の徹底
原則workflowからセッションはスタートするが、そうでない場合もある。
その際に修正した際には必ず /debug-runを実行する必要がある。

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
- Skills: [.agent/skills/](.agent/skills/)
