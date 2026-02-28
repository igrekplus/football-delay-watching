---
description: firebase上へのデプロイを行い、URLを返す
---

このworkflowが呼ばれるときは、基本的にセッションで修正が行われた状態になっている。
行われた修正をWEB上で確認するために、生成したHTMLをfirebaseにdeployし、URLをユーザに通知してほしい。

特定の1試合だけを確認したい場合は、デプロイ前に `TARGET_FIXTURE_ID` を使ってそのfixtureのHTMLを生成しておくこと。
例:

```bash
TARGET_DATE="2026-02-27" TARGET_FIXTURE_ID="1379248" DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```
