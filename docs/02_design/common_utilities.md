# 共通ユーティリティ設計

Issue #88 で整理された共通ユーティリティの設計を文書化する。

## DateTimeUtil

**ファイル**: [datetime_util.py](file:///Users/nagataryou/football-delay-watching/src/utils/datetime_util.py)

日付・時刻操作を一元化するユーティリティクラス。

### 提供メソッド

| メソッド | 用途 | 例 |
|---------|------|-----|
| `now_jst()` | 現在時刻(JST)取得 | `2026-01-02T07:19:00+09:00` |
| `parse_kickoff_jst(str)` | kickoff_jst文字列をパース | `"2025/12/27(土) 21:30 JST"` → UTC datetime |
| `to_utc(datetime)` | UTCに変換 | - |
| `to_jst(datetime)` | JSTに変換 | - |
| `format_jst_display(datetime)` | 表示用JST文字列 | `"2025/12/27(土) 21:30 JST"` |
| `format_utc_iso(datetime)` | ISO 8601 UTC形式 | `"2025-12-27T12:30:00Z"` |
| `format_filename_datetime(datetime)` | ファイル名用 | `"20251227_213000"` |
| `format_date_str(datetime)` | API用日付 | `"2025-12-27"` |
| `format_display_timestamp(datetime)` | 表示用タイムスタンプ | `"2025-12-27 21:30:00 JST"` |
| `get_weekday_ja(datetime)` | 日本語曜日 | `"土"` |
| `format_relative_date(iso_str)` | 相対日付 | `"3日前"` |

### 使用ガイドライン

1. **現在時刻の取得**: `datetime.now(jst)` の代わりに `DateTimeUtil.now_jst()` を使用
2. **日付フォーマット**: 直接 `strftime()` を呼ばず、専用メソッドを使用
3. **曜日変換**: インライン配列ではなく `get_weekday_ja()` を使用

---

## http_utils

**ファイル**: [http_utils.py](file:///Users/nagataryou/football-delay-watching/src/utils/http_utils.py)

キャッシュ不要な単純HTTPリクエスト用のユーティリティ。

### 提供関数

| 関数 | 用途 | 戻り値 |
|------|------|--------|
| `safe_get(url, headers, params, timeout)` | 安全なGET | `Response` or `None` |
| `safe_get_json(url, headers, params, timeout)` | JSON取得 | `dict` or `None` |
| `safe_get_bytes(url, headers, timeout)` | バイナリ取得 | `bytes` or `None` |

### エラーハンドリング

- タイムアウト: ログ警告 + `None` 返却
- 接続エラー: ログ警告 + `None` 返却
- HTTPエラー (4xx/5xx): ログ警告 + `None` 返却

### デフォルト設定

- タイムアウト: **10秒**

### 使い分け

| ケース | 推奨 |
|-------|------|
| キャッシュが必要 | `CachingHttpClient` |
| 単純なGET（画像、外部API） | `http_utils` |
| テスト時のモック | `HttpClient` 抽象クラス |

---

## 関連ドキュメント

- [キャッシュ設計](cache_design.md)
- [外部API連携設計](external_apis.md)
