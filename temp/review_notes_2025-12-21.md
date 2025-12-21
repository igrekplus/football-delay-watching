# レビュー指摘チェックリスト（2025-12-21）

- [ ] 日本人先発でA判定ロジックがスタメン取得前に走り発火しない（`src/match_processor.py::_assign_rank`）。FactsService後に再評価するか、FactsService内フックで補正する。
- [ ] レポート出力ファイル名が実行日ベースで、`TARGET_DATE` をずらした再生成とズレる（`src/report_generator.py`）。ターゲット日付基準の命名へ変更。
- [ ] SpoilerFilterが `goal/得点/ゴール` を検閲し、goalkeeper等も[CENSORED]になる。例外単語や単語境界で誤爆抑制。
- [ ] Googleニュース検索の地域指定が実質常に `gl="us"` （`match.competition`が"EPL"/"CL"のため）。リーグ・クラブ国から `gl`/`lr` を決めるロジックにする。
- [ ] `config.py` で `USE_MOCK_DATA` が重複定義。定義箇所を1つに統一。
- [ ] `temp/send_actual_report.py` が環境変数を上書きし個人メールへ強制送信するため誤送信リスク。README注意喚起＋確認フラグ/警告を追加。
- [ ] `.env.example` を用意し必須/任意の環境変数を整理。
- [ ] 実行モードと出力先の対応、`TARGET_DATE` の決め方をREADMEに追記。
- [ ] ネタバレ防止仕様（禁止パターン・許容例外・誤爆例）をREADMEに要約。
- [ ] キャッシュ/クオータ管理の流れ（QUOTA_INFO、USE_API_CACHE上書き、cache warming条件）をREADMEに追記。
- [ ] Gmailセットアップ手順（tests/setup_gmail_oauth.pyの使い方、スコープ、トークン管理、送信確認フロー）をREADMEに追記。
- [ ] `temp/send_actual_report.py` 用の安全スイッチ実装（例: `--confirm` フラグ）とREADME記載。
