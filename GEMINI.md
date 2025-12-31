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
├── main.py              # エントリーポイント（軽量化済み）
├── config.py            # 設定管理（環境変数読み込み）
├── src/
│   ├── domain/          # ドメインモデル
│   │   ├── models.py        # MatchDataクラス
│   │   ├── match_ranker.py  # 試合ランク付けロジック
│   │   └── match_selector.py # 試合選定ロジック
│   ├── clients/         # 外部APIクライアント
│   │   ├── api_football_client.py  # API-Football統合クライアント
│   │   ├── caching_http_client.py  # キャッシュ付きHTTPクライアント
│   │   └── cache_store.py          # キャッシュストア（Local/GCS）
│   ├── utils/           # ユーティリティ
│   │   ├── formation_image.py   # フォーメーション図生成
│   │   ├── nationality_flags.py # 国名→国旗絵文字
│   │   ├── spoiler_filter.py    # ネタバレフィルター
│   │   └── execution_policy.py  # 実行制御（時間/クォータ）
│   ├── workflows/       # ワークフロー
│   │   └── generate_guide_workflow.py  # メインワークフロー
│   ├── match_processor.py   # 試合データ取得・オーケストレーション
│   ├── facts_service.py     # スタメン・フォーメーション・国籍取得
│   ├── news_service.py      # ニュース収集・Gemini要約
│   ├── youtube_service.py   # YouTube動画検索
│   ├── report_generator.py  # Markdownレポート生成
│   ├── html_generator.py    # HTML変換・Firebase manifest管理
│   ├── cache_warmer.py      # キャッシュプリフェッチ
│   └── email_service.py     # Gmail APIメール送信
├── settings/            # 設定ファイル
│   ├── channels.py          # YouTubeチャンネル優先度設定
│   └── cache_config.py      # キャッシュTTL/バックエンド設定
├── healthcheck/         # APIヘルスチェック
│   ├── check_football_api.py  # API-Football
│   ├── check_google_search.py # Google Custom Search
│   ├── check_gemini.py        # Gemini API
│   ├── check_gmail.py         # Gmail API
│   └── check_gcs_cache.py     # GCSキャッシュ状況
├── docs/
│   ├── 01_requirements/             # 要件定義
│   │   ├── index.md                     # 機能要件概要・目次
│   │   ├── youtube_integration.md       # YouTube動画取得要件
│   │   └── non_functional.md            # 非機能要件・データ定義
│   ├── 02_design/                   # 設計
│   │   ├── index.md                     # 設計概要・目次
│   │   ├── system_overview.md           # システム全体設計
│   │   ├── external_apis.md             # 外部API連携設計
│   │   ├── infrastructure.md            # 実行基盤設計
│   │   ├── cache_design.md              # キャッシュ設計
│   │   ├── login_design.md              # ログイン設計
│   │   └── api_endpoints.md             # APIエンドポイント詳細
│   ├── 03_operations/               # 運用
│   │   ├── deployment.md                # デプロイ設計
│   │   ├── api_quota.md                 # APIクォータ管理
│   │   └── user_utilities.md            # ユーザーユーティリティ
│   └── 04_llm_guides/               # LLM向け指示書
│       ├── raw_acquisition.md           # raw取得指示
│       ├── reviewer.md                  # レビューアーモード
│       └── commentary_investigation.md  # 実況解説調査
├── tests/                   # API検証スクリプト
└── .github/workflows/       # GitHub Actions
```

## 📚 ドキュメント構成と更新ルール

> 詳細は [docs/structure.md](docs/structure.md) を参照。

### ディレクトリの役割

| ディレクトリ | 役割 | 更新タイミング |
|-------------|------|---------------|
| `01_requirements/` | WHAT: 何を作るか（要件定義） | 機能追加・変更時 |
| `02_design/` | HOW: どう実現するか（設計） | 実装前・設計変更時 |
| `03_operations/` | RUN: どう動かすか（運用） | インフラ変更時 |
| `04_llm_guides/` | AI: どう指示するか（LLM用） | AI指示改善時 |

### 更新ルール

1.  **Code follows Design**: コード変更時は `02_design` も更新する
2.  **Single Source of Truth**: 要件は `01_requirements` に書き、設計書からはリンクで参照
3.  **リンク整合性**: ファイル名変更時はリンク切れを確認する

### 変更時チェックリスト

- [ ] 機能仕様が変わった → `01_requirements` 更新
- [ ] 実装方針が変わった → `02_design` 更新
- [ ] 運用手順が変わった → `03_operations` 更新
- [ ] ファイル名変更 → リンク切れ確認

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

### デバッグ/モック実行後のデプロイ

> **モックモード・デバッグモード問わず、実行後は必ずデプロイすること！**

```bash
# 同期 + デプロイ（必ずセットで実行）
# ⚠️ firebaseコマンドが見つからない場合は source ~/.zshrc を先に実行
source ~/.zshrc && python scripts/sync_firebase_reports.py && firebase deploy --only hosting
```

または `/debug-run` ワークフローを使用（実行→デプロイまで自動）

> デプロイ完了後は、**必ずユーザーにレポートURLを連携すること**。
> 
> **レポートURL形式**: `https://football-delay-watching-a8830.web.app/reports/{試合日}_{ホーム}_vs_{アウェイ}_{実行日時}.html`
> 
> ログから生成されたレポートファイル名を確認して連携する。

### ⚠️ モード選択に関する重要注意

> **動作確認時は原則としてデバッグモード（実API）で実行すること！**
> 
> モックモードはUIレイアウトの確認のみに使用する。機能の動作確認は必ずデバッグモードで行う。

| モード | 使用場面 | データソース | 試合選定 |
|--------|----------|-------------|----------|
| **モック** | UIレイアウト確認のみ | 固定のフェイクデータ | 常に同じ3試合 |
| **デバッグ** | **機能の動作確認（基本）** | 実API (API-Football等) | 直近土曜の試合 |

**正しい使い分け:**
- ✅ Issue対応後の動作確認 → **デバッグモード**
- ✅ 新機能実装後のテスト → **デバッグモード**
- ✅ API連携の動作確認 → **デバッグモード**
- ⚠️ CSSやHTMLのレイアウト確認のみ → モックモード

**NG例**: 機能実装後にモックで確認して「問題なし」とする → ❌ 実APIで問題が起きる可能性あり
**OK例**: APIエラーが発生したらユーザーに報告して対応を確認 → ✅ 正解


### 📅 デバッグモードの日付処理

> デバッグモード実行時は、**対象となる試合の時間ウィンドウを必ずユーザーに報告すること**。

**時間ウィンドウの計算方法**:
- 本番モード: `昨日 07:00 JST ～ 今日 07:00 JST`
- デバッグモード: `直近の土曜日 07:00 JST ～ 翌日 07:00 JST`

**報告例**:
```
対象時間ウィンドウ: 2024-12-21 07:00 JST ～ 2024-12-22 07:00 JST
この時間にキックオフした試合が取得されます。
```

**ユーザーが特定の試合を確認したい場合の指示方法**:
- ❌ 「12/23のカラバオカップを確認して」
- ✅ 「12/24朝の本番実行を想定してデバッグして」

| 見たい試合（UK時間） | 指定日（本番実行を想定する日） |
|---------------------|------------------------------|
| 12/23 20:00 開催 | 12/24 |
| 12/21 15:00 開催 | 12/22 |
| 12/26 12:30 開催 | 12/27 |

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

> ユーザーが「クォータ確認して」「API確認して」と言った場合、以下のヘルスチェックスクリプトを順番に実行し、結果を報告すること。

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

> デプロイ前に**必ず同期スクリプトを実行すること**。これをしないと、GitHub Actionsで生成されたレポートが消失する。

```bash
# 1. Firebaseからレポートを同期（紛失防止）
python scripts/sync_firebase_reports.py

# 2. デプロイ
firebase deploy --only hosting
```

詳細については [docs/03_operations/deployment.md](docs/03_operations/deployment.md) を参照。

## 📝 Issue対応フロー

1. `gh issue list` でIssue確認
2. `gh issue view <NUMBER>` で詳細確認
3. コード修正
4. デバッグモードで動作確認
5. **⚠️ クローズ前にユーザーに確認を取る**（勝手にクローズしない）
6. ユーザー承認後、コミット＆クローズ

> Issue対応が完了したら、**必ずユーザーに「クローズしてよいか」確認すること**。勝手にIssueをクローズしてはならない。

### コミットメッセージのお作法

Issue対応時のコミットメッセージは以下の形式を使用：

```
feat(#<ISSUE_NUMBER>): 変更内容の要約

- 変更点1
- 変更点2

Closes #<ISSUE_NUMBER>
```

**重要**: `Closes #<ISSUE_NUMBER>` をコミットメッセージに含めると、プッシュ時にIssueが自動クローズされる。

### Issueクローズ時のコメント（必須）

Issueをクローズする際は、以下の情報を**必ずコメントに記載**すること：

```bash
gh issue comment <NUMBER> --body "## 実装完了 ✅

### コミット
- **コミットID**: \`<COMMIT_HASH>\`
- **ブランチ**: main

### 変更内容
- 変更したファイルと概要

### 動作確認
- [x] モックモード/デバッグモードで確認
- [x] デプロイ・ブラウザ確認（該当する場合）"
```

> これはエンジニアリングの基本的なお作法。Issue対応後は必ず上記形式でコメントを残し、**コミットIDと変更内容を明記すること**。

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
- **Instagram CSV**: `data/player_instagram_50.csv` の選手名は **API-Footballの返却名と完全一致** が必要（例: `E. Haaland` ではなく `Erling Haaland`）

### リファクタリング時の注意

> 既存のサービスクラスが参照しているメソッド名を変更する場合、**依存先が正しく動作するか必ず確認すること**。

**例**: `ApiFootballClient` に新メソッドを追加する際、`FactsService` が `fetch_lineups()` を期待しているなら、そのメソッドも実装する必要がある。

### ghコマンドのパス

> `gh` コマンドが見つからない場合は `/opt/homebrew/bin/gh` を使用すること。

```bash
/opt/homebrew/bin/gh issue list
```
