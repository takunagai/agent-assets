# scanner

解釈を伴わない**機械的スキャン**（網羅的な grep 列挙・ファイル件数集計・出現回数の集計・シンボル使用箇所の列挙）を独立コンテキストで引き受ける Claude Code サブエージェントです。列挙と集計だけを行い、意味の判断はしません。

このリポジトリの多くの収録物が「スキル（`skills/<name>/`）」なのに対し、これは**サブエージェント（単一の `.md` ファイル）**です。独立したコンテキストで動くため、機械的な調査で親セッションのコンテキストを消費しません。

> [!note] explorer との違い
> scanner は**解釈を要さない**列挙・集計専任です。意味理解を伴う調査（仕様理解、ログの解釈、Web 裏取り）は [`explorer`](explorer.md) の領分です。scanner は判断が必要になった時点で自ら explorer への委譲を提案し、自分では判断しません。

---

## 対応／前提

| 項目 | 内容 |
|------|------|
| 対応エージェント | Claude Code 専用（frontmatter の `tools` / `model` / `effort` / `color` が Claude Code サブエージェント形式） |
| model | haiku（機械的作業のため最小コスト） |
| effort | low |
| tools | Grep, Glob, Bash（読み取り集計コマンドのみ。Edit / Write は持たない） |

---

## インストール

このリポジトリを clone し、エージェント本体（`agents/scanner.md`）を `~/.claude/agents/` へ symlink します。実体は 1 つ、参照を張る方式です。

```bash
git clone git@github.com:takunagai/agent-assets.git ~/Projects/agent-assets
ln -s ~/Projects/agent-assets/agents/scanner.md ~/.claude/agents/scanner.md
```

プロジェクト単位で使う場合は `<repo>/.claude/agents/` へ同様に symlink します。

---

## 使い方

### 自動委譲（通常はこちら）

「この関数の使用箇所を全部列挙して」「◯◯ が何ファイルにあるか数えて」「TODO を全部リストアップして」のような、解釈不要の機械的列挙・集計依頼で、メインセッションが自動的にこのエージェントへ委譲します。

```
このプロジェクトで console.log が何箇所あるか数えて
```

```
FIXME コメントを全部列挙して
```

### 明示指定

```
@scanner でこの関数の呼び出し箇所を全部リストして
```

### 起動しない場面

- ファイルの編集・作成（scanner は Edit / Write を持たない）
- 意味理解や妥当性判断が必要な調査（[`explorer`](explorer.md) の領分）

---

## 返却フォーマット

「件数 → 結果（`path:line` リスト）→ 未確認」の 3 セクション構成で返します（共通様式の正本は `~/.claude/rules/agent-output-contract.md`。scanner は列挙専任のため簡略版）。

- 結果は `path:line` の簡潔なリスト、または件数表で返します
- ヒットが大量（100 件超）の場合は件数 + 代表例 10 件に圧縮し、全量が必要かは親に委ねます。圧縮・打ち切りした範囲は `未確認` 欄に明記します（無ければ「なし」）
- 意味の解釈が必要になった場合は、その旨を明記し explorer への委譲を提案します（自分では判断しません）

---

## 詳細

行動原則の全文はエージェント本体 [`agents/scanner.md`](../agents/scanner.md) を参照してください。
