# 環境セットアップ & 閲覧ガイド

本システムを自身の環境でセットアップし、実際に運用するためのガイドです。

## 1. 必要なアカウントとAPIキー

本システムは以下の外部APIを使用します。それぞれのサービスでAPIキーを取得してください。

### 1) RapidAPI (API-Football)
*   **用途**: 試合日程、スタメン、フォーメーション情報の取得
*   **登録とキー取得**:
    1.  [RapidAPI (API-Football)](https://rapidapi.com/api-sports/api/api-football) にアクセス。
    2.  アカウントを作成し、"Subscribe to Test" (Basic Free Plan) を選択。
    3.  `X-RapidAPI-Key` を取得。

### 2) Google AI Studio (Gemini API)
*   **用途**: ニュース記事の要約、戦術プレビューの生成、ネタバレ箇所の検閲
*   **キー取得**:
    1.  [Google AI Studio](https://aistudio.google.com/) にアクセス。
    2.  "Get API key" からAPIキーを作成。

        - [認証情報](https://console.cloud.google.com/apis/credentials) で「APIキーを作成」。  
        - 可能なら HTTP リファラ（*.yourdomain.com）やIPで制限する。ローカル開発なら制限なしでも可。  
        - 得たキーを `.env` の `GOOGLE_SEARCH_API_KEY` に設定。

---

## 2. GitHub Secrets の設定 (自動実行用)

GitHub Actionsで自動実行するために、取得したキーをリポジトリの「Secrets」に保存します。

1.  GitHubリポジトリのページを開きます。
2.  **「Settings」** タブ > 左メニュー **「Secrets and variables」** > **「Actions」** をクリック。
3.  **「New repository secret」** ボタンから以下の4つを追加してください。
    *   名前 (Name) は `.env` の変数名と同じにする必要があります。

| Name | Secret (Value) |
| :--- | :--- |
| `RAPIDAPI_KEY` | (API-Footballのキー) |
| `GOOGLE_API_KEY` | (Gemini APIキー) |
| `GOOGLE_SEARCH_ENGINE_ID`| (Custom Search Engine ID `cx`) |
| `GOOGLE_SEARCH_API_KEY` | (Legacy API Key または CredentialsのKey) |

⚠️ **注意**: `USE_MOCK_DATA` はワークフロー内で自動的に `False` に設定されるため、登録不要です。

---

## 3. 環境変数 (.env) の設定 (ローカル開発・検証用)

ローカルで動作確認を行う場合は `.env` を使用します。

1.  プロジェクトルートの `.env.example` をコピーして `.env` ファイルを作成します。
    ```bash
    cp .env.example .env
    ```
2.  `.env` ファイルを開き、各自のキーを入力して保存します。
    ```ini
    RAPIDAPI_KEY=your_key_here
    GOOGLE_API_KEY=your_key_here
    GOOGLE_SEARCH_ENGINE_ID=your_id_here
    GOOGLE_SEARCH_API_KEY=your_key_here
    ```

### 検証コマンド
以下のコマンドで個別のAPI接続を確認できます。
```bash
python3 tests/verify_api_football.py
python3 tests/verify_google_search.py
python3 tests/verify_gemini.py
```

### 全体実行 (E2Eテスト)
メインプログラムを手動で実行し、`reports/` フォルダにファイルが生成されれば成功です。
```bash
python3 main.py
```

---

## 4. レポートの閲覧方法

システムは毎朝07:00 (JST) に自動実行されます。

1.  **GitHubリポジトリにアクセスする**
2.  **`reports/` フォルダを開く**
    *   日付ごとに `YYYY-MM-DD.md` というファイルが生成されています。
3.  **内容を確認する**
    *   ネタバレなし観戦ガイドが表示されます。
    *   ニュース要約には情報元 (Source) のURLが記載されています。
