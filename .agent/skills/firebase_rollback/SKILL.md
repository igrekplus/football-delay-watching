---
name: firebase_rollback
description: Firebase Hostingでのレポート消失トラブル発生時に、過去の正常なバージョンにロールバックし、データを復旧する手順と判断基準を提供するスキル。ローカルデプロイ等による上書きでデータが失われた場合に使用する。
---

# Firebase Rollback Skill

## 🏈 概要 (Overview)

このスキルは、ローカル環境からの誤ったデプロイ（`firebase deploy`）等によって、Firebase Hosting上のレポートHTMLや画像ファイルが上書き・消失してしまった際に使用します。

Firebase CLIの標準コマンドでは詳細なバージョン情報（ファイル数など）の確認やロールバックが難しい場合があるため、Google Cloud REST APIを活用して確実な復旧を行います。

## 🔍 トリガー条件 (When to Use)

- ユーザーから「最近のレポートが消えた」「過去のバージョンに戻してほしい」という依頼があったとき。
- GitHub Actionsのログでは成功（レポート生成）しているのに、Firebase Hosting上の `public/reports/` に実ファイルが存在しないことが判明したとき。
- ローカルからデプロイしたことで、リモートの最新状態が上書きされてしまった疑いがあるとき。

## 💡 思考プロセス (Thinking Process)

1. **状況把握と原因特定**:
   - `firebase hosting:channel:list` や過去のデプロイ履歴を確認する。
   - GitHub Actionsのログを確認し、いつまで正常に生成・デプロイされていたか特定する。
   - `public/reports/manifest.json` の内容と実際のファイル存在状況を照らし合わせる。
2. **ロールバック対象の特定**:
   - Firebase Hosting REST APIを使用して、各デプロイバージョンに含まれるファイル数を比較する。
   - 最も直近の「正常にすべてのレポートが含まれていたバージョン」を特定する。
3. **ロールバック実行**:
   - ユーザーに状況とロールバック対象の時間を報告し、承認を得た上でREST API経由でロールバックを実行する。
4. **ローカルへのデータ救出と再同期**:
   - Firebaseを元に戻すだけでは、次にローカルからデプロイした際に再び消えてしまう。
   - `scripts/sync_firebase_reports.py` を実行して、ロールバック後のFirebaseからローカルの `public/reports/` にファイルを同期する。

## 🛠 実行手順 (Execution Steps)

### 1. 過去バージョンとファイル数の特定

Firebase Hosting REST API を使用して、過去のデプロイ履歴（ファイル数付き）を取得します。
ファイル数が極端に減っている地点の **直前** が、正常なバックアップバージョンである可能性が高いです。

```bash
# ※ projectId は実際のプロジェクト(football-delay-watching-a8830)に置き換えて実行する
TOKEN=$(gcloud auth print-access-token --billing-project=football-delay-watching-a8830 2>/dev/null) && \
curl -s -H "Authorization: Bearer $TOKEN" \
     -H "x-goog-user-project: football-delay-watching-a8830" \
     "https://firebasehosting.googleapis.com/v1beta1/sites/football-delay-watching-a8830/releases?pageSize=25" | \
python3 -c "
import json, sys
data = json.load(sys.stdin)
releases = data.get('releases', [])
print(f'Total releases: {len(releases)}')
for r in releases[:20]:
    rtype = r.get('type','')
    release_time = r.get('releaseTime','')[:19]
    version = r.get('version', {})
    vid = version.get('name','').split('/')[-1]
    file_count = version.get('fileCount', '?')
    status = version.get('status','')
    print(f'{release_time} | {rtype} | files:{file_count} | status:{status} | {vid}')
"
```

### 2. 対象バージョンのファイル確認 (オプション)

ロールバック対象のバージョンID（例: `7d99dd2d56d58af9`）の中に、探しているレポートファイルが存在するか確認します。

```bash
TARGET_VERSION="7d99dd2d56d58af9"
TOKEN=$(gcloud auth print-access-token --billing-project=football-delay-watching-a8830 2>/dev/null) && \
curl -s -H "Authorization: Bearer $TOKEN" \
     -H "x-goog-user-project: football-delay-watching-a8830" \
     "https://firebasehosting.googleapis.com/v1beta1/sites/football-delay-watching-a8830/versions/${TARGET_VERSION}/files?pageSize=1000" | \
python3 -c "
import json, sys, re
data = json.load(sys.stdin)
files = data.get('files', [])
target = [f for f in files if re.search(r'2026-02-1[9]|2026-02-2[012]', f.get('path',''))]
print(f'Total files: {len(files)}')
for f in sorted(target, key=lambda x: x.get('path',''))[:20]:
    print(f.get('path',''))
"
```

### 3. ロールバックの実行

ユーザーの承認後、特定したバージョンへロールバックするPOSTリクエストを送信します。

```bash
TARGET_VERSION="7d99dd2d56d58af9"
MESSAGE="Rollback to healthy version via Antigravity"
TOKEN=$(gcloud auth print-access-token --billing-project=football-delay-watching-a8830 2>/dev/null) && \
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
     -H "x-goog-user-project: football-delay-watching-a8830" \
     -H "Content-Type: application/json" \
     -d "{\"message\": \"${MESSAGE}\"}" \
     "https://firebasehosting.googleapis.com/v1beta1/sites/football-delay-watching-a8830/releases?versionName=projects/football-delay-watching-a8830/sites/football-delay-watching-a8830/versions/${TARGET_VERSION}"
```

### 4. ローカル環境へのデータ同期（最重要）

ロールバックが完了したら、**必ず** ローカル環境にデータを同期し、Firebase上の最新状態をローカルの `public/reports/` にも反映させます。これを行わないと、次のデプロイで再びデータが消失します。

```bash
python scripts/sync_firebase_reports.py
```

実行後、`ls public/reports/` 等で意図したレポートがローカルに復旧しているか（Downloaded件数と実際のファイル）を確認し、タスク完了を報告します。

## ⚠️ 失敗・注意ポイント (Common Pitfalls)

- Firebase CLI の `firebase hosting:versions:list` コマンドは非推奨/未実装であることが多いため、**REST API + gcloud auth の使用が必須**です。
- リクエスト時に `quota project is not set` エラーが出る場合は、必ず `--billing-project` と `-H "x-goog-user-project: ..."` ヘッダーを付与してください。
- ロールバックするだけでは不完全です。必ず `sync_firebase_reports.py` を使ってローカルのファイルを最新化してください。
