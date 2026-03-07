---
name: fetch_instagram
description: "`/fetch-instagram` 相当。特定チームの選手Instagram URLを調査し、GCS上の選手マスタCSVを安全に更新する。ユーザーが「Instagramを埋めて」「インスタ検索」などを依頼したときに使う。"
---

# Player Instagram Fetch Skill

## 概要
この skill は、`/fetch-instagram` workflow の実質的な正本です。

skill の内部名は `fetch_instagram` とし、workflow / symlink 側は `fetch-instagram` を使います。

選手マスタCSVの `instagram_url` が未設定のときに、Web検索で候補を調査し、ローカル作業コピーを更新してから GCS の正本へ反映します。

- GCS 正本: `master/player/player_<team_id>.csv`
- ローカル作業コピー: `data/player_<team_id>.csv`
- 実行時の紐づけ: `player_id` ベース

## 基本方針
- ユーザーがチーム名を指定したら、そのチームだけを対象にします。
- 公式アカウントと断定できない場合は追加しません。
- 認証バッジ（青バッジ）は補助材料です。青バッジ単独では採用しません。
- 調査が必要なので、Web検索を前提に進めます。
- 新規CSVを作っただけでは反映されないため、未登録チームは `settings/player_instagram.py` の `TEAM_CSV_FILES` も更新します。

## 実行フロー

### 1. 対象チームの特定
まず `settings/player_instagram.py` の `TEAM_CSV_FILES` で対象チームの `team_id` を確認します。

未登録チームなら、以下を順に行います。
1. `python scripts/fetch_squad_list.py --team-id <team_id>` で初期CSVを作る
2. `settings/player_instagram.py` の `TEAM_CSV_FILES` に追加する
3. その後に通常フローへ入る

### 2. GCSから作業コピーを取得
```bash
python src/workflows/generate_player_profile/pull_csv.py --team-id 42
```

未登録チームで初期CSVを作った直後など、GCSに正本がまだない場合は `SKIP` になってもそのまま続行します。

### 3. 未設定選手を確認
```bash
python scripts/analyze_missing_instagram.py --team-id 42
```

一覧に表示された `instagram_url` 空欄の選手だけを調査対象にします。

### 4. 調査してローカルCSVを更新
`data/player_<team_id>.csv` の `instagram_url` を埋めます。形式は以下に統一します。

```text
https://www.instagram.com/{handle}/
```

検索順序の基本は以下です。
1. `"{選手名}" "{チーム名}" instagram`
2. `"{選手名}" "{チーム名}" インスタグラム`
3. `"{選手名}" instagram handle official`
4. `"{選手名}" Transfermarkt instagram handle`
5. `site:instagram.com "{選手名}" verified`

検索エンジンが bot 判定やレート制限で詰まる場合は、`web` ツール、ブラウザ確認、検索結果スニペット、補助的な外部索引へ切り替えて構いません。

#### 公式アカウントの判定
- 最優先: クラブ公式サイトから Instagram へ直接リンクされている
- 次点: Transfermarkt のソーシャルリンクに掲載されている
- 代替: 主要検索結果で Instagram プロフィールが直接ヒットし、プロフィール文や所属クラブが一致している
- 補助: 投稿内容、プロフィール文、所属クラブとの整合性
- 補助的な外部索引は、単独ではなく他の根拠と組み合わせて使う
- 却下: 候補が複数あり断定できない、ファンアカウント、青バッジしか根拠がない

#### スキップすべきケース
- SNSを使わないことで知られている選手
- ユース選手などで公開アカウントが見つからない場合
- 検索結果が曖昧で複数候補がある場合

### 5. GCSへ反映
```bash
python src/workflows/generate_player_profile/push_csv.py --team-id 42
```

### 6. 検証
まず、ローカル作業コピーで未設定数が減っていることを確認します。

```bash
python scripts/analyze_missing_instagram.py --team-id 42
```

必要なら表示確認まで行います。
1. `public/calendar.html` から対象チームの直近 fixture を確認する
2. `TARGET_FIXTURE_ID` を付けてデバッグ実行する
3. 生成HTMLに `player-instagram-link` が入っていることを確認する

例:

```bash
rg -n -C 8 "Arsenal|data-fixture-id" public/calendar.html
TARGET_DATE="2026-02-27" TARGET_FIXTURE_ID="1379248" DEBUG_MODE=True USE_MOCK_DATA=False python main.py
rg -n "instagram.com|player-instagram-link" public/reports/<generated_report>.html
```

切り分けの基本:
- アイコンが出ない: まずCSV未設定を疑う
- CSVにURLがあるのに出ない: その選手が試合表示対象に入っていない可能性がある
- リンク切れに見える: `curl -I https://www.instagram.com/<handle>/` で `404` かを確認する

### 7. コミットと報告
`data/` は `.gitignore` 対象のため、通常は CSV を git commit しません。

未登録チーム対応で `settings/player_instagram.py` を更新した場合のみ、その設定ファイルを確認してコミット対象にします。

```bash
git diff -- settings/player_instagram.py
git add settings/player_instagram.py
git commit -m "docs: register Barcelona player instagram CSV"
```

ユーザーには以下を簡潔に報告します。
1. 対象チーム名と `team_id`
2. 更新した選手数
3. スキップした選手と理由
4. GCS反映まで完了したか
5. 表示確認まで行ったか

## 関連ファイル
- `settings/player_instagram.py`
- `scripts/fetch_squad_list.py`
- `src/workflows/generate_player_profile/pull_csv.py`
- `scripts/analyze_missing_instagram.py`
- `src/workflows/generate_player_profile/push_csv.py`
