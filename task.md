# Issue #216 タスク分解

作成日: 2026-02-23

## Phase 0: 準備

- [x] Issue本文の要件と受け入れ条件を確認する
- [x] 対象ファイルの現状を確認する
- [x] `in-progress` ラベルを付与する

## Phase 1: デプロイ前ガードと CI fail-fast

- [x] `scripts/safe_deploy.sh` に必須JSONファイルの存在チェックを追加する
- [x] `scripts/safe_deploy.sh` に JSON 構文チェックを追加する
- [x] `daily_report.yml` に `FIREBASE_CONFIG` / `ALLOWED_EMAILS` の空チェックを追加する
- [x] `daily_report.yml` に JSON 構文チェックを追加する
- [x] `update-calendar.yml` に `FIREBASE_CONFIG` / `ALLOWED_EMAILS` の空チェックを追加する
- [x] `update-calendar.yml` に JSON 構文チェックを追加する
- [x] 両 workflow にデプロイ後スモークテストを追加する

## Phase 2: キャッシュ整合性改善

- [x] `firebase.json` に `/` 向け no-store ヘッダーを追加する
- [x] `firebase.json` に `/reports/manifest.json` 向け no-store ヘッダーを追加する
- [x] `scripts/sync_firebase_reports.py` に manifest 取得 cache-buster を追加する

## Phase 3: ドキュメント反映

- [x] `docs/04_operations/deployment.md` に新運用（ガード・スモーク・キャッシュ方針）を追記する
- [x] 実装後のコマンド例と検証結果に合わせて文言を最終調整する

## Phase 4: 検証と仕上げ

- [x] ローカルで JSON 構文検証を実行する
- [ ] 対象テストを実行し回帰がないことを確認する（`tests/test_login.py` の依存不足、`test_llm_response_logging` 失敗のため未達）
- [ ] 差分を確認し、Issue 要件との対応表を作成する
- [x] （任意）Phase 3 の設計改善を別Issue化する（#217）

---

# Issue #234 タスク分解

作成日: 2026-03-01

## Phase 0: 準備

- [x] Issue本文の要件を確認する
- [x] `in-progress` ラベルを付与する
- [x] 既存のデバッグセクションとリンク定義箇所を確認する

## Phase 1: 設計反映

- [x] `implementation_plan.md` に #234 の計画を追記する
- [x] `docs/03_components/report_rendering.md` にデバッグ情報の統合ルールを追記する
- [x] `docs/04_operations/api_quota.md` にデバッグリンクの運用URLを追記する

## Phase 2: 実装

- [x] デバッグ情報を単一の折りたたみセクションへ統合する
- [x] `Fixture ID` をデバッグ情報へ表示する
- [x] `対象外動画一覧` の出力をやめる
- [x] `Gemini API` / `Gemini Grounding` のリンクを更新する

## Phase 3: テストと確認

- [x] デバッグ表示の単体テストを追加する
- [x] ローカルで関連テストを実行する
- [x] debug 実行で実画面を確認する
