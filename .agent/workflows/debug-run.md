# Debug Run & Deploy (絶対遵守)

デバッグモードでレポートを生成し、Firebase Hostingにデプロイする。
**「実データをAPIから取得してテストしたい」のか「UIだけ確認したい」のかを、環境変数で厳密に使い分けること。**

## 🚨 重要：実行モードの選択

| 目的 | 指定する環境変数 |
| :--- | :--- |
| **実データの取得・検証** | `DEBUG_MODE=True USE_MOCK_DATA=False` |
| UI/レイアウトのみの確認（APIを叩かない） | `DEBUG_MODE=True USE_MOCK_DATA=True` |

---

## 前提条件

- `.venv` が作成済みであること
- 初回のみ: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

## 手順

// turbo-all

### 1. venv の有効化とレポート生成

以下のコマンドを実行する。**`USE_MOCK_DATA=False` を忘れると、APIを叩かずに偽データで動くので注意。**

```bash
# venvを有効化
source .venv/bin/activate

# 日付(YYYY-MM-DD)は必要に応じて変更
# 指定した日付の「07:00 JST」として実行される（＝その前の晩の試合を拾う）
TARGET_DATE="2026-01-10" DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```

**[確認項目]**
ログの開始直後に出る以下の行を**必ず**目視確認すること：
`Starting workflow... (Dry Run: False, Mock: False)`
→ `Mock: False` になっていればOK。`Mock: True` なら即座に停止してやり直すこと。

### 2. 生成物のローカル確認
HTMLファイルとフォーメーション画像が生成されているか確認。
```bash
# HTMLの確認
ls -lt public/reports/*.html | head -n 5

# 画像の確認
ls -la public/reports/images/*.png | tail -5
```

### 3. Firebaseとの同期（必須：他人の進捗を上書きしないため）
```bash
python scripts/sync_firebase_reports.py
```

### 4. デプロイ
```bash
firebase deploy --only hosting
```

### 5. URLの確認と報告
デプロイ完了後、公開URL（https://football-delay-watching-a8830.web.app）を開く。
**まずLLM（あなた）が確認してから、ユーザ側に報告を促すこと。**

---

## 📅 TARGET_DATE の計算ガイド
「見たい試合の現地日付」の **+1日** を指定するのがルール。

| 見たい試合の現地日付 | 指定する TARGET_DATE (JST) |
| :--- | :--- |
| **過去の例**: 12/23(月) | 2025-12-24 |
| **直近の例**: 1/7(火) | 2026-01-08 |
| **未来の例**: 1/10(土) | 2026-01-11 |

---

## 補足事項

- **1試合のみ処理**: デバッグモード（DEBUG_MODE=True）では、クォータ節約のため1試合のみを処理対象とする。
- **選手情報の制限**: 選手検索クォータ節約のため、1チームあたり1人程度の検索に制限される場合がある。
- **DEBUGバッジ**: 生成されたレポートのタイトル横に `[DEBUG]` または `[MOCK]` バッジが表示される。
- **キャッシュのクリア**: データが古い場合は `rm -rf .gemini/cache` でローカルキャッシュを消して再試行。
