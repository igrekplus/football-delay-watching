---
name: firebase_rollback
description: Firebase Hosting上のレポート消失時に、GCSバックアップバケット（football-delay-watching-backup）からレポートを復旧する実行手順を提供するスキル。誤デプロイや上書き事故で public/reports が失われた場合に使用する。
---

# Firebase Restore From GCS Backup Skill

## 概要

このスキルは、`firebase deploy --only hosting` の上書きで Firebase Hosting 上の `reports/` が欠損したときに、GitHub Actions が保存している GCS バックアップから復旧するための手順です。

バックアップ元は以下です。

- バケット: `gs://football-delay-watching-backup`
- プレフィックス: `reports/<YYYYMMDD_HHMMSS>/`
- 生成元: `.github/workflows/daily_report.yml` の `Backup reports to GCS`

## トリガー条件

- ユーザーから「レポートが消えた」「復旧したい」と依頼されたとき
- Firebase 上の `reports/` 件数が急減しているとき
- ローカル誤デプロイで過去レポートを消した可能性が高いとき

## 判断方針

1. Firebase の履歴ロールバックではなく、GCS スナップショットを正として復旧します。
2. 復旧前に、現在のローカル `public/reports` を退避します。
3. 復旧時は `scripts/safe_deploy.sh` を使いません。
`safe_deploy.sh` は先に Firebase から同期するため、復旧対象のローカル内容が上書きされます。
4. 復旧対象スナップショットは「消失事故の直前時刻」を優先します。

## 実行手順

### 1. バックアップ候補を列挙

```bash
gsutil ls gs://football-delay-watching-backup/reports/
```

最新候補の確認例です（タイムスタンプは GitHub Actions 側時刻で作られます）。

```bash
gsutil ls gs://football-delay-watching-backup/reports/ \
  | sed 's#/$##' \
  | awk -F/ '{print $NF}' \
  | sort \
  | tail -20
```

### 2. 復旧対象スナップショットを決める

```bash
TARGET_SNAPSHOT="20260223_030001"
gsutil ls "gs://football-delay-watching-backup/reports/${TARGET_SNAPSHOT}/**" | head -50
```

最低限、次が含まれることを確認します。

- `manifest.json`
- `report_*.html`
- `images/`（必要な場合）

### 3. 復旧前のローカル退避

```bash
NOW=$(date +%Y%m%d_%H%M%S)
mkdir -p "temp/restore_backups/${NOW}"
if [ -d "public/reports" ]; then
  mv public/reports "temp/restore_backups/${NOW}/reports_before_restore"
fi
mkdir -p public/reports
```

### 4. GCS からローカルへ復元

```bash
TARGET_SNAPSHOT="20260223_030001"
gsutil -m rsync -r \
  "gs://football-delay-watching-backup/reports/${TARGET_SNAPSHOT}/" \
  public/reports/
```

### 5. デプロイ前の必須確認

```bash
find public/reports -type f | wc -l
ls -la public/reports | head
test -f public/reports/manifest.json && echo "manifest exists"
```

`public/firebase_config.json` と `public/allowed_emails.json` が必要です。
不足している場合は環境変数から再生成します。

```bash
echo "$FIREBASE_CONFIG" > public/firebase_config.json
echo "$ALLOWED_EMAILS" > public/allowed_emails.json
```

### 6. Firebase Hosting に反映

```bash
firebase deploy --only hosting
```

### 7. 復旧後同期と最終確認

復旧後の実態をローカルにも揃えます。

```bash
python scripts/sync_firebase_reports.py
```

確認項目:

- Hosting 上で対象レポート URL が表示できる
- `public/reports/manifest.json` に対象レポートが含まれる
- `public/reports/` の件数が想定値以上である

## 事故時の最短手順

時間優先で復旧する場合のみ使用します。

```bash
TARGET_SNAPSHOT="<restore_snapshot>"
NOW=$(date +%Y%m%d_%H%M%S)
mkdir -p "temp/restore_backups/${NOW}"
[ -d public/reports ] && mv public/reports "temp/restore_backups/${NOW}/reports_before_restore"
mkdir -p public/reports
gsutil -m rsync -r "gs://football-delay-watching-backup/reports/${TARGET_SNAPSHOT}/" public/reports/
echo "$FIREBASE_CONFIG" > public/firebase_config.json
echo "$ALLOWED_EMAILS" > public/allowed_emails.json
firebase deploy --only hosting
python scripts/sync_firebase_reports.py
```

## 注意事項

- 復旧操作は破壊的です。対象スナップショット時刻を必ずユーザーに確認してください。
- `scripts/safe_deploy.sh` は復旧時に使わないでください（先に Firebase から同期してしまうため）。
- GCS バックアップに存在しないファイルは復旧できません。

## 検証ステータス

- 2026-02-23 時点で、この手順の実リストア動作確認は未実施です。
- 次回実際にリストアを実行したタイミングで、成功可否、所要時間、詰まった点をこの `SKILL.md` に追記更新してください。
