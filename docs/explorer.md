# explorer

複数ファイルにまたがる調査・仕様/ドキュメント読解・ログ調査・Web リサーチなど、**読み取り専用の探索**を独立コンテキストで引き受ける Claude Code サブエージェントです。親セッションに raw dump を持ち帰らず、`path:line` 参照付きの構造化サマリのみを返します。

このリポジトリの多くの収録物が「スキル（`skills/<name>/`）」なのに対し、これは**サブエージェント（単一の `.md` ファイル）**です。独立したコンテキストで動くため、探索作業で親セッションのコンテキストを消費しません。

> [!note] scanner との違い
> explorer は**意味理解を伴う調査**（仕様理解、ログの解釈、Web での裏取り）を担当します。解釈を要さない機械的な grep 列挙・件数集計は [`scanner`](scanner.md) の領分です。迷ったら「読んで判断が要るか」で切り分けます。

---

## 対応／前提

| 項目 | 内容 |
|------|------|
| 対応エージェント | Claude Code 専用（frontmatter の `tools` / `model` / `effort` / `color` が Claude Code サブエージェント形式） |
| model | sonnet |
| effort | medium |
| tools | Read, Grep, Glob, Bash, WebFetch, WebSearch（Edit / Write は持たない） |

---

## インストール

このリポジトリを clone し、エージェント本体（`agents/explorer.md`）を `~/.claude/agents/` へ symlink します。実体は 1 つ、参照を張る方式です。

```bash
git clone git@github.com:takunagai/agent-assets.git ~/Projects/agent-assets
ln -s ~/Projects/agent-assets/agents/explorer.md ~/.claude/agents/explorer.md
```

プロジェクト単位で使う場合は `<repo>/.claude/agents/` へ同様に symlink します。

---

## 使い方

### 自動委譲（通常はこちら）

「複数ファイルを横断して調べて」「仕様・ドキュメントを読み込んで要点を掴んで」「ログを調査して」「Web で裏取りして」のような発話で、メインセッションが自動的にこのエージェントへ委譲します。読み取り専用ツールを 8 回以上連続で使う見込み、または 5 ファイル以上を読む調査は委譲が原則です。

```
この仕様変更が影響するファイルを全部洗い出して
```

```
このログから直近のエラー傾向を調べて
```

### 明示指定

```
@explorer でこのライブラリの使われ方を調べて
```

### 起動しない場面

- ファイルの編集・作成（親セッションが行う。explorer は Edit / Write を持たない）
- 解釈を要さない機械的な grep 列挙・件数集計（[`scanner`](scanner.md) の領分）
- 記事執筆前の素材収集（`article-researcher` の領分）

---

## 返却フォーマット

常に次の 3 セクション構成で返します（共通様式の正本は `~/.claude/rules/agent-output-contract.md`）。

```
## 結論
（1〜3 行。質問への直接回答）

## 根拠
- path/to/file.ts:42 ─ 該当箇所の要旨と判定（確信度: 高 / 中 / 低）

## 未確認・注意点
- （調べきれなかった点・空振りした検索語・矛盾する情報。無ければ「なし」と明記）
```

推測と実測を区別し、未確認事項は「未確認」と明示します。確信度は 高（実測・原文確認）/ 中（間接確認）/ 低（推測）の 3 値です。

---

## 詳細

行動原則（mutation 禁止・raw dump 返却禁止・網羅性より情報密度優先）の全文はエージェント本体 [`agents/explorer.md`](../agents/explorer.md) を参照してください。
