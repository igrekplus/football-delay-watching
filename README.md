# ⚽ Football Delay Watching

**ネタバレ回避サッカー観戦ガイド自動生成システム**

サッカーの未視聴試合を、スコアや結果を知ることなく楽しむための「ネタバレ回避観戦ガイド」を自動生成します。

## 🎯 特徴

- **ネタバレ防止**: スコア・結果情報を完全排除したレポートを生成
- **毎日自動実行**: GitHub Actionsで毎朝07:00 (JST) に自動生成
- **AI要約**: Gemini APIによる試合前ニュースの自動要約
- **フォーメーション図**: スタメン情報を視覚的に表示

## 📋 対象リーグ

- プレミアリーグ (EPL)
- UEFAチャンピオンズリーグ (CL)

## 🛠️ 技術スタック

| 分類 | 技術 |
|------|------|
| 言語 | Python 3.11 |
| 試合データ | [API-Football](https://www.api-football.com/) (RapidAPI) |
| ニュース検索 | Google Custom Search API |
| AI要約 | Google Gemini API |
| 画像生成 | Pillow (PIL) |
| CI/CD | GitHub Actions |

## 🚀 セットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/igrekplus/football-delay-watching.git
cd football-delay-watching
```

### 2. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### 3. 環境変数を設定

```bash
cp .env.example .env
# .env を編集して各APIキーを設定
```

必要なAPIキー:
- `RAPIDAPI_KEY`: [RapidAPI](https://rapidapi.com/api-sports/api/api-football) から取得
- `GOOGLE_API_KEY`: [Google AI Studio](https://aistudio.google.com/app/apikey) から取得
- `GOOGLE_SEARCH_ENGINE_ID`: [Programmable Search Engine](https://programmablesearchengine.google.com/) から取得
- `GOOGLE_SEARCH_API_KEY`: [Google Cloud Console](https://console.cloud.google.com/apis/credentials) から取得

### 4. 実行

```bash
# デバッグモード（API節約・1試合のみ）
DEBUG_MODE=True USE_MOCK_DATA=False python main.py

# 本番モード
USE_MOCK_DATA=False python main.py

# モックデータ（API不使用）
USE_MOCK_DATA=True python main.py
```

## ⚙️ GitHub Actions

### 自動実行
- **スケジュール**: 毎日 07:00 JST (22:00 UTC)
- **手動実行**: Actions タブから `workflow_dispatch` で実行可能

### Secrets 設定
リポジトリの Settings → Secrets and variables → Actions で以下を設定:

| Secret名 | 説明 |
|----------|------|
| `RAPIDAPI_KEY` | API-Football用キー |
| `GOOGLE_API_KEY` | Gemini API用キー |
| `GOOGLE_SEARCH_ENGINE_ID` | 検索エンジンID |
| `GOOGLE_SEARCH_API_KEY` | Custom Search API用キー |
| `GMAIL_TOKEN` | Gmail OAuthトークン（`tests/setup_gmail_oauth.py` で生成）|
| `GMAIL_CREDENTIALS` | Gmail OAuthクライアント情報（GCPから取得）|
| `NOTIFY_EMAIL` | 通知先メールアドレス |
| `GMAIL_ENABLED` | `True` で有効化 |

### Gmail API セットアップ詳細

#### 1. OAuth 同意画面 (OAuth Consent Screen)
- **User Type**: **External** (外部) を選択
- **アプリ情報**: 任意の名前（例: `football-report`）、メールアドレスを入力
- **スコープ**: デフォルトのままでOK
- **テストユーザー (Test Users)**: **【重要】** 
    - 自分のGmailアドレスを必ず追加してください。
    - これを忘れると `Error 403: access_denied` になります。

#### 2. 認証情報の作成
- **認証情報の種類**: **OAuth クライアント ID**
- **アプリケーションの種類**: **デスクトップ アプリ**
- **名前**: 任意（例: `Desktop client 1`）
- 作成後、JSONをダウンロードして `.gmail_credentials.json` にリネームしてプロジェクトルートに配置。

#### 3. 初回認証 (Local)
```bash
python tests/setup_gmail_oauth.py
```
- ブラウザが開いたら、自分のGoogleアカウントでログイン。
- 「このアプリはGoogleで確認されていません」と出た場合：
    - 「詳細」→「football-report（安全ではないページ）に移動」をクリックして進める。

#### 4. GitHub Secrets への登録
```bash
gh secret set GMAIL_TOKEN < .gmail_token.json
gh secret set GMAIL_CREDENTIALS < .gmail_credentials.json
gh secret set NOTIFY_EMAIL --body 'your-email@gmail.com'
gh secret set GMAIL_ENABLED --body 'True'
```

## 🤖 AI開発について

このプロジェクトは **AIペアプログラミング** で開発されています。
詳細は [GEMINI.md](./GEMINI.md) を参照してください。

## 📁 プロジェクト構造

```
.
├── main.py              # エントリーポイント
├── config.py            # 設定管理
├── src/
│   ├── match_processor.py   # 試合データ取得・選定
│   ├── facts_service.py     # スタメン・フォーメーション取得
│   ├── news_service.py      # ニュース収集・AI要約
│   ├── report_generator.py  # Markdownレポート生成
│   ├── formation_image.py   # フォーメーション図生成
│   └── spoiler_filter.py    # ネタバレフィルター
├── docs/                # ドキュメント
├── .github/workflows/   # GitHub Actions
└── reports/             # 生成されたレポート（.gitignore対象）
```

## 📄 ライセンス

MIT License

## 🙏 謝辞

- [API-Football](https://www.api-football.com/) - 試合データ提供
- [Google AI](https://ai.google/) - Gemini API
