---
description: 誤って生成したレポートとキャッシュを削除する
---

# Delete Report & Cache

誤って試合開始前に処理を実行してしまった場合に、レポートとキャッシュを削除するワークフロー。

## パラメータ

- `FIXTURE_ID`: 削除対象の試合ID（例: 1379169）
- `MATCH_NAME`: 試合名（例: Arsenal_vs_Liverpool）
- `DATE`: 試合日（例: 2026-01-08）

## 手順

1. ローカルのレポートファイルを削除
```bash
# HTMLレポートを削除
rm -f public/reports/${DATE}_${MATCH_NAME}*.html

# フォーメーション画像を削除
rm -f public/reports/images/${FIXTURE_ID}_*.png
```

2. GCSのキャッシュを削除
```bash
# fixture詳細キャッシュ
gsutil rm gs://football-delay-watching-cache/fixtures/id_${FIXTURE_ID}.json

# ラインナップキャッシュ
gsutil rm gs://football-delay-watching-cache/lineups/fixture_${FIXTURE_ID}.json

# 日付別fixturesキャッシュ（必要に応じて）
gsutil rm gs://football-delay-watching-cache/fixtures/league_*_date_${DATE}.json

# 処理済みステータスCSV
gsutil rm gs://football-delay-watching-cache/schedule/fixture_status.csv
gsutil rm gs://football-delay-watching-cache/schedule/report_status.csv
```

3. manifest.jsonからエントリを削除
```bash
python3 -c "
import json

FIXTURE_ID = '${FIXTURE_ID}'
MATCH_NAME = '${MATCH_NAME}'

with open('public/reports/manifest.json', 'r') as f:
    manifest = json.load(f)

# reports_by_dateから該当エントリを除外
for date_key in manifest.get('reports_by_date', {}):
    manifest['reports_by_date'][date_key]['matches'] = [
        m for m in manifest['reports_by_date'][date_key]['matches']
        if m.get('fixture_id') != FIXTURE_ID
    ]

# legacy_reportsからも除外
manifest['legacy_reports'] = [
    r for r in manifest.get('legacy_reports', [])
    if MATCH_NAME not in r
]

with open('public/reports/manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print('Manifest updated')
"
```

4. Firebase Hostingへデプロイ
```bash
firebase deploy --only hosting
```

5. 削除確認
```bash
open https://football-delay-watching-a8830.web.app
```

## 使用例

Arsenal vs Liverpool (fixture_id: 1379169, date: 2026-01-08) を削除する場合:

```bash
FIXTURE_ID=1379169
MATCH_NAME=Arsenal_vs_Liverpool
DATE=2026-01-08

# 1. ローカルファイル削除
rm -f public/reports/${DATE}_${MATCH_NAME}*.html
rm -f public/reports/images/${FIXTURE_ID}_*.png

# 2. GCSキャッシュ削除
gsutil rm gs://football-delay-watching-cache/fixtures/id_${FIXTURE_ID}.json
gsutil rm gs://football-delay-watching-cache/lineups/fixture_${FIXTURE_ID}.json
gsutil rm gs://football-delay-watching-cache/fixtures/league_*_date_${DATE}.json
gsutil rm gs://football-delay-watching-cache/schedule/fixture_status.csv
gsutil rm gs://football-delay-watching-cache/schedule/report_status.csv

# 3. manifest更新 & デプロイ
# (上記のpythonスクリプトを実行)
firebase deploy --only hosting
```
