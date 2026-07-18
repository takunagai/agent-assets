#!/usr/bin/env bash
#
# ocr-images.sh ─ 画像フォルダを一括 OCR し、Obsidian で全文検索できる
# インデックスノート(.md)を生成する。土台は同ディレクトリの Swift Vision CLI `ocr`。
#
# usage: ocr-images.sh <画像フォルダ> [オプション]
#   --out <出力.md>   インデックスノートの出力先を明示指定
#   --txt             .md を作らず、各画像の隣に <画像名>.txt サイドカーを生成
#   --help            使い方を表示
#
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OCR="$SCRIPT_DIR/ocr"
OCR_INDEX_DIR="${OCR_INDEX_DIR:-$HOME/Documents/vault-main/05_Reference/スクショOCR}"

print_help() {
  cat <<'HELP'
usage: ocr-images.sh <画像フォルダ> [オプション]

  <画像フォルダ>    OCR 対象の画像を含むフォルダ（直下のみ・再帰しない）
  --out <出力.md>   インデックスノートの出力先を明示指定
  --txt             .md を作らず、各画像の隣に <画像名>.txt サイドカーを生成
  --help            この使い方を表示

対応形式: png / jpg / jpeg / webp / heic（拡張子の大小不問）

既定（インデックスノート方式）:
  1 フォルダにつき 1 本の .md を生成する。--out 未指定時の出力先は
  $OCR_INDEX_DIR/<フォルダ名> OCRインデックス.md
  （既定 $HOME/Documents/vault-main/05_Reference/スクショOCR ─ 環境変数 OCR_INDEX_DIR で変更可）
  Obsidian のコア検索は .md しかインデックスしないため、既定はこの方式。

--txt について:
  各画像の隣に <画像名>.txt を作る。.txt は Obsidian 内検索の対象外（CLI grep / ripgrep 用）。
HELP
}

# ---- 引数パース ----
DIR=""
OUT=""
MODE="index"   # index | txt
while [ $# -gt 0 ]; do
  case "$1" in
    --help) print_help; exit 0 ;;
    --txt)  MODE="txt"; shift ;;
    --out)  shift; [ $# -gt 0 ] || { echo "error: --out には出力パスが必要" >&2; exit 2; }; OUT="$1"; shift ;;
    -*)     echo "error: 不明なオプション: $1" >&2; exit 2 ;;
    *)      if [ -z "$DIR" ]; then DIR="$1"; else echo "error: 引数が多すぎます: $1" >&2; exit 2; fi; shift ;;
  esac
done

[ -n "$DIR" ] || { echo "error: 画像フォルダを指定してください" >&2; print_help >&2; exit 2; }
[ -d "$DIR" ] || { echo "error: フォルダが存在しません: $DIR" >&2; exit 2; }
[ -x "$OCR" ] || { echo "error: OCR バイナリがありません: $OCR（先に swiftc -O ocr.swift -o ocr）" >&2; exit 3; }

# ---- 対象画像の収集（直下のみ・大小不問・昇順） ----
DIR_ABS="$(cd "$DIR" && pwd)"
shopt -s nullglob nocaseglob
declare -a IMGS=()
for ext in png jpg jpeg webp heic; do
  for f in "$DIR_ABS"/*."$ext"; do IMGS+=("$f"); done
done
shopt -u nullglob nocaseglob
# 重複除去 + 昇順
if [ ${#IMGS[@]} -gt 0 ]; then
  IFS=$'\n' read -r -d '' -a IMGS < <(printf '%s\n' "${IMGS[@]}" | sort -u && printf '\0')
fi
[ ${#IMGS[@]} -gt 0 ] || { echo "error: 対象画像が 0 件です: $DIR_ABS" >&2; exit 4; }

# ---- OCR 実行ヘルパー ----
ocr_one() {  # $1=画像パス → stdout に OCR テキスト。失敗時は非0
  "$OCR" "$1" 2>/dev/null
}

# ================= --txt モード =================
if [ "$MODE" = "txt" ]; then
  count=0
  for f in "${IMGS[@]}"; do
    if text="$(ocr_one "$f")"; then
      printf '%s\n' "$text" > "${f}.txt"
      count=$((count+1))
    else
      echo "warn: OCR 失敗・スキップ: $f" >&2
    fi
  done
  echo "生成: 各画像の隣に .txt サイドカー / 処理 ${count} 枚 / フォルダ: $DIR_ABS"
  exit 0
fi

# ================= index モード（既定） =================
if [ -z "$OUT" ]; then
  mkdir -p "$OCR_INDEX_DIR"
  OUT="$OCR_INDEX_DIR/$(basename "$DIR_ABS") OCRインデックス.md"
fi

# 既存ファイル保護: 自分が生成したノートでなければ上書きしない
if [ -e "$OUT" ] && ! grep -q 'generated_by: ocr-images.sh' "$OUT" 2>/dev/null; then
  echo "error: 出力先に ocr-images.sh 生成でないファイルが既存（上書き中止）: $OUT" >&2
  exit 5
fi

OUT_DIR="$(dirname "$OUT")"
mkdir -p "$OUT_DIR"
TODAY="$(date +%F)"
TITLE="$(basename "$DIR_ABS") OCRインデックス"

# frontmatter
{
  echo "---"
  echo "title: ${TITLE}"
  echo "date: ${TODAY}"
  echo "source_dir: ${DIR_ABS}"
  echo "generated_by: ocr-images.sh"
  echo "tags: [ocr-index]"
  echo "---"
  echo
  echo "# ${TITLE}"
  echo
} > "$OUT"

count=0
for f in "${IMGS[@]}"; do
  name="$(basename "$f")"
  {
    echo "## ${name}"
    echo
    echo "\`${f}\`"
    echo
  } >> "$OUT"
  if text="$(ocr_one "$f")"; then
    if [ -n "$text" ]; then
      printf '%s\n\n' "$text" >> "$OUT"
    else
      printf '（テキスト検出なし）\n\n' >> "$OUT"
    fi
    count=$((count+1))
  else
    echo "warn: OCR 失敗・スキップ本文: $f" >&2
    printf '（テキスト検出なし）\n\n' >> "$OUT"
  fi
done

echo "生成: ${OUT} / 処理 ${count} 枚 / フォルダ: $DIR_ABS"
