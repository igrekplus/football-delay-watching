---
description: デバッグモードでレポートを生成し、Firebase Hostingにデプロイする。
---

# Debug Run & Deploy (絶対遵守)

**「実データをAPIから取得してテストしたい」のか「UIだけ確認したい」のかを、環境変数で厳密に使い分けること。**

## 🚨 重要：実行モードの選択

| 目的 | 指定する環境変数 |
| :--- | :--- |
| **実データの取得・検証** | `DEBUG_MODE=True USE_MOCK_DATA=False` |
| UI/レイアウトのみの確認（APIを叩かない） | `DEBUG_MODE=True USE_MOCK_DATA=True` |

> [!CAUTION]
> **`USE_MOCK_DATA` を省略すると `False`（実API使用）になります。**
> モックモードを使う場合は`USE_MOCK_DATA=True`を指定してください。
> ただし、モックモードで済む修正の場合に限るので、そのケースは少ない。

---

## 前提条件

- `.venv` が作成済みであること
- 初回のみ: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

## 手順

// turbo-all

### 1. venv の有効化とレポート生成

以下のコマンドを実行する。**`USE_MOCK_DATA=False` を忘れると、APIを叩かずに偽データで動くので注意。**

```bash
# 日付(YYYY-MM-DD)は必要に応じて変更するが、原則2日以上前のfixturesが存在する日で実施すること。
# 指定した日付の「07:00 JST」として実行される（＝その前の晩の試合を拾う）
#
# > [!IMPORTANT]
# > **TARGET_DATE は必ず「今日より2日以上前」の日付を指定すること！**
# > 当日や前日を指定するとスタメン情報がまだAPIに存在せず、レポートが不完全になります。
# > 例: 今日が 1/10 なら、1/8 以前を指定する。
TARGET_DATE="2026-01-08" DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```

> [!TIP]
> **run_command のバックグラウンド機能を活用すること**
> `nohup` や `tail -f` は使わない。代わりに `run_command` ツールの `WaitMsBeforeAsync` を **500ms** に設定して実行する。
> これにより自動的にバックグラウンドコマンドとなり、`command_status` ツールで `OutputCharacterCount` と `WaitDurationSeconds` を指定してログをポーリングできる。
>
> **ポーリング手順:**
> 1. `run_command` で実行 → バックグラウンドコマンドID を取得
> 2. `command_status` で `WaitDurationSeconds=30`、`OutputCharacterCount=2000` を指定して定期確認
> 3. Status が `DONE` になったら完了

**[確認項目]**
`command_status` の最初の出力で以下の行を**必ず**目視確認すること：
`Starting workflow... (Dry Run: False, Mock: False)`
→ `Mock: False` になっていればOK。`Mock: True` なら即座に停止（`send_command_input` で Terminate）してやり直すこと。

### 2. 生成物のローカル確認
HTMLファイルとフォーメーション画像が生成されているか確認。
```bash
# HTMLの確認
ls -lt public/reports/*.html | head -n 5

# 画像の確認
ls -la public/reports/images/*.png | tail -5
```

### 3. Firebaseとの同期（必須：他人の進捗を上書きしないため）
```bash
python scripts/sync_firebase_reports.py
```

### 4. デプロイ
```bash
firebase deploy --only hosting
```

### 5. URLの確認と報告
デプロイ完了後、公開URL（https://football-delay-watching-a8830.web.app）を開く。
**まずLLM（あなた）が確認してから、ユーザ側に報告を促すこと。**

---

## 📅 TARGET_DATE の計算ガイド
「見たい試合の現地日付」と **同じ日付** を指定する。
TARGET_DATE を指定すると、その日の早朝 (04:00 JST頃) から翌日の朝 (07:00 JST) までの試合を取得します。

| 見たい試合の現地日付 | 指定する TARGET_DATE |
| :--- | :--- |
| 12/23(月) | 2025-12-23 |
| 1/7(火) | 2026-01-07 |
| 1/10(土) | 2026-01-10 |

---

## 補足事項

- **1試合のみ処理**: デバッグモード（DEBUG_MODE=True）では、クォータ節約のため1試合のみを処理対象とする。
- **選手情報の制限**: 選手検索クォータ節約のため、1チームあたり1人程度の検索に制限される場合がある。
- **DEBUGバッジ**: 生成されたレポートのタイトル横に `[DEBUG]` または `[MOCK]` バッジが表示される。
- **キャッシュのクリア**: データが古い場合は `rm -rf .gemini/cache` でローカルキャッシュを消して再試行。
