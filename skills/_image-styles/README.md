# _image-styles — 共有スタイルライブラリ

画像生成系スキルが横断で参照する「スタイル指定ブロック」の**正本（single source of truth）**です。

このディレクトリ自体は実行されるスキルではありません。`gen-infographic` のような画像生成スキルが、生成プロンプトの `{{STYLE}}` 部分にここのファイル本文を差し込んで使います。スタイルの定義はこの 1 箇所で編集し、参照側スキルへ symlink で配ります。

> スタイルの一覧・各スタイルの向き・参照側スキルからの差し込み方は [`_index.md`](./_index.md) を参照してください。本ファイル（README）は**メンテナ向けの運用ドキュメント**です。

## 設計思想：構造とスタイルの分離

画像生成プロンプトを 2 つの軸に分解しています。

- **構造**（流れ図・対比・循環・グループ一覧）＝ レイアウト・情報設計。各スキルの `references/structures/` が持つ。
- **スタイル**（線・配色・質感・筆致）＝ 見た目。**構造非依存**。ここ `_image-styles/` が持つ。

スタイルファイルはレイアウトに一切触れないため、同じ内容を「構造はそのままスタイルだけ差し替え」「スタイルはそのまま構造だけ差し替え」と独立に組み替えられます。スタイルを複数スキルで共有できるのもこの分離のおかげです。

## 収録ファイル

| ファイル | 役割 |
|---|---|
| `_index.md` | スタイルカタログ（参照側スキル／AI が読む目次・使い方） |
| `handdrawn-marker.md` | 大人の手描きマーカー（**既定スタイル**） |
| `minimal-flat.md` | ミニマル・フラット |
| `watercolor.md` | 水彩・やわらかい |
| `blueprint.md` | 設計図・ブループリント風 |
| `README.md` | このファイル（運用ドキュメント） |

各スタイルファイルは「そのスタイルの絵を出させるための指示ブロック」を本文に持ち、構造には触れません。

## このライブラリを参照しているスキル

| スキル | 参照箇所 |
|---|---|
| `gen-infographic` | `references/styles/` → `../../_image-styles`（symlink）。`SKILL.md` と `scripts/sync-styles.sh` で参照 |

`gen-nanobanana-images` などスタイル分離の設計思想を共有するスキルも、将来ここへ接続する候補です（現時点では `references/styles/` 未接続）。**新しい参照スキルを追加したら、この表に 1 行追記してください。**

## 参照の仕組み（正本はリポ内、参照は symlink）

正本はこのディレクトリ `~/Projects/agent-skills/skills/_image-styles/` で、**agent-skills リポで Git 管理**されています。各スキルの `references/styles/` は同じリポ内の正本への相対 symlink `../../_image-styles` で、**リポ内で自己完結して解決します**（clone しても壊れません）。

```
~/Projects/agent-skills/skills/        ← リポ（正本の置き場）
├── _image-styles/                     ← 正本（実体・Git 管理・このディレクトリ）
└── gen-infographic/
    └── references/styles → ../../_image-styles   ← symlink（= skills/_image-styles）
```

スキル本体は `~/Projects/agent-skills/skills/<skill>` が実体で、`~/.agents/skills/<skill>`（→ さらに `~/.claude/skills/<skill>`）へ symlink を張って各エージェントへ配ります。`references/styles` の相対リンク `../../_image-styles` は、この symlink チェーンを物理解決した先（＝リポ内）で閉じるため、**リポ直・ハブ（`~/.agents`）経由・Claude（`~/.claude`）経由のいずれの経路でも**同じ正本に解決します（相対リンクはハブ階層ではなく実体＝リポ階層を基準に解決されるため）。

`_image-styles` はスキル（`SKILL.md` 持ち）ではなく、ハブを直接参照する用途もありません。上記のとおり参照は全経路でリポ内に解決するので、**`~/.agents/skills/` や `~/.claude/skills/` のスキルハブに `_image-styles` の symlink を置く必要はありません**（置かないのが正）。

## 編集ルール

- **編集はこの正本 1 箇所だけで行う。** symlink 経由で参照している各スキルへ自動的に反映されます。
- 参照側スキルの `references/styles/` を直接編集しない（symlink 先＝この正本を編集することになるか、配布用に embed 展開した実体コピーなら正本へ反映されません）。
- スタイルファイルに**構造・レイアウトの指示を混ぜない**。混ざると構造との独立な差し替えが崩れます。

## 配布（.skill パッケージ化）時の embed / relink

symlink は `.skill` パッケージに同梱されず壊れます。そのため配布時は参照側スキルで symlink を実体コピーへ展開します。`gen-infographic` には専用スクリプトがあります。

```bash
# 配布前：symlink → 実体コピーへ展開（references/styles/ が通常ディレクトリになる）
bash ~/Projects/agent-skills/skills/gen-infographic/scripts/sync-styles.sh --embed

# 開発へ戻す：実体コピー → symlink（../../_image-styles を指し直す）
bash ~/Projects/agent-skills/skills/gen-infographic/scripts/sync-styles.sh --relink
```

- `--embed` は冪等。既に実体ディレクトリならスキップします。
- 公開リポ（`~/Projects/agent-skills`）には **symlink のままコミット**します。正本 `skills/_image-styles` が同じリポ内にあるため、clone しても symlink が解決します。
- `.skill` パッケージ化の**直前にのみ** `--embed` で実体展開し、終わったら `--relink` で開発モード（symlink）に戻します。
- 正本がリポ内にあるため、`--embed` / `--relink` はリポ直・ハブ経由のどちらで実行しても同じ正本に解決します。

## 新しいスタイルを追加する手順

1. このディレクトリに `<style-name>.md` を作成し、スタイル指示ブロックを書く（**構造には触れない**）。
2. `_index.md` の「収録スタイル」表に 1 行追加する。
3. 既定を変える場合のみ、参照側スキルの既定スタイル記述（`gen-infographic/SKILL.md` 等）も更新する。
4. 開発中は symlink なので、追加した時点で各参照スキルに反映される。配布物を作る場合のみ `sync-styles.sh --embed` で再同梱する。

## 新しい参照スキルを接続する手順

1. 対象スキルに `references/styles` を作り、リポ内の正本へ相対 symlink を張る。

   ```bash
   ln -snf ../../_image-styles ~/Projects/agent-skills/skills/<skill>/references/styles
   ```

2. スキルの生成プロンプト骨格に `{{STYLE}}` プレースホルダーを用意し、選択スタイルの本文を差し込む実装にする。
3. 配布対応が要るなら `gen-infographic/scripts/sync-styles.sh` を雛形に embed/relink スクリプトを用意する。
4. 本 README の「このライブラリを参照しているスキル」表に追記する。

## 関連

- [`_index.md`](./_index.md) — スタイルカタログ（参照側が読む目次）
- `~/Projects/agent-skills/skills/gen-infographic/` — 主要な参照元スキル
- `~/Projects/agent-skills/docs/gen-infographic.md` — gen-infographic の人間向けマニュアル（styles 共有の扱いを記載）
