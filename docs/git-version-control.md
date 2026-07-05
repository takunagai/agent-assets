# git-version-control

コミット・ブランチ・PR など **Git 操作を独立コンテキストで実行する** Claude Code サブエージェントです。手順（Conventional Commits 形式の日本語コミット、ブランチ命名、コミット粒度、コミット前チェック）はプリロードされた [`git-workflow`](git-workflow.md) スキルに従います。作業単位が完了したときはプロアクティブに起動して、コミットを提案・実行します。

このリポジトリの多くの収録物が「スキル（`skills/<name>/`）」なのに対し、これは**サブエージェント（単一の `.md` ファイル）**です。独立したコンテキストで動くため、コミット作業で親セッションのコンテキストを消費しません。管理ルール（実体はリポジトリに 1 つ、使用側へ symlink）はスキルと共通です。

> [!note] git-workflow スキルとの関係
> このエージェントは薄いラッパーで、実際の**判断ロジック・テンプレート・チェックスクリプトは対の [`git-workflow`](git-workflow.md) スキルが正本**です。エージェントは「いつ・どのコンテキストで起動するか」と「スキルにない Git 固有の運用上の注意」だけを担います。

---

## 対応／前提

| 項目 | 内容 |
|------|------|
| 対応エージェント | Claude Code 専用（frontmatter の `tools` / `model` / `color` / `skills` が Claude Code サブエージェント形式） |
| model | sonnet（手順が固定的なため） |
| tools | Bash, Read, Grep, Glob, Skill（最小権限。GitHub 操作も `gh` CLI を Bash 経由で使い、GitHub MCP は使わない） |
| プリロードスキル | `git-workflow`（frontmatter の `skills:` で指定。未ロード時は Skill ツールで起動） |
| 必須依存 | git / `gh` CLI（PR 操作時） |

---

## インストール

このリポジトリを clone し、エージェント本体（`agents/git-version-control.md`）を `~/.claude/agents/` へ symlink します。実体は 1 つ、参照を張る方式です（スキルと同じ運用。ただしサブエージェントは Claude Code 固有のため、`~/.agents` を経由せず直接リンクします）。

```bash
git clone git@github.com:takunagai/agent-assets.git ~/Projects/agent-assets
ln -s ~/Projects/agent-assets/agents/git-version-control.md ~/.claude/agents/git-version-control.md
```

対の `git-workflow` スキルも別途 symlink が必要です（[docs/git-workflow.md](git-workflow.md) のインストール手順を参照）。プロジェクト単位で使う場合は `<repo>/.claude/agents/` へ同様に symlink します。

---

## 使い方

### 自動委譲（通常はこちら）

「コミットして」「ブランチ作って」「PR 用意して」「Git の操作」などの発話で、メインセッションが自動的にこのエージェントへ委譲します。加えて、機能実装・バグ修正が一段落した時点で**ユーザーの明示指示を待たずプロアクティブに起動**し、コミットを提案します。

```
このバグ修正をコミットして
```

```
新機能用のブランチを作成して
```

```
この変更を日本語の説明付きで PR にまとめて
```

### 明示指定

```
@git-version-control でこの変更をコミットして
```

### 起動しない場面

- 認証情報や Git 設定そのものの変更（ユーザーに `gh auth login` 等を促す）
- 現在のリポジトリ範囲外のファイル操作（境界を越える前に確認を取る）

---

## スキルにない固有の運用

`git-workflow` スキル本体・CLAUDE.md でカバーされない、このエージェント固有の取り決めです。

- **コミット前チェックの対象**: コードプロジェクトのみ実施。Obsidian Vault 等の非コードリポジトリではスキップし、その旨を報告する
- **GitHub 操作**: `gh` CLI を使う（GitHub MCP は使わない）
- **push 失敗時**: 外部ターミナル経由の Bash は SSH/TLS が通らず `git push` が失敗することがある。その場合は Bash を `dangerouslyDisableSandbox: true` で実行する
- **認証エラー**: 自分で変更しない。ユーザーに `gh auth status` / `gh auth login` の実行を促す
- **Git エラー全般**: 原因を診断して解決策を提示。マージコンフリクトは衝突内容を説明して解決を導く

---

## 詳細

コミットメッセージ形式（Conventional Commits の body/footer）・ブランチ戦略・マージ戦略・コミット前チェックスクリプトの詳細は、対の [`git-workflow`](git-workflow.md) スキル、およびスキル本体の `SKILL.md` / `references/*.md` を参照してください。
