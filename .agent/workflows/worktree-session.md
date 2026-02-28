---
description: git worktreeでタスクごとに作業ディレクトリを分離し、AIセッションを並列運用する。
---

# Worktree Session Workflow

`git worktree` を使い、1タスク = 1ブランチ = 1作業ディレクトリで進める手順です。

## 前提条件

- 実行場所はメインリポジトリ（例: `/Users/nagataryou/football-delay-watching`）
- ブランチ名は `feature-<issue-number>/<task-slug>` を使用する
- `<issue-number>` は数字のみ（例: `253`）
- `<task-slug>` は英小文字・数字・ハイフンで命名する

## 手順

// turbo-all

### 1. 最新化

```bash
git fetch origin --prune
```

### 2. worktree作成（新規ブランチ）

```bash
git worktree add ../football-delay-watching-<issue-number>-<task-slug> -b feature-<issue-number>/<task-slug> origin/main
```

例:

```bash
git worktree add ../football-delay-watching-253-fix-parser -b feature-253/fix-parser origin/main
```

### 3. 作業ディレクトリへ移動

```bash
cd ../football-delay-watching-<issue-number>-<task-slug>
git branch --show-current
```

`feature-<issue-number>/<task-slug>` になっていることを確認する。

### 4. 実装・検証

このディレクトリ内で通常どおり作業する。必要に応じて既存Workflow（`/debug-run`, `/deploy`）を実行する。

特定の1試合だけを検証したい場合は、worktree内で `TARGET_FIXTURE_ID` を付けて実行する。

```bash
TARGET_DATE="2026-02-27" TARGET_FIXTURE_ID="1379248" DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```

### 5. コミット・プッシュ

```bash
git add -A
git commit -m "feat: <summary>"
git push -u origin feature-<issue-number>/<task-slug>
```

### 6. 後片付け（マージ後）

```bash
cd /Users/nagataryou/football-delay-watching
git worktree remove ../football-delay-watching-<issue-number>-<task-slug>
git worktree prune
```

## 注意事項

- 同じブランチを複数worktreeで同時にcheckoutしないこと
- cleanup前に、対象worktreeに未コミット変更がないか確認すること
- mainワークツリー（元ディレクトリ）で別Issueの実装を混在させないこと
