# cloudflare-lesson-note

Cloudflare 学習カリキュラムの**セッション内容を技術ブログ品質の Obsidian ノートに整形・保存し、進捗（Dashboard.md）を更新する**スキルです。会話中で進めた授業（概念説明・図解・コード例・Q&A）を、他人が読んでも理解できるレベルに凝縮し、frontmatter 付きの Markdown として保存先 Vault に書き出したうえで、進捗ダッシュボードを更新します。

授業運営そのものは [cloudflare-lesson-tutor](cloudflare-lesson-tutor.md) が担い、本スキルはその成果の**保存と進捗記録**を担当します。**学習 Vault への書き込みは本スキルに一本化**されています（tutor は読み取り専用）。特定の学習用 Vault に密結合せず、保存先は環境変数で設定可能です。

---

## 概要

学習セッションの会話履歴から、セクション番号・授業本文・Q&A を抽出し、技術ブログとして公開できる品質の Obsidian ノートに整形します。

- ASCII 図やテーブルなど授業中の図解は保持する
- コード例は実行可能な完全版で残す
- Q&A は質問の要旨と回答の核心だけに凝縮する
- 「〜と言えるでしょう」「様々な」「〜することができます」等の AI 臭表現を排除する
- 保存後、`Dashboard.md` の進捗（チェックリスト・完了表・進捗バー・現在地）を更新する

### 参照する 2 つの正本ファイル

保存先 Vault 直下の 2 ファイルを入力として読みます。

| ファイル | 役割 | 本スキルの扱い |
|---|---|---|
| `CURRICULUM.md` | カリキュラムの設計正本（到達目標・参照先。進捗は書かれていない） | 読み取り |
| `Dashboard.md` | 進捗の正本（現在地・完了状況・進捗バー） | 読み取り＋**更新**（唯一のライター） |

### tutor との責務分担

- **cloudflare-lesson-tutor（授業運営）**: カリキュラム進行・鮮度検証・授業実施。Vault へは読み取りのみ
- **cloudflare-lesson-note（本スキル・保存）**: ノート整形・保存 ＋ Dashboard.md の進捗更新
- 接続: tutor がセクション終了時に「ノートを保存して」を促し、本スキルに引き継ぎます

---

## インストール

このリポジトリを clone し、スキル本体（`skills/cloudflare-lesson-note`）を各エージェントのスキルディレクトリへ symlink します。実体は 1 つ、参照を複数張る方式です。当環境では「実体 → `~/.agents` → `~/.claude`」の 2 段 symlink で統一しています。

```bash
git clone git@github.com:takunagai/agent-assets.git ~/Projects/agent-assets
ln -s /Users/$USER/Projects/agent-assets/skills/cloudflare-lesson-note ~/.agents/skills/cloudflare-lesson-note
ln -s ../../.agents/skills/cloudflare-lesson-note ~/.claude/skills/cloudflare-lesson-note
```

> Codex など他のエージェントは `~/.agents/skills/cloudflare-lesson-note` を直接読みます。Claude Code は `~/.claude/skills/` を経由して同じ実体を参照します。

スキル本体の構成は次の通りです（人間用マニュアルである本ファイルは、スキル本体の外＝`docs/` に置いています）。

```
skills/cloudflare-lesson-note/
├── SKILL.md                          # スキル定義（Claude がトリガー時に読む）
└── references/
    └── explain-hard-concepts.md      # → ../../_lesson-methods/explain-hard-concepts.md（相対 symlink）
```

教授法ガイド `explain-hard-concepts.md` は、授業運営スキル（cloudflare-lesson-tutor）と共有するため、共有リソース `skills/_lesson-methods/` に実体を置き、両スキルの `references/` から相対 symlink で参照します。実体は 1 箇所のみで、コピーは作りません。スキル本体の symlink を張れば、この共有リソースへの依存はリポ内相対リンクで解決するため、`_lesson-methods` 自体を個別に symlink 登録する必要はありません。

---

## 設定

保存先 Vault のパスは環境変数 `$LESSON_VAULT_PATH` で指定します。

```bash
# 例: ~/.zshrc などに追記
export LESSON_VAULT_PATH="$HOME/Documents/your-cloudflare-vault"
```

- `$LESSON_VAULT_PATH` が未設定の場合、スキルは保存先をユーザーに確認します
- ノートは `<VAULT>/Phase N/` 形式で保存されます（`<VAULT>` = `$LESSON_VAULT_PATH`、`N` はフェーズ番号）
- Vault 直下に `CURRICULUM.md` と `Dashboard.md` があることを前提とします（授業運営スキルと共通の正本）

---

## 使い方

Cloudflare 学習セッションの途中・終了時に、保存を依頼するだけで発動します。

```
ノートを保存して
```

自然言語でも発動します。「レッスンを保存」「今の内容を保存」「ドキュメントにして」「メモを残して」など。

事前に `$LESSON_VAULT_PATH` を設定しておくと、毎回の保存先確認を省けます。

---

## 生成物

| 項目 | 内容 |
|------|------|
| ファイル形式 | frontmatter 付き Markdown |
| ファイル名 | `<セクション番号> <タイトル>.md`（例: `1-5 2026 年の開発フロー.md`） |
| 保存先 | `<VAULT>/Phase N/`（`<VAULT>` = `$LESSON_VAULT_PATH`） |
| 本文構成 | リード文 → 見出しごとの本文 → まとめ → Q&A 要約 |
| 進捗更新 | `<VAULT>/Dashboard.md`（チェックリスト・完了表・進捗バー・現在地） |

frontmatter には `tags` / `phase` / `section` / `curriculum` / `title` / `date` / `verified` / `status` を含みます。`verified` は授業中に公式情報（retrieval）で検証した日付です。Q&A は質問の要旨と回答の核心（3〜5 行）に凝縮されます。

画像を添える場合は `<VAULT>/assets/` に置き、本文からは `![[<セクション番号>-<内容>.png]]` で埋め込みます（例: `![[2-1-wrangler-lifecycle.png]]`）。ASCII 図は本文にそのまま残します（画像化は必須ではありません）。

---

## 注意点

- **保存先ディレクトリの事前作成**: `<VAULT>/Phase N/` が存在しない場合は、事前に作成しておくか、保存時にユーザーへ確認させてください
- **上書き保護**: 保存先に同名ノートが既に存在する場合、スキルは黙って上書きせず、差分の要約を提示して承認を求めます
- **単一ライター原則**: `Dashboard.md` に書き込むのは本スキルだけです。授業運営スキル（tutor）は Dashboard を読むだけで書きません。書き込み箇所を 1 スキルに集約することで進捗の整合が壊れません
- **鮮度メタデータ**: 本文に授業中 retrieval で未検証の具体値（価格・上限値・API 署名・バージョン・GA/ベータ状態）がある場合、スキルはその箇所を指摘してから保存します。検証済みの日付が `verified` に入ります
- **`$LESSON_VAULT_PATH` の設定**: 未設定だと毎回保存先を尋ねられます。実運用前に環境変数を設定してください
- **AI 臭排除は最終手動確認**: スキルは AI っぽい表現の排除を試みますが、完全ではありません。公開・共有前の目視確認を前提としてください
- **特定 Vault に非依存**: 保存先は設定で差し替え可能です。複数の学習 Vault を使い分ける場合も `$LESSON_VAULT_PATH` を切り替えるだけで対応できます

---

## 詳細

詳細な仕様・ワークフロー・文体ガイドラインは、スキル本体の `SKILL.md` を参照してください。授業運営側は [cloudflare-lesson-tutor](cloudflare-lesson-tutor.md) を参照してください。
