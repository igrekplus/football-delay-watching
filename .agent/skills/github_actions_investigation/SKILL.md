---
name: github_actions_investigation
description: GitHub Actions の直近失敗原因を調査するときに使う。gh run / gh api / ログZIPを確認し、過去の失敗例と照合して原因を短く切り分ける。
---

# GitHub Actions Investigation

## 調査方法
1. `gh run list --limit 10` で直近失敗を特定し、`gh run view <RUN_ID> --json conclusion,status,url,createdAt,jobs` と `gh run view <RUN_ID> --log-failed` を確認する。
2. ログが空または不足する場合は `gh api repos/<OWNER>/<REPO>/actions/runs/<RUN_ID>/logs > /tmp/run.zip` でログZIPを取得し、job metadata と `system.txt` を見る。

## 過去の失敗例
- `steps: []` / `runner_id: 0` かつ `system.txt` が runner 待ちだけなら、コード起因ではなく GitHub-hosted runner 側の一時的キャンセルとして扱う。
- Firebase deploy で `HTTP 429` / Hosting storage quota が出た場合は、Firebase Hosting versions の肥大化が原因。古い versions 削除や保持数設定を確認する。
- Actionsログに Secret Manager 由来の値が env 表示されることがあるため、調査時に露出を見つけたら `::add-mask::` や secret ローテーションを提案する。
