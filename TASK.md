# TASK.md

`docling-to-markitdown-ea4bce` ブランチでの作業用タスクリスト。
バックエンドをDocling→markitdown、OCRをEasyOCR→RapidOCRに変更する。
このファイルは作業進行管理用であり、正式なドキュメント（docs/配下）ではない。
マージ後は削除してよい。

## 方針（合意済み）

- PRは1本にまとめる。
- マージ前に、現行mainの最終コミットへ旧バージョンとしてタグ（例: `v0.1.0`）を打ち、
  `uvx` での旧版ピン留め（ロールバック手段）を確保してからマージする。
- コミットは下記の順で分割し、差分を追いやすくする。
- CIが未整備のため、マージ前にローカルで `pytest` と実書類での手動確認を行う。

## 作業前の準備

- [x] 現行 `main`（コミット `41f6c90`）に `v0.1.0` タグを付与する（ローカル作成済み。origin へのpushはPR作成時に確認）

## 実装ステップ（コミット単位）

### 1. ドキュメント方針の改訂
- [x] `docs/DESIGN.md` 1章・4.4節・4.5節・4.14節・5章・7章を markitdown + RapidOCR 前提に書き換え
- [x] `CLAUDE.md` の依存方針（Docling/EasyOCR以外は安易に追加しない、という記述）を更新

### 2. markitdown導入・Docling依存の除去（通常変換）
- [x] `pyproject.toml` に `markitdown[docx,xlsx,pptx,pdf]` を追加
  （`docling`/`easyocr`はocr.py用に一旦残置。ステップ4で除去）
- [x] `src/doc_title_renamer/converter.py` を markitdown ベースに書き換え
  （docx/xlsx/pptx/テキスト層PDFの変換。`MarkItDown(enable_plugins=False).convert_local(path).markdown`）
- [x] `tests/test_converter.py` / `tests/helpers.py`（`install_fake_markitdown`追加）を更新、`pytest`全77件通過確認
- [ ] markitdown出力のMarkdown書式差分（画像プレースホルダ等）を実書類で確認

### 3. OCR自前実装（RapidOCR組み込み）
- [ ] `src/doc_title_renamer/ocr.py` から Docling 経由の呼び出しを除去し、
      RapidOCR（+ onnxruntime）を直接呼ぶ実装に置き換え
- [ ] 日本語対応OCRモデルの選定（mobile系 vs server系、サイズと精度のトレードオフを実機検証）
- [ ] 既存の制約を自前実装で再現する
  - [ ] スキャンPDFは先頭2ページのみ処理（`OCR_MAX_PAGES`）
  - [ ] テキスト層有無判定（`has_text_layer`、閾値50文字）はそのまま流用可能か確認
  - [ ] 表構造解析・画像キャプション生成は行わない（DESIGN.md 4.4相当）
- [ ] OCR結果をMarkdown相当のテキストに整形する処理を実装

### 4. クリーニング・依存整理・テスト更新
- [ ] `src/doc_title_renamer/md_cleaner.py` の画像プレースホルダ処理などを
      新しい変換・OCR出力フォーマットに合わせて調整
- [ ] `pyproject.toml` の依存を最終整理（`docling`/`easyocr`除去、`markitdown`/`rapidocr-onnxruntime`/`onnxruntime`追加）
- [ ] `tests/test_converter.py` / `tests/test_ocr.py` / `tests/helpers.py` を更新
- [ ] `docs/STRUCTURE.md` のモジュール説明（converter.py, ocr.py）を同期
- [ ] `docs/TEST.md` のテスト方針・対応状況表を同期

### 5. 動作確認
- [ ] `pytest` が全て通ることを確認
- [ ] 実書類での手動確認
  - [ ] docx / xlsx / pptx
  - [ ] テキスト層ありPDF
  - [ ] スキャンPDF（OCR経路、日本語文書）
- [ ] モデルキャッシュ容量が想定通り削減されているか確認（`.EasyOCR`, `huggingface/hub` 相当のキャッシュ先）

### 6. PR作成・マージ後
- [ ] PR説明に「Docling→markitdown+RapidOCRへの移行」である旨と、
      ロールバック手段（`v0.1.0`タグ）を明記
- [ ] マージ後、`v0.2.0` タグを付与

## 未決事項・要検討

- 日本語OCRモデルの具体的な選定（RapidAI/RapidOCRリポジトリのどのモデルを使うか、サイズと精度）
- markitdownのPDFテキスト抽出品質がDoclingと比べてタイトル推測精度にどう影響するか
- OCR自前実装後、Doclingの`page_range`相当（先頭2ページのみ処理して速度を保つ仕組み）をどう再現するか
