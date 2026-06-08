# agent-skills

AI エージェント（Claude Code / Codex / Gemini CLI / Cursor など）で使える自作スキルの公開モノレポです。

公開できるものだけをここに収録しています。案件固有・個人運用などの非公開スキルは、同じディレクトリ構造（`skills/<name>/` + `docs/<name>.md`）のまま、別プロジェクトとして管理しています。

## 設計方針

- **スキル本体は `skills/<name>/`** に置き、AI が実行時に使う資産（`SKILL.md` / `scripts` / `references` / `assets`）だけを入れます。
- **人間向けマニュアルは `docs/<name>.md`** に置きます（スキル本体の外）。スキル本体に README 等の人間向け文書を混ぜない、という方針です。
- **実体は 1 つ（single source of truth）**。各エージェントのスキルディレクトリへ **symlink** して使います。
- **`_` で始まるディレクトリ（例 `skills/_image-styles/`）はスキルではありません**。複数スキルが共有するリソースで、`SKILL.md` を持たずスキルとしてはロードされません。ライブラリとして自身の `README.md` / `_index.md` を同梱します（直前の「スキル本体に人間向け文書を混ぜない」は SKILL.md を持つスキル本体に対する方針です）。
  - 例えば `_image-styles` は、`gen-infographic`（図解）と `gen-lifestyle-images`（商品写真）が共通で使う「手描きマーカー」「水彩」などのスタイル定義を持ちます。これらを各スキルに個別コピーすると、スタイルを 1 つ直すたびに全スキルを直すことになり、定義が少しずつズレていきます。共有ライブラリに実体を 1 つだけ置けば、修正は 1 箇所で全スキルに反映されます。「複数のスキルが同じ素材を使い回す」場面で使います。

```
agent-skills/
├── README.md            # このファイル（カタログ）
├── docs/                # 人間向けマニュアル（スキルごとに 1 ファイル）
│   └── <name>.md
└── skills/              # スキル本体（AI 実行資産のみ）
    ├── <name>/          # 各スキル（SKILL.md を持つ）
    │   ├── SKILL.md
    │   ├── scripts/
    │   └── references/
    └── _image-styles/   # 共有リソース（スキルではない・SKILL.md なし）
        ├── _index.md    #   スタイルカタログ（参照側 AI 用）
        ├── README.md    #   運用ドキュメント（人間用）
        └── *.md         #   各スタイル定義
```

## インストール

スキル本体を、使うエージェントのスキルディレクトリへ symlink します。

```bash
git clone git@github.com:takunagai/agent-skills.git ~/Projects/agent-skills

# Claude Code 用
ln -s ~/Projects/agent-skills/skills/<name> ~/.claude/skills/<name>

# Codex など他エージェント用（任意）
ln -s ~/Projects/agent-skills/skills/<name> ~/.agents/skills/<name>
```

> 画像生成スキル（`gen-infographic` 等）はスタイル定義を共有ライブラリ `_image-styles` に依存します。スキル本体を symlink すれば `references/styles → ../../_image-styles` はリポ内で解決するため、**`_image-styles` を個別に symlink する必要はありません**。`.skill` 形式で配布するときだけ、各スキルの `scripts/sync-styles.sh --embed` で実体を埋め込みます。

## スキル一覧

| スキル | 概要 | ドキュメント |
|--------|------|-------------|
| cc-fork-delete | Claude Code のフォークセッションを sid 指定で安全削除（dry-run → 確認 → 実行、既定はゴミ箱退避） | [docs/cc-fork-delete.md](docs/cc-fork-delete.md) |
| astro-code-review | Astro 6.0+ プロジェクト（Cloudflare デプロイ対応）のコードを体系的にレビュー。ベストプラクティス違反・パフォーマンス・a11y・型安全性・Astro 6.0 移行問題を検出 | [docs/astro-code-review.md](docs/astro-code-review.md) |
| gen-nanobanana-images | Google Gemini の画像生成モデル Nano Banana シリーズ（Flash / Flash2 / Pro）で、テキストからの画像生成・画像編集・スタイルリファレンス・マルチターン反復修正を行う。要 `GEMINI_API_KEY` | [docs/gen-nanobanana-images.md](docs/gen-nanobanana-images.md) |
| gen-infographic | 日本語の文章・メモ・PDF・スクショなどを 1 枚の読みやすい図解画像へ変換。構造（流れ図・対比・循環・一覧）とスタイル（手描き／ミニマル／水彩／設計図風）を独立に組合せ | [docs/gen-infographic.md](docs/gen-infographic.md) |
| gen-lifestyle-images | 商品のライフスタイル写真を一括生成。ブランド・商品カタログ・シーンをプリセット管理し、セミオート（プラン提示→承認→生成）で量産。要 `GEMINI_API_KEY` | [docs/gen-lifestyle-images.md](docs/gen-lifestyle-images.md) |
| git-workflow | Git ワークフロー支援。Conventional Commits（日本語 subject）でのメッセージ生成・コミット前チェック（機密情報/デバッグコード等）・ブランチ命名規則・マージ戦略ガイド | [docs/git-workflow.md](docs/git-workflow.md) |
| obsidian-vault-create | 新しい Obsidian Vault を標準レイアウトで作成。`YYYY-MM-DD-Project` 命名・数値プレフィックスのフォルダ・README/Home・任意で `.obsidian` 設定コピー。`~/Documents` 既定 | [docs/obsidian-vault-create.md](docs/obsidian-vault-create.md) |
| refund-request | 返金・キャンセル請求メールを、相手企業のポリシー調査の上で交渉力のある文面に。英語・日本語対応、送信前チェックリスト＋4 段階フォローアップ戦略つき | [docs/refund-request.md](docs/refund-request.md) |
| article-quality-enhancer | 8 テクニック（裏テーマ・対立構造・失敗注入・読者解像度・比喩・数字と固有名詞・逆説・余白）で日本語記事の内容の質を構造的に高める。Vault 連携はオプション | [docs/article-quality-enhancer.md](docs/article-quality-enhancer.md) |
| note-article-writer | note.com 向け記事を「分析→構造設計→本文執筆→AI 臭排除」の 4 フェーズで生成。外部 API 不要、書き手プロフィールは任意参照 | [docs/note-article-writer.md](docs/note-article-writer.md) |
| deploy-cloudflare | Next.js + OpenNext 構成専用。git status → ビルド → push → wrangler deploy を自動化。本番/プレビュー対応、`DEPLOY_PROJECT_DIR`/`PRODUCTION_URL` で設定 | [docs/deploy-cloudflare.md](docs/deploy-cloudflare.md) |
| deploy-astro-cloudflare | Astro + `@astrojs/cloudflare` 構成専用。Workers Builds（GitHub 連携）とローカル `wrangler deploy` の 2 モードに対応 | [docs/deploy-astro-cloudflare.md](docs/deploy-astro-cloudflare.md) |
| cloudflare-lesson-note | 学習セッションの内容を技術ブログ品質の Obsidian ノートに整形・保存。保存先は `$LESSON_VAULT_PATH` で指定、特定 Vault に非依存 | [docs/cloudflare-lesson-note.md](docs/cloudflare-lesson-note.md) |

## 共有ライブラリ（スキルではない）

`skills/_` で始まるディレクトリは `SKILL.md` を持たず、スキルとしてはロードされない共有リソースです。

| ライブラリ | 概要 | ドキュメント |
|------------|------|-------------|
| _image-styles | 画像生成スキル群が共有するスタイル定義（手描きマーカー／ミニマル・フラット／水彩／設計図風）。構造非依存で、生成プロンプトの `{{STYLE}}` に差し込んで使う | [README](skills/_image-styles/README.md) ／ [カタログ](skills/_image-styles/_index.md) |
