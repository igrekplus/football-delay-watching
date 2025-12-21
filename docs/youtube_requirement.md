# YouTube動画取得ロジック仕様書

## 概要

試合レポートに含めるYouTube動画を取得するロジック。
キックオフ前の動画のみを対象とし、試合結果のネタバレを防ぐ。

## 動画カテゴリ

### カテゴリ1: 過去対戦ハイライト (`historic`)
過去の同一カード試合のハイライト動画。

| 項目 | 値 |
|------|-----|
| 検索クエリ | `{home} vs {away} highlights` |
| 期間 | キックオフ2年前〜キックオフ |
| チャンネル | リーグ公式, U-NEXT, WOWOW |
| 取得件数 | 最大3件 |

### カテゴリ2: 記者会見 (`press_conference`)
試合前の監督・選手会見。

| 項目 | 値 |
|------|-----|
| 検索クエリ | `{team} press conference` |
| 期間 | キックオフ48時間前〜キックオフ |
| チャンネル | チーム公式 |
| 取得件数 | 最大2件/チーム |

### カテゴリ3: 戦術分析 (`tactical`)
チーム・選手の戦術解説動画。

| 項目 | 値 |
|------|-----|
| 検索クエリ | `{team} tactics analysis` |
| 期間 | キックオフ6ヶ月前〜キックオフ |
| チャンネル | Tifo, レオザ, クラック, Athletic FC |
| 取得件数 | 最大3件 |

### カテゴリ4: 練習風景 (`training`)
試合前の練習・雰囲気動画。

| 項目 | 値 |
|------|-----|
| 検索クエリ | `{team} training` |
| 期間 | キックオフ48時間前〜キックオフ |
| チャンネル | チーム公式 |
| 取得件数 | 最大2件 |

### カテゴリ5: 選手紹介 (`player_highlight`)
注目選手のプレー集・紹介動画。

| 項目 | 値 |
|------|-----|
| 検索クエリ | `{player} skills highlights` |
| 期間 | キックオフ6ヶ月前〜キックオフ |
| チャンネル | リーグ公式, U-NEXT |
| 取得件数 | 最大3件 |

---

## パラメータ一覧

| パラメータ名 | デフォルト値 | 説明 |
|-------------|-------------|------|
| `MAX_RESULTS_PER_CATEGORY` | 3 | カテゴリ毎の最大取得数 |
| `HISTORIC_SEARCH_DAYS` | 730 | 過去ハイライト検索期間（日） |
| `RECENT_SEARCH_HOURS` | 48 | 公式動画検索期間（時間） |
| `TACTICAL_SEARCH_DAYS` | 180 | 戦術動画検索期間（日） |

---

## タイムゾーン処理

1. `kickoff_jst`（例: `2025/12/21 00:00 JST`）をパース
2. JSTとしてタイムゾーン設定
3. UTCに変換してYouTube APIに渡す

```python
jst = pytz.timezone('Asia/Tokyo')
kickoff_naive = datetime.strptime(kickoff_jst, "%Y/%m/%d %H:%M")
kickoff_utc = jst.localize(kickoff_naive).astimezone(pytz.UTC)
```

---

## 重複排除

動画IDで重複を排除し、ユニークな動画のみを返却。
