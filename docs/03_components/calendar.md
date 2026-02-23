# カレンダー設計

リーグごとの試合を一覧表示し、レポートへの遷移導線を提供する機能の設計。

---

## 1. 目的

- 複数リーグの試合日程を横断的に俯瞰できるようにする
- 生成済みレポートへ直接遷移できるようにする
- 配信実況情報（解説/実況）を試合単位で確認できるようにする

---

## 2. 実装コンポーネント

| コンポーネント | 責務 |
|---|---|
| `src/calendar_generator.py` | カレンダーHTML生成（4週間、週別/リーグ別表示） |
| `settings/calendar_data_loader.py` | カレンダーCSV読込、`fixture_id`単位の情報取得、レポートリンク更新 |
| `src/html_generator.py` | レポート生成時にCSVへ`report_link`を書き戻し |
| `public/calendar.html` | 生成物（Firebase公開対象） |

---

## 3. データソース

### 3.1 試合データ

- API-Football fixtures（対象リーグは`config.LEAGUE_INFO`）
- 表示範囲: 先週〜再来週の計4週間
- 週区切り: UTC基準の月曜開始〜日曜終了（MECE）
- 表示時刻: JST/UTC併記

### 3.2 付加情報（CSV）

- 保存先: `settings/calendar/*.csv`
- 主キー: `fixture_id`
- 主なカラム:
  - `fixture_id`
  - `date_jst`
  - `home_team`
  - `away_team`
  - `commentator`
  - `announcer`
  - `report_link`

---

## 4. 表示仕様

### 4.1 レイアウト

- 週セクションを縦に並べる
- 各週内はリーグ列を横並び表示
- リーグフィルタ（全選択/全解除）で表示制御

### 4.2 試合行

- メイン行:
  - キックオフ（JST/UTC）
  - ホーム/アウェイチーム名・ロゴ
  - `report_link`がある場合は`📄 Report`リンクを表示
- アコーディオン詳細:
  - ラウンド
  - 会場
  - 実況情報（`commentator`/`announcer`がある場合）

---

## 5. レポートリンク連携

### 5.1 書き込みタイミング

`HtmlGenerator.generate_html_reports()` で試合HTML生成後、`update_report_link()` を呼び出し、対応する `fixture_id` 行へ `report_link` を反映する。

### 5.2 更新方式

- 既存行がある場合: 該当行を更新
- 既存行がない場合: 対応リーグCSVへ新規追記
- 書き込み後は `load_all_calendar_data()` のキャッシュをクリア

---

## 6. 運用フロー（GitHub Actions）

1. `python main.py` でレポート生成
2. `settings/calendar/*.csv` を更新（`report_link`反映）
3. `python -m src.calendar_generator` で `public/calendar.html` を再生成
4. Firebase Hostingへデプロイ

---

## 7. 既知の設計判断

- カレンダーCSVは NoSQL 的な「運用用マッピング」として扱い、厳密正規化は行わない
- リーグ追加は `settings/leagues.yaml` と `settings/calendar/*.csv` の追加で拡張可能
- カレンダー表示は観戦導線のUIであり、試合選定ロジック（レポート対象判定）とは分離する
