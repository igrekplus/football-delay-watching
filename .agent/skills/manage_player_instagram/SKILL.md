---
name: manage_player_instagram
description: 特定チームの選手Instagram URLを調査し、GCS上の選手マスタCSVを安全に更新する。
---

# 選手Instagram情報の更新

## 概要
ユーザーから「〇〇のInstagram情報を更新して」「〇〇の選手Instagramを埋めて」と依頼された場合、このスキルに従います。

この作業の正本は GCS `master/player/player_<team_id>.csv` です。  
ローカル `data/player_<team_id>.csv` は作業用コピーとして扱い、更新前に GCS から取得し、更新後に GCS へ戻します。

## 基本方針
- ユーザーがチーム名を指定したら、そのチームだけを対象にします。
- 実行時の紐づけは `player_id` ベースです。名前一致だけで別行を更新しません。
- 公式アカウントと断定できない場合は追加しません。
- 認証バッジ（青バッジ）は補助材料です。青バッジ単独では採用しません。
- 調査が必要なので、Web検索を前提に進めます。

## 実行フロー

### 1. 対象チームの特定
まず `settings/player_instagram.py` の `TEAM_CSV_FILES` で対象チームの `team_id` を確認します。

未登録チームなら、以下を順に行います。
1. `python scripts/fetch_squad_list.py --team-id <team_id>` で初期CSVを作る
2. `settings/player_instagram.py` の `TEAM_CSV_FILES` に追加する
3. その後に通常フローへ入る

### 2. GCSから作業コピーを取得
```bash
python scripts/pull_player_csv_from_gcs.py --team-id 42
```

### 3. 未設定選手を確認
```bash
python scripts/analyze_missing_instagram.py --team-id 42
```

`Missing URLs` に出た選手だけを対象にします。

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

### 5. GCSへ反映
```bash
python scripts/migrate_player_csv_to_gcs.py --team-id 42
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
```

## 公式アカウントの判定
- 最優先: クラブ公式サイトから Instagram へ直接リンクされている
- 次点: Transfermarkt のソーシャルリンクに掲載されている
- 補助: 投稿内容、プロフィール文、所属クラブとの整合性
- 却下: 候補が複数あり断定できない、ファンアカウント、青バッジしか根拠がない

## 報告内容
ユーザーには以下を簡潔に返します。
1. 対象チーム名と `team_id`
2. 更新した選手数
3. スキップした選手と理由
4. GCS反映まで完了したか
5. 表示確認まで行ったか

## 参照
厳密な手順や確認コマンドの詳細は `.agent/workflows/fetch-instagram.md` を参照します。
