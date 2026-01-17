# Issue Draft: 軽量レポート検証ワークフロー (report-check-html) の作成

## 概要
開発中の変更を素早く検証するため、ブラウザを開かずにコマンドラインベースでHTMLレポートの内容を確認できる軽量ワークフロー `report-check-html` を作成する。
現在は `/debug-run` でブラウザを使って確認しているが、単純なテキストの有無（例：インタビュー記事が含まれているか、特定の選手名があるか）の確認には時間がかかる。

## 目的
- **高速化**: ブラウザ起動のオーバーヘッドなしで検証サイクルを回す。
- **自動化**: `grep` 等を使って検証をスクリプト化しやすくする。 CI/CDへの組み込みも見据える。

## 実装内容

### 1. ワークフロー定義 (`.agent/workflows/report-check-html.md`)
以下のステップを実行するワークフローを定義する：
1. **レポート生成**: `USE_MOCK_DATA=True` (または `DEBUG_MODE=True`) で `main.py` を実行し、ローカルにHTMLを生成。
2. **検証**: 生成されたHTMLファイル（`public/reports/index.html` 等）に対して `grep` コマンドを実行し、キーワードが含まれているかチェックする。

### 2. 使用例
```bash
# ワークフロー実行
/report-check-html target="Manchester City" keyword="Guardiola"

# 内部コマンドイメージ
python main.py
grep -q "Guardiola" public/reports/latest.html && echo "✅ Found" || echo "❌ Not Found"
```

### 3. オプション要件
- 検証対象の文字列を引数で渡せるようにする。
- 成功/失敗を明確に終了コードまたはメッセージで出力する。

## タスク
- [ ] `.agent/workflows/report-check-html.md` の作成
- [ ] テスト実行による動作確認
