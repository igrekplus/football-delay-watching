---
description: 選手のInstagram URLを検索して、GCS上の選手マスタCSVを更新するワークフロー
---

# Player Instagram Fetch Workflow

選手マスタCSVの `instagram_url` が未設定の場合に、Web検索でURLを補完する手順書です。
実行時の紐づけは `player_id` ベースです。

現在の正本は GCS `master/player/player_<team_id>.csv` です。
ローカル `data/player_<team_id>.csv` は作業用コピーとして扱い、更新前に GCS から取得し、更新後に GCS へ再アップロードします。

## 前提条件
- 公式アカウントと確信が持てない場合は、誤情報を避けるため **追加しない**。
- 認証バッジ（青バッジ）は補助材料に留め、**青バッジだけでは採用しない**。
- 判定根拠は、公式サイトからの導線や Transfermarkt のソーシャルリンクを優先する。

## 手順

### 1. GCSから作業コピーを取得
```bash
// turbo
python scripts/pull_player_csv_from_gcs.py --team-id 42
```

チーム指定がない場合でも、実際に更新するチームを先に決めてから、そのチームだけ取得する。

### 2. 現状確認
```bash
// turbo
python scripts/analyze_missing_instagram.py --team-id 42
```

### 3. 検索と更新
ユーザーからチーム名の指定があればそのチームを優先し、なければリスト上位から順に処理する。

#### 検索クエリ戦略
1. **基本クエリ**: `"{選手名}" "{チーム名}" instagram`（英語）
2. **基本クエリ**: `"{選手名}" "{チーム名}" インスタグラム`（日本語）
3. **ハンドル発見できない場合**: `"{選手名}" instagram handle official`
4. **Transfermarkt経由**: `"{選手名}" Transfermarkt instagram handle`
5. **サイト指定検索**: `site:instagram.com "{選手名}" verified` （最終手段）

#### 公式アカウント判定ポイント
| 判定基準 | 信頼度 |
|----------|--------|
| mancity.com など公式サイトからのリンク | ◎ 高 |
| Transfermarkt のソーシャルメディア欄 | ◎ 高 |
| 認証バッジ（青バッジ）の明示 | △ 補助 |
| フォロワー数・投稿内容の整合性 | △ 参考 |

> [!IMPORTANT]
> Instagram の認証バッジは単独では本人確認の根拠になりません。
> 公式導線または信頼できる外部ソースで裏取りできる場合のみ採用してください。

#### スキップすべきケース
- **Rodri** のようにSNSを使わないことで有名な選手
- ユースアカデミー選手で公開アカウントが見つからない場合
- 検索結果が曖昧で複数候補がある場合

### 4. CSV更新
ローカル作業コピー `data/player_<team_id>.csv` の該当行の `instagram_url` カラムにURLを追記する。
対象行は `player_id` を基準に確認する。
フォーマット: `https://www.instagram.com/{handle}/`

更新後は GCS 正本へ反映する:

```bash
// turbo
python scripts/migrate_player_csv_to_gcs.py --team-id 42
```

別チームのCSVを新規作成した場合は、`settings/player_instagram.py` の `TEAM_CSV_FILES` にその `team_id` を追加しないと実行時に読み込まれない。

### 5. 結果確認
まずローカル作業コピーで Missing URLs が減っていることを確認する:

```bash
// turbo
python scripts/analyze_missing_instagram.py --team-id 42
```

更新したチームの直近 fixture を `public/calendar.html` から確認する例:

```bash
rg -n -C 8 "Manchester City|data-fixture-id" public/calendar.html
```

必要なら、対象 fixture を固定してデバッグ実行する:

```bash
TARGET_DATE="2026-02-27" TARGET_FIXTURE_ID="1379248" DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```

狙った試合が通常のデバッグ選定で外れる場合でも、`TARGET_FIXTURE_ID` を付ければその1試合だけを強制的に確認できる。

生成後は、対象HTMLにリンクが埋まっているかを確認する:

```bash
rg -n "instagram.com|player-instagram-link" public/reports/<generated_report>.html
```

#### 確認時の切り分け
- **アイコンが出ない**: まずCSV未設定を疑う。テンプレートは `player.instagram_url` がある場合だけ表示する。
- **CSVにはURLがあるのに出ない**: その選手がその試合の表示対象（スタメン/ベンチ）に入っていない可能性がある。
- **リンク切れに見える**: まずHTTP応答を確認する。Instagramはログイン壁でも `200` を返すことがあるため、`404` だけを明確なリンク切れとみなす。

簡易確認例:

```bash
curl -I https://www.instagram.com/<handle>/
```

表示確認まで含めて完了とする場合は、最低でも以下を満たすこと:
1. `analyze_missing_instagram.py` の Missing URLs が減っている
2. `TARGET_FIXTURE_ID` 付きデバッグ実行で対象カードのHTMLを生成できる
3. 生成HTML内に対象選手の `player-instagram-link` が入っている

### 6. コミット
更新内容を確認してから、対象チームのCSVのみをコミットする。

```bash
git diff -- data/player_42.csv
git add data/player_42.csv
git commit -m "docs: update instagram URLs for Arsenal players"
```

### 7. 報告
ユーザーには以下を簡潔に報告する:

1. 対象チーム名と `team_id`
2. 更新した選手数
3. スキップした選手と理由（曖昧・未発見・非公開など）
4. `python scripts/migrate_player_csv_to_gcs.py --team-id <team_id>` を実行したか
5. 表示確認（`TARGET_FIXTURE_ID` デバッグ）まで実施したか
