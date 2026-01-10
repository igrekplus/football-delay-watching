# レポートステータス管理

レポート生成の状態を GCS 上の CSV で管理し、品質チェックに基づいて再処理を制御する。

---

## 1. ステータス一覧

| ステータス | 説明 | 再処理対象 |
|-----------|------|-----------|
| `pending` | 未処理（レコードなし含む） | ✅ |
| `processing` | 処理中 | ✅ |
| `complete` | 品質チェック合格・完了 | ❌ |
| `partial` | 一部コンテンツ欠損 | ✅ |
| `failed` | エラー終了（3回まで再試行） | 条件付き |

**保存先**: `gs://football-delay-watching-cache/schedule/fixture_status.csv`

---

## 2. 品質判定基準

レポート生成完了時に以下をチェックし、すべて満たせば `complete`、不足があれば `partial`:

### 必須項目

| 項目 | チェック内容 | 欠損時の影響 |
|------|------------|-------------|
| ホームスタメン | `home_lineup` が存在し、要素が1つ以上 | `partial` |
| アウェイスタメン | `away_lineup` が存在し、要素が1つ以上 | `partial` |
| ニュース要約 or 戦術プレビュー | どちらか一方が存在 | `partial` |

### 品質判定から除外される項目

| 項目 | 除外理由 |
|------|---------|
| YouTube動画 | APIクォータ切れ時に無限再処理ループを防ぐため |

---

## 3. partial 再処理フロー

1. 品質チェックで必須項目が不足 → `partial` としてマーク
2. 次回バッチ実行時（3時間後）に `is_processable()` で再処理対象と判定
3. APIで最新データを取得し、不足項目を補完
4. 品質チェック合格 → `complete` に更新

> [!NOTE]
> `partial` はリトライカウントを増加させない。API側のデータ準備待ちを想定した設計。

---

## 4. 関連ファイル

- [fixture_status_manager.py](file:///Users/nagataryou/football-delay-watching/src/utils/fixture_status_manager.py) - ステータス管理実装
- [generate_guide_workflow.py](file:///Users/nagataryou/football-delay-watching/src/workflows/generate_guide_workflow.py) - 品質チェック実装 (`_check_report_quality`)
- [execution_mode.md](./execution_mode.md) - 実行モード設計

---

最終更新: 2026-01-10
