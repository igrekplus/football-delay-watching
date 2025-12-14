# API-Football 利用詳細（パラメータと参照レスポンス項目）

このドキュメントは実装が実際に呼び出しているエンドポイントの**リクエストパラメータ**と、コードが参照している**レスポンス項目**を一覧化したもの。キャッシュ方針やレート制御は `docs/system_design.md` を参照。

## /fixtures (日付指定)
- 用途: 対象日の試合一覧を取得し、試合ID/キックオフ/会場/レフェリーを取得。
- メソッド: GET  
- パラメータ: `date` (YYYY-MM-DD, JST基準で前日を設定), `league` (39=EPL, 2=CL), `season` (月>=6なら年、以外は年-1)  
- 参照しているレスポンス項目:
  - `fixture.id`
  - `fixture.date`
  - `fixture.status.short`
  - `fixture.venue.name`, `fixture.venue.city`
  - `fixture.referee`
  - `teams.home.name`, `teams.away.name`

## /fixtures (id指定)
- 用途: チームIDや追加メタ情報を取得（フォーム・H2H 用の team id）。
- パラメータ: `id` (fixture id)
- 参照項目:
  - `teams.home.id`, `teams.away.id`

## /fixtures/lineups
- 用途: スタメン・ベンチ・フォーメーション、選手ID取得（国籍取得のため）。
- パラメータ: `fixture` (fixture id)
- 参照項目:
  - `team.name`
  - `formation`
  - `startXI[].player.name`, `startXI[].player.id`
  - `substitutes[].player.name`, `substitutes[].player.id`

## /injuries
- 用途: 負傷者・出場停止情報の一覧。
- パラメータ: `fixture` (fixture id)
- 参照項目:
  - `player.name`
  - `team.name`
  - `player.reason`

## /teams/statistics
- 用途: 直近フォーム（W/D/L文字列）。
- パラメータ: `team` (team id), `season`, `league` (現状 39 固定)
- 参照項目:
  - `form`（例 "WDWLW"）

## /players
- 用途: 選手の国籍を取得し、国旗表示に利用。
- パラメータ: `id` (player id), `season`
- 参照項目:
  - `player.name`
  - `player.nationality`

## /fixtures/headtohead
- 用途: 直近対戦成績を集計（勝ち/引分/負けのみ利用）。
- パラメータ: `h2h` (`{home_id}-{away_id}`), `last` (例 5)
- 参照項目:
  - `goals.home`, `goals.away`
  - `teams.home.id`（勝敗判定に使用）
