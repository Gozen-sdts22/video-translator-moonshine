# SubGen - 動画字幕自動生成ツール

Moonshine ASR + 翻訳APIによるローカル字幕生成パイプライン。
日本語動画から字幕を自動生成し、中国語などへの翻訳字幕も出力できます。

## 特徴

- **ローカルASR** — Moonshine日本語モデルでオフライン音声認識
- **話者分離** — pyannote-audioによる話者色分け（ASS形式）
- **翻訳対応** — DeepL / Google Cloud Translation API連携
- **複数形式** — SRT（汎用）+ ASS（スタイル付き）出力
- **Web UI** — ブラウザから操作可能なドラッグ&ドロップUI

## パイプライン

```
動画 (MP4) → 音声抽出 (FFmpeg) → 音声認識 (Moonshine)
  → 話者分離 → 翻訳 (オプション) → 字幕ファイル (SRT/ASS)
```

## 前提条件

- Python 3.10+
- FFmpeg（システムPATHに必要）
- 翻訳機能使用時: DeepL or Google Cloud Translation APIキー

## インストール

```bash
# 基本インストール
pip install -e .

# Web UI付き
pip install -e ".[web]"

# 翻訳API付き
pip install -e ".[deepl]"      # DeepL
pip install -e ".[google]"     # Google Cloud Translation

# 全機能
pip install -e ".[all]"

# 開発用（テスト含む）
pip install -e ".[dev]"
```

## 使い方

### CLI

```bash
# 基本（日本語動画 → 日本語ASS字幕）
subgen input.mp4 --lang ja --format ass

# 翻訳付き（日本語 → 中国語字幕も生成）
subgen input.mp4 --lang ja --translate zh --api deepl

# SRT + ASS 両方出力、出力先指定
subgen input.mp4 -o ./subs/ --format both --translate zh

# 話者数を指定、詳細ログ
subgen input.mp4 --speakers 2 -v
```

### CLIオプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--lang, -l` | `ja` | 音声の言語 |
| `--format, -f` | `ass` | 出力形式（`srt` / `ass` / `both`） |
| `--output, -o` | 入力と同じディレクトリ | 出力先 |
| `--translate, -t` | なし | 翻訳先言語（`zh`, `en` 等） |
| `--api` | `deepl` | 翻訳API（`deepl` / `google`） |
| `--speakers` | `auto` | 話者数（`auto` / `1` / `2` ...） |
| `--verbose, -v` | `false` | 詳細ログ |

### Web UI

```bash
# サーバー起動（http://127.0.0.1:5000）
subgen-web

# ポート・ホスト変更
subgen-web --host 0.0.0.0 --port 8080
```

ブラウザから動画をドラッグ&ドロップし、設定を選んで字幕を生成できます。
リアルタイムの進捗表示、字幕プレビュー、ファイルダウンロード機能付き。

## 環境変数

| 変数 | 用途 |
|---|---|
| `DEEPL_API_KEY` | DeepL APIキー |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Cloud サービスアカウントキーのパス |

## プロジェクト構成

```
subgen/
├── __init__.py          # パッケージ定義
├── cli.py               # CLIエントリーポイント
├── web.py               # Web UIバックエンド (Flask)
├── pipeline.py          # パイプライン統合
├── audio_extractor.py   # F-001: 音声抽出 (FFmpeg)
├── asr.py               # F-002: 音声認識 (Moonshine)
├── diarization.py       # F-003: 話者分離
├── translator.py        # F-004: 翻訳 (DeepL/Google)
├── subtitle_writer.py   # F-005: 字幕生成 (SRT/ASS)
├── config.py            # 設定管理
├── templates/           # Web UIテンプレート
└── static/              # Web UI静的ファイル
```

## テスト

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## ライセンス

MIT
