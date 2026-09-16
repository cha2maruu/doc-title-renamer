# doc-title-renamer

指定したフォルダ（または単一ファイル）内の `docx` / `xlsx` / `pptx` / `pdf` の内容をローカルLLMに読み取らせ、ファイル名と保存フォルダを自動的に整理するWindows向けCLIツールです。文書の内容は手元のLLMだけで処理し、外部のクラウドサービスには送信しません。

## 特徴

- 文書の内容をローカルLLMに読み取らせてタイトル候補と発信日を推測し、`YYYYMMDD_タイトル候補.拡張子`（例: `20260415_見積書.pdf`）にリネームする
- 対象拡張子: `.docx` `.xlsx` `.pptx` `.pdf`（スキャンPDFはOCRで対応）
- OCR特有の余分な空白・ノイズや和暦の日付表記は、LLMに渡す前にクリーニング・西暦変換して読み取り精度を落とさない
- 2つの動作モード: ファイル名変更のみ／ファイル名変更＋`YYYYMM`フォルダへの移動

## 前提環境

- [uv](https://docs.astral.sh/uv/) がインストール済みであること（`uvx` コマンドを使用）
- OpenAI互換API（`/v1/chat/completions` / `/v1/models`）を持つローカルLLMサーバーが起動していること。[LM Studio](https://lmstudio.ai/) なら既定値の `http://localhost:1234/v1` でそのまま動く。[Ollama](https://ollama.com/) 等ポートが異なる場合は `--llm-url` で指定する
- 小規模モデルの利用を想定。CPU実行やthinking対応モデルは応答に数十秒かかることがあり、既定のタイムアウトは120秒（`--llm-timeout` で変更可）

## 使い方

サブコマンドは `rename-only`（リネームのみ）と `organize`（リネーム＋`YYYYMM`フォルダへの移動）の2つです。

```bash
# リネームのみモード: ファイル名変更のみ、移動はしない
uvx --from git+https://github.com/cha2maruu/doc-title-renamer doc-title-renamer rename-only "C:\path\to\folder"

# フォルダ整理モード: フォルダ直下の対象ファイルをリネーム＋YYYYMMフォルダへ移動
uvx --from git+https://github.com/cha2maruu/doc-title-renamer doc-title-renamer organize "C:\path\to\folder"

# 単一ファイル指定も可能
uvx --from git+https://github.com/cha2maruu/doc-title-renamer doc-title-renamer rename-only "C:\path\to\file.pdf"
```

実行すると変更前後のファイル名一覧が表示され、`y` を入力するまで実際のリネーム・移動は行われません。`n` を入力するか何も入力せず終了した場合は、何も変更されません。

### オプション

| オプション | 既定値 | 説明 |
|---|---|---|
| `--llm-url` | `http://localhost:1234/v1` | ローカルLLM（OpenAI互換API）のエンドポイント。`localhost` / `127.0.0.1` のみ指定可 |
| `--llm-model` | 未指定（自動解決） | 使用するモデル名。省略時はローカルLLMのロード済みモデルから自動解決する |
| `--llm-timeout` | `120`（秒） | ローカルLLMへの1回あたりの問い合わせタイムアウト秒数 |
| `--yes` | 無効 | 確認プロンプトを省略し、自動的に実行する |

```bash
# Ollama等、LM Studio以外のローカルLLMを使う場合の例
uvx --from git+https://github.com/cha2maruu/doc-title-renamer doc-title-renamer rename-only "C:\path\to\folder" \
  --llm-url http://localhost:11434/v1 --llm-model qwen3:8b

# LLM応答が遅い環境向け: タイムアウトを300秒に延長
uvx --from git+https://github.com/cha2maruu/doc-title-renamer doc-title-renamer rename-only "C:\path\to\folder" \
  --llm-timeout 300

# タスクスケジューラ等からの自動実行向け: 確認プロンプトを省略
uvx --from git+https://github.com/cha2maruu/doc-title-renamer doc-title-renamer organize "C:\path\to\folder" --yes
```

## ファイル名 / フォルダ命名規則

| 対象 | 形式 | 例 |
|---|---|---|
| ファイル名 | `YYYYMMDD_タイトル候補.拡張子` | `20260415_見積書_株式会社○○.pdf` |
| フォルダ名（整理モード時） | `YYYYMM` | `202604` |

- 日付は文書内の発信日をLLMで推測し、読み取れない場合はファイルの作成日時を使用します。
- タイトル候補はローカルLLMが推測したものを使用します。推測できなかった場合は元のファイル名にフォールバックします。
- タイトルが長すぎる場合は40文字程度に切り詰め、Windowsで使用できない文字は除去・置換します。
- 同名ファイルが既に存在する場合（同じバッチ内での重複を含む）は末尾に連番（`_2` など）を付与します。生成した名前が現在の名前と完全に一致する場合は「変更なし」として扱います。

## 動作環境

- Windows専用です（Mac/Linuxでの動作は保証しません）。Python 3.10以上、CPU実行を前提とします。
- ローカルLLMへの接続先は `localhost` / `127.0.0.1` のみに固定しています（LAN上の別PCなどは指定できません）。
- ローカルLLMに接続・モデルの解決ができない場合は、エラーを表示して処理全体を中断します。
- 個別のファイルの変換・OCR・LLM問い合わせ・リネームに失敗した場合は、そのファイルだけをスキップして他のファイルの処理を続けます。
- 初回実行時は、Docling・EasyOCR等の依存パッケージやOCR用モデルのダウンロードが発生し、時間がかかる場合があります（`uv`のキャッシュに保存され、2回目以降は高速になります）。

## ドキュメント

- [docs/DESIGN.md](docs/DESIGN.md) — 機能要件・非機能要件の詳細仕様
- [docs/STRUCTURE.md](docs/STRUCTURE.md) — ディレクトリ構成
- [docs/TEST.md](docs/TEST.md) — テスト方針・対応状況
- [NOTICE.md](NOTICE.md) — 直接依存ライブラリのサードパーティライセンス

## ライセンス

[MIT License](LICENSE)。直接依存する Docling・EasyOCR・pypdfium2 のライセンス表記は [NOTICE.md](NOTICE.md) を参照してください。
