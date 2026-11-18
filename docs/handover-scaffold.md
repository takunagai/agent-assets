# handover-scaffold

別セッションで無人実行させる「指示書（引き継ぎドキュメント）」の骨組みを、規約に沿って一発生成するスキルです。`handover/` バッチのフォルダ構成・`00_実行順.md` マニフェスト・指示書スケルトンを規約どおりに作ります。

「指示書を作って」「handover 作成」「引き継ぎドキュメントを作って」「バッチ指示書を用意して」で発動します。

---

## インストール

このリポジトリを clone し、スキル本体（`skills/handover-scaffold`）を各エージェントのスキルディレクトリへ **symlink** します。

```bash
git clone git@github.com:takunagai/agent-assets.git ~/Projects/agent-assets

# ハブ（~/.agents）から実体へ絶対 symlink
ln -s /Users/$USER/Projects/agent-assets/skills/handover-scaffold ~/.agents/skills/handover-scaffold

# Claude Code 用に ~/.agents への相対 symlink
ln -s ../../.agents/skills/handover-scaffold ~/.claude/skills/handover-scaffold
```

スキル本体の構成（人間用マニュアルである本ファイルは `docs/` に置いています）:

```
skills/handover-scaffold/
├── SKILL.md                    # スキル定義（実行時に読む）
└── templates/
    ├── 00_実行順.md             # バッチ用マニフェストのテンプレート
    └── 指示書.md                # 単発・バッチ共通の指示書テンプレート
```

> このスキルは規約を複製しません。生成前に必ず正本 `~/.claude/rules/handover-doc.md` を読み、その内容に従います（モデル選定基準・宛先分離・permission mode・アーカイブ規約など）。

---

## クイックスタート

自然言語で発動します。「引き継ぎ指示書を作って」「バッチで 3 本の指示書を用意して」など。

## ワークフロー

1. **ヒアリング** — 単発かバッチか、バッチならバッチ名・各指示書の 1 行サマリ・Wave 構成、対象リポジトリの絶対パス・ブランチ、推奨モデルと思考キーワード要否
2. **日付取得** — `date +%F` で当日を取得
3. **配置** — 単発は `handover/指示書_<内容>.md`、バッチは `handover/<YYYY-MM-DD>_<バッチ名>/` 配下に `00_実行順.md` と各指示書
4. **テンプレート展開** — プレースホルダを対話で埋める
5. **案内** — 作成した全ファイルの絶対パスと、コピペ用の開始プロンプトを提示

実行先が Codex で完了まで自走させる場合は、指示書テンプレートの起動方法ブロックを開始プロンプトの代わりに `/goal` 文へ置き換えます（書き方は正本 `handover-doc.md`「実行先が Codex で /goal を使う場合」。破壊的操作を含む指示書には使いません）。

## 本文の章構成（正本準拠）

1. 前提条件
2. スコープ外
3. Stop And Ask 条件
4. 最初に読むファイル
5. 作業手順
6. 完了条件（DoD）
7. 失敗時の撤退
8. 実行ログ欄

## 詳細

判断基準・アーカイブ規約の全文は正本 `~/.claude/rules/handover-doc.md` を、テンプレートの実体はスキル本体の `templates/` を参照してください。
