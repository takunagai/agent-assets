# gen-infographic

日本語の文章・メモ・画像・PDF・スクリーンショット・スライドを、**内容をよく理解した大人がまとめたような読みやすい 1 枚図解画像**へ変換するスキルです。**構造**（流れ図・対比・循環・グループ一覧）と**スタイル**（手描きマーカー＝既定 / ミニマル・フラット / 水彩 / 設計図風）を独立に組み合わせて生成します。

図解・要約画像・グラフィックノート・手描きインフォグラフィック・SNS 向け解説画像を作りたいときに使います。

---

## インストール

このリポジトリを clone し、スキル本体（`skills/gen-infographic`）を各エージェントのスキルディレクトリへ **symlink** します。実体は 1 つ、参照を複数張る方式です。当環境では「実体 → `~/.agents` → `~/.claude`」の 2 段 symlink で統一しています。

```bash
# 1) リポジトリを取得
git clone git@github.com:takunagai/agent-skills.git ~/Projects/agent-skills

# 2) ハブ（~/.agents）から実体へ絶対 symlink
ln -s /Users/$USER/Projects/agent-skills/skills/gen-infographic ~/.agents/skills/gen-infographic

# 3) Claude Code 用に ~/.agents への相対 symlink
ln -s ../../.agents/skills/gen-infographic ~/.claude/skills/gen-infographic
```

スキル本体の構成は次の通りです（人間用マニュアルである本ファイルは、スキル本体の外＝`docs/` に置いています）。

```
skills/gen-infographic/
├── SKILL.md                       # スキル定義（Claude がトリガー時に読む）
├── scripts/
│   └── sync-styles.sh             # styles の symlink ⇄ 実体コピー切り替え（配布用）
└── references/
    ├── intake-template.md         # 初回ヒアリングテンプレート
    ├── generation-prompt.md       # 画像生成プロンプトの骨格
    ├── revision-prompt.md         # 反復修正プロンプト
    ├── structures/                # 構造ブロック（flow / contrast / cycle / grouped-list）
    │   └── _index.md
    └── styles/                    # スタイルブロック（_image-styles への symlink。配布時のみ実体コピー）
        └── _index.md
```

> **styles の扱い**: `references/styles/` は共有スタイルライブラリ `_image-styles`（リポ内の `skills/_image-styles`）への symlink で、複数の画像生成スキルがスタイルを共有します。正本が同じリポ内にあるため symlink のままコミットされ、clone でも解決します。`.skill` パッケージ化時のみ `scripts/sync-styles.sh --embed` で実体コピーへ展開します。

---

## クイックスタート

自然言語で発動します。「これを図解して」「この記事を 1 枚にまとめて」「手描き風のインフォグラフィックにして」など。

```
この文章を図解して
添付の PDF を 1 枚の図解にまとめて。水彩スタイルで
この手順をフロー図にして。おまかせで生成
```

- 内容が見つかれば、未指定の任意設定（構造・スタイル等）を 1 回だけまとめて質問します。
- 「おまかせ」「デフォルトで」と伝えれば設定確認を省略します。

---

## 主な機能

- **構造とスタイルの分離**: 同じ内容を、構造はそのままにスタイルだけ／スタイルはそのままに構造だけ、独立して差し替え可能
- **4 つの構造**: 流れ図（手順）/ 対比（比較）/ 循環（サイクル）/ グループ一覧
- **4 つのスタイル**: 手描きマーカー（既定）/ ミニマル・フラット / 水彩 / 設計図風
- **必須文字列の保護**: タイトル・固有名詞・数値は引用符で囲んで一字一句保持（文字崩れ対策）
- **反復修正**: 1 回 1 項目の修正で、他の要素を維持したまま調整

### 既定値

| 項目 | 既定 |
|------|------|
| モデル | `gpt-image-2` |
| 品質 | `high` |
| サイズ | `1024x1536`（縦長） |
| 言語 | 日本語 |
| 構造 | 内容から自動選択 |
| スタイル | 手描きマーカー |

生成画像は、保存先指定がなければ `~/Downloads/infographic-YYYYMMDD-HHMMSS.png` に保存します（スキルディレクトリ内には保存しません）。

---

## 注意点

- 画像内の日本語・固有名詞は生成モデルによって崩れることがあります。**生成後は必ず目視確認**し、崩れた箇所は修正プロンプトまたは画像編集ツールで差し替えてください（同じ文字が連続する綴り・長音符・旧字は特に崩れやすい）。
- 情報量が多すぎて 1 枚で判読性を保てない場合は、文字を詰め込まず、範囲の絞り込みか複数画像への分割を提案します。
- `$gpt-image-2` 経由で生成する場合、プロンプトが長くなるとタイムアウトしやすいため `--timeout-sec 540` 程度を渡してください。

## 関連スキル

- `gen-nanobanana-images` — Google Gemini（Nano Banana）系の画像生成エンジン。スタイルライブラリの設計思想を共有しています。

## 詳細

ワークフロー・各構造/スタイルの定義・生成プロンプトの骨格は、スキル本体の `SKILL.md` および `references/*.md` を参照してください。
