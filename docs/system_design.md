# システム設計書 (System Design Document)

## 1. システム概要
サッカーの未視聴試合を、スコアや結果を知ることなく観戦するための「ネタバレ回避観戦ガイド」を自動生成するシステム。
毎日 07:00 (JST) に自動実行され、Markdown形式のレポートを出力する。

## 2. アーキテクチャ構成
コスト効率（個人利用無料）と運用容易性を重視した構成を採用。

### 2.1 データソース層 (Data Sources)
試合日程、結果（システム内部でのみ使用）、スタメン、フォーメーション等の事実データを取得する。
*   **サービス**: **API-Football** (RapidAPI)
*   **選定理由**: 無料枠（100回/日）があり、スタメン・フォーメーション情報が充実しているため。
*   **エンドポイント**:
    | エンドポイント | 用途 |
    | :--- | :--- |
    | `/fixtures` | 試合一覧・基本情報 |
    | `/fixtures/lineups` | スタメン・フォーメーション |
    | `/injuries` | 負傷者・出場停止情報 |
    | `/teams/statistics` | チームフォーム（直近5試合 W/D/L） |
    | `/fixtures/headtohead` | 過去の対戦成績（H2H） |

> 各エンドポイントで実際に送っているパラメータと、実装が参照しているレスポンス項目の詳細は `docs/api_endpoints.md` を参照。

#### 2.1.5 APIキャッシュ方針
- 実装: `src/api_cache.py` の `get_with_cache(url, headers, params)` を経由し、`config.USE_API_CACHE=True` のときのみローカル `api_cache/` に JSON を保存・再利用する。キャッシュキーは `URL + params(json, sort_keys=True)` の MD5。
- パラメータの実態（現行コード）
    - `/fixtures` : `date`, `league`, `season`（マッチ抽出・チームID取得用途）
    - `/fixtures/lineups` : `fixture`（ラインナップ）
    - `/injuries` : `fixture`
    - `/fixtures` : `id`（チームID再取得に再利用）
    - `/teams/statistics` : `team`, `season`, `league`（直近フォーム）※現在は league=39 固定
    - `/players` : `id`, `season`（国籍取得）
    - `/fixtures/headtohead` : `h2h`, `last`
- キャッシュしてよい/慎重にすべき基準
    - **キャッシュ推奨**（結果が準定常・日次で十分）：`/players`（国籍など静的に近い）、`/fixtures/headtohead`、前日固定の `/fixtures`（ターゲット日付ごとにキー分離される）、`/fixtures/lineups`（同一fixture IDに対し再実行時の節約目的）。
    - **キャッシュ非推奨または短期のみ**：`/injuries`（当日でも変動が多い）、`/teams/statistics`（リーグ指定ミスで誤キャッシュのリスク、リーグID修正後はキャッシュクリア要推奨）。
    - **禁止/注意**：ライブスコアや進行中データは現仕様で呼んでいないが、同じキャッシュ層を共有する場合は対象外とする。
- 運用ガイド
    - デバッグでクォータ節約したい場合のみ `USE_API_CACHE=True` をオンにする。本番定時実行は最新性重視のためデフォルトOFFを推奨。
    - キャッシュを ON にしたままリーグIDやクエリ条件を変更した場合、古いキャッシュが混入する可能性があるため `api_cache/` を削除してから再実行する。

#### 2.1.1 負傷者・出場停止情報
*   `/injuries?fixture={id}` で試合IDに紐づく負傷者リストを取得
*   レスポンス: 選手名、チーム名、負傷理由（Knee Injury, Muscle Injury 等）

#### 2.1.2 チームフォーム (H2H / Recent Form)
*   `/teams/statistics?team={id}&season={year}&league={league_id}` でチームの直近フォームを取得
*   **課題**: リーグIDを指定する必要があるため、CL出場チーム（例: アタランタ）の場合はセリエA (league=135) を参照する必要がある
*   **現状の制限**: EPL (league=39) 固定のため、非EPLチームのフォームは空欄になる
*   **TODO**: チームIDからリーグIDを動的に取得するロジックの追加

### 2.2 ニュース・AI層 (News & AI)
試合前情報の収集と要約、およびネタバレ検閲を行う。
*   **ニュース収集**: **Google Custom Search API**
    *   クエリ例: `"Manchester City preview today" -site:bbc.com` (結果速報サイトを除外)
*   **要約・生成・検閲**: **Google Gemini API**
    *   **モデル**: `gemini-pro-latest` (検証済み)
        *   ※地域や設定により `gemini-1.5-flash` 等が使えない場合があるため、安定版の Pro を採用。
    *   **コスト (Google AI Studio)**:
        *   **無料枠 (Free Tier)**:
            *   15 RPM (Requests Per Minute)
            *   1日あたり 1,500 リクエストまで無料
            *   入力トークン: 32k/分, 出力トークン: 1k/分 (十分な余裕あり)
        *   **有料枠への移行**: 明示的に課金設定をしない限り、勝手に課金されることはない。
    *   **役割**: 
        1.  記事要約 (Summarization)
        2.  戦術プレビュー生成 (Tactical Analysis)
        3.  ネタバレ検閲 (Spoiler Filtering)

### 2.3 実行基盤 (Infrastructure)
*   **プラットフォーム**: **GitHub Actions**
*   **ワークフロー名**: `daily_report.yml`
*   **トリガー**:
    1.  **スケジュール実行 (Cron)**: `0 22 * * *` (UTC)
        *   日本時間 (JST) で 毎朝 07:00 に実行。
    2.  **手動実行 (workflow_dispatch)**: GitHub UIから任意のタイミングで実行可能（テスト用）。
*   **処理フロー**:
    1.  **Checkout**: リポジトリの最新コードを取得。
    2.  **Setup Python**: Python 3.9+ 環境を構築。
    3.  **Install Dependencies**: `requirements.txt` からライブラリをインストール。
    4.  **Run Application**:
        *   環境変数 (`secrets.RAPIDAPI_KEY` 等) を注入して `main.py` を実行。
        *   `USE_MOCK_DATA=False` を指定し、実APIを使用。
    5.  **Commit & Push**:
        *   生成された `daily_report.md` をリポジトリにコミットし、メインブランチへプッシュする。
        *   権限: `contents: write` が必要。

### 2.4 閲覧インターフェース (Viewing Interface)
*   **方式**: **メール配信 (Primary)** + GitHubリポジトリ保存 (Backup)
*   **閲覧場所**: 
    *   **メール**: 毎日指定のGmailアドレスにHTMLメールで配信
    *   **リポジトリ**: `reports/YYYY-MM-DD.md` (バックアップ用)
*   **更新フロー**: 毎日07:00 JSTにレポート生成後、メール送信
*   **アーカイブ (Reports Index)**:
    *   すべての過去レポートは `reports/` ディレクトリに保存されます。
    *   GitHub上のファイル一覧から日付 (`YYYY-MM-DD.md`) を選択して閲覧可能です。

### 2.5 メール配信サービス (Email Delivery)
*   **サービス**: **Gmail API** (OAuth2認証)
*   **選定理由**: 個人利用で無料、既存のGoogleアカウントを流用可能
*   **機能**:
    *   Markdown → HTML変換（CSSスタイル付き）
    *   フォーメーション画像のインライン添付
    *   リッチなHTMLテンプレートで視認性向上
*   **認証方式**: OAuth2 (リフレッシュトークン使用)
    *   初回のみローカルでブラウザ認証が必要
    *   以降はリフレッシュトークンで自動更新

## 3. 必要なアカウントとAPIキー
詳細はローカル開発環境の `.env` および GitHub Secrets に設定する。

| サービス | 環境変数名 | 用途 |
| :--- | :--- | :--- |
| **API-Football** | `RAPIDAPI_KEY` | 試合データ取得 |
| **Gemini API** | `GOOGLE_API_KEY` | AI要約・検閲 |
| **Google Search** | `GOOGLE_SEARCH_API_KEY` <br> `GOOGLE_SEARCH_ENGINE_ID` | 記事検索 |
| **Gmail API** | `GMAIL_TOKEN` <br> `GMAIL_CREDENTIALS` | メール送信認証 |
| **メール設定** | `NOTIFY_EMAIL` <br> `GMAIL_ENABLED` | 送信先・有効化フラグ |

## 4. プログラム構造
```mermaid
graph TD
    A[GitHub Actions (07:00 JST)] --> B[main.py]
    B --> C{Match Extraction}
    C -- API-Football --> D[Match Data]
    B --> E{Facts Service}
    E -- API-Football --> F[Lineups/Formations]
    B --> G{News Service}
    G -- Google Search --> H[Articles]
    G -- Gemini API --> I[Summary & Preview]
    B --> J{Report Generation}
    J --> K[daily_report.md]
    J --> M{Email Service}
    M -- Gmail API --> N[HTML Email with Images]
    K --> L[Git Commit & Push]
```

### 4.1 フォーメーション図生成 (Formation Diagram)
*   **ライブラリ**: **Pillow (PIL)**
*   **用途**: 各試合のスタメン情報をフォーメーション配置で可視化
*   **処理フロー**:
    1.  フォーメーション文字列（例: `4-3-3`）をパース
    2.  ピッチ画像テンプレート上に選手名を配置
    3.  PNG画像として `reports/images/` に保存
    4.  Markdownから `![Formation](images/xxx.png)` で参照
*   **コスト**: 無料（外部API不要）

## 5. 時刻・タイムゾーンの考え方

本システムでは複数の環境で時刻を扱うため、タイムゾーンの統一的な取り扱いが重要である。

### 5.1 環境別タイムゾーン

| 環境 | システム時刻 | 対応 |
| :--- | :--- | :--- |
| **GitHub Actions** | **UTC** | Pythonコード内で明示的にJST変換が必要 |
| **ローカル開発 (Mac/日本)** | **JST** | そのままでも動作するが、一貫性のためJST明示推奨 |

### 5.2 時刻処理の設計方針

1. **レポートファイル名**: 実行時のJST日付を使用
   - `datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d')`
   - ✗ `datetime.now()` → GitHub ActionsではUTCとなり日付がずれる

2. **試合データの日付フィルタ**: JSTベースで「前日07:00〜当日06:59」
   - キックオフ時刻をJSTに変換してからフィルタリング

3. **Cron スケジュール**: UTC表記
   - `0 22 * * *` (UTC) = 毎日 07:00 JST

### 5.3 実装上の注意

```python
import pytz
from datetime import datetime

# 正しい例
jst = pytz.timezone('Asia/Tokyo')
now_jst = datetime.now(jst)  # JSTで現在時刻を取得

# 誤った例（GitHub ActionsではUTCになる）
now_utc = datetime.now()  # システムローカル時刻 = UTC
```

## 6. 参考情報：AIモデル選定比較
(Reference: AI Model Comparison)

本システムでは **`gemini-pro`** を採用していますが、要件や環境に応じて他のモデルも検討可能です。

| モデル名 | 特徴 | 料金 (Free Tier) | 制限事項 | 採用可否 |
| :--- | :--- | :--- | :--- | :--- |
| **gemini-1.5-flash** | **最安・最速**。<br>大量のトークンを高速処理可能。 | **15 RPM / 1,500 RPD**<br>入力100万トークン対応 | 一部の古いAPIキーやリージョンで `404 Not Found` が発生する場合がある（今回のケース）。 | **次点 (Alternative)**<br>アクセス可能ならこちらが推奨。 |
| **gemini-pro**<br>*(ver 1.0)* | **安定・標準**。<br>バランスが良い。 | **15 RPM / 1,500 RPD** | Flashより文脈長は短いが、ニュース要約には十分。 | **採用 (Selected)**<br>現環境で最も確実に動作するため。 |
| **gemini-1.5-pro** | **高精度**。<br>複雑な推論が得意。 | **2 RPM / 50 RPD**<br>(制限が厳しい) | 1日50リクエスト制限のため、一括処理時に枯渇するリスクがある。 | **不採用**<br>オーバースペックかつ制限リスクあり。 |

※ **RPM**: Requests Per Minute (1分あたりのリクエスト数)
※ **RPD**: Requests Per Day (1日あたりのリクエスト数)
