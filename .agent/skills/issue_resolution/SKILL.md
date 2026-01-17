---
name: issue_resolution
description: Issue解決のための高度な思考プロセスと手順を定義したスキル。柔軟な判断が求められるIssue対応全般を担当する。
---

# Issue Resolution Skill (Issue解決スキル)

## 概要
GitHub Issueを解決するための包括的なスキルです。
このスキルは単なる手順書ではなく、各フェーズにおける**意思決定のフレームワーク**を提供します。
「どのように作業を進めるべきか」に迷った際、このスキルを参照して判断を行ってください。

## 基本方針
1.  **Design First**: コードを書く前に、必ず設計（既存ドキュメントの更新と実装計画の作成）を行う。
2.  **Incremental Progress**: タスクを細かく分解し、進捗を `task.md` で管理する。
3.  **Visual Verification**: UI変更や出力結果の変更を伴う場合は、必ず実環境へのデプロイ（`/deploy`）とURL報告を行う。
4.  **No Regressions**: マージ前に必ず `main` との差分を確認し、意図しない破壊的変更を防ぐ。

---

## 🎭 意思決定プロセス

### 1. 準備フェーズ (PREPARATION)
- **Issueの理解**: `gh issue view <NUMBER>` で背景と要件を深く理解する。
- **ラベリング**: `gh issue edit <NUMBER> --add-label "in-progress"` で作業中であることを明示する。
- **ブランチ作成**: `feature/issue-<NUMBER>-<SHORT_TITLE>` という命名規則に従う。

### 2. 計画・設計フェーズ (PLANNING & DESIGN)
- **設計ドキュメントの更新**: `docs/02_architecture/` 等を確認し、変更が必要なドキュメントを「事前に」更新する。
- **実装計画の作成**: 複雑な変更には `implementation_plan.md` を作成する。
- **タスク分割**: `task.md` に具体的なステップを記述する。
- **ユーザーレビュー**: 計画の妥当性について `notify_user` で承認を得る。

### 3. 実装・テストフェーズ (EXECUTION & TESTING)
- **コード実装**: 承認された計画に基づき実装を行う。
- **検証環境の構築**:
    - 実データ検証が必要かUIのみで良いかに応じて、`/debug-run` の設定（`USE_MOCK_DATA`）を選択する。
    - `TARGET_DATE` はスタメン確定済みの「2日以上前の日付」を指定する（詳細は `/debug-run` 参照）。
- **デプロイと確認**:
    - `/deploy` ワークフローを使用して Firebase Hosting にデプロイする。
    - **自身でURLを確認した後**、ユーザーに `walkthrough.md` と共にURLを報告する。

### 4. 完了・レビューフェーズ (COMPLETION & REVIEW)
- **マージ前チェック (`/check-close` 相当)**:
    - 解決状況の整理: 課題と解決方針、結果を3列の表にまとめ、`walkthrough.md` に記載する。
    - 残課題の確認: 会話の中で指摘された点に漏れがないか再確認する。
    - 差分確認: `git diff main...HEAD` を実行し、余計な変更がないか厳密にチェックする。
- **マージとクローズ**:
    - 指定されたテンプレートでコミットし、`main` にマージ・プッシュする。
    - workflowの内容をもとに、Issueにコメントを追加のうえでクローズし、機能ブランチを削除する。

---

## 🛠️ 関連ワークフローへの参照
このスキルを実行中に、以下の固定手順（Workflow）を呼び出してください。

- **実行・検証**: [/debug-run](file:///.agent/workflows/debug-run.md)
- **デプロイ**: [/deploy](file:///.agent/workflows/deploy.md)
- **クローズ確認**: [/check-close](file:///.agent/workflows/check-close.md)
- **プロンプト調整**: [/tune-gemini](file:///.agent/workflows/tune-gemini.md)
- **不備修正**: [/delete-report](file:///.agent/workflows/delete-report.md)

---

## 📝 コミットメッセージのテンプレート
```
feat(#123): 実装内容の要約

- 詳細変更点
- ...

Closes #123
```
