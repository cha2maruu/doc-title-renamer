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
- [x] `src/doc_title_renamer/ocr.py` から Docling 経由の呼び出しを除去し、
      RapidOCR（+ onnxruntime）を直接呼ぶ実装に置き換え
- [x] 日本語対応OCRモデルの選定 → **PP-OCRv6 small**（`Rec.ocr_version=PPOCRV6`, `Rec.model_type=SMALL`, `Rec.lang_type=CH`）を採用。
      PP-OCRv6はmobile/server区分ではなくtiny/small/mediumの3段階で、日本語(japan)はsmall/mediumのみ対応（tiny非対応）。
      軽量寄りのsmallを選定（mediumとの精度比較は実書類での動作確認時に評価）。
- [x] スキャンPDFの先頭2ページ制限は撤廃 → OCR速度（PP-OCRv6 small）を検討した結果不要と判断し、
      全ページを処理する方針に変更。テキスト層有無判定（`has_text_layer`）も全ページ対象に統一（DESIGN.md 4.4）。
- [x] 既存の制約を自前実装で再現する
  - [x] テキスト層有無判定（`has_text_layer`、閾値50文字）はそのまま流用可能か確認
- [x] OCR結果をMarkdown相当のテキストに整形する処理を実装

### 4. クリーニング・依存整理・テスト更新
- [x] `src/doc_title_renamer/md_cleaner.py` の画像プレースホルダ処理などを
      新しい変換・OCR出力フォーマットに合わせて調整（Docling固有の`<!-- image -->`処理を削除し、
      MarkItDownの`![alt](PictureN.jpg)`形式の連続画像を先頭1件へ間引く処理に変更）
- [x] `pyproject.toml` の依存を最終整理（`docling`/`easyocr`除去、`markitdown`/`rapidocr>=3.9.0`/`onnxruntime`追加、`uv.lock`再生成）
- [x] `tests/test_converter.py` / `tests/test_ocr.py` / `tests/helpers.py` を更新（旧Docling/EasyOCR用フェイクを削除しRapidOCR/MarkItDownフェイクへ移行）
- [x] `docs/STRUCTURE.md` のモジュール説明（converter.py, ocr.py）を同期
- [x] `docs/TEST.md` のテスト方針・対応状況表を同期

### 5. 動作確認
- [x] `pytest` が全て通ることを確認（78件成功。`uv sync`でDocling/EasyOCR時代の残存パッケージ
      〔torch/torchvision等〕を除去したクリーンな環境で再確認済み）
- [x] 実書類での手動確認（生成したサンプル文書をローカルLLM Ollama `qwen3:8b` で処理、
      `rename-only --yes`で全件成功・タイトル/日付とも文書内容と一致）
  - [x] docx / xlsx / pptx（それぞれ御見積書2026-03-10、経費精算2026-02-20、
        第2四半期営業戦略会議2026-01-15として正しく認識）
  - [x] テキスト層ありPDF（業務委託契約書2026-04-01として正しく認識）
  - [x] スキャンPDF（OCR経路、日本語文書）（画像のみのPDFをRapidOCR(PP-OCRv6 small)で処理し、
        請求書2026-05-20として正しく認識。OCR経路が実機で機能することを確認）
- [x] モデルキャッシュ容量が想定通り削減されているか確認
      → RapidOCRモデル(ONNX) 31MB + onnxruntimeパッケージ 33MB ≒ 64MB。
      旧構成（`.EasyOCR` 96MB + Docling用huggingfaceキャッシュ 506MB ≒ 602MB）から
      約9割削減。`.venv`にtorch/paddle系パッケージが含まれないことも確認済み。

### 6. PR作成・マージ後
- [ ] PR説明に「Docling→markitdown+RapidOCRへの移行」である旨と、
      ロールバック手段（`v0.1.0`タグ）を明記
- [ ] マージ後、`v0.2.0` タグを付与

## 未決事項・要検討

- PP-OCRv6 smallの日本語認識精度: 生成した1ページのスキャンPDF（請求書相当）では
  タイトル・日付とも正しく認識できることを確認済み。ただし手書き文字や低画質スキャン、
  複雑なレイアウトの実書類ではまだ未検証のため、精度不足が判明した場合はmediumへの
  切り替えを検討する。
- 全ページOCRとした結果、ページ数が多いスキャンPDFで処理時間が許容範囲を超えないか
  → 1ページのサンプルでは実用上問題ない速度だったが、複数ページの実書類での検証は未実施。
- markitdownのPDFテキスト抽出品質がDoclingと比べてタイトル推測精度にどう影響するか
