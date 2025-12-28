# raw取得のLLM指示（Playwright MCP）

本書は **Playwright MCP を用いた raw 取得**の指示仕様です。最大の特徴は、**人間からの入力が「ふわっとした依頼」でも成立すること**です。URL探索をLLM側が担います。

---

# 1. 概要・前提
## 1.1 ゴール
- URL単位で、**本文テキスト（画像URL含む）**を抽出して保存する。
- 取得の経緯・判断をログ化し、再現可能にする。

## 1.2 前提
- URL指定は前提とせず、LLMが検索してURL候補を作る。
- rawは後段の structured を**検証可能**にするための一次情報として保存する。
- 初期保存は `knowledge/raw/`、最終的にはGCSに移行する前提。

## 1.3 用語定義（LLMがどう値を決めるか）
### 1.3.1 entity_type
**意味**：対象の分類キー。  
**決め方**：入力文中の対象名と文脈から推定し、迷ったらユーザーに確認する。

| entity_type | 対象 | 判断のヒント |
| --- | --- | --- |
| club | クラブ | 「FC」「City」「United」「クラブ名」等 |
| player | 選手 | 人名、選手名単体 |
| manager | 監督 | 「監督」「manager」等 |
| national | 代表チーム | 「日本代表」「代表」等 |
| stadium | スタジアム | 「スタジアム」「Stadium」等 |
| competition | 大会 | 「リーグ」「CL」「大会名」等 |
| city | 都市 | 都市名単体 |
| region | 地域 | 地域名・州名 |

### 1.3.2 entity_key
**意味**：対象名を正規化したキー。  
**決め方**：対象名を小文字化し、空白・記号をアンダースコアに置換する。

例：
- "Manchester City" → `manchester_city`
- "Erling Haaland" → `earling_haaland`

### 1.3.3 entity_id
**意味**：`{entity_type}-{entity_key}` 形式の正規化ID。  
**決め方**：entity_type と entity_key を連結する。  
例：`player` + `earling_haaland` → `player-earling_haaland`

### 1.3.4 url_id
**意味**：URL単位の識別子。  
**決め方**：`url_id = sha1(normalize_url(source_url))`

### 1.3.5 raw_id
**意味**：取得履歴の識別子（同一URLの複数回取得を区別）。  
**決め方**：`raw_id = url_id + "_" + YYYYMMDDHHMMSS`

### 1.3.6 text.txt / text_before_transfer.txt
- **text.txt**：本文を日本語に翻訳したもの（自然な日本語寄り）。
- **text_before_transfer.txt**：原文そのまま。

---

# 2. 実行プロセス_検索準備
## 2.1 入力の受領
- 人間の依頼文を受け取る（URLは渡されない）。

## 2.2 対象の同定
- entity_type / entity_key / entity_id を推定する。

## 2.3 検索計画の作成
- **検索実行前に計画をユーザーへ提示し、同意を得る。**

### 2.3.1 検索計画テンプレ（端的版）
```
対象: {entity_type} / {entity_id}
テーマ: {調査テーマ}
クエリ（日本語×3）:
1) ...
2) ...
3) ...
クエリ（英語×3）:
1) ...
2) ...
3) ...
想定取得件数: 1クエリあたり10件程度
有用判定: 暫定ルールに基づき選別
```

### 2.3.1 検索クエリの作成ルール
- 関連語を**妄想して広げる**。
- **3件**（日本語3件 + 英語3件 = 合計6件）。
- **1クエリあたり20件程度**のURL候補を確保する（チューニング値）。

### 2.3.2 クエリ例（club history）
- "マンチェスター・シティ 歴史 1990"
- "マンチェスター・シティ 町の評判"
- "マンチェスター・シティ ダービー"
- "Manchester City history 1990"
- "Manchester City city reputation"
- "Manchester derby history"

---

# 3. 実行プロセス_検索実行
## 3.1 検索
- **Antigravity**：内蔵ブラウザツールを使用する。
- **Codex**：Playwright MCPで `google.co.jp` を使用して検索。
- クエリごとに上位10件程度のURL候補を取得。

## 3.2 候補URLの調査
- **【厳禁】検索エンジンの「AI要約」だけで判断して、URL指名取得にショートカットすること。**
- 必ずツールを使って**各クエリ上位10件のURLリスト**を取得し、それをログに出力すること。
- そのリストを見て初めて「どれが有用か」を判定し、選定プロセスに進むこと。

### 3.2.1 有用判定（チューニング値）
※ 以下は **暫定のチューニング値**。運用で調整する。
- **一次情報性**：公式・大手メディア・百科事典を優先（socialは下位）
- **本文の有無**：本文が短すぎる/断片しかない場合は除外
- **テーマ一致**：入力テーマと直接関係する記述が本文に含まれる
- **日付の有無**：可能なら公開日が明示されているものを優先
- **重複**：同一URLや同一内容は除外（source_url 重複は除外）

## 3.3 アクセス制限・403対策（学び）
- 公式サイトやWikipediaなど **防御が堅そうなサイトは最初からブラウザ操作で取得**する。
- API系の高速取得で403が出た場合は **即座にブラウザ操作へ切り替える**。
- 取得手段の切替は **ログに必ず記録**する（ツール名・理由）。

---

# 4. 実行プロセス_結果出力
## 4.1 保存パス
`knowledge/raw/{entity_type}/{entity_key}/{url_id}/{raw_id}/`

### 4.1.1 パス要素の意味
| パス要素 | 意味 | 例 |
| --- | --- | --- |
| entity_type | 分類キー | player |
| entity_key | 小文字 + 記号/空白→アンダースコア | earling_haaland |
| url_id | URL単位の識別子 | a1b2c3d4 |
| raw_id | 取得履歴の識別子 | a1b2c3d4_20251227T021500Z |

## 4.2 URL遷移
1. URLへ遷移
2. Cookie同意・ポップアップを処理

## 4.3 クローリング（本文抽出）
### 4.3.1 クローリング指示（重要）
- **本文領域の特定を最優先**する（`article` / `main` / 見出し+段落の連続ブロック）。
- 広告・サイドバー・関連記事リンクは除外する。
- 「Read more」「全文表示」ボタンがあれば展開する。
- ページ内の画像URLを本文中に `[IMAGE] {url} (alt=...)` 形式で挿入する。

### 4.3.2 抽出の難易度が高いケース
- 無限スクロール
- DOMが分割されている（本文が複数ブロックに分散）
- ペイウォールやログイン要求

### 4.3.3 高難易度ケースの対応手順（fallback）
**A. 無限スクロール**
- 3回までスクロールし、本文量が増えるか確認する。
- 増えない場合は「初期ロード分のみ取得」として notes に記録する。
- それ以上の深追いはしない。

**B. DOMが分割されている**
- `article` / `main` がない場合は「見出し + 段落の連続ブロック」を結合する。
- 見出し直下の段落を優先して抽出する。
- 断片しか取れない場合は notes に「本文分割で断片取得」と記録する。

**C. ペイウォール / ログイン要求**
- 取得不能として終了する。
- **text.txt を空**で保存し、meta.json の notes に理由を書く。
 
**D. 403 / アクセス制限**
- API系取得で403なら **ブラウザ操作へ切替**する。
- 切替後の結果と理由を notes とログに記録する。

## 4.4 保存
1. **text_before_transfer.txt** に原文保存
2. **text.txt** に日本語訳を保存（自然な日本語寄り）
3. **meta.json** を作成し保存

## 4.5 meta.json（項目定義 + 出力例）
| 項目 | 説明 | 例 |
| --- | --- | --- |
| entity_id | 正規化ID（`{entity_type}-{entity_key}`） | player-earling_haaland |
| raw_id | 取得単位の識別子（履歴用） | a1b2c3d4_20251227T021500Z |
| url_id | URL単位の識別子 | a1b2c3d4 |
| source_url | 取得元URL | https://example.com/interview1 |
| fetched_at | 取得時刻（ISO） | 2025-12-27T02:15:00Z |
| status_code | HTTPステータス（取得できない場合はnull） | 200 |
| content_type | text/html など（取得できない場合はnull） | text/html |
| title | ページタイトル（取得できる場合のみ） | Interview with Haaland |
| published_at | 公開日（取得できる場合のみ） | 2023-03-10 |
| extract_method | "playwright_mcp" 固定 | playwright_mcp |
| query_profile | 任意（入力がある場合のみ） | player_background |
| search_queries | 使用した検索クエリ（配列） | ["Haaland interview", "ハーランド インタビュー"] |
| source_type | 推定ソース種別（official/media/social） | media |
| notes | 取得時の注意点（ポップアップ処理・失敗理由など） | Cookie同意処理あり |

---

# 5. 実行プロセス_実行レポート格納
## 5.1 ログ保存先
- `logs/raw_acquisition/YYYY-MM-DD_HHMMSS_[ENTITY_ID].md`

## 5.2 ログ内容（最低限）
- 入力指示（人間の依頼文）
- entity_type / entity_key / entity_id の推定結果
- 検索計画（クエリ一覧）
- 検索実行ログ（取得件数、候補URL一覧）
- クエリごとの **候補URL数 / 採用数**
- **採用/除外理由**（有用判定の要点）
- **使用ツール**（API/ブラウザ）と切替理由
- 有用判定の結果（採用/除外と理由）
- 実際に取得したURL一覧
※ ログは**日本語で出力**する。

---

# 6. 禁止事項
- 取得した本文の要約・加工・再解釈
- 取得できなかった部分の補完
- LLM知識による追記
- **【厳禁】検索結果の要約（Summary）のみを見て、候補URL一覧の取得・ログ化プロセスをスキップすること。**（必ずツールでURLリストを取得せよ）

---

# 7. 補足・今後に向けて
## 7.1 normalize_url の手順（url_id 生成）
1. URLをパースする（scheme/host/path/query/fragment）。
2. scheme と host は小文字化する。
3. デフォルトポート（80/443）は除去する。
4. fragment（#以降）は除去する。
5. path の連続スラッシュを1つに統一し、dot-segment（./..）を解消する。
6. 末尾のスラッシュは **ルート以外**は除去する。
7. query は次の順で正規化する。
   - `utm_*`, `gclid`, `fbclid` などのトラッキング系パラメータを除去
   - 残ったパラメータをキー名で昇順ソート
   - 同一キーは値で昇順ソート
8. 正規化した要素を再結合して normalize_url とする。

## 7.2 運用前提
- 将来的には raw を GCS に移行する前提（現在は `knowledge/raw/` を使用）。
- raw と structured の紐づけは **raw_id** を使用する。
