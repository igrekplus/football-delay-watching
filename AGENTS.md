この資料は、OpenAIのCodex向けの資料です。あなたがGemini(Antigravity)や、Claudeの場合は無視してください。

# 目的
このファイルは「入口（ルーター）」です。詳細ルールをここに重複記載しません。
Codexでも、プロジェクト共通のガイドを参照できるようにするための資料です。

# 参照先（Single Source of Truth）
作業時は以下を優先参照してください。

1. 全体方針・開発ガイド: `CLAUDE.md`（新SSOT）
2. 実行手順（How）: `.agent/workflows/`
3. 専門知識・判断観点（Know/Think）: `.agent/skills/`

> [!IMPORTANT]
> `CLAUDE.md` 内の `<!-- claude-only-start -->` 〜 `<!-- claude-only-end -->` セクション
>（「9. Claude Code Remote 専用セクション」）は **Codex（IDE）環境では適用外**です。スキップしてください。
>
> Codex はローカルIDE環境での開発を前提としています。
> GCP認証は `gcloud auth application-default login`、Secretsは `.env` ファイルを使用してください。

# 運用ルール（Codex）
1. `AGENTS.md` には要点のみを書き、詳細は `GEMINI.md` と `.agent` 側に集約してください（DRY）。
2. 指示が競合した場合は、以下の優先順位で解決してください。  
   `system/developer instructions > user指示 > AGENTS.md > GEMINI.md > .agent/workflows > .agent/skills`
3. 参照先ドキュメントが更新された場合、`AGENTS.md` はリンクと優先順位の整合確認だけ行ってください。
4. 回答は原則として、ですます調で記述してください。
5. `.agent/skills/` にskillを追加した場合は、`.agents/skills/` にも kebab-case 名で対応するsymlinkを作成し、一覧側へ反映してください。
6. CodexでIssue対応や複数ステップの作業を行う場合は、ユーザーが毎回明示しなくても、会話内で計画・タスク分解・進捗整理・完了時の検証結果整理を行ってください。
7. Codexが `implementation_plan.md` / `task.md` / `walkthrough.md` 相当のMarkdownを作成する場合は、リポジトリ直下ではなく `temp/` 配下に都度出力してください。`temp/` は一時作業用であり、原則コミット対象にしません。
8. Codexでは、Markdown成果物の作成は目的ではなく、計画・タスク・検証結果を整理するための補助とします。小規模作業は会話内の整理だけで進めてよく、長い作業・引き継ぎ・証跡が必要な場合に `temp/` へ出力してください。

# 共存方針（Codex / Claude CLI / Gemini）
1. 共通ルールは `GEMINI.md` または `.agent` 側に集約し、エージェント別ファイルへのコピペを禁止します。
2. エージェント固有の差分は「入口ファイル」でのみ吸収し、共通ルール本文を分岐させません。
3. ルール追加時は、どこをSSOTにするかを先に決めてから追記してください。
