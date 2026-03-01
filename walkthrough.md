# Issue #222 Walkthrough

## 解決状況

| 課題 | 方針 | 結果 |
| --- | --- | --- |
| スタメン一覧で `Marc Guéhi` が英語のまま残る | 選手名翻訳キャッシュの壊れた `short` を再取得し、Gemini がアクセントを落としたキーを返しても元の API 名に再対応付けする | `Marc Guéhi` はスタメンカードで `マルク・ゲイ`、フォーメーションでは `M・ゲイ` に統一された |
| `Antoine Semenyo` の国旗がスタメン一覧で欠落する | フォーメーション用の国旗コード解決を専用辞書から共通ヘルパーへ寄せ、`Ghana` などの国籍を網羅する | フォーメーション表示で `A・セメニョ` に `gh.svg` の国旗が付くようになった |
| `Nico O'Reilly` が文中やスタメン一覧で一部英語のまま残る | フルネーム一致だけでなく、一意な姓のみ表記と HTML エスケープ済み表記（`&#39;`）も翻訳対象に含める | `Nico O'Reilly` / `O'Reilly` / `Nico O&#39;Reilly` は `ニコ・オライリー` に統一された |
| 仕様が曖昧で、表示名と内部キーの責務境界が不明確 | 設計書に「`player_*` 辞書のキーは API-Football の生名を保持し、翻訳は表示層でのみ行う」と明記する | 設計方針をドキュメントへ反映し、今後の修正方針を固定した |

## 検証

- ユニットテスト: `python -m unittest tests.test_translation_cache_contamination tests.test_formation_layout_data`
- 実データデバッグ実行: `TARGET_DATE="2026-02-21" TARGET_FIXTURE_ID="1379234" DEBUG_MODE=True USE_MOCK_DATA=False .venv/bin/python main.py`
- 公開確認URL:
  - トップ: [https://football-delay-watching-a8830.web.app](https://football-delay-watching-a8830.web.app)
  - カレンダー: [https://football-delay-watching-a8830.web.app/calendar.html](https://football-delay-watching-a8830.web.app/calendar.html)
  - 最新レポート: [https://football-delay-watching-a8830.web.app/reports/2026-02-21_ManchesterCity_vs_Newcastle_20260301_002206.html](https://football-delay-watching-a8830.web.app/reports/2026-02-21_ManchesterCity_vs_Newcastle_20260301_002206.html)

## ブランチと更新状況

- 作業ブランチ: `codex/feature-222/lineup-translation-fix`
- `main` との差分: 5コミット先行、未push
- 作業ツリー: クリーン（未コミット変更なし）
- 更新ファイル:
  - `docs/02_architecture/domain_models.md` `commit済み / push未実施`
  - `docs/03_components/report_rendering.md` `commit済み / push未実施`
  - `public/calendar.html` `commit済み / push未実施`
  - `src/utils/formation_image.py` `commit済み / push未実施`
  - `src/utils/name_translator.py` `commit済み / push未実施`
  - `src/utils/nationality_flags.py` `commit済み / push未実施`
  - `tests/test_formation_layout_data.py` `commit済み / push未実施`
  - `tests/test_translation_cache_contamination.py` `commit済み / push未実施`

## 補足

- 旧レポートURL（例: `..._20260301_001526.html` より前の生成物）は静的ファイルとして残るため、古いURLを開くと未修正表示が残る。カレンダーは最新レポート `..._20260301_002206.html` を参照している。
- `ruff` はローカルコマンドとして直接は入っていなかったが、commit時の pre-commit フック経由では実行・整形済み。

---

# Issue #232 Walkthrough

## 解決状況

| 課題 | 方針 | 結果 |
| --- | --- | --- |
| 選手詳細を手元ファイルではなく実行時に GCS から参照したい | 既存の Instagram URL 読み込みと同じ `player_<team_id>.csv` を流用し、同一 CSV に `profile_format` / `profile_detail` を追加して一括取得する | `settings/player_instagram.py` で Instagram URL とプロフィール詳細を同時に読み込み、`FactsService` から `player_id` ベースで各試合データへ反映するようにした |
| CSV のスキーマが未確定で、見せ方ルールも持たせたい | 表示ルールを 2 列に限定し、`profile_format=labelled_lines_v1` と `profile_detail` の組み合わせで解釈する | `profile_detail` に `ラベル::本文` を改行区切りで並べるだけで、モーダル上では見出し付きセクションとして整形表示できるようにした |
| スタメン一覧とフォーメーションの両方から詳細へ遷移したい | すべての選手カードとフォーメーションノードをタップ対象にし、共有モーダルを開く | ベンチ含む全カードに「タップで詳細」を付与し、詳細未登録選手は準備中メッセージ、登録済み選手は CSV の内容をモーダル表示するようにした |

## 検証

- ユニットテスト: `.venv/bin/python -m unittest tests.test_player_instagram tests.test_player_profile_ui tests.test_formation_layout_data`
- 実データデバッグ実行: `TARGET_DATE="2026-02-28" TARGET_FIXTURE_ID="1379244" DEBUG_MODE=True USE_MOCK_DATA=False .venv/bin/python main.py`
- デプロイ: `./scripts/safe_deploy.sh`
- 公開確認URL:
  - トップ: [https://football-delay-watching-a8830.web.app](https://football-delay-watching-a8830.web.app)
  - レポート: [https://football-delay-watching-a8830.web.app/reports/2026-02-28_Leeds_vs_ManchesterCity_20260301_214941.html](https://football-delay-watching-a8830.web.app/reports/2026-02-28_Leeds_vs_ManchesterCity_20260301_214941.html)

## 補足

- GCS 上の `master/player/player_50.csv` に `profile_format,profile_detail` を追加し、初回サンプルとして `R. Cherki` の詳細プロフィールを投入した。
- 公開済みレポート HTML では `player-profile-rayan-cherki` のテンプレート、`生まれ` / `経歴` / `特徴` / `面白いエピソード` の各セクション、および `経歴` の `<br>` 改行を確認済み。
- 作業ブランチは `feature-232/player-profile-modal`、実装コミットは `fd78405 feat(#232): add player profile modal`。
