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

## 2. Google Custom Search API
- **Custom Search JSON API**  
  - 100クエリ/日 無料。  
  - 追加: $5 / 1000クエリ（最大 10k クエリ/日）。 citeturn0search3
- **Site Restricted JSON API**  
  - 10サイト以下の限定検索用。$5 / 1000クエリで**日次上限なし**。  
  - 2025-01-08 以降このエンドポイントは停止し、Vertex AI Search への移行が必須。citeturn5search0
- **課金単位**: 1リクエスト=1クエリ。  
- **モニタリング**: Cloud Console の API ダッシュボードで消費確認。

## 3. Google Gemini API (Generative AI)
- 代表的モデルの従量課金（USD / 1M tokens）。citeturn1search0  
  - **Gemini 2.5 Flash**: Input $0.30、Output $2.50（無料ティアあり、同一エンドポイント）。  
  - **Gemini 2.5 Flash-Lite**: Input $0.10、Output $0.40。  
  - **Grounding with Google Search**: 500 RPD まで無料（Flash/Flash-Liteで共有）、1,500 RPD まで無料枠、その後 $35 / 1,000 grounded prompts。  
  - **バッチ**: Flash系は入力 $0.15 / 出力 $1.25（Flash）、$0.05 / $0.20（Flash-Lite）。  
- **レート制限**: RPM/TPM は契約・ティアで異なる。無料ティアは低め、Vertex/Enterprise で拡張可能。  
- **請求計算の目安**: 1M tokens ≒ 英文75万語。要実行前のトークン見積もり。
- **本プロジェクトで使用中のモデル**: `gemini-pro-latest`（ニュース要約・レポート生成で利用）。コード参照: `src/news_service.py`。

## 4. Gmail API (Google Workspace)
- **送信上限（Workspace ユーザー）**: 2,000通/日、総受信者10,000/日、1メールあたり2,000受信者（外部は500まで）、Gmail API 経由は500受信者。citeturn3search1
- **無料 Gmail アカウント**: 1日500通、1メール500受信者が目安。citeturn3search0
- **超過時の挙動**: 24時間以上の送信一時停止。  
- **OAuth テストユーザー枠**: External アプリはテストユーザー数に制約があるため、運用前に本番公開 or 内部（Internal）設定へ切替が必要。

## 5. このプロジェクトでの想定消費目安
- 1日あたり対象リーグ: EPL/CL、最大3試合（`Config.MATCH_LIMIT`）。  
- **API-Football**: 1試合で `fixtures`, `lineups`, `statistics`, `events` など10〜15リクエスト想定 → 最大 ~50 req/day。Free枠(100/day)でも足りるが週末ピーク時にバッファが小さいため Pro 推奨。  
- **Custom Search**: ニュース10件取得×検索1回程度 → 10 req/day。Free枠(100/day)で十分。  
- **Gemini**: ニュース10本要約＋フォーメーション説明で ~40k–80k tokens/日程度。無料ティアの rate limit にかかる可能性があるため有料ティアを検討。  
- **Gmail**: レポート送信 1通/日。Workspace/無料どちらでも上限に余裕あり。

## 6. 運用チェックリスト
- 429/402/403 が出た場合:  
  - API-Football: 日次 or 分間上限を確認（レスポンスヘッダ `x-ratelimit-requests-limit` 等）。  
  - Custom Search: Cloud Console で日次使用量確認。10k/day 上限に達していないか。  
  - Gemini: Cloud Billing の使用量、あるいはレスポンスエラーで rate limit 情報を確認。  
  - Gmail: 管理コンソールで送信制限違反/一時停止を確認。  
- GitHub Actions での実行前に、前日消費量が上限の80%を超えていたら slack/email でアラート（要別途実装）。  
- 料金改定は頻繁。月初に公式価格ページの更新日を確認し、本ファイルの見直しを行うこと。

---
最終更新: 2025-12-14
