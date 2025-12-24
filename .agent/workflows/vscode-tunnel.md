# VS Code Remote Tunnel アクセスガイド

## 🔗 スマホ/iPad からのアクセス方法

ブラウザで以下のURLにアクセス:
```
https://vscode.dev/tunnel/nagataryou-macbook
```

同じGitHubアカウントでログインしてください。

---

## 🖥️ Mac側の操作

### トンネル起動（手動）
```bash
code tunnel --name nagataryou-macbook --accept-server-license-terms
```

### トンネル状態確認
```bash
code tunnel status
```

### トンネル停止
```bash
code tunnel kill
```

---

## 🔋 スリープ防止設定

### 方法1: caffeinate コマンド（一時的）
```bash
# トンネルと一緒に起動
caffeinate -i code tunnel --name nagataryou-macbook
```

### 方法2: システム設定（恒久的）
1. システム設定 → バッテリー → オプション
2. 「電源アダプタ接続時にスリープさせない」を有効化

---

## 🚀 サービスとして自動起動（オプション）

```bash
# サービスとしてインストール
code tunnel service install

# サービス削除
code tunnel service uninstall
```

---

## 📱 Codex CLI の使い方（スマホから）

1. vscode.dev でフォルダを開く
2. ターミナルを開く（☰ → Terminal → New Terminal）
3. `codex` コマンドを実行
