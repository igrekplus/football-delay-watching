---
description: デバッグモードでレポート生成 + Firebase Hostingへデプロイ
---

# Debug Run & Deploy

デバッグモードでレポートを生成し、Firebase Hostingにデプロイするワークフロー。

## 前提条件

- `.venv` が作成済みであること
- 初回のみ: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

## 手順

// turbo-all

1. venv を有効化してデバッグモードで実行
```bash
# 特定の日付(YYYY-MM-DD)を指定する場合は TARGET_DATE を設定
# 計算式: TARGET_DATE = 試合日(現地) + 1日
#
# | 見たい試合の現地日付 | TARGET_DATE (JST) |
# |---------------------|-------------------|
# | 1/7 (火)            | 2026-01-08        |
# | 1/8 (水)            | 2026-01-09        |
#
# ※ TARGET_DATEはJST基準。APIから取得する試合日時はUTC。
#   内部で比較する際、TARGET_DATEの0時(JST)以降の試合を除外する。
TARGET_DATE=2026-01-08 DEBUG_MODE=True USE_MOCK_DATA=False python main.py

# 実行後は必ずデプロイすること
python scripts/sync_firebase_reports.py
firebase deploy --only hosting
```

2. 生成されたHTMLとimagesを確認
```bash
ls -la public/reports/*.html | tail -5
ls -la public/reports/images/*.png | tail -5
```

3. デプロイ前にFirebaseからレポートを同期（紛失防止）
```bash
python scripts/sync_firebase_reports.py
```

4. Firebase Hostingへデプロイ
```bash
firebase deploy --only hosting
```

5. デプロイ完了後、ブラウザでWEBサイトを確認
まずLLM（あなた）が確認してから、ユーザ側に確認を促すこと。
```bash
open https://football-delay-watching-a8830.web.app
```

## 補足

- デバッグモードでは1試合のみ処理
- 選手検索は1人/チームに削減（クォータ節約）
- レポートには `[DEBUG]` バッジが表示される
