# 2026-03-13 Issue #243 過去の対戦UI 実装計画

## Goal
- 「過去の対戦成績」テーブルから home 視点の `結果` 列を削除し、見づらさを解消する。
- 既存の集計要約 (`h2h_summary`) とスコア表示は維持し、情報量を減らしすぎない。
- 変更意図を描画ドキュメントへ反映し、今後のUI実装で `結果` 列を復活させないようにする。

## Scope
- `templates/partials/h2h_table.html` の列定義を更新する。
- 必要なら `public/assets/report_styles.css` のテーブル表示を微調整する。
- `docs/03_components/report_rendering.md` に H2H テーブル表示方針を追記する。
- `implementation_plan.md` `task.md` `walkthrough.md` を #243 向けに更新する。

## Out of Scope
- `src/services/facts_formatter.py` の H2H 集計ロジック変更。
- `h2h_summary` の文言変更。
- 過去の対戦セクション全体のレイアウト刷新やカード化。

## Design Decisions
- データ構造の `result_key` は今回は残す。既存テストや将来の内部利用を壊さず、UIだけを最小変更で直すため。
- 列削除はテンプレート層で完結させる。集計ロジックまで触ると影響範囲が広がり、Issue要件に対して過剰。
- UI後退を防ぐため、テンプレートの単体テストで `結果` 見出しと `Win/Draw/Loss` 表示が含まれないことを確認する。

## Validation
1. `python -m unittest tests.test_h2h_table_template`
2. `DEBUG_MODE=True USE_MOCK_DATA=True TARGET_DATE="2026-01-08" python main.py`
3. 生成された `public/reports/*.html` を開いて、過去の対戦成績テーブルが `日付 / 大会 / 対戦 / スコア` の4列になっていることを確認する。
4. 必要なら `./scripts/safe_deploy.sh` を実行し、公開URLで表示確認する。
