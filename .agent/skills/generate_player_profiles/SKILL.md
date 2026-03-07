---
name: generate_player_profiles
description: 試合レポートの「選手詳細（player_profiles）」を更新する統括スキル。GCS上の選手CSV更新、standalone HTML生成、deploy までを扱う。調査と本文生成は `research_player_profile_content` を参照する。
---

# 選手詳細作成スキル

## 概要

この skill は、選手プロフィール更新の入口です。

- 正本は GCS の `master/player/player_<team_id>.csv`
- ローカル作業コピーは `data/player_<team_id>.csv`
- 公開表示は **レポート HTML 本体** と **選手ごとの standalone HTML** に分離されている

そのため、この方式で生成済みのレポートであれば、CSV 更新後に standalone HTML を更新して deploy するだけで、同じレポート URL をリロードして最新プロフィールを確認できます。

## この skill の担当範囲

1. 対象チーム CSV の特定と GCS からの pull
2. 調査・`labelled_lines_v1` 本文作成・`temp/*.md` 出力の起点
3. ローカル CSV 更新
4. GCS 正本への upload
5. standalone HTML 生成
6. deploy
7. 必要時のみ debug-run

## 下位 skill

本文の調査と下書き作成は、以下の skill を参照します。

- [research_player_profile_content](/Users/nagataryou/football-delay-watching/.agent/skills/research_player_profile_content/SKILL.md)

この下位 skill は、以下までを担当します。

- 情報源の選定
- `labelled_lines_v1` 形式での本文生成
- セルフレビュー
- `temp/player_profiles_YYYYMMDD_[team]_[player].md` の出力

## 実行フロー

### Step 1: 対象チーム CSV の特定とプロフィールの不足確認

`settings/player_instagram.py` の `TEAM_CSV_FILES` で対象チームの `team_id` と CSV 名を確認する。
特定試合のスタメン・控えでプロフィールが未作成の選手を抽出する場合は、専用スクリプト `scripts/check_missing_profiles.py` を実行する。
（※事前に `data/player_<team_id>.csv` を最新化するため、後述のStep2を先に実行しておくことを推奨）

```bash
python scripts/check_missing_profiles.py --fixture-id <FIXTURE_ID> --team-id <TEAM_ID>
```

実行例（マンチェスター・シティの場合）:
```bash
python scripts/check_missing_profiles.py --fixture-id 1523413 --team-id 50
```

### Step 2: GCS 正本をローカルへ pull

```bash
python scripts/pull_player_csv_from_gcs.py --team-id 50
```

注意:
- 既存の `data/player_<team_id>.csv` をそのまま編集し始めないこと。
- 先に GCS 版を取得し、上書き事故を避ける。

### Step 3: 本文調査と `temp/*.md` 出力

この工程は下位 skill を使う。

- [research_player_profile_content](/Users/nagataryou/football-delay-watching/.agent/skills/research_player_profile_content/SKILL.md)

### Step 4: ローカル CSV へ反映

`data/player_<team_id>.csv` の対象選手行に以下 2 カラムを反映する。

- `profile_format`: `labelled_lines_v1`
- `profile_detail`: `\n` 区切りの本文

重要:
- `経歴` は **1 回だけ `経歴::` を使い、続きはラベルなし行で改行追記する**
- `経歴::` が複数回あると standalone HTML 生成時にエラーになる
- `生まれ` / `国籍` / `ポジション` / `身長・利き足` は HTML 側で `基本情報` 1カードにまとまる前提で整える
- `国籍` と現所属クラブ名は、レポートで使う国旗・チームロゴ表記と対応づけやすい名称を優先する

反映前に、差分がその選手の 1 行だけであることを確認する。

### Step 5: GCS 正本へ upload

```bash
python scripts/migrate_player_csv_to_gcs.py --team-id 50
```

### Step 6: standalone HTML を生成する

#### これは何か

- 通常は `public/player-profiles/<player_id>.html` に置かれる、選手プロフィール本文だけの単体 HTML
- レポート HTML のカードはこのファイルを `fetch()` してモーダルに表示する

#### 何に注意するか

- **通常の生成先は `player_id` ベースの固定ファイル名であり、レポート HTML が参照している URL と同じファイル名で上書きすること**
- `経歴::` が複数行あるプロフィールは、この段階でエラーとして止まる。先に CSV を修正する
- 既存選手を更新する場合は、まず現在の参照先を確認する
  - `public/reports/<report>.html` 内の `data-player-profile-url`
  - または `public/player-profiles/` に既にある対象ファイル
- 任意の `--output-path` で別名ファイルを生成することもできるが、その場合は既存レポートの参照先は自動では切り替わらない

#### 最低限の生成方法

```bash
python scripts/generate_player_profile_html.py --team-id 50 --player-id 156477
```

必要なら出力先を明示する。

```bash
python scripts/generate_player_profile_html.py \
  --team-id 50 \
  --player-id 156477 \
  --output-path public/player-profiles/156477.html
```

### Step 7: deploy する

standalone HTML を生成したら、既存の deploy workflow に従って Hosting へ反映する。

- 参照先: [.agent/workflows/deploy.md](/Users/nagataryou/football-delay-watching/.agent/workflows/deploy.md)

```bash
./scripts/safe_deploy.sh
```

### Step 8: 必要に応じて debug-run

以下は必須ではない。新規プロフィールで URL 自体を確認したい場合や、対象レポートがまだその選手を参照していない場合に限って使う。

```bash
TARGET_DATE="2026-02-28" TARGET_FIXTURE_ID="1379244" DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```

## 最低限の検証

1. ローカル CSV の対象行に `profile_format` / `profile_detail` が入っていることを確認する。
2. standalone HTML を更新した場合は、対象の `public/player-profiles/*.html` に期待する本文断片が出ていることを確認する。
3. deploy 後は、公開 URL 側でもプロフィール本文の断片語句を検索して確認する。
4. レポートから確認する場合は、対象レポート HTML がその `data-player-profile-url` を参照していることを確認する。
5. レポートのモーダル確認は `fetch()` を使うため、`file://` 直開きではなく、deploy 後の公開 URL かローカル HTTP サーバ経由で確認する。
