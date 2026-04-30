# niconico_inspire_comment_local

指定したアプリケーションの画面を **ローカル LLM（Ollama + LLaVA）** が分析し、ニコニコ動画風の流れるコメントをリアルタイムでオーバーレイ表示するツールです。

---

## 概要

- 任意のウィンドウの上に透過オーバーレイを重ねて表示
- **Ollama + LLaVA**（ローカル実行）が画面内容を分析し、コメントを自動生成
- コメントは右から左へ流れるアニメーションで表示
- オーバーレイはクリックスルー（背後のアプリをそのまま操作可能）
- **インターネット接続・API キー不要**

---

## 必要環境

| 項目 | 要件 |
|------|------|
| OS | Windows 10 / 11 |
| Python | 3.10 以上 |
| GPU | NVIDIA GPU 推奨（VRAM 6GB 以上） |
| Ollama | [ollama.com](https://ollama.com) からインストール |

> CPU のみでも動作しますが、分析に数十秒かかることがあります。
> 低スペック環境では `OLLAMA_MODEL = "moondream"` への変更を推奨します。

---

## インストール

### 1. Ollama のセットアップ

```bash
# Ollama 公式サイトからインストーラをダウンロード
# https://ollama.com

# インストール後、LLaVA モデルを取得（約 4GB）
ollama pull llava
```

### 2. Python 環境のセットアップ

```bash
cd niconico_inspire_comment_local

# 仮想環境を作成・有効化
python -m venv .venv
.venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt
```

---

## クイックスタート

```bash
# ターミナル1: Ollama サーバーを起動
ollama serve

# ターミナル2: アプリを起動
.venv\Scripts\activate
python main.py
```

1. ウィンドウ選択ダイアログが開く
2. コメントを流したいアプリを選択して **「開始」** をクリック
3. 約 8 秒ごとに画面を分析してコメントが流れ始める
4. ウィンドウを閉じると停止

---

## 設定のカスタマイズ

タスクトレイのアイコンを右クリックして **「設定...」** を開くと、コメント表示量や表示速度を調整できます。
設定は `settings.json` に保存され、次回起動時にも引き継がれます。

| 設定項目 | 説明 |
|----------|------|
| 1回あたりの表示数 | 1回のAI分析で流すコメント数 |
| 分析間隔 | 画面をキャプチャしてAI分析する間隔 |
| 流し始めの間隔 | 同じ分析結果内のコメントを流し始める時間差 |
| レーン数 | 同時表示できる行数 |
| 文字サイズ | コメント文字のランダムサイズ範囲 |
| 速度 | コメントが右から左へ流れる速さ |

モデルや Ollama 接続先などの基本設定は `config.py` の値を変更します。

| 設定値 | デフォルト | 説明 |
|--------|-----------|------|
| `OLLAMA_MODEL` | `"llava"` | 使用するモデル名 |
| `OLLAMA_HOST` | `"http://localhost:11434"` | Ollama サーバーのアドレス |
| `CAPTURE_INTERVAL_MS` | `8000` | 分析の間隔（ミリ秒） |
| `COMMENT_SPEED_MIN/MAX` | `4 / 8` | コメントの流れる速さ（px/tick） |
| `LANE_COUNT` | `10` | 同時表示できる行数 |

### モデルの切り替え

```python
# config.py
OLLAMA_MODEL = "llava"       # 標準（推奨、約4GB）
OLLAMA_MODEL = "llava:13b"   # 高品質（約8GB VRAM必要）
OLLAMA_MODEL = "moondream"   # 軽量（低スペック向け、約1.7GB）
```

```bash
# モデルの事前ダウンロード
ollama pull moondream
ollama pull llava:13b
```

詳細は [docs/usage.md](docs/usage.md) を参照してください。

---

## ファイル構成

```
niconico_inspire_comment_local/
├── main.py            # エントリポイント・ウィンドウ選択
├── overlay.py         # PyQt6 透過オーバーレイ本体
├── capture.py         # スクリーンキャプチャ
├── analyzer.py        # Ollama (LLaVA) 連携
├── comment_lane.py    # コメントアニメーション管理
├── config.py          # 設定値（OLLAMA_MODEL 等）
├── requirements.txt
└── docs/
    └── usage.md       # 詳細な使用方法
```

---

## ライセンス

MIT License
