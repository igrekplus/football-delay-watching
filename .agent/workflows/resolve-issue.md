---
description: Issue番号を指定して、ブランチ作成から実装、検証、マージまでの一連のフローを実行します。
---

1. Ensure you have the Issue Number provided by the user (e.g., "102"). If not, ask the user for it.
2. Read the issue details using `gh issue view <NUMBER>`.
3. Create a new branch named `feature/issue-<NUMBER>-<SHORT_TITLE>`. Use the issue title to generate the short title (kebab-case).
4. **Planning Phase**:
   - **Update Design Docs (Pre)**: Update relevant design documents in `docs/02_design/` to reflect the intended changes *before* writing code.
   - Create or update `implementation_plan.md` outlining the changes.
   - Use `notify_user` to request review of the plan and design docs.
5. **Execution Phase**:
   - Once approved, implement the changes according to the plan.
   - Update `task.md` as you progress.
6. **Verification Phase**:
   - Run the application in debug mode to verify changes: `DEBUG_MODE=True USE_MOCK_DATA=False python main.py`
   - Check logs and generated reports.
   - If UI changes involved, deploy to Firebase Hosting using `/debug-run` workflow or manual command.
   - Create `walkthrough.md` to report results.
   - Use `notify_user` to request final review before merging.
7. **Documentation Phase (Final Review)**:
   - Update relevant design documents in `docs/02_design/` to capture any changes made during implementation/debugging.
   - Update `GEMINI.md` if necessary.
   - Ensure "Code follows Design" principle is respected.
8. **Completion Phase**:
   - Once approved, merge the branch into `main`.
   - Push to remote: `git push origin main`.
   - Close the issue with a comment summarizing the changes and verification results.
   - Delete the feature branch.

### Commit Message Template
```
feat(#123): 実装内容の要約

- 詳細変更点
- ...

Closes #123
```

Example usage: `/resolve-issue 102`
