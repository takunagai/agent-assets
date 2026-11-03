# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## リポジトリの性格

AI エージェント（Claude Code / Codex / Gemini CLI / Cursor など）用の自作スキル・サブエージェントの**公開モノレポ**。Markdown とスクリプト資産の管理が主で、ビルド・lint・テストの仕組みは存在しない。

対となる**非公開モノレポ agent-assets-private**（ローカル: `~/Projects/agent-assets-private`）と同一のディレクトリ構造を維持する。ここに置けるのは公開できるものだけ。案件固有・個人運用・機密設定を含むスキルは非公開側で管理する（例: article 系サブエージェント 4 体はすべて非公開側で管理する）。片方の構造を変えるときは、もう片方との整合を必ず確認する。

## 配置規約（最重要 ─ ファイルを新規作成する前に必ずここを確認）

| 置くもの | 場所 |
|---|---|
| スキル本体（AI 実行資産: `SKILL.md` / `references/` / `scripts/` / `assets/`） | `skills/<name>/` |
| サブエージェント（1 体 1 ファイル） | `agents/<name>.md` |
| 人間向けマニュアル | `docs/<name>.md` |
| 共有リソースライブラリ（スキルではない） | `skills/_<name>/` |

- **`skills/<name>/` 配下に README 等の人間向け文書を作らない**。人間向けドキュメントの新規作成・更新は、必ず既存の `docs/<name>.md` を第一候補にする
- 例外はこの 2 つだけ:
  1. `SKILL.md` から参照される運用ファイルは AI 実行資産として同梱可
  2. `_` で始まる共有リソースディレクトリ（`SKILL.md` を持たずスキルとしてロードされない。例: `skills/_image-styles/`）は自身の `README.md` / `_index.md` を同梱する
- 共有リソースは「複数スキルが同じ素材を使い回す」場面で使う。各スキルへの個別コピーは定義のズレを生むため禁止（例: `gen-infographic` と `gen-lifestyle-images` は `references/styles → ../../_image-styles` の相対 symlink で共有）

## Single Source of Truth（symlink 運用）

実体はこのリポジトリだけに置き、各エージェントのディレクトリ（`~/.claude/skills/<name>` など）からは symlink で参照する。**編集は常にこのリポジトリ側の実体に対して行う**（symlink 経由でも実体が変わるため即反映される）。コピーによる二重管理をしない。

新規登録:

```bash
ln -s ~/Projects/agent-assets/skills/<name> ~/.claude/skills/<name>
ln -s ~/Projects/agent-assets/agents/<name>.md ~/.claude/agents/<name>.md
```

- `_image-styles` に依存するスキルは、スキル本体の symlink だけで依存が解決する（リポ内相対リンクのため）。`_image-styles` 自体の symlink は不要
- `.skill` 形式で配布するときだけ、各スキルの `scripts/sync-styles.sh --embed` でスタイル実体を埋め込む

## スキル・エージェント追加/変更時のチェックリスト

1. 本体を作成・変更する（`skills/<name>/` / `agents/<name>.md`）
2. `docs/<name>.md` を作成・同期する ─ **実装（SKILL.md / references/）を変更したら docs を必ず追随させる**。動作の正本はスキル側、docs は人間向けの写像
3. `README.md` のカタログ表（スキル一覧・サブエージェント一覧）に行を追加・更新する
4. 新規なら symlink を登録する

手順 2 は pre-commit フック（`.githooks/pre-commit`）が機械的に検査する ─ 実装をステージしたのに対応する `docs/<name>.md` が同一コミットに無いと失敗する。docs の抽象度に影響しない変更だと判断した場合のみ `SKIP_DOCS_CHECK=1 git commit` で明示スキップ（その場合も README カタログ行の陳腐化は目視確認。`--no-verify` は使わない）。clone 直後は `git config core.hooksPath .githooks` で有効化する。導入経緯: 姉妹リポジトリ agent-assets-private で、ホットフィックス時にチェックリストの想起が飛んだ実例（2026-07-07）があったため機械化し、両リポジトリにミラー配置した。

## 機密の扱い（公開リポジトリ）

- 機密値・個人情報・案件固有情報は**一切置かない**。API キー等の実値が必要なスキルは環境変数で受け取る設計にする（例: `GEMINI_API_KEY`）
- 機密を含む必要が出たスキルは、非公開側（agent-assets-private）へ移す

## その他

- `handover/`（実行指示書）は git 管理外。完了後の正本は Vault の実行指示書アーカイブ
