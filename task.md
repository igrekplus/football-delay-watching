# Issue #215 タスク分解

作成日: 2026-02-23

## Phase 0: 計画承認

- [x] Issue本文の要件を確認する（現状導線/目標導線/デバッグリンク位置）
- [x] 現行実装を調査する（`public/index.html`, `src/calendar_generator.py`, `public/calendar.html`）
- [x] 実装方針の承認を得る（シンプル導線、遷移固定方針）

## Phase 1: 導線変更（ログイン後カレンダー）

- [x] `public/index.html` でログイン成功後の既定遷移を `calendar.html` に変更する
- [x] レポート一覧を表示する query（例: `view=reports`）を実装する
- [ ] 既存のログイン/エラーハンドリングが回帰していないことを確認する

## Phase 2: カレンダー導線追加

- [x] カレンダーヘッダーに「レポート一覧」導線を追加する

## Phase 3: 生成物更新・検証

- [x] `python -m src.calendar_generator` を実行し `public/calendar.html` を再生成する
- [x] カレンダー関連テスト（`tests/test_calendar_generator.py`, `tests/test_calendar_data_loader.py`）を実行し回帰を確認する
- [ ] 手動で以下遷移を確認する
- [ ] ログイン画面 → カレンダー → レポート
- [ ] ログイン画面 → カレンダー → レポート一覧 → レポート

## Phase 4: 仕上げ

- [ ] 変更差分を `git diff main...HEAD` 観点で確認する
- [ ] 実装結果を `walkthrough.md` に整理する
- [ ] 必要時 `/deploy` 実施後、確認URLを共有する
