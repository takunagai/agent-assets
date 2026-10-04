# image-gen-handoff

> **お蔵入り（2026-09-30）**: 使用を終了し、各エージェントのスキルディレクトリから symlink 登録を解除した。本体はリポジトリに残している。再開するときは README の手順で symlink を張り直す。

Codex の `image_gen` / Image 2.0 で大量生成した後に、保存済み画像と session JSONL から成果物を整理する後処理スキルです。画像生成そのものは行いません。

## できること

- 保存済み画像を走査し、`sha256`、寸法、ファイルサイズ、mtime を記録
- Codex session JSONL から `image_generation_call` と最終生成プロンプト候補を抽出
- 画像とプロンプトを対応付け、`high` / `medium` / `low` / `missing` の信頼度を記録
- `manifest.json` と確認用 `manifest.md` を生成
- `作業記録/<batch-name>_引き継ぎ.md` のような軽量な引き継ぎノートを生成
- 明示指定時のみ、JSONL 内の未保存画像抽出、画像コピー、JSONL 圧縮コピーを実行

## やらないこと

- デフォルトでは既存画像を移動・リネームしません。
- デフォルトでは JSONL を圧縮・移動しません。
- JSONL 削除機能はありません。
- 取得できないプロンプトを推測で埋めません。

## サンプルプロンプト

Codex や Claude Code にこのスキルを使わせるときは、先に対象プロジェクト、画像ディレクトリ、session JSONL、batch 名、期待件数を渡すと安定します。最初は dry-run を指定してください。

### まず dry-run で確認

```text
$image-gen-handoff を使って、画像生成バッチの引き継ぎ準備を dry-run してください。

対象:
- project root: <PROJECT_ROOT>
- image dir: <IMAGE_DIR>
- Codex session JSONL: <CODEX_SESSION_JSONL>
- batch name: <BATCH_NAME>
- expected count: <EXPECTED_COUNT>

要件:
- 既存画像は移動・リネームしない。
- JSONL は圧縮・移動・削除しない。
- dry-run の結果として、画像数、抽出イベント数、missing/low confidence の件数、重複ハッシュ有無を報告してください。
- 公開ファイルや manifest に base64 画像本体を入れないでください。
```

### manifest と引き継ぎノートを作る

```text
$image-gen-handoff を使って、次の画像生成バッチを成果物化してください。

対象:
- project root: <PROJECT_ROOT>
- image dir: <IMAGE_DIR>
- Codex session JSONL: <CODEX_SESSION_JSONL>
- batch name: <BATCH_NAME>
- expected count: <EXPECTED_COUNT>

生成してほしい成果物:
- <IMAGE_DIR>/<BATCH_NAME>-manifest.json
- <IMAGE_DIR>/<BATCH_NAME>-manifest.md
- 作業記録/<BATCH_NAME>_引き継ぎ.md

完了前に validate_manifest.py で再検証し、confidence=low / missing のファイルがあれば一覧で報告してください。
```

### JSONL がない状態で画像だけ監査する

```text
$image-gen-handoff で、session JSONL なしの画像監査 manifest を作ってください。

対象:
- project root: <PROJECT_ROOT>
- image dir: <IMAGE_DIR>
- batch name: <BATCH_NAME>
- expected count: <EXPECTED_COUNT>

--no-jsonl を使い、最終生成プロンプトは推測で埋めず missing として扱ってください。
sha256、寸法、欠損、重複ハッシュの検証結果を manifest と Markdown に残してください。
```

### JSONL にしかない未保存画像を抽出する

```text
$image-gen-handoff で、Codex session JSONL 内の image_gen 画像を抽出してください。

対象:
- Codex session JSONL: <CODEX_SESSION_JSONL>
- extract dir: <EXTRACT_OUTPUT_DIR>
- extract prefix: <PREFIX>

要件:
- 既存ファイルは上書きしない。
- 抽出後、何枚保存したか、ファイル名、抽出できなかったイベントがあるかを報告してください。
- JSON 出力や Markdown に base64 本体を貼らないでください。
```

### manifest 完成後に JSONL の圧縮コピーだけ作る

```text
$image-gen-handoff で、manifest 作成済みの session JSONL を圧縮コピーしてください。

対象:
- JSONL: <CODEX_SESSION_JSONL>
- manifest: <PROJECT_ROOT>/<IMAGE_DIR>/<BATCH_NAME>-manifest.json
- archive dir: <ARCHIVE_DIR>
- format: gz

元 JSONL は削除しないでください。圧縮コピーの保存先と、元ファイルを削除していないことを報告してください。
```

## 基本コマンド

まず dry-run で件数と対応付けの見込みを確認します。

```bash
python3 <SKILL_DIR>/scripts/build_manifest.py \
  --project-root <PROJECT_ROOT> \
  --image-dir <IMAGE_DIR> \
  --jsonl <CODEX_SESSION_JSONL> \
  --batch-name <BATCH_NAME> \
  --out-json <IMAGE_DIR>/<BATCH_NAME>-manifest.json \
  --out-md <IMAGE_DIR>/<BATCH_NAME>-manifest.md \
  --handoff-md '作業記録/<BATCH_NAME>_引き継ぎ.md' \
  --expected-count <EXPECTED_COUNT> \
  --dry-run
```

問題なければ `--dry-run` を外して生成します。

```bash
python3 <SKILL_DIR>/scripts/build_manifest.py \
  --project-root <PROJECT_ROOT> \
  --image-dir <IMAGE_DIR> \
  --jsonl <CODEX_SESSION_JSONL> \
  --batch-name <BATCH_NAME> \
  --out-json <IMAGE_DIR>/<BATCH_NAME>-manifest.json \
  --out-md <IMAGE_DIR>/<BATCH_NAME>-manifest.md \
  --handoff-md '作業記録/<BATCH_NAME>_引き継ぎ.md'
```

生成後は manifest を再検証します。

```bash
python3 <SKILL_DIR>/scripts/validate_manifest.py \
  --manifest <PROJECT_ROOT>/<IMAGE_DIR>/<BATCH_NAME>-manifest.json
```

## 個別機能

### JSONL イベント抽出

```bash
python3 <SKILL_DIR>/scripts/extract_imagegen_events.py \
  --jsonl <CODEX_SESSION_JSONL> \
  --out <OUTPUT_JSON> \
  --limit-events 20
```

JSON 出力には base64 画像本体を含めません。

### JSONL から画像を抽出

未保存画像が JSONL にしかない場合だけ使います。

```bash
python3 <SKILL_DIR>/scripts/extract_imagegen_events.py \
  --jsonl <CODEX_SESSION_JSONL> \
  --extract-images \
  --extract-dir <OUTPUT_DIR>
```

### 画像コピーと命名

既存画像はそのままにし、コピー先へだけ書き出します。

```bash
python3 <SKILL_DIR>/scripts/build_manifest.py \
  --project-root <PROJECT_ROOT> \
  --image-dir <IMAGE_DIR> \
  --jsonl <CODEX_SESSION_JSONL> \
  --batch-name <BATCH_NAME> \
  --copy-to <COPIED_IMAGE_DIR> \
  --rename-format '{batch}-{index:03d}{ext}'
```

### JSONL 圧縮コピー

manifest 作成後に、必要な場合だけ圧縮コピーします。元 JSONL は削除されません。

```bash
python3 <SKILL_DIR>/scripts/archive_jsonl.py \
  --jsonl <CODEX_SESSION_JSONL> \
  --manifest <PROJECT_ROOT>/<IMAGE_DIR>/<BATCH_NAME>-manifest.json \
  --archive-dir <ARCHIVE_DIR> \
  --format gz
```

## 出力

標準的な出力は次の 3 点です。

```text
<IMAGE_DIR>/<BATCH_NAME>-manifest.json
<IMAGE_DIR>/<BATCH_NAME>-manifest.md
作業記録/<BATCH_NAME>_引き継ぎ.md
```

`manifest.json` は機械処理用、`manifest.md` は確認用、引き継ぎノートは次セッションで作業を再開するための軽量メモです。

## 注意

`confidence=low` と `confidence=missing` は必ず目視確認してください。`confidence=high` でも画像内容そのものを保証するものではなく、ファイル名・生成順・プロンプト番号などの対応付け根拠が強いという意味です。
