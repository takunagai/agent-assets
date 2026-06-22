# cc-project-relocate

Claude Code の**プロジェクトフォルダを移動・リネームした後**に、パスに紐づく状態（セッションログ・プロジェクト設定）を新しいパスへ**追随させる**スキルです。

移行はすべて同梱のシェルスクリプトが決定的に実行し、ログ dir はハード削除せず**バックアップへ退避（復元可）**で扱います。

---

## 何を解決するか

Claude Code はセッションログを `~/.claude/projects/<エンコード済み絶対パス>/` に保存します。プロジェクトフォルダを移動・リネームすると、Claude Code は新パスを別物として扱い、**過去の会話履歴・memory が新パスから参照されなくなります**（ログ自体は旧 dir に残ったまま）。

このスキルは旧 dir を新パスのエンコード名へ**リネーム/マージ**して履歴を引き継ぎます。さらに任意で `~/.claude.json` の `projects` キー（trust 承認・allowedTools・MCP 有効化）も移行できます。

手作業でやると **エンコード規則を間違えて別 dir を作る／既存 dir を上書きして現行セッションを壊す** リスクがあります。このスキルは Claude Code 本体と同一のエンコード計算を使い、衝突時はマージで安全に処理します。

---

## エンコード規則（つまずきポイント）

ディレクトリ名は「`/` を `-` に置換」ではありません。**英数字 `[a-zA-Z0-9]` 以外の全文字を `-` に置換**します（`/` `_` `.` ・スペース・記号・**日本語**すべて。日本語は 1 文字 = 1 ダッシュ）。Claude Code 本体の `path.replace(/[^a-zA-Z0-9]/g,'-')` と同じです。

| 元パス | エンコード結果 |
|--------|----------------|
| `/Users/me/Projects/_temp-abc` | `-Users-me-Projects--temp-abc` |

`_temp` の `_` と直前の `/` がどちらも `-` になり `--temp` とダッシュが 2 連になる点に注意。素朴な `/`→`-` 置換では一致しません。マルチバイトのズレを避けるため、スクリプトは `sed` ではなく **node** でエンコードを計算します。

---

## 主な特徴

- **dry-run ファースト** — `--dry-run` で計画（移行元/先 dir・衝突の有無）だけ表示。確認してから実行。
- **本体と同一エンコード** — node の `replace(/[^a-zA-Z0-9]/g,'-')` で計算し、Claude Code が作る dir 名と完全一致を保証。
- **2 種類の状態を移行** — セッションログ dir（JSONL・tool-results・**memory** を内包）は常に移行。`~/.claude.json` の `projects` キー（trust・allowedTools・MCP）は `--update-config` 時のみ。
- **衝突は安全にマージ** — 移動後に新パスで CC を開くと移行先 dir が既に存在する（頻出）。その場合は移行先を優先してマージし、旧 dir は `~/.claude/backups/relocate/` へ退避（復元可）。
- **健全性チェック** — 旧フォルダが残存（コピーの疑い）／新フォルダ不在（未移動）を検知して中止（`--yes` で続行可）。
- **JSON は安全に編集** — `~/.claude.json` はバックアップ → `jq` 生成 → 妥当性検証 → 原子的差し替え。

---

## 動作環境・前提

| 項目 | 内容 |
|------|------|
| 対象 | Claude Code（プロジェクト単位でセッションログを保存する環境） |
| OS | macOS（`cp -n` 等の BSD 挙動に対応。Linux でも概ね動作） |
| 依存 | `bash` / `node`（必須）／ `jq`（`--update-config` 時のみ） |
| 実体の場所 | `~/Projects/agent-skills/skills/cc-project-relocate/`（各エージェントのスキルディレクトリへ symlink して使う） |

---

## インストール

スキル本体を、使うエージェントのスキルディレクトリへ symlink します。

```bash
# Claude Code 用
ln -s ~/Projects/agent-skills/skills/cc-project-relocate ~/.claude/skills/cc-project-relocate

# Codex など他エージェント用（任意）
ln -s ~/Projects/agent-skills/skills/cc-project-relocate ~/.agents/skills/cc-project-relocate
```

---

## 使い方

### AI に任せる場合

移動後の新パスでセッションを開き、「プロジェクトを移動したのでログを引き継ぎたい」と伝えると発火します。AI が移動の完了確認 → 旧パスの特定 → dry-run → 確認 → 実行の順で進めます。

### スクリプトを直接実行する場合

```bash
SH=~/.claude/skills/cc-project-relocate/scripts/relocate.sh

# 1. まず dry-run で計画確認（--new 省略時は $PWD）
bash "$SH" --old /Users/me/Projects/old-name --new /Users/me/work/new-name --dry-run

# 2. 問題なければ実行
bash "$SH" --old /Users/me/Projects/old-name --new /Users/me/work/new-name

# trust/権限/MCP 設定も引き継ぐ場合は --update-config を追加
bash "$SH" --old /Users/me/Projects/old-name --new /Users/me/work/new-name --update-config
```

| オプション | 説明 |
|------------|------|
| `--old PATH` | 移動前のプロジェクト絶対パス（必須） |
| `--new PATH` | 移動後のプロジェクト絶対パス（既定: `$PWD`） |
| `--update-config` | `~/.claude.json` の projects キーも移行（既定: しない） |
| `--dry-run` | 実行せず計画だけ表示 |
| `--yes` | 健全性チェックの警告を無視して実行 |

旧パスを思い出せないときは、名前の断片でログ dir 候補を探せます。

```bash
ls ~/.claude/projects | grep -i <フォルダ名の断片>
```

---

## 注意点

- **`~/.claude.json` の設定移行（`--update-config`）は Claude Code を完全終了してから**実行するのが確実です。起動中は次回フラッシュで上書きされ得ます。ログ dir の移行自体は起動中でも安全です（現行セッションの JSONL に触れないため）。
- パスに紐づかない `~/.claude/todos/`・`~/.claude/history.jsonl`・`shell-snapshots/` は移行不要です。
- プロジェクト内の `.claude/settings.local.json` はフォルダごと移動するので自動追随します。

---

## 復旧

- **ログ**: 退避先 `~/.claude/backups/relocate/<旧enc>.<timestamp>/` を元の場所へ戻す。
- **設定**: バックアップ `~/.claude/backups/relocate/claude.json.<ts>.bak` を `~/.claude.json` へ戻す（Claude Code 終了中に）。

AI 実行時の詳細仕様・状態の対応表は、スキル本体の `references/encoding-and-state.md` を参照してください。
