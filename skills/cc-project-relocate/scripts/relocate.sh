#!/usr/bin/env bash
set -euo pipefail

# cc-project-relocate: Claude Code プロジェクトを移動/リネームした後、
# パスに紐づく状態を新パスへ追随させるツール。
#   1. ~/.claude/projects/<encoded>  … セッションログ dir（JSONL・tool-results・memory）
#   2. (任意) ~/.claude.json の projects["<絶対パス>"] … trust/allowedTools/MCP 設定
#
# encode 規則は Claude Code 本体と同一の  path.replace(/[^a-zA-Z0-9]/g,'-')
# （/ も _ も . もスペースも日本語も非英数字は全て '-'）。
# sed 等での自前再実装はマルチバイトでズレるため、必ず node で計算する。

PROJECTS_DIR="$HOME/.claude/projects"
CLAUDE_JSON="$HOME/.claude.json"
BK_DIR="$HOME/.claude/backups/relocate"

OLD=""
NEW=""
DRY=0
YES=0
UPDATE_CONFIG=0

die() { echo "エラー: $*" >&2; exit 1; }
info() { echo "$*"; }
warn() { echo "$*" >&2; }

usage() {
  cat <<'EOF'
使い方: relocate.sh --old <移動前の絶対パス> [--new <移動後の絶対パス>] [オプション]

  --old PATH        移動前のプロジェクト絶対パス（必須）
  --new PATH        移動後のプロジェクト絶対パス（既定: 現在の作業ディレクトリ $PWD）
  --update-config   ~/.claude.json の projects キーも移行する（既定: しない）
  --dry-run         実行せず計画だけ表示
  --yes             健全性チェックの警告を無視して実行
  -h, --help        このヘルプ

例:
  relocate.sh --old /Users/me/Projects/old --new /Users/me/work/new --dry-run
  relocate.sh --old /Users/me/Projects/old --new /Users/me/work/new --update-config
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --old) OLD="${2:-}"; shift 2 ;;
    --new) NEW="${2:-}"; shift 2 ;;
    --update-config) UPDATE_CONFIG=1; shift ;;
    --dry-run) DRY=1; shift ;;
    --yes) YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage; die "不明な引数: $1" ;;
  esac
done

command -v node >/dev/null 2>&1 || die "node が必要です（Claude Code と同じ規則で encode するため）"
[ -n "$OLD" ] || { usage; die "--old は必須です"; }
[ -n "$NEW" ] || NEW="$PWD"

# 正規化: ~ 展開と末尾スラッシュ除去のみ（過剰正規化で CC の実 encode とズレないように最小限）
expand() { printf '%s' "${1/#\~/$HOME}"; }
strip_slash() {
  local p="$1"
  while [ "$p" != "/" ] && [ "${p%/}" != "$p" ]; do p="${p%/}"; done
  printf '%s' "$p"
}
OLD="$(strip_slash "$(expand "$OLD")")"
NEW="$(strip_slash "$(expand "$NEW")")"

case "$OLD" in /*) ;; *) die "--old は絶対パスで指定してください: $OLD" ;; esac
case "$NEW" in /*) ;; *) die "--new は絶対パスで指定してください: $NEW" ;; esac

# OLD/NEW を node 1 回起動でまとめて encode（encode 結果は [A-Za-z0-9-] のみなのでスペース区切りで安全）
read -r ENC_OLD ENC_NEW <<<"$(node -e 'const f=s=>String(s).replace(/[^a-zA-Z0-9]/g,"-");process.stdout.write(f(process.argv[1])+" "+f(process.argv[2]))' "$OLD" "$NEW")"
SRC="$PROJECTS_DIR/$ENC_OLD"
DEST="$PROJECTS_DIR/$ENC_NEW"

info "── 計画 ──────────────────────────────"
info "移動前パス : $OLD"
info "移動後パス : $NEW"
info "ログ元 dir : $SRC"
info "ログ先 dir : $DEST"
info "config移行 : $([ $UPDATE_CONFIG -eq 1 ] && echo 'する' || echo 'しない')"
info "モード     : $([ $DRY -eq 1 ] && echo 'dry-run（変更なし）' || echo '実行')"
info "──────────────────────────────────────"

[ "$ENC_OLD" != "$ENC_NEW" ] || die "移動前後が同じ encode 結果になります（${ENC_OLD}）。リネーム不要です。"

if [ ! -d "$SRC" ]; then
  warn "移動前のログ dir が見つかりません: $SRC"
  warn "--old のパス文字列が CC 起動時と一致していない可能性があります。"
  warn "下記から名前の断片で探してみてください（例: ls ~/.claude/projects | grep <断片>）:"
  ls "$PROJECTS_DIR" >&2 || true
  die "中断しました"
fi

# 健全性チェック（移動ではなくコピー/未移動を検知）
if [ -d "$OLD" ] && [ "$YES" -ne 1 ]; then
  warn "警告: 移動前パスにフォルダがまだ存在します（${OLD}）。"
  warn "      移動ではなくコピーの可能性があります。問題なければ --yes で続行。"
  [ $DRY -eq 1 ] || die "中断しました（--yes で続行可能）"
fi
if [ ! -d "$NEW" ] && [ "$YES" -ne 1 ]; then
  warn "警告: 移動後パスにフォルダが存在しません（${NEW}）。先にフォルダを移動してください。"
  [ $DRY -eq 1 ] || die "中断しました（--yes で続行可能）"
fi

mkdir -p "$BK_DIR"
TS="$(date +%Y%m%d-%H%M%S)"

migrate_logs() {
  if [ ! -e "$DEST" ]; then
    info "[ログ] 移動先が無い → 単純リネーム"
    [ $DRY -eq 1 ] && return 0
    mv "$SRC" "$DEST"
    info "[ログ] 完了: $DEST"
  else
    info "[ログ] 移動先が既存（新セッション作成済み等）→ マージ（移動先を優先・元はバックアップへ退避）"
    local collisions=""
    collisions="$(cd "$SRC" && find . -type f 2>/dev/null | while IFS= read -r f; do [ -e "$DEST/$f" ] && echo "$f"; done)" || true
    if [ -n "$collisions" ]; then
      info "[ログ] 同名ファイルあり（移動先を残し、元は退避先に保全）:"
      printf '%s\n' "$collisions" | sed 's/^/        /'
    fi
    [ $DRY -eq 1 ] && return 0
    # BSD(macOS) cp -n は既存スキップ時に終了コード1を返すため set -e 対策で || true
    cp -Rn "$SRC"/. "$DEST"/ || true
    mv "$SRC" "$BK_DIR/${ENC_OLD}.${TS}"
    info "[ログ] マージ完了: $DEST"
    info "[ログ] 元 dir を退避（復元可）: $BK_DIR/${ENC_OLD}.${TS}"
  fi
}

migrate_config() {
  [ -f "$CLAUDE_JSON" ] || { info "[config] ~/.claude.json が無いためスキップ"; return 0; }
  command -v jq >/dev/null 2>&1 || { info "[config] jq が無いためスキップ"; return 0; }
  if ! jq -e --arg old "$OLD" '(.projects // {}) | has($old)' "$CLAUDE_JSON" >/dev/null 2>&1; then
    info "[config] projects に移動前キーが無いためスキップ（${OLD}）"
    return 0
  fi
  info "[config] projects[\"$OLD\"] → projects[\"$NEW\"] へ移行"
  warn "         注意: Claude Code 起動中は次回フラッシュで上書きされ得ます。"
  warn "         確実に反映するには CC を完全終了してから実行してください。"
  [ $DRY -eq 1 ] && return 0
  cp "$CLAUDE_JSON" "$BK_DIR/claude.json.${TS}.bak"
  local tmp; tmp="$(mktemp)"
  # 上の has($old) ガードで $old の存在は確定済みなので bare 代入でよい
  jq --arg old "$OLD" --arg new "$NEW" \
    '.projects[$new] = (.projects[$new] // .projects[$old]) | del(.projects[$old])' \
    "$CLAUDE_JSON" > "$tmp"
  jq -e . "$tmp" >/dev/null 2>&1 || { rm -f "$tmp"; die "[config] 生成 JSON が不正。中断（バックアップ: $BK_DIR/claude.json.${TS}.bak）"; }
  mv "$tmp" "$CLAUDE_JSON"
  info "[config] 完了（バックアップ: $BK_DIR/claude.json.${TS}.bak）"
}

migrate_logs
if [ $UPDATE_CONFIG -eq 1 ]; then migrate_config; fi

if [ $DRY -eq 1 ]; then
  info "── dry-run 終了（変更は加えていません）──"
else
  info "── 完了 ──"
  if [ -d "$DEST" ]; then
    info "新ログ dir の中身（先頭のみ）:"
    ls -la "$DEST" | head -12 || true
  fi
fi
exit 0
