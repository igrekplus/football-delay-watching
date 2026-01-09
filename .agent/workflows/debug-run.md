# Debug Run & Deploy (絶対遵守)

デバッグモードでレポートを生成し、Firebase Hostingにデプロイする。
**「実データをAPIから取得してテストしたい」のか「UIだけ確認したい」のかを、環境変数で厳密に使い分けること。**

## 🚨 重要：実行モードの選択

| 目的 | 指定する環境変数 |
| :--- | :--- |
| **実データの取得・検証**（今回のようなケース） | `DEBUG_MODE=True USE_MOCK_DATA=False` |
| UI/レイアウトのみの確認（APIを叩かない） | `DEBUG_MODE=True USE_MOCK_DATA=True` |

---

## 手順

// turbo-all

### 1. レポート生成（実データ検証モード）

以下のコマンドをコピーして実行する。**`USE_MOCK_DATA=False` を忘れると、APIを叩かずに偽データで動くので注意。**

```bash
# 日付(YYYY-MM-DD)は必要に応じて変更
# 指定した日付の「07:00 JST」として実行される（＝その前の晩の試合を拾う）
TARGET_DATE="2026-01-10" DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```

**[確認項目]**
ログの開始直後に出る以下の行を**必ず**目視確認すること：
`Starting workflow... (Dry Run: False, Mock: False)`
→ `Mock: False` になっていればOK。`Mock: True` なら即座に停止してやり直すこと。

### 2. 生成物のローカル確認
ファイルが存在するか、日付が正しいかを確認。
```bash
ls -lt public/reports/*.html | head -n 5
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
デプロイ完了後、公開URL（https://football-delay-watching-a8830.web.app）を開き、生成されたレポートのURLを特定してユーザーに報告する。

---

## 📅 TARGET_DATE の計算ガイド
「見たい試合の現地日付」の **+1日** を指定するのがルール。

| 見たい試合の現地日付 | 指定する TARGET_DATE (JST) |
| :--- | :--- |
| 1/7(火) の試合 | 2026-01-08 |
| 1/10(土) の試合 | 2026-01-11 |

---

## 💡 トラブルシューティング
- **"No matches found" と出る**: TARGET_DATEがずれているか、指定した期間に試合がない。
- **データが古い**: `rm -rf .gemini/cache` でローカルキャッシュを消して再試行。
