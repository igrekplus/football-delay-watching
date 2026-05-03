# 選手プロフィール作成 Automation Prompt

このファイルは、Codex recurring automation に設定するための固定指示文である。
実行時に変わる `Last run` や実際の memory path は、automation 実行環境側の値を優先する。

## Automation Metadata

- Automation: 選手プロフィールの作成
- Automation ID: `automation`
- Automation memory: `$CODEX_HOME/automations/automation/memory.md`

## Prompt

プロジェクト football-delay-watching で、generate_player_profiles skill の手順に従って実行してください。

目的:
- 公開済みまたは生成可能な試合レポートを起点に、選手プロフィール未整備のチーム・選手を継続的に整備する。
- 対象選定は「新しい試合・新しい公開レポート」を優先し、古いfixtureを未整備数だけで選ばない。

入力:
- fixture-id: 任意。
  - 未指定の場合は、公開レポート・manifest・calendar.html・ローカルデータを確認し、日付降順で候補fixtureを探す。
- チーム名: 任意。
  - 未指定の場合は、対象fixtureの出場チームのうち、プロフィール未整備選手が多いチームを選ぶ。

対象選定ルール:
1. まず公開済みレポートまたは生成可能なカレンダー対象試合を、試合日または公開レポート日付の降順で確認する。
2. 直近候補の中から、管理対象CSVが存在し、プロフィール未整備選手がいるfixture/teamを選ぶ。
3. 未整備数が多くても、明確な理由なく古いレポートを優先しない。
4. 同程度の候補が複数ある場合は、以下の順で優先する。
   - 公開レポートが存在する
   - レポートHTMLが現行のプロフィールモーダル導線に対応している
   - 先発未整備選手が多い
   - 注目選手・若手・新加入・レポート上の見どころになりやすい選手がいる

必須要件:
1. generate_player_profiles をSSOTとして、下位skill research_player_profile_content を必要箇所で使う。
2. 1回あたり更新対象は最大5名。
3. skill上、fixture-id / チーム名が必須である。しかし、未指定の場合は実ファイル・公開レポート・カレンダーを確認し、上記の対象選定ルールで fixture とチームを決める。
4. 対象チーム内では、先発・注目度・未整備状況を踏まえて最大5名を選ぶ。
5. CSV更新、GCS push、standalone HTML生成、必要時debug-run、deployまで実行する。
6. check_missing_profiles.py がAPIキー・キャッシュ期限切れ・lineup欠落などで失敗した場合も即停止しない。
   - 公開済みレポートHTML、ローカルCSV、manifest、calendar.html から出場選手と未整備状況を照合できる場合は、それを根拠に継続する。
   - 継続した場合は、最終応答に「API確認が失敗したため代替確認した」ことを明記する。
7. レポートHTML側の導線確認では、data-player-profile-url の文字列確認だけで完了扱いにしない。
   - 現行レポートなら、モーダルJS・badge・fetch導線が存在することを確認する。
   - 古いDEBUGレポートなどでモーダルJSが無い場合は、debug-runで再生成するか、レポートHTMLへ互換導線を追加してからdeployする。
8. deploy後は公開URLで以下を確認する。
   - 対象レポートHTMLに data-player-profile-url がある。
   - 対象レポートHTMLにプロフィールモーダル/読み込み導線がある。
   - standalone profile URLで本文断片が取得できる。
   - 可能ならブラウザ表示上でもプロフィール導線が見える状態になっている。

最終応答に必ず含める:
- 選定した fixture-id とチーム名
- その fixture/team を選んだ理由
  - 特に、日付降順で確認したうえで選んだこと
- 更新した選手一覧（5名以内）
- 更新したチームが含まれる公開レポートURL
- 公開URL上で確認した事項
  - data-player-profile-url
  - モーダル/読み込み導線
  - standalone HTMLの本文断片
- APIやcheck scriptが失敗した場合は、その失敗内容と代替確認方法

禁止:
- skill手順と矛盾する独自省略
- fixture-id / チーム名が未指定であることだけを理由に停止すること
- 古いレポートを、未整備数が多いという理由だけで優先すること
- data-player-profile-url の文字列だけを見て、公開UI反映済みと判断すること
- ただし、公開レポート・カレンダー・ローカルデータから妥当な対象を特定できない場合は停止して理由を明記する。
