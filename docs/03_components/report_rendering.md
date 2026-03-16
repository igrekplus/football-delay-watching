# レポート描画設計

レポートHTMLの描画基盤（Jinja2）と、表示統合ルールを定義する。

---

## 1. 目的

- レンダリング責務を `ReportGenerator` + テンプレートへ集約する
- 情報生成責務（News/Facts/Tribute）と表示責務を分離する
- セクション追加時の影響範囲をテンプレート単位に限定する

---

## 2. 主要コンポーネント

| コンポーネント | 役割 |
|---|---|
| `src/report_generator.py` | 描画用コンテキスト組み立て、テンプレート呼び出し |
| `src/template_engine.py` | Jinja2環境設定、`render_template()` |
| `templates/report.html` | 試合レポート全体テンプレート |
| `templates/partials/*.html` | セクション単位の部分テンプレート |

---

## 3. 描画フロー

1. `FactsService` / `NewsService` が `MatchAggregate` を更新  
2. `ReportGenerator` が描画用コンテキストを生成  
3. `template_engine.render_template("report.html", **context)` でHTML化  
4. `HtmlGenerator` が試合ごとに保存し、manifest更新

---

## 4. 表示統合ルール

### 4.1 責務分離

- **News系**: `NewsService`  
  - `news_summary`, `tactical_preview`, `*_interview`, `*_transfer_news`
- **Trivia系**: `FactsService` 内の `TributeGenerator`  
  - `same_country_matchups`, `same_country_text`, `former_club_trivia`

実装責務は分離し、**表示層（ReportGenerator + template）で近接配置**する。

### 4.2 パース・フォーマット

- 同国対決: 構造化データ（`same_country_matchups`）を優先し、必要時のみテキストパースへフォールバック
- 古巣対決: `parse_former_club_text()` で構造化し、カード形式へ変換

### 4.3 デバッグ情報

- デバッグ表示は 1 つの `<details class="collapsible-section">` に統合し、部分的に分離しない
- 先頭に `Fixture ID` と `Importance` を表示し、調査対象の試合を即判別できるようにする
- YouTube の `removed` / `overflow` 一覧は画面に出力しない
- API使用状況や選外試合リストなどの共有情報は、同じ折りたたみ内に差し込む

### 4.4 過去の対戦成績（H2H）

- H2H テーブルは `日付 / 大会 / 対戦 / スコア` の4列を基本表示とする
- home 視点の `結果` 列は表示しない
- 勝者の強調表示は対戦カード内のチーム名太字で表現し、列追加で重複説明しない

---

## 5. 翻訳レイヤ

### 5.1 選手名翻訳（表示向け）

- 実装: `src/utils/name_translator.py`
- 用途:
  - レポートHTML内の選手名カタカナ化
  - フォーメーション図向け短縮名生成
- キャッシュ: `name_translation/*`
- 設計ルール:
  - 翻訳対象の入力キーは API-Football の原名をそのまま使う（アクセント付き氏名を含む）。
  - Gemini がアクセントを落としたキーを返すことがあるため、保存前に「要求時の原名」へ再対応付けする。
  - `short` が空文字・欠落しているキャッシュは不正値として扱い、再翻訳で自己修復する。
  - 翻訳は表示専用であり、`MatchFacts.player_*` の辞書キーは変更しない。

### 5.2 国籍表示（formation）

- 実装: `src/utils/nationality_flags.py`, `src/utils/formation_image.py`
- 用途:
  - 選手カードでは絵文字国旗を表示
  - フォーメーション図では flagcdn のSVG国旗を表示
- 設計ルール:
  - 国名の正規化（空白/ハイフン/別名対応）は `nationality_flags` に集約する。
  - フォーメーション専用の国コード変換で独自辞書を増やさず、共通ヘルパーから flagcdn コードを取得する。

### 5.3 チーム名翻訳（解析向け）

- 実装: `src/utils/team_name_translator.py`
- 用途:
  - 古巣対決パーサの関連性判定キーワード補助
- キャッシュ: `team_translation/*`

---

## 6. テンプレート分割ポリシー

- 1セクション1パーシャルを原則とする
- データ整形はPython側（Formatter/Parser）で実施し、テンプレートは表示責務に限定する
- 新規セクション追加時は `templates/partials/` に追加し、`report.html` で組み込む

---

## 7. 選手詳細モーダル

- 実装: `templates/partials/player_profile_modal.html`, `templates/report.html`, `public/assets/report_styles.css`
- モーダル本体は表示責務のみを持ち、本文は外部の選手プロフィールHTMLを事前fetchして差し込む
- レスポンシブ方針:
  - モバイルは1カラムを維持する
  - `769px` 以上では本文カードを2カラム表示にして、デスクトップ/iPadでの縦スクロールを減らす
  - 画面幅が十分に大きくても、可読性のためモーダル最大幅には上限を設ける
