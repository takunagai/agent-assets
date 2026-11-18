#!/usr/bin/env bash
# Paradev のローカルワークスペース作成時に 1 回走るセットアップ（雛形: paradev-workspace-setup スキル）
#
# 使い方: 「要編集」の箇所をプロジェクトに合わせ、使わない節は消す。
# 設定に入れるのは次の 1 行だけ。設定画面の欄は 1 行 = 1 コマンドとして保存・連結されるので、この本体を欄に貼らない。
#   このマシンだけ（このファイルが gitignore 済みでメインにだけある）: bash "$SUPERSET_ROOT_PATH/.paradev/setup.sh"
#   チームで共有（このファイルをコミットする）:                   bash ./.paradev/setup.sh
#
# 出力の決まり（確認用のポーリングが読む）:
#   copied: <名前> / skip: <理由> / setup failed: <理由> / 最後に setup done
#
# macOS の /bin/bash 3.2 でも動くように書く（空の配列は ${a[@]+"${a[@]}"} で展開する）。
set -Eeuo pipefail
on_error() {
	local exit_code=$?
	echo "setup failed: $1 行目のコマンドが失敗（終了コード ${exit_code}）" >&2
}
trap 'on_error "$LINENO"' ERR

# ===== 要編集: このプロジェクトに合わせる =====
# ルートにあるはずのファイル（ロックファイル等）。cwd がリポジトリのルートかを確かめる
ROOT_MARKERS=(package.json)
# メインから複製する gitignore 済みの秘密ファイル（ルートからの相対パス。無ければ空の () にする）
SECRET_FILES=(.env)
# メインから複製するローカル状態のフォルダ（ルートからの相対パス。例: .wrangler/state。無ければ空の () にする）
STATE_DIRS=()
# 最後に表示する案内。"setup done" で始める（確認用のポーリングがこの文言で完了を判定する）
DONE_MESSAGE="setup done: pnpm dev で起動（使用中のポートは dev サーバーがずらすか、--port で指定する）"
# ==============================================

# 依存関係の準備（要編集: 使うものだけ残す。手掛かりは stack-recipes.md）
install_dependencies() {
	# mise install                                  # mise.toml / .tool-versions で版を固定しているとき
	# mise exec -- pnpm install --frozen-lockfile   # mise の版で pnpm を動かす
	# pnpm install --frozen-lockfile
	# npm ci
	# uv sync --frozen
	echo "setup failed: install_dependencies が未編集（setup-template.sh の要編集箇所を埋める）" >&2
	return 1
}

# --- ここから下は通常は編集しない ---

# ルートからの相対パスだけを受け付ける（絶対パスや .. で外へ出る指定を止める）
require_relative_path() {
	case "$1" in
	"" | /* | ..* | */..*)
		echo "setup failed: ルートからの相対パスで書く: '$1'" >&2
		exit 1
		;;
	esac
}

# 秘密ファイルを値を読まずにファイルごと複製する。既にあれば上書きしない
copy_secret_file() {
	local file="$1"
	require_relative_path "$file"
	if [ ! -f "$ROOT/$file" ]; then
		echo "skip: メインに $file が無い"
		return 0
	fi
	# リンク切れの symlink も「ある」と扱う（-e だけだと無いと判定して上書きする）
	if [ -e "$file" ] || [ -L "$file" ]; then
		echo "skip: $file は既にある（上書きしない）"
		return 0
	fi
	mkdir -p "$(dirname "$file")"
	# cp -p は元の権限・ACL を写すので使わない。作った直後から本人だけが読める権限にする
	(umask 077 && cp "$ROOT/$file" "$file")
	chmod 600 "$file"
	echo "copied: $file"
}

# 同じボリュームならクローンで複製する（容量を使わず速い）
clone_copy() {
	if [ "$(uname -s)" = "Darwin" ]; then
		# macOS: clonefile が使えなければ cp 自身が通常のコピーに切り替える
		cp -Rpc "$1" "$2"
	else
		# GNU coreutils。--reflink を持たない cp の環境では --reflink=auto を消す
		cp -Rp --reflink=auto "$1" "$2"
	fi
}

# 複製した SQLite を検査する（dev 稼働中のコピーで db・wal・shm の時点が食い違うと壊れることがある）
check_sqlite_files() {
	local database result
	if ! command -v sqlite3 >/dev/null 2>&1; then
		echo "skip: sqlite3 が無いので $1 の検査を飛ばす"
		return 0
	fi
	while IFS= read -r -d '' database; do
		# 先頭が SQLite のヘッダーのファイルだけを検査する（拡張子に頼らない）
		[ "$(head -c 15 "$database" 2>/dev/null)" = "SQLite format 3" ] || continue
		result="$(sqlite3 "$database" 'PRAGMA integrity_check;' 2>&1 || true)"
		if [ "$result" != "ok" ]; then
			echo "setup failed: 複製した $database の検査に失敗。メインの dev を止めてからワークスペースを作り直す" >&2
			exit 1
		fi
	done < <(find "$1" -type f ! -name '*-wal' ! -name '*-shm' ! -name '*-journal' -print0)
}

# ローカル状態を一時フォルダ経由で複製し、検査に通ってから入れ替える
copy_state_dir() {
	local dir="${1%/}" staging
	require_relative_path "$dir"
	staging="$dir.copying"
	if [ ! -d "$ROOT/$dir" ]; then
		echo "skip: メインに $dir が無い"
		return 0
	fi
	if [ -e "$dir" ] || [ -L "$dir" ]; then
		echo "skip: $dir は既にある（上書きしない。セットアップより先に dev を起動して空の状態ができた場合は、それを消して作り直す）"
		return 0
	fi
	mkdir -p "$(dirname "$dir")"
	# 前回の中断で残った作りかけを消す（このスクリプトが作る一時フォルダだけ）
	rm -rf -- "$staging"
	clone_copy "$ROOT/$dir" "$staging"
	check_sqlite_files "$staging"
	mv "$staging" "$dir"
	echo "copied: $dir"
}

# --- 0. 実行場所の確認 ---
# cloud との一致だけで判定する（2.0.9 のアプリの端末では SUPERSET_ENV=production が入っていて、local ではない）
if [ "${SUPERSET_ENV:-}" = "cloud" ]; then
	echo "setup failed: ローカル用のスクリプト（クラウドは別に用意する）" >&2
	exit 1
fi
ROOT="${SUPERSET_ROOT_PATH:?setup failed: SUPERSET_ROOT_PATH が未設定（Paradev のワークスペース作成以外で実行された）}"

for marker in ${ROOT_MARKERS[@]+"${ROOT_MARKERS[@]}"}; do
	if [ ! -e "$marker" ]; then
		echo "setup failed: cwd がリポジトリのルートではない（$marker が無い）: $PWD" >&2
		exit 1
	fi
done
if [ "$(pwd -P)" = "$(cd "$ROOT" && pwd -P)" ]; then
	echo "skip: メインのチェックアウトなので何もしない"
	exit 0
fi

# --- 1. ツールの PATH（要編集: バージョン管理ツールを使わなければ消す）---
# Paradev の端末の PATH に mise 等が無いときの保険
if ! command -v mise >/dev/null 2>&1; then
	PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
fi

# --- 2. 秘密ファイルをメインから複製 ---
for file in ${SECRET_FILES[@]+"${SECRET_FILES[@]}"}; do
	copy_secret_file "$file"
done

# --- 3. ローカル状態をメインから複製 ---
for dir in ${STATE_DIRS[@]+"${STATE_DIRS[@]}"}; do
	copy_state_dir "$dir"
done

# --- 4. 依存関係（install の postinstall が秘密ファイルを読むことがあるので複製の後に置く）---
install_dependencies

echo "$DONE_MESSAGE"
