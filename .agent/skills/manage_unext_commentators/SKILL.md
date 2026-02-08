---
name: manage_unext_commentators
description: U-NEXTの実況・解説者情報の調査からCSV更新、カレンダー反映までを行う総合スキル。
---

# U-NEXT解説者情報の管理

## 概要
ユーザーから「解説者情報を更新して」「カレンダーに解説を反映して」等の依頼があった場合、このスキルに従って作業を行います。

## 前提
- 対象リーグ: プレミアリーグ、ラ・リーガ
- データ保管場所: `settings/commentators/epl.csv`, `laliga.csv`
- カレンダー生成: `src/calendar_generator.py`

---

## Step 1: 情報ソースの確認

### ユーザー提供画像がある場合
画像を「正」として、そこから情報を読み取ります。

### 外部調査が必要な場合
以下の優先順位でソースを確認します：

1. **サッカーキング (推奨)**
   - 検索: `Soccer King プレミアリーグ 実況 解説 YYYY年M月`
   - 検索: `Soccer King ラ・リーガ 実況 解説 YYYY年M月`
   - 一覧性が高く、最も効率的です。

2. **U-NEXT公式X (@UNEXT_football)**
   - 検索: `site:x.com/UNEXT_football "実況" "解説"`
   - 画像付き投稿（「今週の配信予定」等）を探します。

3. **PR TIMES**
   - 検索: `site:prtimes.jp U-NEXT プレミアリーグ 解説`

> [!NOTE]
> 情報は通常、試合の1〜3日前に解禁されます。3日前より前の調査は「未定」と判断します。

---

## Step 2: fixture_id の特定

`public/calendar.html` から対象試合の `fixture_id` を検索します。

```bash
# チーム名でgrepし、前後の行からfixture_idを取得
grep -B 10 "Chelsea" public/calendar.html | grep "data-fixture-id"
```

> [!IMPORTANT]
> 大きなJSONファイル (`tmp_fixtures.json` 等) に対して複雑な `jq` クエリを実行するとスタックする可能性があります。`grep` を優先してください。

---

## Step 3: CSV更新

### CSV形式
```csv
fixture_id,date_jst,home_team,away_team,commentator,announcer
1379221,2026-02-11,Chelsea,Leeds,戸田和幸,下田恒幸
```

### 更新対象ファイル
- `settings/commentators/epl.csv`: プレミアリーグ
- `settings/commentators/laliga.csv`: ラ・リーガ

### 注意点
- **commentator** = 解説者
- **announcer** = 実況

---

## Step 4: 反映と検証

### カレンダー再生成
```bash
python -c "from src.calendar_generator import CalendarGenerator; CalendarGenerator().generate()"
```

### デプロイ
```bash
firebase deploy --only hosting
```

### 確認
生成されたカレンダー (`public/calendar.html`) で対象試合に解説者情報が表示されていることを確認します。

```bash
grep "林陵平" public/calendar.html
```

---

## Step 5: 報告

調査結果と反映内容を `temp/report_commentary_truth_YYYY-MM-DD.md` に記録し、ユーザーに報告します。

```markdown
# 解説者情報 正解データレポート (YYYY-MM-DD)

## プレミアリーグ
| 試合日時 (JST) | 対戦カード | 実況 | 解説 |
|---|---|---|---|
| ... | ... | ... | ... |

## ラ・リーガ
| 試合日時 (JST) | 対戦カード | 実況 | 解説 |
|---|---|---|---|
| ... | ... | ... | ... |
```

---

## トラブルシューティング

| 問題 | 対策 |
|---|---|
| 解説者情報が表示されない | CSVの `fixture_id` がカレンダーの `data-fixture-id` と一致しているか確認 |
| カレンダー再生成時にエラー | `settings/commentator_loader.py` のキャッシュをクリア |
| 大きなJSONがスタック | `jq` を避け、`grep` で個別に検索 |
