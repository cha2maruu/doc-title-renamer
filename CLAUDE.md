# CLAUDE.md

このリポジトリで作業するAIエージェント（Claude Code等）向けの方針をまとめたものです。

機能要件・非機能要件（動作モード、対象ファイル、PDF/OCRの扱い、Markdownクリーニング、
タイトル・発信日の推測、プロンプトインジェクション対策、命名規則、衝突回避、実行前確認、
ローカルLLM接続設定、エラー処理、終了コード等）は、すべて [docs/DESIGN.md](docs/DESIGN.md)
に定義されています。実装を始める前に必ず確認し、そこから逸脱しないでください。

## 設計・実装時の指針

- 依存は最小限に。MarkItDown / RapidOCR（onnxruntime）以外の重量級ライブラリを安易に追加しない。
  特にPyTorch・PaddlePaddleのような重量級の深層学習フレームワークは、モデルキャッシュ容量削減
  （旧Docling + EasyOCR構成からの移行目的）を損なうため導入しない。
  ローカルLLMとの通信（`/v1/chat/completions`・`/v1/models`）は**標準ライブラリの`urllib.request`**で
  実装し、`openai`/`httpx`/`requests`等の追加HTTPクライアントライブラリは導入しない
  （単純なJSON POST/GETのみで、SDKの機能を必要としないため）。

## ドキュメント運用

- 要件が変わった場合は [docs/DESIGN.md](docs/DESIGN.md) を更新してから実装に着手する。
- ディレクトリ構成を変更した場合は [STRUCTURE.md](docs/STRUCTURE.md) を同期させる。
- テストを追加・変更した場合は [TEST.md](docs/TEST.md) のテスト方針・対応状況表を同期させる。
