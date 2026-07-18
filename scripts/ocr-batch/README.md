# ocr-batch ─ ローカル無料 OCR バッチ（macOS / Apple Vision）

Apple Vision framework を使った、無料・ローカル・オフラインの OCR ユーティリティ。
画像フォルダを一括 OCR して Obsidian などで全文検索できるインデックスノート(.md)を生成する用途と、
動画の焼き込みテロップ/字幕を抽出して captions.txt / srt に落とす用途をカバーする。

TRex CLI(`trex --input`)はバッチ用途でハングし stdout に結果を返さないため、
土台に Swift Vision の自作 CLI(`ocr`)を使う。

## 構成

| ファイル | 役割 |
|---|---|
| `ocr.swift` | Vision OCR CLI のソース（`VNRecognizeTextRequest`、ja+en） |
| `ocr`（gitignore） | 上をビルドしたバイナリ。約 345ms/枚（warm） |
| `ocr-images.sh` | フォルダ一括 OCR → .md インデックス生成ラッパー |
| `video-captions.sh` | 動画の焼き込みテロップ/字幕を抽出 → captions.txt / srt |
| `dedupe_captions.py` | 隣接する類似キャプションを縮約（video-captions.sh が使用） |

## ビルド

```bash
swiftc -O ocr.swift -o ocr
```

macOS 実機・Xcode Command Line Tools 必須（Vision / AppKit 依存）。

## 使い方

```bash
# 単一画像 → stdout に OCR テキスト
./ocr image.png

# フォルダ一括 → Obsidian 検索に乗る .md インデックスを生成
#   既定出力先: $OCR_INDEX_DIR（未指定なら $HOME/Documents/vault-main/05_Reference/スクショOCR）
./ocr-images.sh ~/Downloads/screenshots

# 出力先を明示
./ocr-images.sh ~/Downloads/screenshots --out ~/notes/shots-index.md

# 出力先の既定を環境変数で変更
OCR_INDEX_DIR=~/ocr-index ./ocr-images.sh ~/Downloads/screenshots

# .md でなく各画像の隣に <画像名>.txt サイドカー（CLI grep 用・Obsidian 検索対象外）
./ocr-images.sh ~/Downloads/screenshots --txt
```

### 動画の焼き込みテロップ/字幕を抽出

```bash
# 1 秒間隔でサンプリング → <ベース名>.captions.txt を生成
./video-captions.sh demo.mp4

# srt も出力・字幕は画面下 1/3 に多いので --crop-bottom でノイズ減
./video-captions.sh demo.mp4 --srt --crop-bottom

# シーン変化検出モード（実写の目安 0.3）
./video-captions.sh demo.mp4 --scene 0.3 --srt
```

- 対応: `.mp4` / `.mov`。画面に焼き込まれたテロップの OCR のみ（音声・字幕トラックは対象外）
- 連続フレームで同一テロップが数百回重複するのを、抽出時の間引き（`--interval` / `--scene`）と OCR 後の隣接 dedupe（`dedupe_captions.py`）の両方で除去する
- 目安処理量: 1 秒間隔の 10 分動画 ≈ 600 フレーム × 約 345ms ≈ 3.5 分

## 動画テロップ抽出のしくみ

### パイプライン

```
動画 ─ ffmpeg でフレーム間引き抽出 ─ 各フレームを ocr で OCR ─ dedupe_captions.py で隣接類似を縮約 ─ captions.txt / srt
```

`video-captions.sh` が抽出と整形を担い、縮約（重複除去）だけを `dedupe_captions.py` に委譲する二段構成。

### video-captions.sh のオプション

| オプション | 既定 | 説明 |
|---|---|---|
| `--interval <秒>` | 1 | `fps=1/<秒>` で等間隔サンプリング。秒 = (連番−1)×interval で紐付け |
| `--scene <閾値>` | ─ | シーン変化検出モード。`select='eq(n,0)+gt(scene,<閾値>)'` で変化点のみ抽出。先頭フレーム必須（`eq(n,0)` ─ 開始直後テロップの取りこぼし防止）。秒は `showinfo` の `pts_time` 由来。実写の目安 0.3。指定時 `--interval` は無視 |
| `--srt` | off | 標準 srt も出力。終了時刻＝次キャプションの開始時刻、最終キャプションのみ開始+2 秒 |
| `--crop-bottom` | off | フレーム下 1/3 のみ OCR（`crop=iw:ih/3:0:2*ih/3`）。字幕帯に絞りノイズ減 |
| `--out <dir>` | 動画と同じ dir | 出力先ディレクトリ |
| `--keep-frames` | off | 一時フレームを削除せず残す（デバッグ用） |

- 出力: `<ベース名>.captions.txt`（`[HH:MM:SS] テキスト` 形式）、`--srt` 時は `<ベース名>.srt`
- 1 フレームの OCR 出力全体を 1 キャプションブロックとして扱い、空ブロックは捨てる
- パスは自己位置基準で `ocr` / `dedupe_captions.py` を解決するため、`~/.claude/scripts/` への symlink 経由でも動く
- macOS 標準 `/bin/bash`（3.2）で動作（`mapfile` 等の bash 4+ 機能に依存しない）

### なぜ dedupe が要るか ─ dedupe_captions.py の役割

連続フレームをそのまま OCR すると、同じテロップが表示され続ける間フレーム数ぶん重複する（3 秒表示・1 秒間隔なら同一文が約 3 回）。抽出時の間引きだけでは足りず、OCR には揺れ（句読点・空白・一部文字の差）があるため完全一致の uniq でも取りこぼす。そこで類似度ベースの縮約を挟む。

`dedupe_captions.py` の処理:

1. 各フレームの OCR ブロックを正規化（前後空白・空行を除去。空になったブロックは捨てる）
2. **隣接**ブロックを `difflib.SequenceMatcher(None, a, b).ratio()` で比較し、**≥ 0.90 なら同一キャプション**とみなして 1 本に縮約。表示終了時刻を後続フレームの時刻まで延長する
3. 比較は隣接のみ。別ブロックを挟んで再出現した同文は別キャプションとして残す（全体 uniq はしない）
4. 閾値は先頭の `RATIO_THRESHOLD` 定数（既定 0.90）で調整できる

インターフェース: `video-captions.sh` が `秒<TAB>テキストファイルパス` のマニフェストを渡し、`dedupe_captions.py` が `開始秒 終了秒 縮約本文ファイルパス` を返す。本文をパイプでなく**ファイルで受け渡す**のは、OCR テキストの改行・引用符がシェルのクォートを壊すのを防ぐため。

### 向き / 不向き

- 得意: **静止テロップ・字幕**（一定時間固定表示される文字）。dedupe がよく効き、キャプション数が素直に縮む
- 不得手: スクロール/アニメーションで毎フレーム内容が変わる画面。dedupe が効かず 1 ブロックが肥大し、OCR ノイズ（動きによる歪み）も増える

## 仕様メモ

- 対応形式: png / jpg / jpeg / webp / heic（大小不問）。フォルダ直下のみ・再帰しない・昇順
- 再実行は全再生成（冪等）。ただし出力先に `generated_by: ocr-images.sh` を含まない既存ファイルは上書きせずエラー終了（手書きノート保護）
- Obsidian のコア検索は .md しかインデックスしないため、既定は .md インデックス方式（.txt は CLI grep 用のオプション）

## 用途例

- スクショ束の全文検索インデックス化
- 領収書・レシートの文字化（機微情報をクラウドに出さずローカル完結）
- 過去資料・名刺・書籍ページ写真の一括デジタル化
- 既存サイトのスクショ/バナーから文言だけ一括抽出
- 動画フレームからのテロップ/字幕抽出（`video-captions.sh`）
