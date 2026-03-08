# 2026-03-08 Google OAuth 公開化 実装計画

## Goal
- Google OAuth では許可リストなしで誰でもログインできるようにする。
- ID/PW ログインは既存どおり `allowed_emails.json` ベースで制限し、運用用途を維持する。
- Firebase/Firebase Hosting 側の設定意図をドキュメントに残し、再デプロイで巻き戻らない状態にする。

## Scope
- `public/assets/auth_common.js` に provider ごとの認可判定を追加する。
- `public/index.html` と `src/calendar_generator.py` のログイン後判定を新ルールへ置き換える。
- `docs/03_components/login.md` と `docs/04_operations/deployment.md` を更新する。
- Firebase MCP で現行プロジェクトと Web App 設定を確認し、Auth 設定反映の前提を整理する。

## Design Decisions
- Google の初回ログインは Firebase Authentication の標準挙動に任せ、クライアント側では遮断しない。
- ID/PW は誤開放を避けるため、従来どおり許可リストを必須とする。
- 認可判定は `user.getIdTokenResult()` の `sign_in_provider` を優先し、取得不能時のみ `providerData` にフォールバックする。
- `calendar.html` は生成物のため、生成元の `src/calendar_generator.py` を修正して反映する。

## Validation
1. `python -m src.calendar_generator`
2. `python -m py_compile src/calendar_generator.py`
3. `git diff -- public/assets/auth_common.js public/index.html src/calendar_generator.py docs/03_components/login.md docs/04_operations/deployment.md implementation_plan.md task.md`
4. Firebase CLI / MCP でプロジェクト・Web App・SDK config を再確認する
