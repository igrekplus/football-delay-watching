---
name: create_codex_skill_reference
description: Gemini / Antigravity などで追加された skill を Codex でも `$...` 指定で使えるようにするスキル。ユーザーが「この skill を Codex でも見えるようにしたい」「$で呼べるようにしたい」「Codex 向けの参照や symlink を追加したい」と依頼したときに使う。
---

# Codex Skill Reference 作成スキル

## 概要

この skill は、既存の `.agent/skills/...` 配下の skill を Codex でも発見できる状態に揃えます。

skill の内部名は `create_codex_skill_reference` とし、symlink 側は `create-codex-skill-reference` を使います。

## 実行方針

- 既存 skill の本文や SSOT をむやみに複製しない。
- Codex 側の導線不足だけを埋める。
- プロジェクト既存の命名規約に合わせ、`.agent/skills/` は既存名を尊重し、`.agents/skills/` は kebab-case にする。

## 手順

### 1. 対象 skill を確認する

- `.agent/skills/<skill_name>/SKILL.md` が存在するか確認する。
- frontmatter に `name` と `description` があるか確認する。
- `description` が「何をする skill か」と「どういう依頼で使うか」を十分に含んでいるか確認する。

### 2. 公開名を決める

- 内部名は既存 skill の `name` とフォルダ名を尊重する。
- Codex 公開名は kebab-case に正規化する。
- 既存パターンがある場合は、それに揃える。

例:

- `generate_player_profiles` -> `generate-player-profiles`
- `fetch_instagram` -> `fetch-instagram`

### 3. Codex 向け symlink を追加する

`.agents/skills/` に対応する symlink を作る。

```bash
ln -s ../../.agent/skills/<skill_dir> .agents/skills/<kebab-case-name>
```

すでに symlink がある場合は、リンク先が正しいか確認する。

## 4. 一覧側を最小限同期する

- `GEMINI.md` に Skills 一覧がある場合は、1 行説明を追加する。
- 入口ファイルに重複記載しすぎず、SSOT は skill 本体に残す。

## 5. 検証する

以下を確認する。

```bash
ls -la .agents/skills
git status --short
```

必要に応じて、対象 skill の先頭も確認する。

```bash
sed -n '1,40p' .agent/skills/<skill_dir>/SKILL.md
```

## 6. ユーザーへ伝える

- 追加した内部名
- 追加した symlink 名
- 更新したファイル
- 現在のセッションでは Available skills が再読込されない可能性があるため、新しいセッションで確認すると確実であること
