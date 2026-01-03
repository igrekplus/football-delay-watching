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
| 認証 | `gcloud auth login` (アカウントは `.env` 参照) |

### Antigravityブラウザプロファイル
| 項目 | 内容 |
|------|------|
| プロファイルパス | `~/.gemini/antigravity-browser-profile` |
| ログインアカウント | `.env`の`BROWSER_LOGIN_EMAIL`を参照 |
| 永続化 | ✅ セッション間でログイン状態維持 |

## 📂 プロジェクト構造

```
.
├── main.py              # エントリーポイント（軽量化済み）
├── config.py            # 設定管理（環境変数読み込み）
├── src/
│   ├── domain/          # ドメインモデル
│   ├── clients/         # 外部APIクライアント
│   ├── utils/           # ユーティリティ
│   ├── workflows/       # ワークフロー
│   ├── match_processor.py   # 試合データ取得・オーケストレーション
│   ├── report_generator.py  # Markdownレポート生成
│   ├── html_generator.py    # HTML変換・Firebase manifest管理
│   ├── cache_warmer.py      # キャッシュプリフェッチ
│   └── email_service.py     # Gmail APIメール送信
├── settings/            # 設定ファイル（検索仕様・プロンプト）
│   ├── search_specs.py      # YouTube/Google検索クエリテンプレート
│   └── gemini_prompts.py    # LLMプロンプトテンプレート (Issue #120)
├── healthcheck/         # APIヘルスチェック
├── docs/
│   ├── 01_requirements/             # 要件定義
│   ├── 02_architecture/             # 全体アーキテクチャ
│   ├── 03_components/               # コンポーネント設計
│   └── 04_operations/               # 運用・デプロイ・クォータ管理
├── tests/                   # API検証スクリプト
└── .github/workflows/       # GitHub Actions
```

## 📚 ドキュメント構成と更新ルール

> 詳細は [docs/structure.md](docs/structure.md) を参照。

### ディレクトリの役割

| ディレクトリ | 役割 | 更新タイミング |
|-------------|------|---------------|
| `01_requirements/` | WHAT: 何を作るか（要件定義） | 機能追加・変更時 |
| `02_architecture/` | HOW: 全体アーキテクチャ | 設計変更時 |
| `03_components/` | WHAT EACH: 各コンポーネント設計 | コンポーネント変更時 |
| `04_operations/` | RUN: どう動かすか（運用） | インフラ変更時 |
| `GEMINI.md` | AI: 開発ガイド・AI指示書 | 都度 |

### 更新ルール
1.  **Code follows Design**: コード変更時は `02_architecture` または `03_components` も更新する
2.  **Single Source of Truth**: 要件は `01_requirements`、全体設計は `02_architecture`
3.  **リンク整合性**: ファイル移動・リネーム時はリンク切れを確認する

## 🔧 開発コマンド

### 🐍 Python実行環境
> **必ず `/usr/local/bin/python` (3.11.11) を使用すること**

```bash
/usr/local/bin/python main.py
```

### 🏃 実行モード
> 詳細な仕様は [docs/04_operations/execution_mode.md](docs/04_operations/execution_mode.md) を参照。

| モード | コマンド | 用途 |
|--------|---------|------|
| **モック** | `DEBUG_MODE=True USE_MOCK_DATA=True python main.py` | UIレイアウト確認 |
| **デバッグ** | `DEBUG_MODE=True USE_MOCK_DATA=False python main.py` | 実API・1試合のみ |
| **本番** | `USE_MOCK_DATA=False python main.py` | バッチ実行 |

### 📅 デバッグ対象日の指定・計算
デバッグ実行等で「特定の日付の試合」を処理したい場合、**「実行日(レポート生成日)」**を指定する（`TARGET_DATE`）。
計算式: `試合日(現地) + 1日`

| 見たい試合の現地日付 | 指定する日付 (`TARGET_DATE`) |
|---|---|
| 12/23 (月) | **12/24** |
| 12/26 (木) | **12/27** |

### 🚀 デプロイ
**モックモード・デバッグモード問わず、実行後は必ずデプロイすること！**

```bash
# 同期 + デプロイ（必ずセットで実行）
source ~/.zshrc && python scripts/sync_firebase_reports.py && firebase deploy --only hosting
```
または `/debug-run` ワークフローを使用。

## ⏳ 定期実行スケジュール (Dynamic Schedule)

GitHub Actions により **3時間ごと** に実行される。

- **トリガー**: `0 */3 * * *` (cron)
- **Early Termination**:
  - 対象期間（過去24時間〜未来24時間等）に試合がない場合、APIを消費せずに即時終了する。
  - GCS上のCSVファイルで処理ステータスを管理し、重複実行を防止する。
- **優先順位**:
  - キックオフ直後の試合、未処理の試合を優先的に処理する。

## 🔑 環境変数 & APIクォータ管理

詳細は [docs/04_operations/api_quota.md](docs/04_operations/api_quota.md) を参照。
各APIのヘルスチェックコマンドは `docs/04_operations/api_quota.md` の「ヘルスチェックスクリプト」セクションを参照すること。ユーザーからクオータ確認を求められた場合は、それらのスクリプトを実行する。

## 🌐 Web開発（Firebase Hosting）

### アーキテクチャ
`public/` 以下の静的ファイルをホスティング。`reports/` にはMarkdownから変換されたHTMLレポートが格納される。

> [!CAUTION]
> **絶対に `rm -rf public/reports` を実行しないこと！**
> デプロイ時にローカルの `public/` でFirebase上が上書きされるため、同期 (`sync_firebase_reports.py`) が必須。

## 🛠️ 開発者ユーティリティ

### 選手SNS情報のメンテナンス
選手カードのInstagramアイコンは `data/player_instagram_50.csv` で管理。
- **更新手順**: API-Footballの登録名と完全一致する名前で行を追加し、PRを作成・マージする。

## 🤖 AIガイドライン (AI Guidelines)

AIアシスタント（あなた）が特定のタスクを行う際の行動規範と手順。

### 1. レビューア行動規範 (Reviewer Mode)
コードやドキュメントのレビューを行う際は、**高度な技術レビューアー (Expert Reviewer)** として振る舞う。
- **姿勢**: 「良いと思います」等の曖昧な肯定を避け、**批判的かつ建設的**に、**理由と根拠**を持って指摘する。
- **観点**:
  - **正確性**: 事実・仕様の誤りはないか。
  - **構造整合性**: 重複、矛盾、粒度の不一致はないか。
  - **リスク**: 隠れた前提や副作用はないか。
- **Output**: 可能な限り代替案や修正案を具体的に提示する。

### 2. 生データ取得 (Raw Acquisition via Playwright)
ユーザーから「この件について調べて」とふわっとした依頼があった場合、自律的に調査を行う。
- **ツール**: Playwright MCP (Browser Tool)
- **プロセス**:
  1. **検索計画**: 日本語・英語で検索クエリを計画し、ユーザーに提示・合意を得る。
  2. **URL探索**: 検索結果の要約だけで判断せず、実際にサイトを巡回する。
  3. **本文抽出**: 本文、画像URLを抽出し、`knowledge/raw/...` に保存する。
  4. **禁止**: 取得した本文の勝手な要約・加工。ありのまま保存すること。

### 3. 実況・解説情報の調査
「〇〇の試合の実況解説者は？」という問いに対して：
- **ソース優先度**:
  1. U-NEXT公式X (@UNEXT_football) の直前投稿（画像）
  2. PR TIMES (`site:prtimes.jp U-NEXT プレミアリーグ 解説`)
  3. U-NEXT公式サイト
- **注意**: 情報解禁は試合1〜2日前。それ以前は「未定」と回答する。
- **報告形式**: 試合日時、実況者、解説者を明記した表を作成する。

### 4. 検証 (Verification)
レポート生成ロジックの変更やチューニングを行った際は、必ず `/report-check-html` ワークフローを使用して検証を行う。
- **目的**: 期待するキーワード（チーム名、監督名、特定のフレーズ等）が最終成果物（HTML）に含まれているか、機械的に保証するため。
- **タイミング**: コード修正後、ユーザーにレビューを依頼する前。
- **コマンド**: `/report-check-html keyword="<確認したい文字列>"`

## 📝 Issue対応フロー

Issue対応の標準プロセスは、Workflowsの `resolve-issue` に定義されている。
基本的には `/resolve-issue <Issue番号>` コマンドを使用してフローを開始すること。

詳細は [.agent/workflows/resolve-issue.md](.agent/workflows/resolve-issue.md) を参照。
