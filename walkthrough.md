# 2026-05-01 Issue #252 Walkthrough

## 解決状況

| 課題 | 方針 | 結果 |
|---|---|---|
| 選手詳細モーダルの顔写真が外枠と噛み合わず、二重枠のように見える | API-Footballのナマ画像は維持し、四角い外枠側の余白・背景・角丸を調整する | `.player-profile-modal-photo-frame` の内側paddingをなくし、画像が枠いっぱいに自然に収まるようにした |
| 画像を枠に合わせるための不自然な拡大・トリミングは避けたい | 画像自体の顔位置補正は行わず、`object-fit: contain` で元画像を保つ | `.player-profile-modal-photo` は四角枠内でナマ画像を保つ設定にした |
| 通常の選手カードも同じ問題があるか | 選手カードの構造を確認し、同じズレがある場合だけ揃える | 選手カードは外枠+内側画像の二重構造ではないため、今回は変更しない |

## 変更内容

- `public/assets/report_styles.css`
  - `.player-profile-modal-photo-frame`
    - `padding: 4px` を削除
    - `overflow: hidden` を追加
    - 背景を写真になじむ明るい背景へ変更
    - 角丸を内側画像と一致させる
  - `.player-profile-modal-photo`
    - `border-radius: inherit` に変更
    - `object-fit: contain` に変更
    - 背景を透明に変更
- `docs/03_components/report_rendering.md`
  - 選手詳細モーダルの写真は四角枠のまま、ナマ画像を不自然に加工しない方針を追記
- `implementation_plan.md` / `task.md`
  - #252 向けの計画と進捗へ更新

## 検証

- 既存生成済みレポートをローカル静的サーバで配信し、HTTP 200を確認した。
  - `http://localhost:8000/reports/2026-03-15_Liverpool_vs_Tottenham_20260316_033518.html`
- まだdebug-runは実行していない。
  - 理由: ユーザー確認で「問題ないと判断したらdebug-runで再確認」という流れになったため。

## 残課題

- ユーザーの見た目確認後、`DEBUG_MODE=True USE_MOCK_DATA=True` でdebug-runを実行する。
- debug-run後、生成HTMLを `file://` で開いてプロフィールモーダルを確認する。
