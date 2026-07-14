#!/bin/bash
# cc-fork-delete スキルの delete-fork.sh を、隔離サンドボックス($HOME偽装)で総当たり検証する。
# 実データは一切触らない。各ケースごとに使い捨ての SANDBOX を作る。
# check() は第 2 引数を eval する。OUT は eval 文字列内で参照されるため、
# 静的解析では未使用に見える（偽陽性）。ファイル全体で SC2034 を抑制する。
# shellcheck disable=SC2034
set -uo pipefail

# スクリプト自己位置基準で解決（symlink 経由・clone 先・~/.agents 経由のいずれでも動く）
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/delete-fork.sh"
PARENT_SID="11111111-1111-1111-1111-111111111111"
FORK_SID="22222222-2222-2222-2222-222222222222"
FORK2_SID="33333333-3333-3333-3333-333333333333"  # forkedFrom が dict 形式
NONFORK_SID="44444444-4444-4444-4444-444444444444" # forkedFrom なし(大元)
OTHER_SID="55555555-5555-5555-5555-555555555555"
FORKCHILD_SID="66666666-6666-6666-6666-666666666666" # フォークの子(孫フォーク) forkedFrom=FORK_SID
ORPHAN_SID="77777777-7777-7777-7777-777777777777"    # 親 transcript が存在しないフォーク
MISSING_SID="00000000-0000-0000-0000-000000000000"   # 実体のない親(欠落)

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf "  \033[32mPASS\033[0m %s\n" "$1"; }
ng()   { FAIL=$((FAIL+1)); printf "  \033[31mFAIL\033[0m %s\n" "$1"; }
check(){ if eval "$2"; then ok "$1"; else ng "$1  [条件: $2]"; fi; }

# サンドボックスを一式組み立てて、その HOME を echo する
# $1（任意）: grandchild=孫フォークを足す / orphan=親 transcript 欠落フォークを足す
make_sandbox() {
  local EXTRA="${1:-}"
  local SB; SB=$(mktemp -d)
  local PROJ="$SB/.claude/projects/-demo-project"
  mkdir -p "$PROJ" "$SB/.claude/sessions" "$SB/.claude/.trash"
  local VAULT="$SB/vault"; mkdir -p "$VAULT/Log/Session/_Index"

  # 親(大元) transcript
  printf '%s\n' '{"sessionId":"'"$PARENT_SID"'","type":"summary"}' > "$PROJ/$PARENT_SID.jsonl"
  # フォーク transcript (forkedFrom = 文字列)
  printf '%s\n' '{"sessionId":"'"$FORK_SID"'","forkedFrom":"'"$PARENT_SID"'"}' > "$PROJ/$FORK_SID.jsonl"
  # フォーク transcript (forkedFrom = dict)
  printf '%s\n' '{"sessionId":"'"$FORK2_SID"'","forkedFrom":{"sessionId":"'"$PARENT_SID"'","messageUuid":"abc"}}' > "$PROJ/$FORK2_SID.jsonl"
  # 大元(forkedFrom なし)
  printf '%s\n' '{"sessionId":"'"$NONFORK_SID"'","type":"summary"}' > "$PROJ/$NONFORK_SID.jsonl"
  # 付随ディレクトリ(subagents 等)
  mkdir -p "$PROJ/$FORK_SID"; echo "sub" > "$PROJ/$FORK_SID/agent.jsonl"

  # sessions メタ: フォークのものと、別 sid のもの(消えてはいけない)
  printf '%s\n' '{"sessionId":"'"$FORK_SID"'"}' > "$SB/.claude/sessions/fork.json"
  printf '%s\n' '{"sessionId":"'"$OTHER_SID"'"}' > "$SB/.claude/sessions/other.json"

  # Vault 索引: フォーク行 + 別 sid 行(残るべき)
  cat > "$VAULT/Log/Session/_Index/2026-06.md" <<EOF
- $FORK_SID  フォークのログ
- $OTHER_SID 別セッションのログ
EOF
  # Vault 全文ログ: ヘッダ一致(消える) / 本文だけ言及(残る) / 別 sid(残る)
  printf '%s\n' "**セッションID**: $FORK_SID" "本文" > "$VAULT/Log/Session/fork-log.md"
  printf '%s\n' "**セッションID**: $OTHER_SID" "本文中に $FORK_SID が出てくるだけ" > "$VAULT/Log/Session/mention-only.md"

  # 系図テスト用の追加フィクスチャ（既定では作らない）
  case "$EXTRA" in
    grandchild)  # フォークの子(孫フォーク): forkedFrom=FORK_SID → 削除対象の子孫
      printf '%s\n' '{"sessionId":"'"$FORKCHILD_SID"'","forkedFrom":"'"$FORK_SID"'"}' > "$PROJ/$FORKCHILD_SID.jsonl" ;;
    orphan)      # 親 transcript が存在しないフォーク
      printf '%s\n' '{"sessionId":"'"$ORPHAN_SID"'","forkedFrom":"'"$MISSING_SID"'"}' > "$PROJ/$ORPHAN_SID.jsonl" ;;
  esac

  # mtime を古くして「直近更新」警告を避ける
  find "$SB" -exec touch -t 202601010000 {} + 2>/dev/null
  printf '%s' "$SB"
}

run() { # HOME と VAULT を偽装してスクリプト実行。$1=HOME 以降=引数
  local SB="$1"; shift
  HOME="$SB" CLAUDE_SESSION_INDEX_VAULT="$SB/vault" CLAUDE_CODE_SESSION_ID="" \
    bash "$SCRIPT" "$@" 2>"$SB/stderr.txt"
}

echo "=============================================="
echo " cc-fork-delete サンドボックス検証"
echo "=============================================="

############################################
echo; echo "■ ケース1: dry-run プレビュー (フォーク・文字列 forkedFrom)"
SB=$(make_sandbox)
OUT=$(run "$SB" "$FORK_SID"); RC=$?
check "exit 0 で正常終了"                     "[ $RC -eq 0 ]"
check "フォーク元として親 sid を表示"          "echo \"\$OUT\" | grep -q '$PARENT_SID'"
check "方式=ゴミ箱退避 と表示"                 "echo \"\$OUT\" | grep -q 'ゴミ箱退避'"
check "transcript を削除対象に列挙"            "echo \"\$OUT\" | grep -q '$FORK_SID.jsonl'"
check "付随ディレクトリを列挙"                 "echo \"\$OUT\" | grep -q '/$FORK_SID\$'"
check "全文ログ fork-log.md を列挙"            "echo \"\$OUT\" | grep -q 'fork-log.md'"
check "本文言及のみの mention-only は出さない"  "! echo \"\$OUT\" | grep -q 'mention-only.md'"
check "索引ヒットを表示"                       "echo \"\$OUT\" | grep -q '2026-06.md'"
check "dry-run の案内文を表示"                 "echo \"\$OUT\" | grep -q 'dry-run'"
check "実データはまだ存在(削除されてない)"      "[ -f '$SB/.claude/projects/-demo-project/$FORK_SID.jsonl' ]"
rm -rf "$SB"

############################################
echo; echo "■ ケース2: forkedFrom が dict 形式でも親を解決できる"
SB=$(make_sandbox)
OUT=$(run "$SB" "$FORK2_SID"); RC=$?
check "exit 0"                                "[ $RC -eq 0 ]"
check "dict から親 sid を抽出"                 "echo \"\$OUT\" | grep -q 'フォーク元(残す) : $PARENT_SID'"
rm -rf "$SB"

############################################
echo; echo "■ ケース3: ガード — UUID 形式でない"
SB=$(make_sandbox)
OUT=$(run "$SB" "not-a-uuid"); RC=$?
check "exit 2"                                "[ $RC -eq 2 ]"
check "UUID 形式エラーを出力"                  "grep -q 'UUID 形式' '$SB/stderr.txt'"
rm -rf "$SB"

############################################
echo; echo "■ ケース4: ガード — transcript が存在しない"
SB=$(make_sandbox)
OUT=$(run "$SB" "99999999-9999-9999-9999-999999999999"); RC=$?
check "exit 4"                                "[ $RC -eq 4 ]"
check "transcript 無しエラー"                 "grep -q 'transcript が見つかりません' '$SB/stderr.txt'"
rm -rf "$SB"

############################################
echo; echo "■ ケース5: ガード — 大元(forkedFrom なし)は中止"
SB=$(make_sandbox)
OUT=$(run "$SB" "$NONFORK_SID"); RC=$?
check "exit 5"                                "[ $RC -eq 5 ]"
check "フォークでない旨を警告"                 "grep -q 'forkedFrom がありません' '$SB/stderr.txt'"
check "大元 transcript は無傷"                 "[ -f '$SB/.claude/projects/-demo-project/$NONFORK_SID.jsonl' ]"
rm -rf "$SB"

############################################
echo; echo "■ ケース6: ガード — 現在実行中セッションは消せない"
SB=$(make_sandbox)
OUT=$(HOME="$SB" CLAUDE_SESSION_INDEX_VAULT="$SB/vault" CLAUDE_CODE_SESSION_ID="$FORK_SID" \
       bash "$SCRIPT" "$FORK_SID" --apply 2>"$SB/stderr.txt"); RC=$?
check "exit 3"                                "[ $RC -eq 3 ]"
check "自分自身は削除不可エラー"               "grep -q '自分自身は削除できません' '$SB/stderr.txt'"
check "復帰コマンドを案内"                     "grep -q 'claude -r $PARENT_SID' '$SB/stderr.txt'"
check "フォークは無傷(消えてない)"             "[ -f '$SB/.claude/projects/-demo-project/$FORK_SID.jsonl' ]"
rm -rf "$SB"

############################################
echo; echo "■ ケース7: --apply ゴミ箱退避(復元可)"
SB=$(make_sandbox)
OUT=$(run "$SB" "$FORK_SID" --apply); RC=$?
P="$SB/.claude/projects/-demo-project"
check "exit 0"                                "[ $RC -eq 0 ]"
check "フォーク transcript が消えた"           "[ ! -f '$P/$FORK_SID.jsonl' ]"
check "付随ディレクトリが消えた"               "[ ! -d '$P/$FORK_SID' ]"
check "★親(大元)は残っている"                 "[ -f '$P/$PARENT_SID.jsonl' ]"
check "フォークの sessions メタが消えた"       "[ ! -f '$SB/.claude/sessions/fork.json' ]"
check "★別 sid の sessions メタは残る"        "[ -f '$SB/.claude/sessions/other.json' ]"
check "全文ログ fork-log.md が消えた"          "[ ! -f '$SB/vault/Log/Session/fork-log.md' ]"
check "★本文言及のみログは残る"              "[ -f '$SB/vault/Log/Session/mention-only.md' ]"
check "索引ファイル自体は残る"                 "[ -f '$SB/vault/Log/Session/_Index/2026-06.md' ]"
check "索引からフォーク行が消えた"             "! grep -q '$FORK_SID' '$SB/vault/Log/Session/_Index/2026-06.md'"
check "★索引の別 sid 行は残る"               "grep -q '$OTHER_SID' '$SB/vault/Log/Session/_Index/2026-06.md'"
check "退避先 .trash が作られた"               "[ -d \"\$(ls -d $SB/.claude/.trash/forks/${FORK_SID}_* 2>/dev/null | head -1)\" ]"
check "退避先に transcript が復元可能な形で存在" "find '$SB/.claude/.trash' -name '$FORK_SID.jsonl' | grep -q ."
check "退避先に索引バックアップが存在"          "find '$SB/.claude/.trash' -path '*_index-backup*' -name '2026-06.md' | grep -q ."
rm -rf "$SB"

############################################
echo; echo "■ ケース8: --apply --purge 完全削除(退避先を作らない)"
SB=$(make_sandbox)
OUT=$(run "$SB" "$FORK_SID" --apply --purge); RC=$?
check "exit 0"                                "[ $RC -eq 0 ]"
check "フォーク transcript が消えた"           "[ ! -f '$SB/.claude/projects/-demo-project/$FORK_SID.jsonl' ]"
check "★親は残っている"                       "[ -f '$SB/.claude/projects/-demo-project/$PARENT_SID.jsonl' ]"
check "退避先(.trash/forks)は作られない"       "[ -z \"\$(ls $SB/.claude/.trash/forks 2>/dev/null)\" ]"
check "プレビューに「完全削除」と表示"          "echo \"\$OUT\" | grep -q '完全削除'"
rm -rf "$SB"

############################################
echo; echo "■ ケース9: ガード — 不明な引数"
SB=$(make_sandbox)
OUT=$(run "$SB" "$FORK_SID" --force); RC=$?
check "exit 2"                                "[ $RC -eq 2 ]"
check "不明な引数エラー"                       "grep -q '不明な引数' '$SB/stderr.txt'"
rm -rf "$SB"

############################################
echo; echo "■ ケース10: Vault が無い環境でも淡々と動く"
SB=$(make_sandbox)
rm -rf "$SB/vault"
OUT=$(run "$SB" "$FORK_SID"); RC=$?
check "exit 0(Vault 無しでも止まらない)"        "[ $RC -eq 0 ]"
check "全文ログは(なし)表示"                    "echo \"\$OUT\" | grep -A1 '全文ログ' | grep -q 'なし'"
check "索引は(なし)表示"                        "echo \"\$OUT\" | grep -A1 '索引' | grep -q 'なし'"
rm -rf "$SB"

############################################
echo; echo "■ ケース11: 系図セクション（削除対象=✗ / 大元=●）"
SB=$(make_sandbox)
OUT=$(run "$SB" "$FORK_SID"); RC=$?
check "exit 0"                                "[ $RC -eq 0 ]"
check "フォーク系図セクションを出力"            "echo \"\$OUT\" | grep -q 'フォーク系図'"
check "削除対象に ✗ マーカー"                  "echo \"\$OUT\" | grep -q '✗ ${FORK_SID:0:8}'"
check "大元に ● マーカー"                      "echo \"\$OUT\" | grep -q '● ${PARENT_SID:0:8}'"
check "[削除対象] 注記を表示"                   "echo \"\$OUT\" | grep -qF '[削除対象]'"
check "兄弟フォークは残す注記(○)"              "echo \"\$OUT\" | grep -q '○ ${FORK2_SID:0:8}'"
check "系図構築失敗メッセージは出ない"          "! echo \"\$OUT\" | grep -q '系図を構築できませんでした'"
rm -rf "$SB"

############################################
echo; echo "■ ケース12: フォークのフォーク（⚠ と子フォーク WARNING・ブロックしない）"
SB=$(make_sandbox grandchild)
OUT=$(run "$SB" "$FORK_SID"); RC=$?
check "exit 0（警告のみで中止しない）"          "[ $RC -eq 0 ]"
check "子孫フォークに ⚠ マーカー"              "echo \"\$OUT\" | grep -q '⚠ ${FORKCHILD_SID:0:8}'"
check "子フォーク WARNING（件数表示）"          "echo \"\$OUT\" | grep -q '子フォークが 1 件'"
check "削除を中止しない旨を明記"                "echo \"\$OUT\" | grep -q '中止しません'"
rm -rf "$SB"
# --apply でも子フォーク警告は削除をブロックしない（子の transcript は残る）
SB=$(make_sandbox grandchild)
OUT=$(run "$SB" "$FORK_SID" --apply); RC=$?
P="$SB/.claude/projects/-demo-project"
check "exit 0（--apply も完走）"               "[ $RC -eq 0 ]"
check "削除対象フォークが消えた"                "[ ! -f '$P/$FORK_SID.jsonl' ]"
check "★子フォークの transcript は残る"        "[ -f '$P/$FORKCHILD_SID.jsonl' ]"
check "★親(大元)は残る"                        "[ -f '$P/$PARENT_SID.jsonl' ]"
rm -rf "$SB"

############################################
echo; echo "■ ケース13: --tree-all で家系外の別ルートも表示"
SB=$(make_sandbox)
OUT=$(run "$SB" "$FORK_SID" --tree-all); RC=$?
check "exit 0"                                "[ $RC -eq 0 ]"
check "家系外ルート(大元)も ● で表示"          "echo \"\$OUT\" | grep -q '● ${NONFORK_SID:0:8}'"
rm -rf "$SB"
# 既定（--tree-all なし）では家系外ルートは描かない
SB=$(make_sandbox)
OUT=$(run "$SB" "$FORK_SID"); RC=$?
check "★既定では家系外ルートを出さない"        "! echo \"\$OUT\" | grep -q '${NONFORK_SID:0:8}'"
rm -rf "$SB"

############################################
echo; echo "■ ケース14: 親 transcript 欠落でも系図が落ちず削除フロー続行"
SB=$(make_sandbox orphan)
OUT=$(run "$SB" "$ORPHAN_SID"); RC=$?
check "exit 0（dry-run 続行）"                 "[ $RC -eq 0 ]"
check "系図セクションは出力される"              "echo \"\$OUT\" | grep -q 'フォーク系図'"
check "系図構築失敗にならない"                  "! echo \"\$OUT\" | grep -q '系図を構築できませんでした'"
check "親 transcript 欠落の注記を表示"          "echo \"\$OUT\" | grep -q '親 transcript 欠落'"
rm -rf "$SB"
# --apply も欠落フォークを完走して削除できる
SB=$(make_sandbox orphan)
OUT=$(run "$SB" "$ORPHAN_SID" --apply); RC=$?
check "exit 0（--apply 完走）"                 "[ $RC -eq 0 ]"
check "欠落フォークの transcript が消えた"       "[ ! -f '$SB/.claude/projects/-demo-project/$ORPHAN_SID.jsonl' ]"
rm -rf "$SB"

echo
echo "=============================================="
printf " 結果: \033[32m%d PASS\033[0m / \033[31m%d FAIL\033[0m\n" "$PASS" "$FAIL"
echo "=============================================="
[ $FAIL -eq 0 ]
