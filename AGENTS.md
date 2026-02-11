この資料は、OpenAIのCodex向けの資料です。あなたがGemini(Antigravity)や、Claudeの場合は無視してください。

# 目的
このファイルは「入口（ルーター）」です。詳細ルールをここに重複記載しません。
codexでも、GeminiやAntigravity向けのガイドを参照できるようにするための資料です。

# 参照先（Single Source of Truth）
作業時は以下を優先参照してください。

1. 全体方針・開発ガイド: `GEMINI.md`
2. 実行手順（How）: `.agent/workflows/`
3. 専門知識・判断観点（Know/Think）: `.agent/skills/`

# 運用ルール（Codex）
1. `AGENTS.md` には要点のみを書き、詳細は `GEMINI.md` と `.agent` 側に集約してください（DRY）。
2. 指示が競合した場合は、以下の優先順位で解決してください。  
   `system/developer instructions > user指示 > AGENTS.md > GEMINI.md > .agent/workflows > .agent/skills`
3. 参照先ドキュメントが更新された場合、`AGENTS.md` はリンクと優先順位の整合確認だけ行ってください。
4. 回答は原則として、ですます調で記述してください。

# 共存方針（Codex / Claude CLI / Gemini）
1. 共通ルールは `GEMINI.md` または `.agent` 側に集約し、エージェント別ファイルへのコピペを禁止します。
2. エージェント固有の差分は「入口ファイル」でのみ吸収し、共通ルール本文を分岐させません。
3. ルール追加時は、どこをSSOTにするかを先に決めてから追記してください。
