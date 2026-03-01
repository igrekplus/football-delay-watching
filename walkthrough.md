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
- 公開確認URL:
  - トップ: [https://football-delay-watching-a8830.web.app](https://football-delay-watching-a8830.web.app)
  - レポート: [https://football-delay-watching-a8830.web.app/reports/2026-02-27_Wolves_vs_AstonVilla_20260301_220926.html](https://football-delay-watching-a8830.web.app/reports/2026-02-27_Wolves_vs_AstonVilla_20260301_220926.html)
- ローカル確認:
  - `Fixture ID: 1379248` を確認
  - `https://aistudio.google.com/app/u/1/api-keys?pli=1&project=gen-lang-client-0394252790` を確認
  - `https://console.cloud.google.com/billing?authuser=1` を確認
  - `対象外動画一覧` が含まれないことを確認

## ブランチと更新状況

- 作業ブランチ: `codex/issue-234-close`
- `main` との差分: #234 の変更のみ
- 作業ツリー: クリーン化してから main へ取り込む前提
- 更新ファイル:
  - `docs/03_components/report_rendering.md` `commit済み / push前`
  - `docs/04_operations/api_quota.md` `commit済み / push前`
  - `implementation_plan.md` `commit済み / push前`
  - `src/formatters/youtube_section_formatter.py` `commit済み / push前`
  - `src/report_generator.py` `commit済み / push前`
  - `src/utils/api_stats.py` `commit済み / push前`
  - `task.md` `commit済み / push前`
  - `templates/report.html` `commit済み / push前`
  - `tests/test_debug_info.py` `commit済み / push前`
  - `walkthrough.md` `commit済み / push前`

## 補足

- `TARGET_FIXTURE_ID=1379248` の実行でも `rank=None` のため YouTube 検索がスキップされ、今回の確認は動画一覧が空のケースでのデバッグ表示検証に留まった。
