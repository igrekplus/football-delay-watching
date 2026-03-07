---
name: regenerate_report
description: 既に生成されてしまった試合レポートの CSV・manifest・キャッシュをリセットし、fixture_id を指定して安全に再生成するスキル。ユーザーが「このレポートを作り直したい」「fixture_id 指定で再生成したい」「早すぎる生成や欠損レポートを消して再実行したい」と依頼したときに使う。
---

# Regenerate Report

## 概要

この skill は、`fixture_id` を起点に、既存レポートの状態確認、古い出力の除去、GCS キャッシュの削除、対象 fixture の再生成、カレンダー・公開確認までを一通り扱います。

想定ケース:

- 試合開始前に早すぎるタイミングで生成してしまった
- lineup 欠損などで `fixture_status.csv` が `partial` になっている
- `report_link` や `manifest.json` が古いレポートを指している
- 同じ fixture の古い HTML が複数本残っている

## 引数

- `fixture_id`: 必須。再生成したい試合の fixture id

例:

- `fixture_id=1523413`

## 実行方針

- まず現状確認を行い、削除対象を fixture 単位で特定する。
- `manifest.json` の同一 fixture の古いエントリを消してから再生成する。
- `fixtures/id_<fixture_id>.json` と `lineups/fixture_<fixture_id>.json` は原則削除して取り直す。
- 再生成は `TARGET_FIXTURE_ID` を使い、対象試合だけを処理する。
- 「最終的に正しい 1 本だけ残ること」を確認する。

## 手順

### 1. fixture の現状を確認する

- カレンダー CSV と GCS オーバーレイ上の `report_link`
- GCS の `schedule/fixture_status.csv`
- ローカル `public/reports/manifest.json`
- 公開中 manifest
- ローカル/公開 HTML の本数

確認例:

```bash
python - <<'PY'
from settings.calendar_data_loader import get_calendar_info
print(get_calendar_info("1523413"))
PY

.venv/bin/python - <<'PY'
from src.utils.fixture_status_manager import FixtureStatusManager
m = FixtureStatusManager()
for row in m.get_all_statuses():
    if row.get("fixture_id") == "1523413":
        print(row)
        break
PY

python - <<'PY'
import json
from pathlib import Path
path = Path("public/reports/manifest.json")
data = json.loads(path.read_text(encoding="utf-8"))
for date_key, date_data in data.get("reports_by_date", {}).items():
    for m in date_data.get("matches", []):
        if str(m.get("fixture_id")) == "1523413":
            print(date_key, m["file"])
PY
```

### 2. 対象試合の日付を決める

- 基本はカレンダー CSV の `date_jst`
- なければ fixture API の kickoff から確認する
- `TARGET_DATE` には試合日の JST 日付を使う

### 3. 古いレポート参照を消す

- `public/reports/manifest.json` から対象 fixture の古いエントリを削除する
- 古い HTML を削除する
- 必要ならローカルの `settings/calendar/*.csv` の `report_link` を空に戻す

注意:

- `manifest.json` は再生成時に Firebase 上の remote manifest を再マージするため、古い公開レポートを残したままだと再出現する
- そのため、最終的には Hosting 側からも古い HTML を消す前提で進める

### 4. GCS キャッシュを削除する

最低限これを削除する:

```bash
gsutil rm gs://football-delay-watching-cache/fixtures/id_<fixture_id>.json
gsutil rm gs://football-delay-watching-cache/lineups/fixture_<fixture_id>.json
```

必要に応じて削除する:

- `gs://football-delay-watching-cache/injuries/fixture_<fixture_id>.json`
- `schedule/fixture_status.csv` 全体削除ではなく、対象 row の状態更新

`fixture_status.csv` の扱い:

- `partial` はそのまま再処理対象なので、必ずしも削除不要
- 再生成後に `complete` へ更新されているか確認する
- `complete` だが強制的にやり直したい場合は、対象 row を `pending` に戻すか削除する

### 5. 本番モードで再生成する

`DEBUG_MODE` は使わず、`TARGET_FIXTURE_ID` だけを指定して本番モードで 1 試合を再生成する。

```bash
source .venv/bin/activate
TARGET_DATE="2026-03-07" TARGET_FIXTURE_ID="1523413" python main.py
```

確認点:

- `Starting workflow... (Dry Run: False, Mock: False)` が出ること
- `fixture_status.csv` が最終的に `complete` になること
- 新しい HTML が 1 本生成されること
- lineup 欠損が解消されていること

### 6. カレンダーと manifest を整える

- ローカル `settings/calendar/*.csv` の `report_link` を新しい URL に合わせる
- `python -m src.calendar_generator` を実行して `public/calendar.html` を更新する
- `public/reports/manifest.json` に対象 fixture が新しい 1 件だけ残っていることを確認する

### 7. デプロイする

```bash
./scripts/safe_deploy.sh
```

対話環境で確認プロンプトが不要な場合は、状況に応じて `firebase deploy --only hosting` でもよいが、原則は `safe_deploy.sh` を優先する。

### 8. 公開確認する

- 新しいレポート URL が `200`
- 古いレポート URL が `404`
- 公開 manifest に対象 fixture が 1 件だけ
- `get_calendar_info(fixture_id)` の `report_link` が新 URL

## 検証チェックリスト

- 対象 fixture の `report_link` は新 URL か
- `fixture_status.csv` は `complete` か
- `error_message` は空か、少なくとも古い欠損理由を引きずっていないか
- lineup 表示が `選手情報なし` ではないか
- 公開 manifest に重複がないか
- 古い公開 URL が消えているか

## 失敗しやすい点

- `manifest.json` のみ削除しても、古い公開 HTML が残ると remote merge で戻る
- GCS の lineups キャッシュを消さずに再生成すると欠損が再利用される
- ローカル CSV を更新せず GCS だけ直すと、次回ローカル起点の更新で巻き戻る
- `DEBUG_MODE=True` で作ると debug バッジ付きの別レポートが増える

## 関連ワークフロー

- 実行確認: `.agent/workflows/debug-run.md`
- 誤生成削除の考え方: `.agent/workflows/delete-report.md`
- デプロイ: `.agent/workflows/deploy.md`
