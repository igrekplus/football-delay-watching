---
name: llm-section-investigation
description: 生成レポート内の「LLM応答由来セクション」（古巣対決、同国対決、キーマッチアップ、戦術スタイルなど）について、表示/非表示や除外理由を調査するスキル。開発者が「なぜこのセクションが出ないのか」「どの候補がどの判定で落ちたのか」「Actionsログで根拠を示してほしい」と質問したときに使う。
---

# LLM Section Investigation

## 概要
LLM応答が最終HTMLにどう反映されたかを、次の順に追跡する。
1. 生成HTMLで事象を確認する
2. ActionsログでLLM応答と判定結果を取得する
3. 実装コードで表示条件を確認する
4. 「どこで落ちたか」を時系列で確定する

推測で結論を出さず、必ずログ行とコード箇所を根拠として示す。

## 入力確認
調査開始時に次を確認する。
- レポートURLまたは `public/reports/*.html` のパス
- 対象セクション名（例: 古巣対決）
- 対象試合（対戦カード）
- 生成日時の目安（例: 2026-02-18 朝）

不足情報があっても作業は開始し、URLやファイル名から補完できる値を先に確定する。

## 調査手順

### 1. 生成HTMLで症状を固定する
1. 対象HTML内にセクション見出しが存在するか確認する。
2. 対象選手・対象文言がスタメン/本文に存在するか確認する。
3. ファイル名から生成時刻を読み取る（例: `..._20260218_063826.html`）。

### 2. Actions run を特定する
1. `gh run list --workflow daily_report.yml` で該当時刻付近の run を列挙する。
2. 候補 run を `gh run view <RUN_ID> --log` で取得する。
3. 対象カードとレポート名で一致確認する。

推奨コマンド:
```bash
gh run list --workflow daily_report.yml --limit 30
gh run view <RUN_ID> --log > /tmp/run_<RUN_ID>.log
rg -n "Benfica vs Real Madrid|Generated report for:|former_club|FACT_CHECK|TRIBUTE|FORMER_CLUB" /tmp/run_<RUN_ID>.log
```

### 3. LLM応答の受信内容を抽出する
対象セクションに対応するログキーを抽出する。

- 古巣対決: `former_club_trivia`, `former_club_fact_check`, `[FORMER_CLUB]`, `[FACT_CHECK]`, `[TRIBUTE]`
- 同国対決: `same_country_trivia`
- キーマッチアップ: `matchup`, `key_player`
- 戦術スタイル: `tactical_style`

確認ポイント:
1. LLM Response に候補が含まれているか
2. Parser が `Parsed N ...` で何件通したか
3. Fact check が `Approved` / `Rejected` か
4. Rejected reason に何が書かれているか

### 4. 実装コードで「表示条件」を確定する
ログだけでなく、表示条件をコードで確認する。

- 例: `match.facts.<section_data>` が空なら描画しない
- 例: fact-check 後に `No valid ...` で空文字化される

対象ファイル例:
- `src/services/tribute_generator.py`
- `src/clients/llm_client.py`
- `src/report_generator.py`
- `src/parsers/*.py`

### 5. 落下点を1つに特定する
次のいずれで落ちたかを必ず1つに決める。
- 候補未生成（LLM response が空）
- パースで0件
- ファクトチェックで全件 reject
- レンダリング条件未達
- 生成後の別処理で欠落

## 出力フォーマット
回答は次の順で簡潔に出す。
1. 結論（1-2文）
2. 時系列トレース（受信 -> パース -> 判定 -> 描画）
3. 根拠ログ（ファイル名 + 行番号）
4. 必要なら改善案（ログ追加、判定条件修正など）

テンプレート:
```markdown
結論:
- <どこで除外されたか>

時系列:
1. <LLM候補>
2. <Parser件数>
3. <Fact-check結果>
4. <Render結果>

根拠:
- `<log-file>:<line>`
- `<code-file>:<line>`
```

## 注意点
- 相対時刻だけで書かず、必ず絶対日時（UTC/JST）を併記する。
- 「公開HTMLにないから不明」で終わらせず、Actionsログまたはローカル実行ログを取りに行く。
- ログが取得不能な場合は、どの情報が不足して断定できないかを明記する。
- 調査質問への回答では、実装変更を勝手に行わない。必要な場合だけ改善案を別途提示する。
