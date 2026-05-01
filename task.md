# 2026-05-01 Issue #252 Tasks

## Phase 1: Planning
- [x] Issue #252 の本文と添付スクリーンショットを確認
- [x] `in-progress` ラベルを付与
- [x] 選手詳細モーダルのHTML/CSS実装箇所を特定
- [x] `implementation_plan.md` を #252 向けに更新
- [x] `docs/03_components/report_rendering.md` に写真枠の設計方針を追記
- [x] 計画についてユーザー承認を得る

## Phase 2: Implementation
- [x] `feature-252/fix-player-photo-frame` ブランチを作成
- [x] `.player-profile-modal-photo-frame` を四角のまま、ナマ画像と喧嘩しない枠・背景・余白へ調整
- [x] `.player-profile-modal-photo` は不自然な拡大/トリミングを避けて調整
- [x] 通常の選手カードにも同じズレがあるか確認し、必要な場合のみ揃える
- [x] モバイル幅のヘッダー表示を必要に応じて調整
- [x] 必要ならテンプレート構造を最小修正

## Phase 3: Verification
- [ ] 関連するユニットテストを実行
- [ ] `DEBUG_MODE=True USE_MOCK_DATA=True` でdebug-runを実行
- [ ] 生成HTMLを `file://` で開き、プロフィールモーダルの写真枠を確認
- [ ] デスクトップ幅とモバイル幅で、写真・名前・国旗・チームロゴの重なりがないことを確認
- [ ] 検証結果を `walkthrough.md` に記録

## Phase 4: Deploy and Report
- [ ] 修正したファイルだけをcommit
- [ ] `/deploy` ワークフローでFirebase Hostingへデプロイ
- [ ] 公開URLを `curl` で取得してHTTP 200を確認
- [ ] Issueの課題・方針・結果を `walkthrough.md` に3列表で整理
- [ ] ユーザーへURL、walkthrough、苦労点、残課題を報告

## Notes
- 現在の未追跡 `.claude/worktrees/` は本件と無関係のため触らない。
- CSSだけで解決できる可能性が高いため、データ取得ロジックには触れない。
- UI微修正のため検証は原則 `USE_MOCK_DATA=true` でよい。
- まず見た目を確認し、ユーザーが問題ないと判断した後にdebug-runで再確認する。
