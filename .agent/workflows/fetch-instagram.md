---
description: 選手のInstagram URLを検索してCSVを更新するワークフロー
---

# Player Instagram Fetch Workflow

`data/player_instagram_<team_id>.csv` に登録されている選手のInstagram URLが未設定の場合に、Web検索を行ってURLを補完する手順書です。実行時の紐づけは `player_id` ベースです。

## 前提条件
- 1回の実行で処理する人数は **5〜10名** 程度に留める（レート制限・ハルシネーション防止）。
- 公式アカウントと確信が持てない場合は、誤情報を避けるため **追加しない**。

## 手順

### 1. 現状確認
```bash
// turbo
python scripts/analyze_missing_instagram.py
```

別チームを確認する場合:

```bash
// turbo
python scripts/analyze_missing_instagram.py --team-id 42
```

### 2. 検索と更新
ユーザーからチーム名の指定があればそのチームを優先し、なければリスト上位から順に処理する。

#### 検索クエリ戦略
1. **基本クエリ**: `"{選手名}" "{チーム名}" instagram`
2. **ハンドル発見できない場合**: `"{選手名}" instagram handle official`
3. **Transfermarkt経由**: `"{選手名}" Transfermarkt instagram handle`
4. **サイト指定検索**: `site:instagram.com "{選手名}" verified` （最終手段）

#### 公式アカウント判定ポイント
| 判定基準 | 信頼度 |
|----------|--------|
| mancity.com など公式サイトからのリンク | ◎ 高 |
| Transfermarkt のソーシャルメディア欄 | ◎ 高 |
| 認証バッジ（青バッジ）の明示 | ○ 中 |
| フォロワー数・投稿内容の整合性 | △ 参考 |

#### スキップすべきケース
- **Rodri** のようにSNSを使わないことで有名な選手
- ユースアカデミー選手で公開アカウントが見つからない場合
- 検索結果が曖昧で複数候補がある場合

### 3. CSV更新
`data/player_instagram_50.csv` の該当行の `instagram_url` カラムにURLを追記。対象行は `player_id` を基準に確認する。
フォーマット: `https://www.instagram.com/{handle}/`

別チームのCSVを新規作成した場合は、`settings/player_instagram.py` の `TEAM_CSV_FILES` にその `team_id` を追加しないと実行時に読み込まれない。

### 4. 結果確認
```bash
// turbo
python scripts/analyze_missing_instagram.py
```
更新した選手数だけ Missing URLs が減っていることを確認。

必要なら、実際の試合カード上で表示確認する:

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

### 5. コミット
```bash
git add data/player_instagram_50.csv
git commit -m "docs: update instagram URLs for {チーム名} players"
```
