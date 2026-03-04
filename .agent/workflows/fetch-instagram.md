---
description: 選手のInstagram URLを検索して、GCS上の選手マスタCSVを更新するワークフロー
---

# Player Instagram Fetch Workflow

この workflow は `/fetch-instagram` の入口です。
内部で参照する skill 名は `fetch_instagram`、公開側の workflow / symlink 名は `fetch-instagram` です。
調査基準と判断ルールの正本は `.agent/skills/fetch_instagram/SKILL.md` を参照してください。

## 手順

### 1. 対象チームを決める
ユーザーがチーム名を指定したら、そのチームだけを対象にします。
`team_id` の確認や未登録チーム対応は `.agent/skills/fetch_instagram/SKILL.md` に従います。

### 2. GCSから作業コピーを取得
```bash
python scripts/pull_player_csv_from_gcs.py --team-id 42
```

未登録チームで初期CSVを作った直後など、GCSにまだ正本がない場合は `SKIP` を確認してそのまま続行します。

### 3. 現状確認
```bash
python scripts/analyze_missing_instagram.py --team-id 42
```

一覧に表示された `instagram_url` 空欄の選手を調査対象にします。

### 4. 検索してCSVを更新
ローカル作業コピー `data/player_<team_id>.csv` の `instagram_url` を更新します。
検索クエリの順序、採用基準、スキップ条件は `.agent/skills/fetch_instagram/SKILL.md` を参照してください。

### 5. GCSへ反映
```bash
python scripts/migrate_player_csv_to_gcs.py --team-id 42
```

### 6. 結果確認
```bash
python scripts/analyze_missing_instagram.py --team-id 42
```

必要なら、対象 fixture を固定してデバッグ実行します。

```bash
TARGET_DATE="2026-02-27" TARGET_FIXTURE_ID="1379248" DEBUG_MODE=True USE_MOCK_DATA=False python main.py
rg -n "instagram.com|player-instagram-link" public/reports/<generated_report>.html
```

### 7. 報告
以下を簡潔に報告します。
1. 対象チーム名と `team_id`
2. 更新した選手数
3. スキップした選手と理由
4. GCS反映まで完了したか
5. 表示確認まで行ったか
