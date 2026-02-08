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

### 優先順位
1. **ユーザー提供画像** ← 最優先。画像があればそれを「正」とする。
2. **U-NEXT公式X (@UNEXT_football)** ← 外部調査が必要な場合のみ。

### U-NEXT公式Xの調査方法
```
https://x.com/UNEXT_football
```
- 直近の画像付き投稿（「今週の配信予定」等）を探す。
- Google検索も活用可: `site:x.com/UNEXT_football "実況" "解説"`

> [!IMPORTANT]
> **公式Xに情報がなければ調査終了**。ユーザーに「現時点で公式情報が見つかりませんでした」と報告する。

---

## Step 2: fixture_id の特定

`public/calendar.html` から対象試合の `fixture_id` を検索します。

```bash
# チーム名でgrepし、前後の行からfixture_idを取得
grep -B 10 "Chelsea" public/calendar.html | grep "data-fixture-id"
```

> [!IMPORTANT]
> 大きなJSONファイルに対して複雑な `jq` クエリを実行するとスタックする可能性があります。`grep` を優先してください。

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
```bash
grep "林陵平" public/calendar.html
```

---

## Step 5: 報告

調査結果と反映内容を `temp/report_commentary_truth_YYYY-MM-DD.md` に記録し、ユーザーに報告します。

---

## トラブルシューティング

| 問題 | 対策 |
|---|---|
| 解説者情報が表示されない | CSVの `fixture_id` がカレンダーの `data-fixture-id` と一致しているか確認 |
| 大きなJSONがスタック | `jq` を避け、`grep` で個別に検索 |
