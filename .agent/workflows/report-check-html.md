---
description: HTMLレポート内に特定のキーワードが存在するか検証する
---

# Report Check HTML

生成されたHTMLレポートに、特定のキーワード（チーム名、選手名、監督名など）が含まれているか検証するワークフロー。
AIがチューニングやリファクタリングを行った後、意図したコンテンツが出力されているか自動確認するために使用する。

## 手順

// turbo-all

1. モックデータ/デバッグモードでレポート生成を実行
```bash
# 生成を実行（既存のレポートを上書きするリスクを考慮し、実行前に少し待機してもよいが、今回は直列実行）
source .venv/bin/activate && DEBUG_MODE=True USE_MOCK_DATA=True python main.py
```

2. 最新のHTMLファイルに対してgrep検索を実行
```bash
# 最新のレポートファイルを特定
LATEST_REPORT=$(ls -t public/reports/*.html | head -n 1)
echo "Checking file: $LATEST_REPORT"

# 引数 keyword が指定されている前提
grep -q "${keyword}" "$LATEST_REPORT" && echo "✅ Found: ${keyword}" || { echo "❌ Not Found: ${keyword}"; exit 1; }
```

## 使用例

```bash
/report-check-html keyword="Guardiola"
```
