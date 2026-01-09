---
description: Issue番号を指定して、ブランチ作成から実装、検証、マージまでの一連のフローを実行します。
---

1. ユーザーからIssue番号（例："102"）が提供されているか確認する。提供されていない場合はユーザーに尋ねる。
2. `gh issue view <NUMBER>` を使用してIssueの詳細を確認する。
3. 作業を開始する際、Issueに `in-progress` ラベルを追加する: `gh issue edit <NUMBER> --add-label "in-progress"`。
4. `feature/issue-<NUMBER>-<SHORT_TITLE>` という名前の新しいブランチを作成する。ショートタイトル（ケバブケース）の生成にはIssueのタイトルを使用する。
5. **計画フェーズ (Planning Phase)**:
   - **設計ドキュメントの更新 (事前)**: コードを書く*前に*、意図した変更を反映させるために `docs/02_design/` 内の関連する設計ドキュメントを更新する。
   - 変更内容を概説する `implementation_plan.md` を作成または更新する。
   - `notify_user` を使用して、計画と設計ドキュメントのレビューを依頼する。
6. **実行フェーズ (Execution Phase)**:
   - 承認されたら、計画に従って変更を実装する。
   - 進行に合わせて `task.md` を更新する。
7. **検証フェーズ (Verification Phase)**:
   - `debug-run.md`の内容に則り作業を行う。明確にdebug-runの何の作業をするか宣言してから作業を実施する。
   - デバッグモードでアプリケーションを実行し、変更を検証する: `DEBUG_MODE=True USE_MOCK_DATA=False python main.py`
   - ログと生成されたレポートを確認する。
   - `/debug-run` ワークフローまたは手動コマンドを使用してFirebase Hostingにデプロイする。
   - 結果を報告するために `walkthrough.md` を作成する。
   - マージ前の最終レビューを依頼するために `notify_user` を使用する。
   
   > [!CAUTION]
   > **モックモード（`USE_MOCK_DATA=True`）で検証する場合は、必ず事前にユーザーに「この変更はモックで検証可能か」を確認すること。**
   > LLMプロンプト変更やAPI連携の変更はモックでは検証できない。
8. **ドキュメントフェーズ (最終レビュー)**:
   - 実装/デバッグ中に行われた変更を取り込むため、`docs/02_design/` 内の関連する設計ドキュメントを更新する。
   - 必要に応じて `GEMINI.md` を更新する。
   - "Code follows Design"（コードは設計に従う）の原則が守られていることを確認する。
9. **完了フェーズ (Completion Phase)**:
   - **マージ前の最終確認 (Critical)**: `git diff main...HEAD` を実行し、意図しない変更（特に既存機能の削除や不要なファイルの上書き）が含まれていないか必ず確認する。
   - 承認されたら、ブランチを `main` にマージする。
   - リモートにプッシュする: `git push origin main`。
   - 変更内容と検証結果を要約したコメントを添えてIssueをクローズする。
   - 機能ブランチを削除する。

### コミットメッセージのテンプレート
```
feat(#123): 実装内容の要約

- 詳細変更点
- ...

Closes #123
```

Example usage: `/resolve-issue 102`
