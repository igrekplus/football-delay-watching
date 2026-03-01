# Issue #216 実装計画（Firebase 運用堅牢化）

作成日: 2026-02-23  
対象Issue: [#216](https://github.com/igrekplus/football-delay-watching/issues/216)

## 1. 背景と課題

2026-02-23 に発生したログイン障害（`Firebase config not found` / `login is not defined`）の再発防止が必要です。  
今回の実装では、欠落設定の早期検知・キャッシュ整合性・デプロイ後の自動検証を強化します。

## 2. ゴール / 非ゴール

### 2.1 ゴール

1. `public/firebase_config.json` と `public/allowed_emails.json` の欠落/不正JSONをデプロイ前に確実に検知する  
2. CI で `FIREBASE_CONFIG` / `ALLOWED_EMAILS` の空設定を fail-fast で止める  
3. デプロイ後に必須 3 エンドポイント（config / allowlist / manifest）の 200 応答を保証する  
4. `/` と `/index.html` のキャッシュ方針を一致させる  
5. `sync_firebase_reports.py` が stale manifest を掴まない実装にする

### 2.2 非ゴール

1. Firebase Auth の方式変更  
2. Hosting 配信を Cloud Run/Functions へ移行する本実装  
3. `reports/*.html` の配信制御方式の全面刷新（Phase 3 は設計決定のみ）

## 3. 実装方針

### Phase 1: 即対応（ガード + CI + スモーク）

- `scripts/safe_deploy.sh`
  - 必須JSONファイルの存在チェック
  - JSON構文チェック
  - 上記が通らない場合はデプロイ前に終了
- `.github/workflows/daily_report.yml`
  - `FIREBASE_CONFIG` / `ALLOWED_EMAILS` の空チェック
  - JSON構文チェック
  - デプロイ後スモークテストを追加
- `.github/workflows/update-calendar.yml`
  - `FIREBASE_CONFIG` / `ALLOWED_EMAILS` の空チェック
  - JSON構文チェック
  - デプロイ後スモークテストを追加

### Phase 2: 整合性改善（キャッシュ）

- `firebase.json`
  - `/` に `no-cache, no-store, must-revalidate` ヘッダー追加
  - `/reports/manifest.json` に同ヘッダー追加
- `scripts/sync_firebase_reports.py`
  - manifest 取得時URLに cache-buster を付与
  - `Cache-Control: no-cache` ヘッダーも併用

### Phase 3: 設計改善（中期）

- 認可をクライアント判定からサーバーサイド検証へ移行するための方針を整理
- 実装は別Issueへ切り出す（本Issueでは方針確定まで）

## 4. 変更対象ファイル

1. `docs/04_operations/deployment.md`  
2. `scripts/safe_deploy.sh`  
3. `scripts/sync_firebase_reports.py`  
4. `firebase.json`  
5. `.github/workflows/daily_report.yml`  
6. `.github/workflows/update-calendar.yml`  
7. `task.md`

## 5. 検証計画

### 5.1 ローカル静的検証

1. `python -m json.tool public/firebase_config.json`  
2. `python -m json.tool public/allowed_emails.json`  
3. `python -m unittest discover tests`（回帰確認）

### 5.2 スクリプト検証

1. `scripts/safe_deploy.sh` のガード分岐を確認（欠落/不正JSONで失敗）  
2. `scripts/sync_firebase_reports.py` 実行ログで cache-buster 付き URL 取得を確認

### 5.3 デプロイ後確認（CI想定）

1. `curl -f /firebase_config.json`  
2. `curl -f /allowed_emails.json`  
3. `curl -f /reports/manifest.json`

## 6. リスクと対策

1. secret の改行・エスケープ差で JSON 構文エラーになる  
  - 対策: CI で deploy 前に `python -m json.tool` を必須化
2. ルートキャッシュ変更の副作用（初回表示の再取得増）  
  - 対策: 対象を `/` と `manifest` のみに限定し、静的資産全体には波及させない
3. 認可強化は設計範囲が大きく、同一Issueで完了しにくい  
  - 対策: Phase 3 は別Issue化して実装スコープを分離

---

# Issue #232 実装計画（選手詳細モーダル）

作成日: 2026-03-01
対象Issue: [#232](https://github.com/igrekplus/football-delay-watching/issues/232)

## 1. 背景と課題

スタメン一覧とフォーメーション図には、現状は選手の基本カードしかありません。  
Issue #232 では、画面遷移なしでタップ時に詳細を読める導線を追加し、まずは 2026-02-28 開催の Leeds vs Manchester City における `R. Cherki` の詳細表示を成立させます。

## 2. ゴール / 非ゴール

### 2.1 ゴール

1. `R. Cherki` に対して、生まれ・所属クラブ履歴・特徴・面白いエピソードを保持できるデータ構造を追加する
2. スタメンカードから詳細モーダルを開けるようにする
3. フォーメーション図からも同じ詳細モーダルを開けるようにする
4. 詳細データを持たない選手には既存表示を維持し、回帰を起こさない

### 2.2 非ゴール

1. 全チーム・全選手の詳細データ収集
2. 詳細情報の自動スクレイピングや LLM 自動生成
3. 別ページ遷移や URL ルーティング追加

## 3. 実装方針

### Phase 1: データ保持

- GCS 上の `player_<team_id>.csv` を実行時に直接読み、既存フォーマットを後方互換のまま拡張する
- `profile_format` / `profile_detail` の2列を追加し、詳細ブロックのラベルと改行ルールを持てるようにする
- `settings/player_instagram.py` で Instagram URL と同時に詳細プロフィールもロードできるようにする
- `FactsService` で `player_id` ベースに `MatchFacts` へ取り込む

### Phase 2: レポート UI

- スタメンカードに、詳細を持つ場合のみクリック可能な属性を付与する
- フォーメーションの選手カードにも同じ属性を付与する
- `report.html` に共通モーダルを 1 つだけ配置し、JS で内容を差し替えて開閉する
- CSS は既存のカードデザインを崩さず、タップ可能状態だけ視認できるようにする

### Phase 3: 初期データ投入

- GCS 上の `player_50.csv` に `R. Cherki` の詳細を投入して表示できる前提にする
- 将来の横展開を見据え、他選手は空欄でも壊れない設計にする

## 4. 変更対象ファイル

1. `implementation_plan.md`
2. `task.md`
3. `docs/02_architecture/domain_models.md`
4. `settings/player_instagram.py`
5. `src/domain/models.py`
6. `src/facts_service.py`
7. `src/formatters/player_formatter.py`
8. `src/utils/formation_image.py`
9. `src/utils/player_profile.py`
10. `src/report_generator.py`
11. `templates/partials/player_card.html`
12. `templates/partials/formation_section.html`
13. `templates/partials/player_profile_modal.html`
14. `templates/report.html`
15. `public/assets/report_styles.css`
16. `scripts/fetch_squad_list.py`
17. `tests/test_player_instagram.py`

## 5. 検証計画

1. `python -m unittest tests.test_player_instagram`
2. `TARGET_DATE="2026-02-28" TARGET_FIXTURE_ID="1379244" DEBUG_MODE=True USE_MOCK_DATA=False .venv/bin/python main.py`
3. 生成された `public/reports/*Leeds_vs_ManchesterCity*.html` を確認し、`R. Cherki` に詳細セクションが表示され、他選手もタップでモーダルが開くことを確認する

## 6. リスクと対策

1. 既存 CSV に新列がなくても読み込みで落ちる
  - 対策: 新列はすべて任意列として `DictReader.get()` ベースで扱う
2. カード内の Instagram リンククリックでモーダルが誤発火する
  - 対策: JS 側で `player-instagram-link` クリックを明示的に除外する
3. 名前翻訳後の HTML 置換が data 属性を壊す
  - 対策: モーダル表示に必要な値はプレーン文字列で保持し、JS では `textContent` で描画する

---
# Issue #234 実装計画（デバッグ情報の整理）

作成日: 2026-03-01
対象Issue: [#234](https://github.com/igrekplus/football-delay-watching/issues/234)

## 1. 背景と課題

デバッグ情報が「一部だけ折りたたみ」「対象外動画一覧を大量表示」「外部リンクの遷移先が運用実態とずれている」という状態です。
Issue #234 では、調査時に必要な識別情報を増やしつつ、不要な一覧を削り、運用導線を実際の確認先に合わせます。

## 2. ゴール / 非ゴール

### 2.1 ゴール

1. デバッグ情報の先頭で `Fixture ID` を確認できるようにする
2. デバッグ情報全体を 1 つの折りたたみセクションに統合する
3. `対象外動画一覧` を画面に出力しない
4. `Gemini Grounding` と `Gemini API` の確認リンクを指定 URL に更新する

### 2.2 非ゴール

1. YouTube のフィルタリングロジック自体の変更
2. 対象外動画データ構造（`removed` / `overflow`）の削除
3. デバッグ以外の通常セクション構成変更

## 3. 実装方針

### Phase 1: 表示設計の整理

- `docs/03_components/report_rendering.md` に、デバッグ情報を単一の折りたたみへ統合するルールを追記する
- `docs/04_operations/api_quota.md` に、レポート内デバッグリンクの運用URLを追記する

### Phase 2: レポート UI 実装

- `YouTubeSectionFormatter` は、対象外動画一覧を廃止し、`Fixture ID` / `Importance` と共有デバッグ情報だけを描画する
- `ReportGenerator` は、共有デバッグ情報を同じ `<details>` 内へ差し込む
- `templates/report.html` から重複したデバッグ表示の差し込みを除去する

### Phase 3: リンク更新と回帰確認

- `ApiStats` の `Gemini API` / `Gemini Grounding` の確認リンクを更新する
- デバッグHTMLの構造とリンク文字列をテストで固定する

## 4. 変更対象ファイル

1. `implementation_plan.md`
2. `task.md`
3. `docs/03_components/report_rendering.md`
4. `docs/04_operations/api_quota.md`
5. `src/formatters/youtube_section_formatter.py`
6. `src/report_generator.py`
7. `templates/report.html`
8. `src/utils/api_stats.py`
9. `tests/test_debug_info.py`

## 5. 検証計画

1. `python -m unittest tests.test_debug_info`
2. `TARGET_DATE="2026-02-27" TARGET_FIXTURE_ID="1379248" DEBUG_MODE=True USE_MOCK_DATA=False .venv/bin/python main.py`
3. 生成されたレポートで、デバッグ情報が 1 つの折りたたみになっていることと `Fixture ID` が表示されることを確認する

## 6. リスクと対策

1. 共有デバッグ情報が各レポートから消える
  - 対策: `ReportGenerator` 側で既存の共有HTMLを維持しつつ、差し込み位置だけ統合する
2. API統計リンク変更がメール表示など別経路にも影響する
  - 対策: 変更は要件どおり同じ `ApiStats` 定義に集約し、リンク先だけを差し替える
3. デバッグ情報の折りたたみ統合で CSS が崩れる
  - 対策: 既存の `collapsible-section` を再利用し、新規スタイル追加を避ける
