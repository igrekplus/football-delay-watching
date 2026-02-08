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

---

## 5. 翻訳レイヤ

### 5.1 選手名翻訳（表示向け）

- 実装: `src/utils/name_translator.py`
- 用途:
  - レポートHTML内の選手名カタカナ化
  - フォーメーション図向け短縮名生成
- キャッシュ: `name_translation/*`

### 5.2 チーム名翻訳（解析向け）

- 実装: `src/utils/team_name_translator.py`
- 用途:
  - 古巣対決パーサの関連性判定キーワード補助
- キャッシュ: `team_translation/*`

---

## 6. テンプレート分割ポリシー

- 1セクション1パーシャルを原則とする
- データ整形はPython側（Formatter/Parser）で実施し、テンプレートは表示責務に限定する
- 新規セクション追加時は `templates/partials/` に追加し、`report.html` で組み込む
