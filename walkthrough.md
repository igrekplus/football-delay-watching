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
| スタメン一覧とフォーメーションの両方から詳細へ遷移したい | 共有モーダルを 1 つ用意し、スタメン一覧とフォーメーションの両方から同じプロフィールを開く | 2/28 の Leeds vs Manchester City で `Rayan Cherki` をスタメン一覧・フォーメーションのどちらからでもクリックすると、同じモーダルで `生まれ / 経歴 / 特徴 / 面白いエピソード` を表示できる |
| 情報がない選手まで押せるとノイズになる | `has_profile` を持つ選手だけをクリック可能にし、未登録選手は通常カードのままにする | `Rodri` などプロフィール未登録の選手は非クリック、プロフィール登録済みの選手だけ詳細モーダルを開けるようにした |
| `i` アイコンが小さく、フォーメーションでは国旗に被る | スタメン一覧は視認用の `i` バッジだけ残し、実際のトリガーはカード全体へ移す。フォーメーションは `i` を消してカード全体クリックに統一する | スタメン一覧は Instagram の右に情報バッジだけを表示し、フォーメーションはアイコンなしでカード本体クリック時のみモーダルが開くようにした |
| モーダルが白背景で見づらく、情報の視認性が低い | ダークトーンのモーダルへ変更し、選手名の横に顔写真を表示する | モーダルは濃紺背景に変更し、右上付近の背景グラデーションを削除、選手名の横に枠付きの顔写真を表示するようにした |

## 検証

- ユニットテスト: `.venv/bin/python -m unittest tests.test_player_instagram tests.test_player_profile_ui tests.test_formation_layout_data`
- 実データデバッグ実行: `TARGET_DATE="2026-02-28" TARGET_FIXTURE_ID="1379244" DEBUG_MODE=True USE_MOCK_DATA=False .venv/bin/python main.py`
- デプロイ: `./scripts/safe_deploy.sh`
- 公開確認URL:
  - トップ: [https://football-delay-watching-a8830.web.app](https://football-delay-watching-a8830.web.app)
  - レポート: [https://football-delay-watching-a8830.web.app/reports/2026-02-28_Leeds_vs_ManchesterCity_20260301_224531.html](https://football-delay-watching-a8830.web.app/reports/2026-02-28_Leeds_vs_ManchesterCity_20260301_224531.html)

## 補足

- GCS 上の `master/player/player_50.csv` に `profile_format,profile_detail` を追加し、初回サンプルとして `R. Cherki` の詳細プロフィールを投入した。
- 公開済みレポート HTML では `player-profile-rayan-cherki` のテンプレート、`生まれ` / `経歴` / `特徴` / `面白いエピソード` の各セクション、モーダルの顔写真、フォーメーション側のカードクリック導線を確認済み。

## ブランチと更新状況

- 作業ブランチ: `feature-232/player-profile-modal`
- `main...HEAD` の差分: 3コミット（`fd78405`, `f5486ea`, `2cfd799`）、未push
- 作業ツリー:
  - #232 の追加UX調整（カード全体クリック、モーダル配色見直し、顔写真表示、フォーメーションの `i` 非表示）は未コミット
  - #234 由来の未コミット変更も同じ作業ツリーに混在
- マージ前の注意点:
  - 現在公開されている #232 の最終状態は、`main...HEAD` にはまだ含まれていない
  - `templates/report.html` と `walkthrough.md` は #232 と #234 の変更が混在しているため、マージ前に差分の切り分けか追加commitが必要

---

# Issue #234 Walkthrough

## 解決状況

| 課題 | 方針 | 結果 |
| --- | --- | --- |
| デバッグ情報に対象試合の識別子がなく、調査時に fixture を特定しづらい | デバッグセクションの先頭に `Fixture ID` を固定表示する | 生成HTMLで `Fixture ID: 1379248` を確認できるようになった |
| デバッグ情報が部分的にしか折りたたまれず、API使用状況だけ常時展開されている | 共有デバッグ情報を既存の `<details class="collapsible-section">` に統合する | デバッグ情報は 1 つの折りたたみセクションにまとまり、重複表示を除去した |
| `対象外動画一覧` が長く、調査ノイズになっている | 対象外動画の描画自体を廃止し、必要最小限のデバッグ情報だけ残す | `対象外動画一覧` は出力されなくなり、HTML内からも除去された |
| Gemini 系の確認リンクが運用で見たいアカウント / プロジェクトを指していない | `ApiStats` のリンク定義を指定URLへ差し替える | `Gemini API` は AI Studio の指定プロジェクト、`Gemini Grounding` は `authuser=1` 付き Billing へ飛ぶようになった |

## 検証

- ユニットテスト: `python -m unittest tests.test_debug_info`
- 実データデバッグ実行: `TARGET_DATE="2026-02-27" TARGET_FIXTURE_ID="1379248" DEBUG_MODE=True USE_MOCK_DATA=False .venv/bin/python main.py`
- デプロイ: `./scripts/safe_deploy.sh`
- ローカル確認:
  - 生成HTML: `public/reports/2026-02-27_Wolves_vs_AstonVilla_20260301_220926.html`
  - `Fixture ID: 1379248` を確認
  - `https://aistudio.google.com/app/u/1/api-keys?pli=1&project=gen-lang-client-0394252790` を確認
  - `https://console.cloud.google.com/billing?authuser=1` を確認
  - `対象外動画一覧` が含まれないことを確認
- 公開確認URL:
  - トップ: [https://football-delay-watching-a8830.web.app](https://football-delay-watching-a8830.web.app)
  - レポート: [https://football-delay-watching-a8830.web.app/reports/2026-02-27_Wolves_vs_AstonVilla_20260301_220926.html](https://football-delay-watching-a8830.web.app/reports/2026-02-27_Wolves_vs_AstonVilla_20260301_220926.html)

## 補足

- 現在の作業ツリーは `feature-232/player-profile-modal` 上で、別件由来の未コミット変更 `public/calendar.html` が残っている。
- ユーザー了承のうえでこの状態のまま `./scripts/safe_deploy.sh` を実行したため、#232 由来の未コミット変更も同時に公開されている。
- 追加で見つかった要件外課題: `TARGET_FIXTURE_ID=1379248` の実行でも `rank=None` のため YouTube 検索がスキップされ、今回のデバッグセクション検証では動画一覧が空のケースしか見えていない。

## ブランチと更新状況

- 作業ブランチ: `feature-232/player-profile-modal`
- `main` との差分: #234 の変更は未コミットのため、`main...HEAD` にはまだ含まれていない
- 作業ツリー:
  - #234 対象の変更は未コミット
  - `public/calendar.html` はデプロイ時の再生成差分として未コミット
- 更新ファイル:
  - `docs/03_components/report_rendering.md` `未コミット / 未push`
  - `docs/04_operations/api_quota.md` `未コミット / 未push`
  - `implementation_plan.md` `未コミット / 未push`
  - `src/formatters/youtube_section_formatter.py` `未コミット / 未push`
  - `src/report_generator.py` `未コミット / 未push`
  - `src/utils/api_stats.py` `未コミット / 未push`
  - `task.md` `未コミット / 未push`
  - `templates/report.html` `未コミット / 未push`
  - `tests/test_debug_info.py` `未コミット / 未push`
  - `walkthrough.md` `未コミット / 未push`
