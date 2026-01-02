# ドキュメントガイド

本ページは `docs/` の入口として、目的別の読み方と主要ドキュメントの地図を提供する。

---

## 🗺️ 目的別ガイド

### 「このシステムは何をするの？」 → 要件理解
1. [01_requirements/index.md](./01_requirements/index.md) - 機能要件一覧
2. [01_requirements/non_functional.md](./01_requirements/non_functional.md) - 非機能要件

### 「どう実装されてるの？」 → 実装理解
1. [02_design/system_overview.md](./02_design/system_overview.md) - 全体アーキテクチャ
2. [02_design/implementation_flow.md](./02_design/implementation_flow.md) - 処理フロー・責務境界
3. 詳細設計は [02_design/index.md](./02_design/index.md) を参照

### 「どう動かすの？」 → 運用理解
1. [03_operations/deployment.md](./03_operations/deployment.md) - デプロイ手順
2. [03_operations/execution_mode.md](./03_operations/execution_mode.md) - 実行モード（本番/デバッグ/モック）
3. [03_operations/api_quota.md](./03_operations/api_quota.md) - APIクォータ管理

### 「AIと一緒に開発したい」 → AI協業
1. [GEMINI.md](../GEMINI.md) - AI向けガイド・開発コマンド・Issue対応フロー

---

## 📂 ディレクトリ構成

| ディレクトリ | 役割 | 主なファイル |
|-------------|------|-------------|
| `01_requirements/` | WHAT: 何を作るか | `index.md`, `non_functional.md` |
| `02_design/` | HOW: どう実現するか | `system_overview.md`, `api_football.md`, `cache.md` |
| `03_operations/` | RUN: どう動かすか | `deployment.md`, `api_quota.md`, `execution_mode.md` |
| `GEMINI.md` | AI: 開発ガイド | (ルート配置) |

---

## 🔄 更新頻度の高い文書

開発中に頻繁に更新される文書の一覧。

| 文書 | 更新タイミング | 理由 |
|------|--------------|------|
| [GEMINI.md](../GEMINI.md) | 頻繁 | 開発コマンド・Issue対応フローが都度追記される |
| [03_operations/api_quota.md](./03_operations/api_quota.md) | 月次 | API料金・クォータの変更に追従 |
| [02_design/tuning_workflow.md](./02_design/tuning_workflow.md) | Issue対応時 | チューニングパラメータの変更 |

---

## 📝 更新ルール

1. **Code follows Design**: コード変更時は `02_design` も更新
2. **Single Source of Truth**: 要件は `01_requirements`、設計は `02_design`
3. **リンク整合性**: ファイル名変更時はリンク切れを確認

> 詳細は [GEMINI.md](../GEMINI.md#-ドキュメント構成と更新ルール) を参照。
