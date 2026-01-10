---
description: 選手のInstagram URLを検索してCSVを更新するワークフロー
---

# Player Instagram Fetch Workflow

このワークフローは、`data/player_instagram_50.csv` に登録されている選手のInstagram URLが未設定の場合に、Web検索を行ってURLを補完するための手順書です。

## 前提
- エージェント（あなた）が `search_web` ツールを使用して手動で検索を行います。
- 1回の実行で処理する人数は、レート制限やハルシネーション防止のため **5名〜10名** 程度に留めてください。

## 手順

### 1. 現状の確認
まず、Instagram URLが未設定の選手を確認します。以下のスクリプトを実行してください。

```bash
python scripts/analyze_missing_instagram.py
```

### 2. 検索と更新
出力されたリストの上から順に、以下の手順でURLを調査・更新してください。

1.  **検索**: 以下のクエリで検索を行います。
    - クエリ例: `"{選手名}" "{所属チーム名}" instagram` (所属チームが不明な場合は `football player` 等を追加)
    - ツール: `search_web`
2.  **検証**: 検索結果から、本人の公式アカウントであるか確認します。
    - 認証バッジ（青バッジ）に関する記述があるか。
    - フォロワー数や投稿内容がプロサッカー選手として妥当か。
    - ファンアカウント（fan page）ではないか注意する。
3.  **CSV更新**: `data/player_instagram_50.csv` を編集し、URLを追記します。
    - 該当行の `instagram_url` カラム（末尾）にURLを追加してください。
    - 見つからなかった場合は、無理に埋めずにスキップしてください。

### 3. 結果の確認
再度スクリプトを実行し、更新した選手がリストから消えている（または残り数が減っている）ことを確認します。

```bash
python scripts/analyze_missing_instagram.py
```

### 4. コミットとPR作成
変更が確認できたら、ブランチを作成してコミット・プッシュし、PRを作成（またはユーザーに報告）してください。

```bash
git checkout -b feature/update-instagram-urls
git add data/player_instagram_50.csv
git commit -m "docs: update player instagram urls"
# その後、PR作成等の指示に従う
```
