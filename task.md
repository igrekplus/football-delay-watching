# 2026-03-08 Google OAuth 公開化 Tasks

- [x] 認証実装と Firebase 設定の現状を確認
- [x] 変更方針を `implementation_plan.md` に記録
- [x] provider 別の認可判定を共通化
- [x] ログイン画面とカレンダー画面へ新ルールを反映
- [x] 関連ドキュメントを更新
- [x] Firebase MCP / CLI で設定前提を再確認
- [x] 差分と静的検証結果を整理

## Notes

- `firebase_init` で Authentication 設定を `firebase.json` に反映しました。
- `firebase deploy --only auth` は現行 CLI で `No targets in firebase.json match '--only auth'` となり、リモート反映には使えませんでした。
- Hosting 側の変更は `./scripts/safe_deploy.sh` で本番へ反映済みです。
