---
description: 選手のInstagram URLを検索してCSVを更新するワークフロー
---

# Player Instagram Fetch Workflow

`data/player_instagram_50.csv` に登録されている選手のInstagram URLが未設定の場合に、Web検索を行ってURLを補完する手順書です。

## 前提条件
- 1回の実行で処理する人数は **5〜10名** 程度に留める（レート制限・ハルシネーション防止）。
- 公式アカウントと確信が持てない場合は、誤情報を避けるため **追加しない**。

## 手順

### 1. 現状確認
```bash
// turbo
python scripts/analyze_missing_instagram.py
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
`data/player_instagram_50.csv` の該当行の `instagram_url` カラムにURLを追記。
フォーマット: `https://www.instagram.com/{handle}/`

### 4. 結果確認
```bash
// turbo
python scripts/analyze_missing_instagram.py
```
更新した選手数だけ Missing URLs が減っていることを確認。

### 5. コミット
```bash
git add data/player_instagram_50.csv
git commit -m "docs: update instagram URLs for {チーム名} players"
```
