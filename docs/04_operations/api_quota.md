# APIクオータ＆レート制限まとめ (2025-12-14版)

このプロジェクトで利用する外部APIの料金・クオータ・レート制限をまとめる。各サービスは頻繁に変更されるため、定期的に公式ドキュメントを確認すること。

## 1. API-Football (API-Sports / RapidAPI経由可)
- **日次リクエスト上限**（直接契約プラン）  
  - Free: 100 req/day  
  - Pro: 7,500 req/day  
  - Ultra: 75,000 req/day  
  - Mega: 150,000 req/day citeturn0search0
- **分間レートリミット**  
  - Free: 10 req/min  
  - Pro: 300 req/min  
  - Ultra: 450 req/min  
  - Mega: 900 req/min  
  - Custom: 1,200 req/min (〜1.5M req/day) citeturn0search1
- **超過時の挙動**: クオータ超過時は課金されず 429 で打ち止め。citeturn0search0
- **課金モデル**: 月額サブスク（Free/Pro/Ultra/Mega）。RapidAPI経由の場合は各プランのクオータ・課金設定に従う。

> [!CAUTION]
> **シーズンアクセス制限**
> Free プランは**最新シーズンにアクセスできません**。
> 2026年1月時点では、Free プランは 2022〜2024 シーズンのみ利用可能で、2025-26 シーズンのデータ取得には **Pro プラン以上が必須**です。

## 2. YouTube Data API v3
- **日次クォータ**: 10,000 units/日（無料）
- **search.list**: 100 units/リクエスト（maxResultsに関わらず固定）
- **videos.list**: 1 unit/リクエスト（再生数等の詳細取得用、現在未使用）
- **channels.list**: 1 unit/リクエスト
- **本プロジェクトでの使用**:
  - 試合前動画検索（記者会見、因縁、戦術、選手紹介、練習風景）
  - 各カテゴリ50件取得 → post-filterでフィルタリング
  - **予想消費: 約1,300 units/試合**（13クエリ × 100ユニット）
- **実装**: `src/youtube_service.py`、チャンネル設定: `settings/channels.py`

> [!IMPORTANT]
> **YouTube動画検索の対象制限 (Issue #163)**
> 動画検索はS/Aランク（およびAbsolute）の試合のみに実行されます。
> Bランク以下（フィラー枠）の試合では動画検索がスキップされ、レポートに動画セクションが表示されません。

### クォータ確認方法

> ⚠️ **注意**: APIレスポンスにはクォータ消費量は含まれていません。

| 方法 | 説明 |
|------|------|
| **GCP Console** | [YouTube API Quotas](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas) で確認 |
| **GCP Metrics** | [API Metrics Dashboard](https://console.cloud.google.com/apis/api/youtube.googleapis.com/metrics) でリアルタイム確認 |
| **ローカル概算** | `YouTubeService.api_call_count × 100` で概算可能 |
| **ログ確認** | `YouTube API: '...' -> N results (API calls: X)` で呼び出し回数を確認 |

## 3. Google Gemini API (Generative AI)
- 代表的モデルの従量課金（USD / 1M tokens）。citeturn1search0  
  - **Gemini 2.5 Flash**: Input $0.30、Output $2.50（無料ティアあり、同一エンドポイント）。  
  - **Gemini 2.5 Flash-Lite**: Input $0.10、Output $0.40。  
  - **Grounding with Google Search**: 500 RPD まで無料（Flash/Flash-Liteで共有）、1,500 RPD まで無料枠、その後 $35 / 1,000 grounded prompts。  
  - **バッチ**: Flash系は入力 $0.15 / 出力 $1.25（Flash）、$0.05 / $0.20（Flash-Lite）。  
- **無料枠の範囲**:
  - 上記の「無料ティア／RPD無料枠」は **Gemini API（Google AI Studio / Gemini Developer API）側の無料枠**。  
  - **GCPのFree Trial/Free Tierとは別**なので混同しないこと。Vertex AI経由で使う場合はVertex AI側の料金・クォータに従う。  
- **レート制限**: RPM/TPM は契約・ティアで異なる。無料ティアは低め、Vertex/Enterprise で拡張可能。  
- **請求計算の目安**: 1M tokens ≒ 英文75万語。要実行前のトークン見積もり。
- **本プロジェクトで使用中のモデル**: `gemini-pro-latest`（ニュース要約・レポート生成で利用）。コード参照: `src/news_service.py`。

## 4. Gmail API (Google Workspace)
- **送信上限（Workspace ユーザー）**: 2,000通/日、総受信者10,000/日、1メールあたり2,000受信者（外部は500まで）、Gmail API 経由は500受信者。citeturn3search1
- **無料 Gmail アカウント**: 1日500通、1メール500受信者が目安。citeturn3search0
- **超過時の挙動**: 24時間以上の送信一時停止。  
- **OAuth テストユーザー枠**: External アプリはテストユーザー数に制約があるため、運用前に本番公開 or 内部（Internal）設定へ切替が必要。

## 5. このプロジェクトでの想定消費目安

1日あたり対象リーグ: EPL/CL、最大3試合（`Config.MATCH_LIMIT`）。

| API | 1試合あたり | 3試合/日 | 上限 | 消費率※ |
|-----|-----------|---------|------|---------|
| **API-Football** | ~25 req | ~75 req | 7,500/日 (Pro) | ✅ 1% |
| **YouTube Data API** | ~13クエリ=1,300 units | ~3,900 units | 10,000/日 | ⚠️ 39% |
| **Gemini** | ~20k tokens | ~60k tokens | 無料枠あり | ✅ |
| **Gmail** | 1通/日 | 1通/日 | 500/日 | ✅ 0.2% |

※ 消費率 = 3試合/日の消費量 ÷ 日次上限 × 100。低いほど余裕あり。

### 詳細

- **API-Football**: `fixtures`, `lineups`, `players`(22人分), `statistics`, `injuries` など。選手データはGCSキャッシュで削減可能。
- **YouTube Data API**: 現状20クエリ/試合 → 改善後13クエリ/試合（Issue #27対応後）。search.list=100units/req。
- **GCSキャッシュ効果**: 選手データはGCSに永続キャッシュ。2回目以降はAPI消費ゼロ。
- **Gemini**: ニュース要約で使用。トークン消費は軽量。
- **Gmail**: レポート送信1通/日。上限に余裕あり。

> ⚠️ **注意**: YouTube APIはクォータ消費が激しい。デバッグ+本番で枯渇リスクあり。キャッシュ（1週間TTL）を活用すること。

## 6. 運用チェックリスト
- 429/402/403 が出た場合:  
  - API-Football: 日次 or 分間上限を確認（レスポンスヘッダ `x-ratelimit-requests-limit` 等）。  
  - Gemini: Cloud Billing の使用量、あるいはレスポンスエラーで rate limit 情報を確認。  
  - Gmail: 管理コンソールで送信制限違反/一時停止を確認。  
- GitHub Actions での実行前に、前日消費量が上限の80%を超えていたら slack/email でアラート（要別途実装）。  
- 料金改定は頻繁。月初に公式価格ページの更新日を確認し、本ファイルの見直しを行うこと。

## 6.5. ヘルスチェックスクリプト

各APIのクォータ・ステータスを確認するスクリプト:

| スクリプト | 対象API | 確認内容 |
|-----------|---------|----------|
| `check_football_api.py` | API-Football | 残りリクエスト数、日次上限 |
| `check_youtube.py` | YouTube Data API | クォータ消費状況、キャッシュ状態 |
| `check_gemini.py` | Gemini API | API接続確認 |
| `check_gmail.py` | Gmail API | OAuth認証状態、送信可否 |
| `check_gcs_cache.py` | GCS Cache | キャッシュカバレッジ確認 |

### 実行方法

```bash
# 全API一括確認
python3 healthcheck/check_football_api.py
python3 healthcheck/check_youtube.py
python3 healthcheck/check_gemini.py
python3 healthcheck/check_gmail.py

# GCSキャッシュ確認
python3 healthcheck/check_gcs_cache.py
```

### AI向け指示
> ユーザーが「クォータ確認して」「API確認して」と言った場合、上記スクリプトを順番に実行して結果を報告すること。

## 7. キャッシュウォーミング
試合がない平日にAPI消費を活用し、上位チームの選手データを事前にGCSにキャッシュする機能。

- **目的**: 週末の試合レポート時にキャッシュHITさせ、API消費を削減
- **対象**: EPL上位10チーム + CL上位13チーム（`config.EPL_CACHE_TEAMS`, `config.CL_CACHE_TEAMS`）
- **制御**: `CACHE_WARMING_ENABLED` 環境変数（デフォルト: False）
  - 週初め（月〜木）に手動でTrueに設定
  - 週末（金〜日）はFalseのまま運用
- **キャッシュ確認**: `python3 healthcheck/check_gcs_cache.py`

## 8. 日次クォータリフレッシュタイミング

各APIのクォータリセット時刻（日本時間）:

| API | リセット時刻（JST） | リセット時刻（UTC） | 備考 |
|-----|------------------|------------------|------|
| **API-Football** | 09:00 JST | 00:00 UTC | 毎日UTC 0時にリセット |
| **YouTube Data API** | 17:00 JST | 08:00 UTC | 太平洋時間 0:00（PDT/PST）にリセット |
| **Gemini API** | 17:00 JST | 08:00 UTC | 太平洋時間 0:00にリセット |
| **Gmail API** | 17:00 JST | 08:00 UTC | 太平洋時間 0:00にリセット |

> **Note**: 太平洋時間は夏時間（PDT: UTC-7）と冬時間（PST: UTC-8）で1時間ずれる。
> - 夏時間（3月〜11月）: 16:00 JST
> - 冬時間（11月〜3月）: 17:00 JST

### 運用上の注意
- **デバッグ実行**: クォータ消費が多い場合は翌日のリセット後に実行
- **YouTube API**: 特にクォータ消費が激しい（100ユニット/リクエスト）ため、17:00 JST以降の実行を推奨
- **GitHub Actions**: 毎日 7:00 JST に実行するため、YouTube以外は余裕あり

---
最終更新: 2025-12-24
