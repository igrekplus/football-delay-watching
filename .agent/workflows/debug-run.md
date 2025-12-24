---
description: デバッグモードでレポート生成 + Firebase Hostingへデプロイ
---

# Debug Run & Deploy

デバッグモードでレポートを生成し、Firebase Hostingにデプロイするワークフロー。

## 手順

// turbo-all

1. デバッグモードで実行
```bash
DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```

2. 生成されたHTMLとimagesを確認
```bash
ls -la public/reports/*.html | tail -5
ls -la public/reports/images/*.png | tail -5
```

3. Firebase Hostingへデプロイ
```bash
firebase deploy --only hosting
```

4. デプロイ完了後、ブラウザでWEBサイトを確認
```bash
open https://football-delay-watching-a8830.web.app
```

## 補足

- デバッグモードでは1試合のみ処理
- 選手検索は1人/チームに削減（クォータ節約）
- レポートには `[DEBUG]` バッジが表示される
