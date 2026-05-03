---
name: generate_player_profiles
description: 試合レポートの「選手詳細（player_profiles）」を更新する統括スキル。GCS上の選手CSV更新、standalone HTML生成、deploy までを扱う。調査と本文生成は `research_player_profile_content` を参照する。
---

# 選手詳細作成運用スキル

## 概要

この skill は、選手プロフィール更新の入口です。
継続運用としての設計・責務境界は `docs/04_operations/player_profile_generation.md` を参照し、実行手順はこの skill を SSOT とします。

想定 input は以下の 2 つだけである。

- `fixture-id`
- `チーム名`

この skill では、対象試合・対象チームについて **一度に 5 選手まで** を更新対象とする。

理由:
- 5選手を超えると、1人あたりの調査密度と本文品質が落ちやすい
- そのため、ユーザーが明示的に別指定しない限り、**1回の作業上限は5選手** とする

- 正本は GCS の `master/player/player_<team_id>.csv`
- ローカル作業コピーは `data/player_<team_id>.csv`
- 公開表示は **レポート HTML 本体** と **選手ごとの standalone HTML** に分離されている

重要:
- `public/player-profiles/<player_id>.html` を更新しただけでは、**既存レポート側の `data-player-profile-url` が空ならモーダル導線は生えない**
- 既存レポートでプロフィールを見せるには、**standalone HTML の更新** と **レポート HTML 側の参照導線確認** を別々に扱う必要がある
- そのため、同じレポート URL で確認できるのは、**対象レポートがすでに正しい `data-player-profile-url` を持っている場合に限る**
- `data/player_*.csv` は原則として `profile_format,profile_detail` 付きの新形式に揃っている前提で扱う

## この skill の担当範囲

1. 対象チーム CSV の特定と GCS からの pull
2. 対象チーム内で既存プロフィールの有無を確認
3. 更新対象 5 選手の選定
4. 調査・`labelled_lines_v1` 本文作成・`temp/*.md` 出力の起点
5. ローカル CSV 更新
6. GCS 正本への upload
7. standalone HTML 生成
8. レポート HTML 側の参照導線確認
9. deploy
10. 必要時のみ debug-run

## 下位 skill

本文の調査と下書き作成は、以下の skill を参照します。

- [research_player_profile_content](/Users/nagataryou/football-delay-watching/.agent/skills/research_player_profile_content/SKILL.md)

この下位 skill は、以下までを担当します。

- 情報源の選定
- `labelled_lines_v1` 形式での本文生成
- セルフレビュー
- `temp/player_profiles_YYYYMMDD_[team]_[player].md` の出力

## 実行フロー

### Step 1: GCS 正本をローカルへ pull

まず `fixture-id` と `チーム名` から対象 team を特定する。

- `チーム名` から `team_id` を確認する
- `settings/player_instagram.py` の `TEAM_CSV_FILES` で対象 CSV 名を確認する

```bash
python src/workflows/generate_player_profile/pull_csv.py --team-id 50
```

注意:
- 既存の `data/player_<team_id>.csv` をそのまま編集し始めないこと。
- 先に GCS 版を取得し、上書き事故を避ける。

### Step 2: 対象チーム内で既存プロフィールの有無を確認する

対象 fixture の対象チームについて、まず出場選手と既存プロフィール有無を照合する。

目的:
- すでに `profile_format` / `profile_detail` が入っている選手を把握する
- 未作成の選手候補を把握する
- その上で、今回更新する 5 選手を選ぶ

前提:
- `data/player_*.csv` は `profile_format` / `profile_detail` 列を持つ新形式を前提とする
- もし例外的に古いCSVが見つかった場合のみ、先に次のスクリプトで一括マイグレーションする

```bash
python src/workflows/generate_player_profile/migrate_player_csv_format.py
```

```bash
python src/workflows/generate_player_profile/check_missing_profiles.py --fixture-id <FIXTURE_ID> --team-id <TEAM_ID>
```

実行例:
```bash
python src/workflows/generate_player_profile/check_missing_profiles.py --fixture-id 1523413 --team-id 50
```

補足:
- ユーザーから明示的に「既存選手情報の確認は不要」と指示されない限り、**毎回ここで既存有無を確認する**
- 既存プロフィールがある選手を除いたうえで、今回の 5 選手を決める

### Step 3: 更新対象 5 選手を選定する

選定ルール:
- **先発優先**
- ただし先発だけを機械的に上から選ぶのではなく、**LLM が最適判断** して 5 選手を選ぶ

判断観点:
- 先発かどうか
- 既存プロフィールが未作成かどうか
- 若手・新加入・注目株かどうか
- 試合レポート内で見どころになりやすいか
- 同質な選手に偏りすぎないか

基本方針:
- まず先発の未作成選手から優先して検討する
- 先発だけで 5 人埋まる場合でも、情報価値が低い組み合わせなら最適判断で入れ替えてよい
- それでも上限は **5 選手まで**

### Step 4: 本文調査と `temp/*.md` 出力

この工程は下位 skill を使う。

- [research_player_profile_content](/Users/nagataryou/football-delay-watching/.agent/skills/research_player_profile_content/SKILL.md)

注意:
- 調査対象は Step 3 で選んだ **5 選手のみ**
- 6人目以降は同ターンで広げない

### Step 5: ローカル CSV へ反映

`data/player_<team_id>.csv` の対象選手行に以下 2 カラムを反映する。

- `profile_format`: `labelled_lines_v1`
- `profile_detail`: `\n` 区切りの本文

重要:
- `経歴` は **1 回だけ `経歴::` を使い、続きはラベルなし行で改行追記する**
- `経歴::` が複数回あると standalone HTML 生成時にエラーになる
- `生まれ` / `国籍` / `ポジション` / `身長・利き足` は HTML 側で `基本情報` 1カードにまとまる前提で整える
- `国籍` と現所属クラブ名は、レポートで使う国旗・チームロゴ表記と対応づけやすい名称を優先する

複数の選手を一括で更新する場合は、Pythonスクリプト（例: `temp`ディレクトリのMarkdown群をパースしてCSVに書き込む一時スクリプト）を作成・実行して一気に反映させると、改行崩れなどのミスがなく確実である。
反映前に、差分が対象選手の行だけであることを確認する（`git diff` の活用を推奨）。

### Step 6: GCS 正本へ upload

```bash
python src/workflows/generate_player_profile/push_csv.py --team-id 50
```

### Step 7: standalone HTML を生成する

#### これは何か

- 通常は `public/player-profiles/<player_id>.html` に置かれる、選手プロフィール本文だけの単体 HTML
- レポート HTML のカードは、このファイルを `fetch()` してモーダルに表示する
- ただし、**レポート HTML 側に `data-player-profile-url` が入っていないと fetch 自体が走らない**

#### 何に注意するか

- **通常の生成先は `player_id` ベースの固定ファイル名であり、レポート HTML が参照している URL と同じファイル名で上書きすること**
- `経歴::` が複数行あるプロフィールは、この段階でエラーとして止まる。先に CSV を修正する
- 既存選手を更新する場合は、まず現在の参照先を確認する
  - `public/reports/<report>.html` 内の `data-player-profile-url`
  - または `public/player-profiles/` に既にある対象ファイル
- 任意の `--output-path` で別名ファイルを生成することもできるが、その場合は既存レポートの参照先は自動では切り替わらない

重要:
- **standalone HTML を生成しただけでは既存レポートには反映されない場合がある**
- 既存レポートの `data-player-profile-url` が空なら、以下のどちらかが必要
  - 対象fixtureを再生成する
  - 対象レポート HTML を直接修正する
- どちらが必要かは、必ず Step 7 で確認する

#### 最低限の生成方法

```bash
python src/workflows/generate_player_profile/generate_profile_html.py --team-id 50 --player-id 156477
```

必要なら出力先を明示する。

```bash
python src/workflows/generate_player_profile/generate_profile_html.py \
  --team-id 50 \
  --player-id 156477 \
  --output-path public/player-profiles/156477.html
```

### Step 8: レポート HTML 側の参照導線を確認する

確認ポイント:
- `public/reports/<report>.html` 内の対象選手カードに `data-player-profile-url="/player-profiles/<player_id>.html"` が入っているか
- 既存レポートでこれが空なら、standalone HTML だけ更新しても公開URLではプロフィールを開けない

対応方針:
- すでにURLが入っている場合:
  - standalone HTML の生成と deploy だけでよい
- URLが空の場合:
  - 対象fixtureを debug-run で再生成する
  - もしくは対象レポート HTML を直接修正する

### Step 9: deploy する

standalone HTML を生成したら、既存の deploy workflow に従って Hosting へ反映する。

- 参照先: [.agent/workflows/deploy.md](/Users/nagataryou/football-delay-watching/.agent/workflows/deploy.md)

```bash
./scripts/safe_deploy.sh
```

### Step 10: 必要に応じて debug-run

以下は常に必須ではないが、次の場合は **実質必須** と考える。

- 新規プロフィールで URL 自体を確認したい場合
- 対象レポートがまだその選手を参照していない場合
- `data-player-profile-url` が空で、既存レポート HTML を直接直したくない場合
- レポート再生成後も、対象選手の導線が正しく張られることを検証したい場合

```bash
TARGET_DATE="2026-02-28" TARGET_FIXTURE_ID="1379244" DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```

補足:
- debug-run は「本文生成」のためではなく、**対象fixtureのレポート HTML 側に正しいプロフィール参照が入るかを確認する工程** として使う
- 既存公開URLをそのまま活かしたい場合は、生成された新しい HTML 名と既存公開URLの差異にも注意する

## 最低限の検証

1. fixture の対象チームについて、既存プロフィール有無を確認したうえで 5 選手を選定したことを明示する。
2. ローカル CSV の対象行に `profile_format` / `profile_detail` が入っていることを確認する。
3. 更新対象が 5 選手以内であることを確認する。
4. standalone HTML を更新した場合は、対象の `public/player-profiles/*.html` に期待する本文断片が出ていることを確認する。
5. レポートから確認する場合は、対象レポート HTML がその `data-player-profile-url` を参照していることを確認する。
6. `data-player-profile-url` が空だった場合は、debug-run または HTML修正のどちらで導線を作ったかを明示する。
7. deploy 後は、公開 URL 側でもレポートHTML内の `data-player-profile-url` と、プロフィール本文の断片語句の両方を確認する。
8. レポートのモーダル確認は `fetch()` を使うため、`file://` 直開きではなく、deploy 後の公開 URL かローカル HTTP サーバ経由で確認する。
