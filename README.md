# agent-assets

AI エージェント（Claude Code / Codex / Gemini CLI / Cursor など）で使える自作スキル・サブエージェントの公開モノレポです。

公開できるものだけをここに収録しています。案件固有・個人運用などの非公開スキルは、同じディレクトリ構造（`skills/<name>/` + `docs/<name>.md`）のまま、別プロジェクトとして管理しています。

## 設計方針

- **スキル本体は `skills/<name>/`** に置き、AI が実行時に使う資産（`SKILL.md` / `scripts` / `references` / `assets`）だけを入れます。
- **サブエージェントは `agents/<name>.md`** に置きます（Claude Code サブエージェント形式の単一ファイル）。人間向けマニュアルの分離・symlink 運用はスキルと共通です。
- **人間向けマニュアルは `docs/<name>.md`** に置きます（スキル本体の外）。スキル本体に README 等の人間向け文書を混ぜない、という方針です。
- **実体は 1 つ（single source of truth）**。各エージェントのスキルディレクトリへ **symlink** して使います。
- **`_` で始まるディレクトリ（例 `skills/_image-styles/`）はスキルではありません**。複数スキルが共有するリソースで、`SKILL.md` を持たずスキルとしてはロードされません。ライブラリとして自身の `README.md` / `_index.md` を同梱します（直前の「スキル本体に人間向け文書を混ぜない」は SKILL.md を持つスキル本体に対する方針です）。
  - 例えば `_image-styles` は、`gen-infographic`（図解）と `gen-lifestyle-images`（商品写真）が共通で使う「手描きマーカー」「水彩」などのスタイル定義を持ちます。これらを各スキルに個別コピーすると、スタイルを 1 つ直すたびに全スキルを直すことになり、定義が少しずつズレていきます。共有ライブラリに実体を 1 つだけ置けば、修正は 1 箇所で全スキルに反映されます。「複数のスキルが同じ素材を使い回す」場面で使います。

```
agent-assets/
├── README.md            # このファイル（カタログ）
├── agents/              # サブエージェント本体（Claude Code 用・1 エージェント 1 ファイル）
│   └── <name>.md
├── docs/                # 人間向けマニュアル（スキル・エージェントごとに 1 ファイル）
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
git clone git@github.com:takunagai/agent-assets.git ~/Projects/agent-assets

# Claude Code 用
ln -s ~/Projects/agent-assets/skills/<name> ~/.claude/skills/<name>

# Codex など他エージェント用（任意）
ln -s ~/Projects/agent-assets/skills/<name> ~/.agents/skills/<name>
```

サブエージェントは Claude Code 固有のため、`~/.claude/agents/` へ直接 symlink します。

```bash
ln -s ~/Projects/agent-assets/agents/<name>.md ~/.claude/agents/<name>.md
```

> 画像生成スキル（`gen-infographic` 等）はスタイル定義を共有ライブラリ `_image-styles` に依存します。スキル本体を symlink すれば `references/styles → ../../_image-styles` はリポ内で解決するため、**`_image-styles` を個別に symlink する必要はありません**。`.skill` 形式で配布するときだけ、各スキルの `scripts/sync-styles.sh --embed` で実体を埋め込みます。

## スキル一覧

| スキル | 概要 | ドキュメント |
|--------|------|-------------|
| cc-fork-delete | Claude Code のフォークセッションを sid 指定で安全削除（dry-run → 確認 → 実行、既定はゴミ箱退避） | [docs/cc-fork-delete.md](docs/cc-fork-delete.md) |
| cc-project-relocate | Claude Code のプロジェクトを移動・リネームした後、パスに紐づくセッションログ dir（会話・memory）を新パスへリネーム/マージ。任意で `~/.claude.json` の trust/権限も移行。本体と同一エンコードを node で計算、dry-run → 確認 → 実行 | [docs/cc-project-relocate.md](docs/cc-project-relocate.md) |
| astro-code-review | Astro 7+ プロジェクト（Cloudflare Workers デプロイ対応）のコードを体系的にレビュー。ベストプラクティス違反・パフォーマンス・a11y・型安全性・レガシー API（5→6 削除済み）・Astro 7 移行問題（Rust コンパイラ HTML 厳格化・Sätteri・src/fetch.ts 予約名）を検出 | [docs/astro-code-review.md](docs/astro-code-review.md) |
| gen-nanobanana-images | Google Gemini の画像生成モデル Nano Banana シリーズ GA 版（Flash2 / Pro / Nano Banana 2 Lite）で、Interactions API 基盤のテキストからの画像生成・画像編集・スタイルリファレンス・マルチターン反復修正を行う。生成のたびに出力先へ生成記録 Markdown（指示原文・プロンプト・料金目安・検証メモ）を自動作成。要 `GEMINI_API_KEY`・SDK >= 2.11.0 | [docs/gen-nanobanana-images.md](docs/gen-nanobanana-images.md) |
| gen-infographic | 日本語の文章・メモ・PDF・スクショなどを 1 枚の読みやすい図解画像へ変換。構造（流れ図・対比・循環・一覧）とスタイル（手描き／ミニマル／水彩／設計図風）を独立に組合せ | [docs/gen-infographic.md](docs/gen-infographic.md) |
| gen-lifestyle-images | 商品のライフスタイル写真を一括生成。ブランド・商品カタログ・シーンをプリセット管理し、セミオート（プラン提示→承認→生成）で量産。要 `GEMINI_API_KEY` | [docs/gen-lifestyle-images.md](docs/gen-lifestyle-images.md) |
| image-gen-handoff | Codex `image_gen` / Image 2.0 の大量生成後に、保存済み画像と session JSONL から最終生成プロンプト・sha256・寸法・欠損・重複を manifest 化し、軽量な引き継ぎノートを作成 | [docs/image-gen-handoff.md](docs/image-gen-handoff.md) |
| git-workflow | Git ワークフロー支援。Conventional Commits（日本語 subject）でのメッセージ生成・コミット前チェック（機密情報/デバッグコード等）・ブランチ命名規則・マージ戦略ガイド | [docs/git-workflow.md](docs/git-workflow.md) |
| obsidian-vault-create | 新しい Obsidian Vault を標準レイアウトで作成。`YYYY-MM-DD-Project` 命名・数値プレフィックスのフォルダ・README/Home・任意で `.obsidian` 設定コピー。`~/Documents` 既定 | [docs/obsidian-vault-create.md](docs/obsidian-vault-create.md) |
| refund-request | 返金・キャンセル請求メールを、相手企業のポリシー調査の上で交渉力のある文面に。英語・日本語対応、送信前チェックリスト＋4 段階フォローアップ戦略つき | [docs/refund-request.md](docs/refund-request.md) |
| article-quality-enhancer | 8 テクニック（裏テーマ・対立構造・失敗注入・読者解像度・比喩・数字と固有名詞・逆説・余白）で日本語記事の内容の質を構造的に高める。Vault 連携はオプション | [docs/article-quality-enhancer.md](docs/article-quality-enhancer.md) |
| deploy-nextjs-cloudflare | Next.js + OpenNext 構成専用。公式 CLI（opennextjs-cloudflare deploy / upload）で本番デプロイと Preview URL 発行を自動化。フレームワーク検出・認証確認などプリフライトつき deploy.sh 同梱 | [docs/deploy-nextjs-cloudflare.md](docs/deploy-nextjs-cloudflare.md) |
| deploy-astro-cloudflare | Astro 7 + `@astrojs/cloudflare` v14 構成専用。Workers Builds（GitHub 連携）・ローカル `wrangler deploy`・プレビューの 3 モード + プリフライト検証（バージョン・wrangler.jsonc・認証）・デプロイ完了確認・ロールバック | [docs/deploy-astro-cloudflare.md](docs/deploy-astro-cloudflare.md) |
| cloudflare-lesson-tutor | Cloudflare 学習カリキュラムの授業運営。Dashboard.md で現在地把握 → 一次情報で鮮度検証（retrieval 優先・フレームワークは公式 docs を正）→ 対話形式で 1 セクション授業 → 保存案内。Vault へは読み取りのみ | [docs/cloudflare-lesson-tutor.md](docs/cloudflare-lesson-tutor.md) |
| cloudflare-lesson-note | 学習セッションの内容を技術ブログ品質の Obsidian ノートに整形・保存し、Dashboard.md の進捗を更新（Vault への唯一のライター）。上書き保護・鮮度メタデータ（`verified`）つき。保存先は `$LESSON_VAULT_PATH` で指定、特定 Vault に非依存 | [docs/cloudflare-lesson-note.md](docs/cloudflare-lesson-note.md) |
| print-card-comp | 印刷物（名刺・しおり・ポストカード・DL・ショップ/二つ折りカード等）の表裏デザインカンプを依頼内容から一括生成。色数対応（4C/1C/2C 特色）・レイアウトパターン 8 種・縦書き/字間/duotone 組版・QR 生成（segno）・合成後セルフレビュー・入稿指示書まで。背景は gen-nanobanana-images / gpt-image-2 を委譲利用 | [docs/print-card-comp.md](docs/print-card-comp.md) |
| mac-gui-router | Mac の GUI 操作・スクショ依頼の方式判定ルーター。公式 computer-use / 自作ループ（screencapture + CGEvent）/ chrome-devtools から最適を選び、操作 = 公式・撮影 = 自作のハイブリッド（操作マニュアル作成）にも対応。要ヘルパー 3 種（付属手順でビルド） | [docs/mac-gui-router.md](docs/mac-gui-router.md) |
| claude-config-audit | `~/.claude` グローバル設定の健全性検査。死 symlink・disabled なのにキャッシュ残存の plugin・MCP 重複登録・orphan commands を検出。レポートのみ・自動削除なし。pre-add モードで追加前の重複チェックも可能 | [docs/claude-config-audit.md](docs/claude-config-audit.md) |
| handover-scaffold | 別セッションで無人実行させる「指示書（引き継ぎドキュメント）」の骨組みを一発生成。`handover/` バッチのフォルダ・`00_実行順.md` マニフェスト・指示書スケルトンを規約どおりに作成 | [docs/handover-scaffold.md](docs/handover-scaffold.md) |
| emdash-cms | EmDash（Astro + Cloudflare の full-stack TypeScript CMS、emdash 0.29 基準）の構築支援。セットアップ・コンテンツモデリング・クエリ / Portable Text・認証・プラグイン開発（sandboxed / native）・メール（公式 `cloudflareEmail()` + Email Service）・Forms・WordPress 移行・MCP 連携。v0.x ベータのため鮮度検証手順を内蔵 | [docs/emdash-cms.md](docs/emdash-cms.md) |

## サブエージェント一覧

`agents/` 配下は Claude Code のサブエージェント（独立コンテキストで動く専門エージェント）です。

| サブエージェント | 概要 | ドキュメント |
|------------------|------|-------------|
| git-version-control | コミット・ブランチ・PR を独立コンテキストで実行。手順は git-workflow スキルに従う（Conventional Commits の日本語コミット、コミット前チェック、AI 署名なし）。作業完了時にプロアクティブに起動してコミットを提案する | [docs/git-version-control.md](docs/git-version-control.md) |
| explorer | 読み取り専用の探索専任（model: sonnet / effort: medium）。複数ファイル横断調査・仕様/ログ読解・Web リサーチを引き受け、path:line 参照付きの構造化サマリのみを返す。8 回以上の連続読み取り・5 ファイル以上の調査で委譲推奨 | [docs/explorer.md](docs/explorer.md) |
| scanner | 機械的スキャン専任（model: haiku / effort: low）。解釈不要な grep 列挙・件数集計・シンボル使用箇所の列挙を行う。判断が必要になったら explorer への委譲を提案する | [docs/scanner.md](docs/scanner.md) |

## 共有ライブラリ（スキルではない）

`skills/_` で始まるディレクトリは `SKILL.md` を持たず、スキルとしてはロードされない共有リソースです。

| ライブラリ | 概要 | ドキュメント |
|------------|------|-------------|
| _image-styles | 画像生成スキル群が共有するスタイル定義（手描きマーカー／ミニマル・フラット／水彩／設計図風）。構造非依存で、生成プロンプトの `{{STYLE}}` に差し込んで使う | [README](skills/_image-styles/README.md) ／ [カタログ](skills/_image-styles/_index.md) |
| _lesson-methods | Cloudflare 学習の 2 スキル（cloudflare-lesson-tutor／cloudflare-lesson-note）が共有する教授法リソース（難解な概念を平易に伝える実行ガイド）。各スキルの `references/` から相対 symlink で参照 | [README](skills/_lesson-methods/README.md) |
