# Issue #239 Implementation Plan

## Goal
- `wider-player-modal` の現行内容を引き継ぎつつ、選手詳細モーダルをデスクトップ/iPadで見やすくする。
- モーダル本文はスクロール量を減らすため、十分な横幅と2カラム表示を採用する。

## Scope
- `public/assets/report_styles.css` のモーダル寸法とレスポンシブ条件を調整する。
- 既存の `templates/partials/player_profile_modal.html` とプロフィール本文構造は維持する。
- デバッグモードで実データのレポートを再生成し、見た目を確認する。

## Design Decisions
- モーダルの基本方針は「大画面では広く、モバイルでは従来どおり1カラム」。
- 本文カードは `769px` 以上で2カラム表示にし、iPad相当でもスクロール量を削減する。
- 画面幅いっぱいに広がりすぎないよう、最大幅には固定上限を設ける。
- 既存のセクション順、ヘッダ、写真、閉じる操作、キーボード操作は変更しない。

## Validation
1. `TARGET_DATE="2026-03-05" DEBUG_MODE=True USE_MOCK_DATA=False python main.py`
2. 生成HTMLをローカルで開き、PC幅とiPad幅でモーダル確認
3. `git diff` で意図しない変更がないことを確認
