# cloudflare-lesson-tutor

Cloudflare 学習カリキュラムの**授業を運営する**スキルです。進捗ダッシュボード（Dashboard.md）で現在地を把握し、カリキュラム設計正本（CURRICULUM.md）の到達目標に沿って、最新の一次情報で裏を取りながら 1 セクションを対話形式で教えます。

ノートの保存・進捗の記録は [cloudflare-lesson-note](cloudflare-lesson-note.md) が担います。**本スキルは学習 Vault へは読み取りのみ**で、進捗の書き込みは一切行いません（単一ライター原則）。

---

## 概要

「Cloudflare のレッスンを続きから」と言うだけで、次の流れを追加指示なしに進めます。

1. **現在地の特定**: `Dashboard.md` で現在地・次セクションを読み、`CURRICULUM.md` で到達目標と参照先を確認する
2. **鮮度検証（授業前の裏取り）**: 扱うプロダクトの現状を一次情報で確認する。pre-training の知識で断定せず retrieval を優先。価格・上限値・API 署名・GA/ベータ状態は必ず一次情報で確認し、検証日を控える
3. **授業の実施**: 導入 → 概念（既知から入る）→ 図解（ASCII 図）→ コード実演（完全版）→ 演習・確認 → まとめ
4. **クロージング**: 「ノートを保存して」で cloudflare-lesson-note に引き継ぐ

教授法は共有リソース `_lesson-methods/explain-hard-concepts.md`（保存スキルと共通）のメソッドに従います。

### フレームワーク情報はフレームワーク公式を正とする

鮮度検証には一般則があります。Cloudflare docs のフレームワークガイドは滞留しうるため、フレームワークのバージョン・API は**フレームワーク公式**を正とします（例: Astro は `docs.astro.build`、Next.js/OpenNext は `opennext.js.org`、Hono は `hono.dev`、Drizzle は `orm.drizzle.team`）。両者が食い違ったらフレームワーク公式を信じます。

---

## インストール

このリポジトリを clone し、スキル本体（`skills/cloudflare-lesson-tutor`）を各エージェントのスキルディレクトリへ symlink します。当環境では「実体 → `~/.agents` → `~/.claude`」の 2 段 symlink で統一しています。

```bash
git clone git@github.com:takunagai/agent-assets.git ~/Projects/agent-assets
ln -s /Users/$USER/Projects/agent-assets/skills/cloudflare-lesson-tutor ~/.agents/skills/cloudflare-lesson-tutor
ln -s ../../.agents/skills/cloudflare-lesson-tutor ~/.claude/skills/cloudflare-lesson-tutor
```

> Codex など他のエージェントは `~/.agents/skills/cloudflare-lesson-tutor` を直接読みます。Claude Code は `~/.claude/skills/` を経由して同じ実体を参照します。

スキル本体の構成は次の通りです。

```
skills/cloudflare-lesson-tutor/
├── SKILL.md                          # スキル定義（Claude がトリガー時に読む）
└── references/
    └── explain-hard-concepts.md      # → ../../_lesson-methods/explain-hard-concepts.md（相対 symlink）
```

教授法ガイド `explain-hard-concepts.md` は保存スキル（cloudflare-lesson-note）と共有するため、共有リソース `skills/_lesson-methods/` に実体を置き、両スキルの `references/` から相対 symlink で参照します。スキル本体の symlink を張れば依存はリポ内相対リンクで解決するため、`_lesson-methods` 自体を個別に symlink 登録する必要はありません。

---

## 設定

学習 Vault のパスは環境変数 `$LESSON_VAULT_PATH` で指定します（保存スキルと共通）。

```bash
# 例: ~/.zshrc などに追記
export LESSON_VAULT_PATH="$HOME/Documents/your-cloudflare-vault"
```

- 未設定の場合、スキルは Vault パスをユーザーに確認します
- Vault 直下に `CURRICULUM.md`（設計正本）と `Dashboard.md`（進捗正本）があることを前提とします

---

## 使い方

Cloudflare 学習を再開・継続するときに発動します。

```
Cloudflare のレッスンを続きから
```

「今日のレッスン」「次のセクション」「カリキュラムの進捗を見せて」「Cloudflare 学習を再開」などでも発動します。特定のセクションを指定すればそこから、指定がなければ Dashboard の次の未完了セクションから始めます。

---

## 生成物

このスキル自体はファイルを生成・保存しません（授業は対話で進みます）。授業の成果をノート化・進捗記録するのは cloudflare-lesson-note です。セクション終了時に「ノートを保存して」と言うと、その会話内容が技術ブログ品質のノートとして保存され、Dashboard.md の進捗が更新されます。

---

## 注意点

- **読み取り専用**: 本スキルは学習 Vault へ書き込みません。進捗更新・ノート保存は cloudflare-lesson-note の責務です
- **retrieval 優先**: 価格・上限値・API 署名・GA/ベータ状態は pre-training の知識で断定せず、必ず一次情報で確認します。確認日はノート保存時の `verified` に反映されます
- **フレームワーク公式優先**: フレームワークのバージョン・API はフレームワーク公式を正とします（Cloudflare docs のフレームワークガイドは滞留しうる）
- **ベータ／プレビュー製品**: CURRICULUM.md の「状態」欄がベータ／プレビューの製品は、API が数ヶ月で変わりうる前提で実行時に現行版を再確認し、「変化前提の学び方」も伝えます
- **カリキュラム非ハードコード**: Phase 構成・セクション名は SKILL.md に固定せず、常に CURRICULUM.md から読みます。カリキュラム改訂時にスキルの変更は不要です

---

## 詳細

詳細な仕様・ワークフローは、スキル本体の `SKILL.md` を参照してください。保存側は [cloudflare-lesson-note](cloudflare-lesson-note.md) を参照してください。
