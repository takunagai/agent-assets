# cc-fork-delete 回帰テスト

`delete-fork.sh` の安全ガードと削除挙動を、隔離サンドボックス（偽 `$HOME` + 偽 Vault）で総当たり検証する。
**実データには一切触らない**。各ケースごとに `mktemp -d` で使い捨て環境を組み立てて消す。

## 実行

```bash
~/.claude/skills/cc-fork-delete/tests/run-tests.sh
```

全パスなら exit 0。1 つでも失敗すると exit 1。

## カバーしているケース（14 ケース / 71 アサーション）

| # | 内容 | 狙い |
|---|------|------|
| 1 | dry-run プレビュー（文字列 `forkedFrom`） | 削除対象の列挙・本文言及のみログの除外・非破壊 |
| 2 | `forkedFrom` が dict 形式 | `{sessionId,...}` から親を解決できる |
| 3 | UUID 形式でない | exit 2 で中止 |
| 4 | transcript が存在しない | exit 4 で中止 |
| 5 | 大元（`forkedFrom` なし） | exit 5 で中止・大元は無傷 |
| 6 | 現在実行中セッション | exit 3 で中止・復帰コマンド案内 |
| 7 | `--apply`（ゴミ箱退避） | 親・別 sid メタ・別 sid 索引行・本文言及ログの保全／退避先と索引バックアップ |
| 8 | `--apply --purge`（完全削除） | 退避先を作らず削除・親は無傷 |
| 9 | 不明な引数 | exit 2 で中止 |
| 10 | Vault 無し環境 | 止まらず「（なし）」でスキップ |
| 11 | フォーク系図の描画 | 削除対象に `✗`・大元に `●`・兄弟に `○`／構築失敗なし |
| 12 | フォークのフォーク | 子孫に `⚠`・子フォーク WARNING／`--apply` でも子を残して完走（ブロックしない） |
| 13 | `--tree-all` | 家系外の別ルートも描く／既定では家系外を出さない |
| 14 | 親 transcript 欠落 | 系図が落ちず「親 transcript 欠落」注記・削除フロー続行 |

## いつ走らせるか

- `delete-fork.sh` を編集したとき
- Claude Code 側の transcript 仕様が変わった疑いがあるとき
  （特に `forkedFrom` の形式、`sessions/*.json` の `sessionId` キー、索引・全文ログのヘッダ書式）
