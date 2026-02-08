---
description: firebase上へのデプロイを行い、URLを返す
---

# Deploy Workflow

ローカルで生成したレポートをFirebase Hostingにデプロイする手順です。
デプロイ前に必ず同期処理を行うことで、サーバー上のデータを意図せず上書き・消失することを防ぎます。

## 手順

// turbo-all

### 1. 安全なデプロイスクリプトの実行
このスクリプトは内部で `sync_firebase_reports.py` を実行し、デプロイ前にサーバー上の最新状態をローカルに同期します。これにより、GitHub Actionsなどで生成された最新レポートを誤って上書きして消去してしまう事故を防止します。

```bash
./scripts/safe_deploy.sh
```

### 2. URLの確認と報告
デプロイ完了後、公開URL（https://football-delay-watching-a8830.web.app）を開き、レポートやカレンダーが正しく表示されているか確認してください。
/](https://football-delay-watching-a8830.web.app/)

必要に応じて `curl -I https://football-delay-watching-a8830.web.app/` で導通を確認してください。
