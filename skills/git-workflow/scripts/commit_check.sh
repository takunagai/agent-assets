#!/bin/bash
# commit_check.sh - コミット前チェックスクリプト
# Usage: ./commit_check.sh [options]
#   --skip-build    ビルドチェックをスキップ
#   --skip-test     テストをスキップ
#   --skip-lint     Lint チェックをスキップ

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Options
SKIP_BUILD=false
SKIP_TEST=false
SKIP_LINT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build) SKIP_BUILD=true; shift ;;
        --skip-test) SKIP_TEST=true; shift ;;
        --skip-lint) SKIP_LINT=true; shift ;;
        *) shift ;;
    esac
done

echo "========================================"
echo "  コミット前チェック開始"
echo "========================================"

ERRORS=0

# ----------------------------------------
# 1. ハードコードされた値のチェック
# ----------------------------------------
echo -e "\n${YELLOW}[1/5] ハードコードチェック${NC}"

PATTERNS=(
    "password\s*=\s*['\"][^'\"]+['\"]"
    "api[_-]?key\s*=\s*['\"][^'\"]+['\"]"
    "secret\s*=\s*['\"][^'\"]+['\"]"
    "token\s*=\s*['\"][^'\"]+['\"]"
    "private[_-]?key"
)

STAGED_FILES=$(git diff --cached --name-only)
HARDCODE_FOUND=false
if [ -n "$STAGED_FILES" ]; then
    for pattern in "${PATTERNS[@]}"; do
        if echo "$STAGED_FILES" | xargs grep -l -i -E "$pattern" 2>/dev/null; then
            HARDCODE_FOUND=true
        fi
    done
fi

if [ "$HARDCODE_FOUND" = true ]; then
    echo -e "${RED}[FAIL] ハードコードされた機密情報が見つかりました${NC}"
    ((ERRORS++))
else
    echo -e "${GREEN}[OK] ハードコードなし${NC}"
fi

# ----------------------------------------
# 2. デバッグコードのチェック
# ----------------------------------------
echo -e "\n${YELLOW}[2/5] デバッグコードチェック${NC}"

DEBUG_PATTERNS=(
    "console\.log"
    "console\.debug"
    "debugger;"
    "print("
    "puts "
    "var_dump"
    "dd("
)

DEBUG_FOUND=false
for pattern in "${DEBUG_PATTERNS[@]}"; do
    MATCHES=$(git diff --cached -G"$pattern" --name-only 2>/dev/null || true)
    if [ -n "$MATCHES" ]; then
        echo -e "${YELLOW}  警告: $pattern が見つかりました:${NC}"
        echo "$MATCHES" | while read -r file; do
            echo "    - $file"
        done
        DEBUG_FOUND=true
    fi
done

if [ "$DEBUG_FOUND" = true ]; then
    echo -e "${YELLOW}[WARN] デバッグコードが残っている可能性があります（確認してください）${NC}"
else
    echo -e "${GREEN}[OK] デバッグコードなし${NC}"
fi

# ----------------------------------------
# 3. Lint チェック
# ----------------------------------------
if [ "$SKIP_LINT" = false ]; then
    echo -e "\n${YELLOW}[3/5] Lint チェック${NC}"
    
    if [ -f "package.json" ] && grep -q '"lint"' package.json; then
        npm run lint && echo -e "${GREEN}[OK] Lint passed${NC}" || { echo -e "${RED}[FAIL] Lint エラー${NC}"; ((ERRORS++)); }
    elif [ -f "Cargo.toml" ]; then
        cargo fmt --check && cargo clippy && echo -e "${GREEN}[OK] Lint passed${NC}" || { echo -e "${RED}[FAIL] Lint エラー${NC}"; ((ERRORS++)); }
    elif [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
        if command -v ruff &> /dev/null; then
            ruff check . && echo -e "${GREEN}[OK] Lint passed${NC}" || { echo -e "${RED}[FAIL] Lint エラー${NC}"; ((ERRORS++)); }
        elif command -v flake8 &> /dev/null; then
            flake8 . && echo -e "${GREEN}[OK] Lint passed${NC}" || { echo -e "${RED}[FAIL] Lint エラー${NC}"; ((ERRORS++)); }
        else
            echo -e "${YELLOW}[SKIP] Python linter が見つかりません${NC}"
        fi
    else
        echo -e "${YELLOW}[SKIP] Lint 設定が見つかりません${NC}"
    fi
else
    echo -e "\n${YELLOW}[3/5] Lint チェック - スキップ${NC}"
fi

# ----------------------------------------
# 4. テスト
# ----------------------------------------
if [ "$SKIP_TEST" = false ]; then
    echo -e "\n${YELLOW}[4/5] テスト実行${NC}"
    
    if [ -f "package.json" ] && grep -q '"test"' package.json; then
        npm test && echo -e "${GREEN}[OK] テスト passed${NC}" || { echo -e "${RED}[FAIL] テスト失敗${NC}"; ((ERRORS++)); }
    elif [ -f "Cargo.toml" ]; then
        cargo test && echo -e "${GREEN}[OK] テスト passed${NC}" || { echo -e "${RED}[FAIL] テスト失敗${NC}"; ((ERRORS++)); }
    elif [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
        if command -v pytest &> /dev/null; then
            pytest && echo -e "${GREEN}[OK] テスト passed${NC}" || { echo -e "${RED}[FAIL] テスト失敗${NC}"; ((ERRORS++)); }
        else
            echo -e "${YELLOW}[SKIP] pytest が見つかりません${NC}"
        fi
    else
        echo -e "${YELLOW}[SKIP] テスト設定が見つかりません${NC}"
    fi
else
    echo -e "\n${YELLOW}[4/5] テスト - スキップ${NC}"
fi

# ----------------------------------------
# 5. ビルド
# ----------------------------------------
if [ "$SKIP_BUILD" = false ]; then
    echo -e "\n${YELLOW}[5/5] ビルドチェック${NC}"
    
    if [ -f "package.json" ] && grep -q '"build"' package.json; then
        npm run build && echo -e "${GREEN}[OK] ビルド成功${NC}" || { echo -e "${RED}[FAIL] ビルド失敗${NC}"; ((ERRORS++)); }
    elif [ -f "Cargo.toml" ]; then
        cargo build && echo -e "${GREEN}[OK] ビルド成功${NC}" || { echo -e "${RED}[FAIL] ビルド失敗${NC}"; ((ERRORS++)); }
    elif [ -f "go.mod" ]; then
        go build ./... && echo -e "${GREEN}[OK] ビルド成功${NC}" || { echo -e "${RED}[FAIL] ビルド失敗${NC}"; ((ERRORS++)); }
    else
        echo -e "${YELLOW}[SKIP] ビルド設定が見つかりません${NC}"
    fi
else
    echo -e "\n${YELLOW}[5/5] ビルド - スキップ${NC}"
fi

# ----------------------------------------
# 結果サマリ
# ----------------------------------------
echo -e "\n========================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}  全チェック完了 - コミット可能です${NC}"
    echo "========================================"
    exit 0
else
    echo -e "${RED}  $ERRORS 件のエラーがあります${NC}"
    echo "========================================"
    exit 1
fi
