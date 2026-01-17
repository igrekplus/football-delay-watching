---
description: firebase上へのデプロイを行い、URLを返す
---

# Deploy Workflow

ローカルで生成したレポートをFirebase Hostingにデプロイする手順です。
デプロイ前に必ず同期処理を行うことで、サーバー上のデータを意図せず上書き・消失することを防ぎます。

## 手順

// turbo-all

### 1. 同期処理 (Firebase -> Local)
サーバー上の既存レポートをローカルの `public/reports` に同期します。これを忘れると、デプロイ時に古いデータが消えてしまいます。

```bash
source .venv/bin/activate
python scripts/sync_firebase_reports.py
```

### 2. デプロイ実行
Firebase Hostingへファイルをアップロードします。

```bash
firebase deploy --only hosting
```

### 3. URL確認と報告
デプロイ完了後、以下のURLを確認し、ユーザーに報告してください。

- **URL**: [https://football-delay-watching-a8830.web.app/](https://football-delay-watching-a8830.web.app/)

必要に応じて `curl -I https://football-delay-watching-a8830.web.app/` で導通を確認してください。
