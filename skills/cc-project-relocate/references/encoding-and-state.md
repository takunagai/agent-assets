# cc-project-relocate リファレンス

## 1. ログ dir のエンコード規則

Claude Code はセッションログを次に保存する。

```
~/.claude/projects/<エンコード済み絶対パス>/
```

エンコードは **絶対パス文字列の英数字 `[a-zA-Z0-9]` 以外を全て `-` に置換**する。

```js
encoded = absolutePath.replace(/[^a-zA-Z0-9]/g, '-')
```

- `/` `_` `.` ・スペース・記号・**日本語**すべてが `-` になる。
- 日本語など非 ASCII は **1 コードポイント = 1 ダッシュ**。複数文字の連続は連続ダッシュになる。
- 先頭の `/` も `-` になるので、エンコード結果は常に `-` で始まる。
- **不可逆**: `_temp` も `/temp` も `.temp` も同じ `-temp` になる。エンコード名から元パスは復元できない。

### 検証例

| 元パス | エンコード結果 |
|---|---|
| `/Users/takna/Projects/_temp-agilabo-2026-06-21` | `-Users-takna-Projects--temp-agilabo-2026-06-21` |

`_temp` の `_` と直前の `/` がどちらも `-` になり `--temp` と**ダッシュが 2 連**になる点に注意。
「`/`→`-` だけ」の素朴な置換では `-_temp` となり**実際の dir 名と一致しない**。
日本語フォルダ名は `-Users-...-Projects-----` のように連続ダッシュ化する。

### 自前実装を避ける理由

`sed 's#[^a-zA-Z0-9]#-#g'` はロケール/実装によりマルチバイト 1 文字を複数バイト＝複数ダッシュに化けさせる。
本体（JS）と確実に一致させるため、スクリプトは `node -e '...replace(/[^a-zA-Z0-9]/g,"-")'` で計算する。

## 2. パスに紐づく状態の一覧

### 移行が必要

| 対象 | 場所 | 内容 | キー形式 |
|---|---|---|---|
| セッションログ | `~/.claude/projects/<enc>/*.jsonl` | 会話全文 | エンコード済みパス |
| tool-results | `~/.claude/projects/<enc>/<session-id>/` | ツール出力の退避 | 同上（dir 内包） |
| memory | `~/.claude/projects/<enc>/memory/` | ファイルベース記憶 | 同上（dir 内包） |
| プロジェクト設定 | `~/.claude.json` の `projects["<絶対パス>"]` | trust 承認・allowedTools・MCP 有効化・直近メトリクス | **生の絶対パス**（エンコードしない） |

- ログ dir 配下（tool-results・memory 含む）は、dir をリネーム/マージすれば一括で追随する。
- `~/.claude.json` の `projects` キーだけは**別管理**で、エンコードせず生パスをキーにする。
  ここを移さないと、新パスは「初見の未 trust プロジェクト」扱いになり、権限再付与・trust 再承認が必要になる
  （データ消失ではないので必須ではない。`--update-config` で任意移行）。

### 移行不要（パス非依存）

| 対象 | 理由 |
|---|---|
| `~/.claude/todos/` | session-id keyed |
| `~/.claude/history.jsonl` | グローバル（プロンプト履歴） |
| `~/.claude/shell-snapshots/` | session/グローバル keyed |
| プロジェクト内 `.claude/settings.local.json` | フォルダごと移動するので自動追随 |

## 3. よくあるケースと挙動

### ケース A: 移動後まだ CC を開いていない
- 新パスのログ dir は未作成 → スクリプトは**単純リネーム**（`mv`）。最もクリーン。

### ケース B: 移動後すでに新パスで CC を開いた（頻出）
- 新セッションが新パスのログ dir を作成済み → スクリプトは**マージ**。
  - 移動先を優先しつつ旧 dir の内容をコピー（`cp -Rn`）。
  - 旧 dir は `~/.claude/backups/relocate/<旧enc>.<timestamp>/` へ退避（ハード削除しない）。
  - JSONL は UUID 名なので衝突しない。`memory/MEMORY.md` 等は衝突し得る → 移動先を残し、旧側は退避先で保全・報告。

### ケース C: 移動でなくコピーだった / まだ移動していない
- 旧フォルダが残存 or 新フォルダ不在をスクリプトが検知して警告・中断（`--yes` で続行可）。

## 4. ~/.claude.json 編集の注意

- Claude Code は起動中この巨大ファイルを読み書きする。**起動中の編集は次回フラッシュで上書きされ得る**。
  - ログ移行（`~/.claude/projects/`）は起動中でも安全（現行セッションの JSONL に触れないため）。
  - 設定移行（`--update-config`）は **CC を完全終了してから**実行するのが確実。
- スクリプトは編集前に `~/.claude/backups/relocate/claude.json.<ts>.bak` を取り、`jq` 生成 → 妥当性検証 → 原子的差し替えを行う。

## 5. 復旧

- ログ: 退避先 `~/.claude/backups/relocate/<旧enc>.<timestamp>/` を元の場所へ戻す。
- 設定: バックアップ `~/.claude/backups/relocate/claude.json.<ts>.bak` を `~/.claude.json` に戻す（CC 終了中に）。
