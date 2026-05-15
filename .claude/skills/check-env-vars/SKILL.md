---
name: check-env-vars
description: 環境変数・APIキー・GCP認証など、セッション開始時に設定される全シークレットの動作確認を行うスキル。ユーザーが「環境変数を確認して」「APIキーが生きているか確認して」「セッションの動作確認をして」などを依頼したときに使う。
---

# Check Env Vars Skill（環境変数・API動作確認スキル）

## 概要

Claude Code Remote セッションで利用可能な全 API キー・認証情報の疎通確認を行う。
`session-start` フックがロードするシークレットが正常に動作しているかを素早く把握するためのスキル。

---

## 確認対象と確認方法

### 1. GCP サービスアカウント（基盤認証）

```bash
gcloud auth list 2>&1 | head -5
echo "Project: $(gcloud config get-value project 2>/dev/null)"
```

期待値: `fb-non-result@gen-lang-client-0394252790.iam.gserviceaccount.com` が ACTIVE

---

### 2. Gemini API（GOOGLE_API_KEY）

```bash
curl -sf "https://generativelanguage.googleapis.com/v1beta/models?key=${GOOGLE_API_KEY}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); models=[m['name'] for m in d.get('models',[])[:3]]; print(f'Gemini API: OK (models={models})')"
```

期待値: モデル一覧（`gemini-2.5-flash` など）が返る

---

### 3. YouTube Data API（YOUTUBE_API_KEY）

```bash
curl -sf "https://www.googleapis.com/youtube/v3/search?part=snippet&q=test&maxResults=1&key=${YOUTUBE_API_KEY}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'YouTube API: OK (totalResults={d[\"pageInfo\"][\"totalResults\"]})')"
```

期待値: `totalResults` が返る

---

### 4. API-Football（API_FOOTBALL_KEY）

```bash
curl -sf -H "x-rapidapi-key: ${API_FOOTBALL_KEY}" \
  "https://v3.football.api-sports.io/status" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('response',{}); print(f'API-Football: OK (plan={s.get(\"subscription\",{}).get(\"plan\",\"?\")}, requests_today={s.get(\"requests\",{}).get(\"current\",\"?\")})')"
```

期待値: `plan=Pro` が返る

---

### 5. GCS バックアップバケット

```bash
gsutil ls gs://football-delay-watching-backup/ 2>&1 | head -3 && echo "GCS backup: OK" || echo "GCS backup: FAIL"
```

期待値: `gs://football-delay-watching-backup/reports/` が見える

---

### 6. GCS Firebase Storage バケット

```bash
gsutil ls gs://football-delay-watching-a8830.firebasestorage.app/ 2>&1 | head -3 && echo "GCS firebase: OK" || echo "GCS firebase: FAIL"
```

---

### 7. GitHub MCP ツール

直接 curl では **このセッションの GITHUB_TOKEN は無効**（`Bad credentials`）のため、MCP ツールで確認する。

```
mcp__github__get_me を呼び出す
```

期待値: `login=igrekplus` が返る

> [!WARNING]
> `GITHUB_TOKEN` 環境変数は現在 `Bad credentials (401)` 状態。
> curl では使用不可。GitHub 操作は必ず `mcp__github__*` ツール経由で行うこと。

---

### 8. Gmail OAuth2 トークン（GMAIL_TOKEN / GMAIL_CREDENTIALS）

```bash
python3 << 'EOF'
import json, os, subprocess

token_data = json.loads(os.environ.get("GMAIL_TOKEN", "{}"))
cred_data = json.loads(os.environ.get("GMAIL_CREDENTIALS", "{}")).get("installed", {})

result = subprocess.run([
    "curl", "-sf", "--cacert", "/tmp/combined-ca.pem",
    "-X", "POST", "https://oauth2.googleapis.com/token",
    "-d", f"client_id={cred_data['client_id']}&client_secret={cred_data['client_secret']}&refresh_token={token_data['refresh_token']}&grant_type=refresh_token"
], capture_output=True, text=True)
resp = json.loads(result.stdout) if result.stdout else {}
if "access_token" in resp:
    print("Gmail OAuth2: OK")
else:
    print(f"Gmail OAuth2: FAIL ({resp.get('error_description', resp.get('error', 'unknown'))})")
EOF
```

> [!WARNING]
> 2026-05-15 時点で `invalid_grant (Bad Request)` が確認されている。
> リフレッシュトークンの再発行が必要。Gmail 送信機能は現在利用不可。

---

## 一括確認スクリプト

すべてのチェックをまとめて実行したい場合：

```bash
python3 << 'ALLCHECK'
import subprocess, json, os

results = {}

# 1. GCP SA
r = subprocess.run(["gcloud", "auth", "list", "--format=value(account,status)"], capture_output=True, text=True)
active = [l for l in r.stdout.splitlines() if "ACTIVE" in l]
results["GCP SA"] = f"OK ({active[0].split()[0]})" if active else "FAIL"

# 2. Gemini
r = subprocess.run(["curl", "-sf", f"https://generativelanguage.googleapis.com/v1beta/models?key={os.environ.get('GOOGLE_API_KEY','')}"], capture_output=True, text=True)
try:
    d = json.loads(r.stdout)
    models = [m["name"] for m in d.get("models", [])[:2]]
    results["Gemini API"] = f"OK ({models})"
except:
    results["Gemini API"] = "FAIL"

# 3. YouTube
r = subprocess.run(["curl", "-sf", f"https://www.googleapis.com/youtube/v3/search?part=snippet&q=test&maxResults=1&key={os.environ.get('YOUTUBE_API_KEY','')}"], capture_output=True, text=True)
try:
    d = json.loads(r.stdout)
    results["YouTube API"] = f"OK (totalResults={d['pageInfo']['totalResults']})"
except:
    results["YouTube API"] = "FAIL"

# 4. API-Football
r = subprocess.run(["curl", "-sf", "-H", f"x-rapidapi-key: {os.environ.get('API_FOOTBALL_KEY','')}", "https://v3.football.api-sports.io/status"], capture_output=True, text=True)
try:
    d = json.loads(r.stdout)
    s = d.get("response", {})
    plan = s.get("subscription", {}).get("plan", "?")
    reqs = s.get("requests", {}).get("current", "?")
    results["API-Football"] = f"OK (plan={plan}, requests_today={reqs})"
except:
    results["API-Football"] = "FAIL"

# 5. GCS backup
r = subprocess.run(["gsutil", "ls", "gs://football-delay-watching-backup/"], capture_output=True, text=True)
results["GCS backup"] = "OK" if r.returncode == 0 else f"FAIL ({r.stderr.strip()[:80]})"

# 6. GCS firebase
r = subprocess.run(["gsutil", "ls", "gs://football-delay-watching-a8830.firebasestorage.app/"], capture_output=True, text=True)
results["GCS firebase"] = "OK" if r.returncode == 0 else f"FAIL ({r.stderr.strip()[:80]})"

# 7. GitHub (GITHUB_TOKEN直接 - 通常FAILのためMCP推奨)
r = subprocess.run(["curl", "-sf", "-H", f"Authorization: Bearer {os.environ.get('GITHUB_TOKEN','')}", "https://api.github.com/user"], capture_output=True, text=True)
try:
    d = json.loads(r.stdout)
    if "login" in d:
        results["GitHub Token"] = f"OK (login={d['login']})"
    else:
        results["GitHub Token"] = f"FAIL ({d.get('message','?')}) → use mcp__github__* instead"
except:
    results["GitHub Token"] = "FAIL → use mcp__github__* instead"

# 8. Gmail OAuth2
token_data = json.loads(os.environ.get("GMAIL_TOKEN", "{}"))
cred_data = json.loads(os.environ.get("GMAIL_CREDENTIALS", "{}")).get("installed", {})
r = subprocess.run([
    "curl", "-sf", "--cacert", "/tmp/combined-ca.pem",
    "-X", "POST", "https://oauth2.googleapis.com/token",
    "-d", f"client_id={cred_data.get('client_id','')}&client_secret={cred_data.get('client_secret','')}&refresh_token={token_data.get('refresh_token','')}&grant_type=refresh_token"
], capture_output=True, text=True)
try:
    resp = json.loads(r.stdout)
    if "access_token" in resp:
        results["Gmail OAuth2"] = "OK"
    else:
        results["Gmail OAuth2"] = f"FAIL ({resp.get('error_description', resp.get('error', '?'))})"
except:
    results["Gmail OAuth2"] = "FAIL"

# 表示
print("=" * 50)
print("  Environment Variable Check Results")
print("=" * 50)
for k, v in results.items():
    icon = "✓" if v.startswith("OK") else "✗"
    print(f"  {icon} {k:<20} {v}")
print("=" * 50)
ALLCHECK
```

---

## 既知の問題（2026-05-15 時点）

| 項目 | 状態 | 対処 |
|------|------|------|
| `GITHUB_TOKEN` | ❌ Bad credentials (401) | `mcp__github__*` ツールを使う |
| `GMAIL_TOKEN` | ❌ invalid_grant | リフレッシュトークンの再発行が必要 |
| Firebase CLI (`firebase` コマンド) | ❌ not installed | `safe_deploy.sh` / `gsutil` で代替 |

---

## 参考

- session-start フック: `.claude/hooks/session-start.sh`
- ロードされるシークレット: `CLAUDE.md` §8「GCP Secret Manager 登録済みシークレット」参照
- GCS バケット一覧: `gsutil ls` で確認
