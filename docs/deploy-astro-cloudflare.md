# deploy-astro-cloudflare

**Astro 7 + `@astrojs/cloudflare` v14 構成専用**の Cloudflare Workers デプロイスキルです。Workers Builds（GitHub 連携の自動デプロイ）・ローカルからの `wrangler deploy`・プレビューデプロイの 3 モードに対応します。デプロイ前のプリフライト検証（バージョン・`wrangler.jsonc`・認証）→ ビルド確認 → デプロイ → 完了確認までを自動で実行し、ロールバックも扱います。

---

## 対応環境

| 項目 | 内容 |
|------|------|
| フレームワーク | Astro 7 以降 |
| アダプター | `@astrojs/cloudflare` v14 以降（統一エントリポイント `@astrojs/cloudflare/entrypoints/server`） |
| デプロイ先 | Cloudflare Workers（static assets 付き。Cloudflare Pages は廃止済み） |
| Node.js | v22.12.0 以上（奇数メジャー v23 等は非対応） |
| デプロイツール | wrangler（`wrangler.jsonc` で設定） |
| CI/CD | Workers Builds（Cloudflare の GitHub 連携） |

> **旧バージョンは非対応**: `astro < 7` または `@astrojs/cloudflare < 14` を検出した場合、スキルはデプロイせず停止し、公式移行ガイド（[v7 へのアップグレード](https://docs.astro.build/en/guides/upgrade-to/v7/)、v5 系からは [v6 ガイド](https://docs.astro.build/en/guides/upgrade-to/v6/)も経由）を案内します。既存プロジェクトも v7 へ更新する前提のため、旧バージョン向けのデプロイ手順は提供しません。

> **注意**: Next.js + OpenNext 構成のデプロイには別スキル `deploy-nextjs-cloudflare` を使ってください（末尾の使い分け表を参照）。

---

## インストール

このリポジトリを clone し、スキル本体（`skills/deploy-astro-cloudflare`）を各エージェントのスキルディレクトリへ symlink します。実体は 1 つ、参照を複数張る方式です。当環境では「実体 → `~/.agents` → `~/.claude`」の 2 段 symlink で統一しています。

```bash
git clone git@github.com:takunagai/agent-assets.git ~/Projects/agent-assets
ln -s /Users/$USER/Projects/agent-assets/skills/deploy-astro-cloudflare ~/.agents/skills/deploy-astro-cloudflare
ln -s ../../.agents/skills/deploy-astro-cloudflare ~/.claude/skills/deploy-astro-cloudflare
```

> Codex など他のエージェントは `~/.agents/skills/deploy-astro-cloudflare` を直接読みます。Claude Code は `~/.claude/skills/` を経由して同じ実体を参照します。

スキル本体の構成は次の通りです（人間用マニュアルである本ファイルは、スキル本体の外＝`docs/` に置いています）。

```
skills/deploy-astro-cloudflare/
├── SKILL.md                         # スキル定義（Claude がトリガー時に読む）
└── references/                      # SKILL.md から参照する詳細資料
    ├── preflight-checklist.md       # プリフライト各項目の実行コマンド・期待結果・失敗時対処
    ├── secrets-and-env.md           # 環境変数の 4 層整理・keep_vars・astro:env / cloudflare:workers
    └── troubleshooting.md           # エラー対応表（v7 / v14 固有の落とし穴を含む）
```

---

## クイックスタート

Claude Code で以下を入力するだけ:

```bash
/deploy-astro-cloudflare
```

これだけで、プリフライト検証 → 未コミット変更の処理 → デプロイ → 完了確認までを自動で実行します。

自然言語でも発動します。「デプロイして」「本番に反映」「Cloudflare にデプロイ」「プレビューにデプロイ」など。

---

## 3 つのデプロイモード

### モード A: Workers Builds（デフォルト・推奨）

GitHub 連携済みなら、`git push` だけで Cloudflare が自動ビルド・デプロイします。

```bash
/deploy-astro-cloudflare
```

**流れ:** プリフライト → 状態確認 → 未コミット変更をコミット → `git push origin main` → Workers Builds が自動ビルド・デプロイ → **デプロイ完了確認** → 報告

> `git push` はトリガーにすぎず、push 直後はまだデプロイ未完了です。スキルは `wrangler deployments list` での新デプロイ確認、または本番 URL への疎通確認を経てから完了を報告します。
>
> GitHub 連携・Workers Builds がまだの場合は Cloudflare ダッシュボードでセットアップしてください。セットアップ完了まではモード B を使います。

### モード B: ローカルデプロイ（`--local`）

Workers Builds が未設定の場合や、手元から直接デプロイしたい場合:

```bash
/deploy-astro-cloudflare --local
```

**流れ:** プリフライト（認証・Node 確認を含む）→ コミット → ビルド事前チェック → デプロイ（`package.json` の `deploy` スクリプト優先、なければ `npx astro build && npx wrangler deploy` にフォールバック、タイムアウト 10 分）→ `git push origin main` → 完了確認

> 初回は `wrangler login` で Cloudflare にログインしておく必要があります。
>
> **二重デプロイに注意**: Workers Builds 設定済みのリポジトリで `--local` デプロイ後に push すると、ローカルと Workers Builds で二重にデプロイが走ります。Workers Builds 運用中はモード A を使ってください。

### モード C: プレビューデプロイ（`--preview`）

本番トラフィックに影響を与えずにプレビュー URL を発行して検証します:

```bash
/deploy-astro-cloudflare --preview
```

**ローカル起点（推奨）:** `wrangler versions upload --preview-alias <alias>` でプレビュー URL（`<alias>-<worker>.<subdomain>.workers.dev`）を発行します。本番の Active Deployment は変わりません。workers.dev サブドメインが有効である必要があります。

**Workers Builds 利用時:** 非本番ブランチへの push でプレビューを出せますが、デフォルトでは無効です。ダッシュボードで「Builds for non-production branches」を有効化すると、非本番ブランチの deploy コマンドが `npx wrangler versions upload` となりプレビュー URL が生成されます。

## MCP 連携（接続済みなら優先。CLI が実行骨格）

公式プラグイン `cloudflare` の MCP サーバーが接続済み（OAuth 認証済み）なら、次を CLI コマンドの代わりに使ってよい。未接続・未認証の場合は従来どおり CLI で続行する。

- **デプロイ状態確認** ─ `cloudflare-builds`（Workers Builds のビルド・デプロイ状態）。未接続時は `wrangler deployments list`。
- **本番ログ確認** ─ `cloudflare-observability`（本番 Workers ログ・分析）。未接続時は `wrangler tail`。
- **ドキュメント疑問点の確認** ─ `cloudflare-docs`（認証不要・常時使用可）。ドキュメント参照の第一手段としてよい。

---

## オプション

| オプション | 説明 | 使いどころ |
|-----------|------|-----------|
| （なし） | Workers Builds 経由でデプロイ | 通常のデプロイ |
| `--local` | ローカルから直接 `wrangler deploy` | Workers Builds 未設定時、手元から直接デプロイしたいとき |
| `--preview` | プレビュー URL を発行（本番に載せない） | マージ前の検証、レビュー用 URL の共有 |
| `--skip-build` | ビルド事前チェックを省略 | 急ぎのデプロイ時（ビルド済みの場合）。緊急時のみ |

---

## 前提条件

- `wrangler.jsonc`（または `.json` / `.toml`）の `main` が `"@astrojs/cloudflare/entrypoints/server"` であること（シンプルな構成では設定ファイルを Astro が自動生成する運用も可）
- `assets.directory`（通常 `"./dist"`）・`compatibility_date` が設定済みであること
- ダッシュボードで環境変数を管理する運用では `wrangler.jsonc` に **`"keep_vars": true`** があること
- モード B / C では Cloudflare に認証済み（`wrangler whoami`）で、Node.js が v22.12.0 以上であること

### `keep_vars: true` がなぜ必要か

`wrangler deploy` はデフォルトで、Cloudflare ダッシュボードに設定した環境変数を上書き・削除します。`wrangler.jsonc` に `"keep_vars": true` を設定しておくと、ダッシュボードの環境変数が保持されます。**これがないと、デプロイ後に環境変数が消えてサイトが動作しなくなります。**（すべての変数を `wrangler.jsonc` で管理する運用なら不要です。）

> `@astrojs/cloudflare` v14 では、統一エントリポイントにより `_worker.js` を静的アセットとして出力しないため、旧構成で必要だった `public/.assetsignore` は不要になりました。

---

## Astro 固有の注意点

Cloudflare Workers 上の Astro では、**サーバーサイドで `import.meta.env` を使えません**。ビルド時に値が固定されるため、リクエスト時のランタイム環境変数（ダッシュボード設定値や Secrets）を読めないからです。

ランタイム値を読むには `cloudflare:workers` の `env` を使います（型安全にするなら `astro:env/server`）。

```astro
---
// NG: サーバーサイドでは値が取れない / ビルド時固定
const apiKey = import.meta.env.API_KEY;

// OK: ランタイム環境変数・バインディングを参照する
import { env } from 'cloudflare:workers';
const apiKey = env.API_KEY;
---
```

> 旧構成（Astro 5 / 6・adapter v13 以前）の `Astro.locals.runtime.env` は**削除済み API**です。新規コードでは使わず、`cloudflare:workers` の `env` へ移行してください。

ビルドは通るのに本番で 500 エラーになる場合、ほぼこの移行漏れが原因です。詳細は `references/secrets-and-env.md` を参照してください。

---

## よくあるトラブルと対処

| こんなとき | やること |
|-----------|---------|
| `wrangler: command not found` | `npm install -D wrangler`（`npx` / `pnpm dlx` / `bunx` で実行してもよい） |
| 認証エラーが出る | `wrangler login` で再ログイン（CI は API トークン） |
| デプロイ後にサイトが動かない（環境変数消失） | `wrangler.jsonc` に `"keep_vars": true` があるか確認 |
| サーバーで `Astro.locals.runtime` が undefined | 削除済み API。`cloudflare:workers` の `env` へ移行 |
| ビルドは通るが本番で 500 エラー | サーバーコードで `import.meta.env` を使っていないか確認 |
| v7 更新後にビルドが落ちる | Rust コンパイラの HTML 厳格化 / Markdown プロセッサ（Sätteri）変更 / `src/fetch.ts` 予約名衝突（`references/troubleshooting.md`） |
| Workers Builds が失敗する | ダッシュボードの View build history でビルドログを確認 |
| 本番でエラーが再現するがログを追いたい | 接続済みなら `cloudflare-observability` MCP で本番ログ・分析を確認。未接続時は `wrangler tail` |
| 二重デプロイ | Workers Builds 設定済みで `--local` + push を併用していないか確認 |

---

## deploy-nextjs-cloudflare との使い分け

同じリポジトリに、Cloudflare Workers へデプロイするスキルが 2 つあります。対象フレームワーク・ビルド成果物が異なるため、構成に合わせて選びます。

| | deploy-astro-cloudflare（本スキル） | deploy-nextjs-cloudflare |
|---|---|---|
| 対象 | Astro 7+ | Next.js |
| アダプター / ビルダ | `@astrojs/cloudflare` v14+ | `@opennextjs/cloudflare`（OpenNext） |
| ビルドコマンド | `astro build && wrangler deploy` | OpenNext ビルド + `wrangler deploy` |
| こういうとき | `astro.config.*` に Astro 設定があり `@astrojs/cloudflare` を使っている | `next.config.*` があり OpenNext で Cloudflare 化している |

「デプロイして」のような曖昧な指示ではトリガー語が衝突しうるので、Astro 構成では本スキルを、Next.js 構成では `deploy-nextjs-cloudflare` を明示的に選んでください。

---

## 詳細

実行フロー（各モードのステップ詳細）・プリフライト項目・エラー対応表・環境変数管理の根拠は、スキル本体の `SKILL.md` と `references/` 配下を参照してください。

## 外部リファレンス

- [Cloudflare Adapter（Astro）](https://docs.astro.build/en/guides/integrations-guide/cloudflare/)
- [Astro v7 へのアップグレード](https://docs.astro.build/en/guides/upgrade-to/v7/)
- [Astro 7 リリース記事](https://astro.build/blog/astro-7/)
- [Workers Builds](https://developers.cloudflare.com/workers/ci-cd/builds/)
- [Workers Builds ─ ビルドブランチ設定](https://developers.cloudflare.com/workers/ci-cd/builds/build-branches/)
- [プレビュー URL（wrangler versions upload）](https://developers.cloudflare.com/workers/configuration/previews/)
- [wrangler deploy](https://developers.cloudflare.com/workers/wrangler/commands/#deploy)
