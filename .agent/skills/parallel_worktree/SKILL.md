---
name: parallel_worktree
description: 複数AIセッションをgit worktreeで安全に並列運用するための判断基準を定義したスキル。
---

# Parallel Worktree Skill

## 概要

複数のAIセッション（Codex / Claude / Geminiなど）が同じリポジトリを同時に扱う際に、競合と混線を防ぐための判断基準です。

## 基本方針

1. **1セッション1ブランチ1worktree**: セッションごとに専用ブランチと専用ディレクトリを割り当てる。
2. **命名統一**: ブランチは `feature-<issue-number>/<task-slug>`、worktreeディレクトリは `../football-delay-watching-<issue-number>-<task-slug>` を使う。
3. **タスク境界の厳守**: 1セッションは1Issue/1タスクに集中し、別Issueへ横展開しない。
4. **衝突予防**: 競合しやすい共通ファイル（設定・ドキュメント）は担当者を先に決める。
5. **早期統合**: 長期分岐を避け、小さな差分で早めにPR・マージする。

## 判断ルール

### worktreeを作るべきケース

- 別Issueを並行で進めるとき
- 同一Issueでも、調査系タスクと実装系タスクを分離したいとき
- レビュー待ち中に別タスクへ着手するとき

### 同一worktreeでよいケース

- 直前コミットの軽微修正（タイポ、コメント、テスト期待値修正）
- 5分程度で完了する単一ファイル修正

## 禁止事項

- 同一ブランチを複数worktreeで同時checkoutする運用
- mainワークツリー上で複数Issueの変更を混在させる運用
- 未コミット変更を残したままworktreeを削除する運用

## 完了チェック

1. `git diff main...HEAD` で不要差分がない
2. 対象Issue以外の変更が含まれていない
3. push済みで、レビュー可能な状態になっている
4. 不要になったworktreeを削除し、`git worktree prune` を実行済み

## 関連Workflow

- worktree作成・削除手順: [/worktree-session](file:///.agent/workflows/worktree-session.md)
- 実行・検証: [/debug-run](file:///.agent/workflows/debug-run.md)
- クローズ前確認: [/check-close](file:///.agent/workflows/check-close.md)
