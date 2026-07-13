---
name: emdash-cms
description: "EmDash（Cloudflare 発の TypeScript/Astro ベース CMS、WordPress の精神的後継・MIT）のセットアップ・構成・運用スキル。emdash 0.29 基準。新規サイト作成（pnpm create emdash）・既存 Astro への統合・Cloudflare（D1/R2/KV）と Node/SQLite の設定・コンテンツモデル定義と getEmDashCollection 取得・Portable Text レンダリング・認証（Astro.locals.user）・プラグイン開発（sandboxed / native）・メールとフォーム・WordPress からの移行・MCP サーバー・CLI を扱う。『EmDash をセットアップして』『EmDash でコンテンツタイプを作って』『EmDash プラグインを作って』『WordPress から EmDash に移行して』『EmDash に問い合わせフォームを追加して』などのリクエストで発動。デプロイ実行自体は deploy-astro-cloudflare と連携する。"
---

# EmDash CMS Skill

## 概要・適用範囲

EmDash は Cloudflare 発の CMS で、WordPress の精神的後継として設計されている。全編 TypeScript・Astro integration として動作し、ライセンスは MIT。管理画面（Portable Text エディタ・スキーマビルダー・メディア管理）と、Astro プロジェクトへのコンテンツ配信を 1 パッケージで担う。

このスキルは次を扱う ─ 新規サイトの作成、既存 Astro プロジェクトへの統合、Cloudflare（D1 / R2 / KV）および Node / SQLite でのデータベース・ストレージ設定、コンテンツモデル定義とクエリ、Portable Text レンダリング、認証、プラグイン開発、メール・フォーム、WordPress 移行、MCP サーバー、CLI。**デプロイの実行自体**は Astro + Cloudflare Workers 構成なので、既存スキル `deploy-astro-cloudflare` と連携する（本スキルは構成まで、デプロイ操作はそちらへ委譲）。

> [!important] EmDash は v0.x の早期ベータ ─ 作業開始前に必ず鮮度検証する
> 本スキルは **emdash 0.29.0（2026-07-10 リリース）/ 2026-07-13 検証**を基準とする。EmDash は v0.x のため API・CLI・設定が数ヶ月単位で大きく変わる。作業を始める前に必ず次を実行し、乖離があれば公式ドキュメントを優先すること。
>
> ```bash
> pnpm view emdash version          # 現行の最新版を確認
> pnpm view create-emdash version   # スキャフォールダも同時に確認
> ```
>
> GitHub の releases（https://github.com/emdash-cms/emdash/releases）でメジャーな変更を確認する。基準（0.29.x）とメジャー／マイナーがずれていたら、本スキルのコード例をそのまま使わず、公式ドキュメント（下記）で該当 API を裏取りしてから進める。
> - 情報の正本: https://github.com/emdash-cms/emdash （docs は `docs/src/content/docs/` 配下）
> - ドキュメントサイト: https://docs.emdashcms.com

## 技術スタック前提

パッケージマネージャーは **pnpm** を基準とする（`pnpm create emdash` に対応）。

| パッケージ / ツール | 基準バージョン | 備考 |
|---|---|---|
| emdash / create-emdash | 0.29.0 | npm の `1.0.0` は誤公開 deprecated。無視する |
| astro | 7.x | v7 GA（2026-06-22）。emdash の peer は `astro >=6.0.0-beta.0` |
| vite | 8.x | Astro 7 同梱。Rolldown 統合済み |
| @astrojs/cloudflare | 14.x | Cloudflare デプロイ時のアダプタ |
| @emdash-cms/cloudflare | 0.29 系 | D1 / R2 / KV / Hyperdrive / Cloudflare Email 用の別パッケージ |
| tailwindcss / @tailwindcss/vite | 4.x | CSS-first。`tailwind.config.js` 不要 |
| @biomejs/biome | 2.x | `.astro` は実験的サポート（2.3.0+） |
| pnpm | 11.x | |
| wrangler | 4.x | Cloudflare デプロイ用 |

Cloudflare 構成では D1（DB）・R2（メディア）が既定。KV はオブジェクトキャッシュ用（任意）、Worker Loaders は sandboxed プラグイン実行時のみ。

## セットアップ

### 新規サイト作成

```bash
pnpm create emdash@latest my-site
```

対話は 2 段階 ─ プラットフォーム（`node` / `cloudflare`）→ テンプレート（`blog` / `starter` / `marketing` / `portfolio`）。非対話で作るなら `--yes`（既定は cloudflare + blog + `my-site`）。テンプレート実体は `emdash-cms/templates` リポジトリから取得される。生成されるプロジェクトには `astro.config.mjs`・`wrangler.jsonc`（Cloudflare 時）・`src/worker.ts` が含まれる。

### 既存 Astro プロジェクトへの統合

`emdash()` integration を `astro.config.mjs` に追加する。データベースとストレージのアダプタは必須。**アダプタの import 元がプラットフォームで分かれる**点に注意する。

- コア（integration 本体）と Node 向けストレージ: `emdash/astro`（`emdash`・`local`・`s3`）
- Node 向けデータベース: `emdash/db`（`sqlite`・`libsql`・`postgres`）
- Cloudflare 向けアダプタ: `@emdash-cms/cloudflare`（`d1`・`r2`・`kvCache`・`hyperdrive`）

Node / SQLite の最小構成:

```js
import { defineConfig } from "astro/config";
import emdash, { local } from "emdash/astro";
import { sqlite } from "emdash/db";

export default defineConfig({
  integrations: [
    emdash({
      database: sqlite({ url: "file:./data.db" }),
      storage: local({
        directory: "./uploads",
        baseUrl: "/_emdash/api/media/file",
      }),
    }),
  ],
});
```

### TailwindCSS v4 と Biome 2 の併用

TailwindCSS は v4 の CSS-first 方式を使う。`@tailwindcss/vite` を Vite プラグインに追加し、CSS 側は `@import "tailwindcss";` の 1 行のみ（`tailwind.config.js` は作らない）。

```js
// astro.config.mjs（抜粋）
import tailwindcss from "@tailwindcss/vite";
export default defineConfig({
  vite: { plugins: [tailwindcss()] },
  integrations: [emdash({ /* ... */ })],
});
```

Biome 2 は `.astro` を実験的にサポートする（2.3.0+）。EmDash 管理 UI の生成物や Astro テンプレート特有の構文で誤検出が出ることがあるため、該当ルールはプロジェクトの `biome.json` でオフにして運用する。フォーマットは対象拡張子を明示し、`.astro` の未対応領域は対象外にする。

## 設定（Cloudflare 既定）

Cloudflare 構成では `@astrojs/cloudflare` アダプタ + `@emdash-cms/cloudflare` のアダプタを使う。

```js
// astro.config.mjs
import { defineConfig } from "astro/config";
import cloudflare from "@astrojs/cloudflare";
import emdash from "emdash/astro";
import { d1, r2 } from "@emdash-cms/cloudflare";

export default defineConfig({
  output: "server",
  adapter: cloudflare(),
  integrations: [
    emdash({
      database: d1({ binding: "DB" }),
      storage: r2({ binding: "MEDIA", publicUrl: "https://pub-xxxx.r2.dev" }),
    }),
  ],
});
```

Worker のエントリポイントで EmDash の `PluginBridge` を再エクスポートする。テンプレートには生成済みだが、手動構成なら `src/worker.ts` を作る。

```ts
// src/worker.ts
export { default, PluginBridge } from "@emdash-cms/cloudflare/worker";
```

`wrangler.jsonc` のバインディング（要点。新規テンプレートは生成済み）:

```jsonc
{
  "name": "my-emdash-site",
  "main": "src/worker.ts",
  "compatibility_date": "2026-07-13", // ← 生成時点の日付を入れる（固定値をコピーしない）
  "compatibility_flags": ["nodejs_compat"],
  "d1_databases": [
    { "binding": "DB", "database_name": "emdash-db", "database_id": "<id>" }
  ],
  "r2_buckets": [
    { "binding": "MEDIA", "bucket_name": "emdash-media" }
  ],
  // 任意: オブジェクトキャッシュに KV を使う場合
  "kv_namespaces": [{ "binding": "CACHE", "id": "<id>" }],
  // sandboxed プラグインを実行する場合のみ
  "worker_loaders": [{ "binding": "LOADER" }]
}
```

> [!note] compatibility_date は生成時点の日付にする
> ドキュメントの例に載っている日付をそのままコピーしない。プロジェクト生成・設定作成時点の日付（例: `2026-07-13`）を入れる。

- **オブジェクトキャッシュ（任意）**: `objectCache: kvCache({ binding: "CACHE" })` を `emdash()` に渡す（`@emdash-cms/cloudflare`）。Node 環境では `memoryCache()`（`emdash/astro`）。EmDash に専用の sessions 設定 API は無く、KV の役割はこのオブジェクトキャッシュ。
- **read replicas**: `d1({ binding: "DB", session: "auto" })` で D1 の Sessions API（読み取りレプリカ）を有効化できる（`"disabled" | "auto" | "primary-first"`）。これは DB のレプリカ設定であり、ユーザーセッションとは無関係。
- **Hyperdrive + Postgres**: `hyperdrive({ binding: "HYPERDRIVE" })`（`@emdash-cms/cloudflare`）。

### ローカル開発・Node / SQLite 代替

Node プラットフォームでは `sqlite({ url: "file:./data.db" })` + `local()` ストレージで動く。外部 DB は `libsql`（Turso）・`postgres`（いずれも `emdash/db`）、S3 互換ストレージは `s3()`（`emdash/astro`、`@aws-sdk/client-s3` の追加インストールが必要）が選べる。開発サーバーは `pnpm exec emdash dev`（Astro の dev に相当）。

> [!important] Dynamic Workers（sandboxed プラグイン実行）は Open Beta・Workers Paid 必須
> sandboxed プラグインは Cloudflare の Dynamic Workers（Worker Loaders）上で動く。これは Open Beta（2026-03-24 開始 ─ Cloudflare changelog）かつ **Workers Paid プラン必須**で、無料プランでは sandboxed プラグインを実行できない。native プラグインはこの制約を受けない。

管理画面は `/_emdash/admin`（ローカルは `http://localhost:4321/_emdash/admin`）。REST API は `/_emdash/api/...`、メディア配信は `/_emdash/api/media/file`。

## コンテンツモデルとクエリ

スキーマ（コンテンツタイプ）は**管理 UI で定義**する。定義後、型を生成する。

```bash
pnpm exec emdash types   # スキーマから TypeScript 型を生成
```

コンテンツは `getEmDashCollection` / `getEmDashEntry`（`emdash`）で取得する。

```ts
import { getEmDashCollection, getEmDashEntry } from "emdash";

// 一覧（公開済みを新しい順に 10 件）
const posts = await getEmDashCollection("posts", {
  filter: { status: "published" },
  sort: { publishedAt: "desc" },
  limit: 10,
});

// ページネーション
const page2 = await getEmDashCollection("posts", { limit: 10, offset: 10 });

// タクソノミーでフィルタ
const tagged = await getEmDashCollection("posts", {
  filter: { tags: { contains: "astro" } },
});

// 単体（slug で 1 件）
const post = await getEmDashEntry("posts", { slug: "hello-world" });
```

フィールド型は 16 種 ─ `string` / `text` / `url` / `number` / `integer` / `boolean` / `datetime` / `select` / `multiSelect` / `portableText` / `image` / `file` / `reference` / `json` / `slug` / `repeater`。正本は `docs/src/content/docs/reference/field-types.mdx`。

## Portable Text レンダリング

本文（`portableText` フィールド）は `<PortableText />`（`emdash/ui`）で描画する。**コンポーネント方式**で、`renderPortableText` のような関数は存在しない。

```astro
---
import { PortableText } from "emdash/ui";
import CustomImage from "../components/CustomImage.astro";
const post = await getEmDashEntry("posts", { slug: Astro.params.slug });
---
<PortableText
  value={post.data.content}
  components={{
    type: { image: CustomImage },
    marks: { /* リンク・装飾のカスタム描画 */ },
  }}
/>
```

- `components` で型（block / mark）ごとの描画をカスタムできる。ユーザー指定の `components` が最優先。
- native プラグインは `componentsEntry` から `export const blockComponents = { youtube: YouTube }`（export 名固定）でブロックコンポーネントを提供できる。

## 認証

ミドルウェアが `Astro.locals.user`（型: `@emdash-cms/auth` の `User`）を自動セットする。**`requireAuth` / `getUser` / `requireRole` のようなガード関数は存在しない**。ページ側で有無と `role` を自前チェックする。

```astro
---
const { user } = Astro.locals;
if (!user) return Astro.redirect("/_emdash/admin");
// 数値でロールを比較（Author 以上のみ許可）
if (user.role < 30) return new Response("Forbidden", { status: 403 });
---
```

ロールは 5 種で、数値が大きいほど権限が強い ─ Subscriber(10) / Contributor(20) / Author(30) / Editor(40) / Admin(50)。ログインは passkey-first（WebAuthn）で、OAuth（`authProviders` に GitHub / Google / ATProto）・magic link にも対応する。`emdash()` の関連オプション: `siteUrl`（passkey の origin）・`allowedOrigins`・`auth`（外部認証アダプタ、例: Cloudflare Access）・`authProviders`。magic link 等のコアメールは後述の email transport 経由で配信される。

## プラグイン

プラグインは 2 形式ある。用途で使い分ける。

- **sandboxed（既定・マーケットプレイス配布形式）**: Worker isolate（Dynamic Workers）で隔離実行する。`emdash-plugin.jsonc`（manifest）+ エントリコードで構成し、`emdash()` の `sandboxed: []` 配列に登録する。信頼できない第三者コードを安全に動かせるのが利点。ただし Workers Paid 必須（前掲）。
- **native（trusted）**: `emdash()` の `plugins: []` 配列に登録する。React 製の管理 UI・Portable Text コンポーネント・ページフラグメントを提供する必要がある場合はこちら。トラストレベルは高いがサンドボックス隔離は無い。

判断基準 ─ **管理 UI / Portable Text コンポーネント / page fragments が要るなら native、それ以外は sandboxed 推奨**。capabilities・hooks・manifest スキーマ・最小テンプレートの詳細は `references/plugin-development.md` を参照する。

## メール・フォーム

- **メール（Cloudflare）**: first-party の `cloudflareEmail` プラグイン（`@emdash-cms/cloudflare/plugins`）を `plugins: []` に登録するのが最短。Cloudflare Email Service（`send_email` binding）へ繋ぐ。magic link・招待・パスワードリセット等のコアメールもこの transport 経由で配信される。

  ```js
  import { cloudflareEmail } from "@emdash-cms/cloudflare/plugins";
  emdash({
    plugins: [
      cloudflareEmail({
        from: { email: "cms@mails.example.com", name: "My Site CMS" },
        replyTo: "hello@example.com",
        binding: "EMAIL",
      }),
    ],
  });
  ```

  自作トランスポート（`email-transport:register` フックで独自プロバイダに繋ぐ）や、Cloudflare Email Service の有効化手順・DNS 設定・第三者プラグインの互換性は `references/email-and-forms.md` を参照する。
- **フォーム**: 公式 `@emdash-cms/plugin-forms`（native 形式）を `plugins: [formsPlugin(options)]` で登録する。フォームビルダー・送信保存・CSV エクスポート・スパム対策（honeypot / Turnstile）を持つ。**メール通知は email transport が未設定だと静かにスキップされる**ため、通知が要るなら先にメールを構成する。詳細は `references/email-and-forms.md`。

## WordPress 移行

移行は**管理ダッシュボードのインポートウィザード**から行う（REST は `/_emdash/api/import/wordpress/`）。**専用の CLI コマンドは無い**（`emdash import:wordpress` や `emdash migrate` は存在しない）。

- WP 側に PHP プラグイン `emdash-exporter`（https://github.com/emdash-cms/wp-emdash）を入れ、REST `/wp-json/emdash/v1/` を Application Passwords 認証で公開する。
- 変換は prepare → execute の 2 フェーズ。WXR パーサーで取り込み、Gutenberg ブロックは `gutenberg-to-portable-text` で Portable Text に変換する。

手順の詳細・つまずきどころは `references/wordpress-migration.md` を参照する。

## MCP サーバー

EmDash には別物の MCP サーバーが 2 種類ある。混同しない。

- **サイト管理用**: `/_emdash/api/mcp`（自分のサイトに対して）。45 ツール・8 ドメイン。認証は OAuth 2.1 + PKCE / PAT / Device Flow。自サイトのコンテンツ・スキーマ・メディア等を AI から操作する。
- **ドキュメント検索用**: `https://docs.emdashcms.com/mcp`。`search_docs` 1 個のみ・認証不要。EmDash の使い方を調べる用途。

接続例（Claude Code、ドキュメント検索を追加する場合）:

```bash
claude mcp add --transport http emdash-docs https://docs.emdashcms.com/mcp
```

サイト管理用は自サイトの URL 配下（`https://<your-site>/_emdash/api/mcp`）を指定し、上記いずれかの認証を通す。

### Cloudflare 公式 MCP との連携（接続済みなら優先。CLI が実行骨格）

公式プラグイン `cloudflare` の MCP サーバーが接続済み（OAuth 認証済み）なら、次を CLI コマンドの代わりに使ってよい。未接続・未認証の場合は従来どおり CLI で続行する。

- **Cloudflare 側仕様の裏取り** ─ `cloudflare-docs`（認証不要・常時使用可）。Email Service / Dynamic Workers / D1 / wrangler の最新仕様確認の第一手段としてよい。EmDash 本体の仕様は上記 docs 検索 MCP（`https://docs.emdashcms.com/mcp`）か GitHub リポジトリが正本
- **D1 / R2 / KV の作成・確認** ─ `cloudflare-bindings`。未接続時は `wrangler d1 create` / `wrangler r2 bucket create` / `wrangler kv namespace create` 等の CLI
- **本番ログ確認** ─ `cloudflare-observability`（メール transport 失敗・sandboxed プラグインのエラー等の調査）。未接続時は `wrangler tail`

デプロイ状態の確認（`cloudflare-builds`）は、委譲先の `deploy-astro-cloudflare` 側のガイダンスに従う。

## CLI

`pnpm exec emdash <command>`。よく使うもの:

| コマンド | 用途 |
|---|---|
| `types` | スキーマから TypeScript 型を生成 |
| `dev` | 開発サーバー起動 |
| `init` | package.json の emdash 設定からテンプレート DB を初期化 |
| `doctor` | DB 接続・マイグレーション・スキーマ整合性を診断 |
| `seed` / `export-seed` | シードの適用 / 書き出し |
| `content` / `schema` / `media` / `search` / `taxonomy` / `menu` | 各ドメインの操作 |
| `login` / `logout` / `whoami` | 認証（`auth` は非推奨エイリアス） |
| `plugin` | プラグインの `init` / `bundle` / `validate` / `publish` |

プラグイン開発用の別バイナリ `emdash-plugin`（`@emdash-cms/plugin-cli` の `build` / `dev` / `validate`）と混同しない。全コマンドの詳細は `references/cli.md` を参照する。

## デプロイ・トラブルシューティング

Cloudflare Workers へのデプロイは Astro + `@astrojs/cloudflare` 構成なので、**デプロイ操作は既存スキル `deploy-astro-cloudflare` に委譲する**（Workers Builds / ローカル wrangler / プレビューの 3 モード、プリフライト、ロールバックを持つ）。EmDash 固有の注意点（D1 マイグレーション適用、`worker_loaders` を含む場合のプラン要件、`src/worker.ts` の PluginBridge エクスポート）は `references/cloudflare-deploy.md` にまとめる。デプロイ前に `pnpm exec emdash doctor` で DB・スキーマの整合性を確認しておくとよい。

## x402（マイクロペイメント）

`@emdash-cms/x402` は EmDash 本体と疎結合の独立した Astro integration で、HTTP 402 ベースのマイクロペイメントを提供する。Cloudflare Bot Management と連携する bot-only 課金モード（人間は無料、ボットからのアクセスに課金）が目玉。有料コンテンツ・API 課金を組み込む場合に検討する。詳細 API は導入前に公式ドキュメントで裏取りする。

## 関連リソース（一次情報）

- リポジトリ / releases: https://github.com/emdash-cms/emdash ・ https://github.com/emdash-cms/emdash/releases
- ドキュメント: https://docs.emdashcms.com （docs 検索 MCP: `https://docs.emdashcms.com/mcp`）
- docs ソース: `docs/src/content/docs/`（reference/ ・ deployment/ ・ plugins/ ・ migration/）
- WordPress エクスポーター: https://github.com/emdash-cms/wp-emdash
- Cloudflare Email Service: https://developers.cloudflare.com/email-service/
- 本スキルの詳細ドキュメント: `references/cli.md` ・ `references/plugin-development.md` ・ `references/email-and-forms.md` ・ `references/wordpress-migration.md` ・ `references/cloudflare-deploy.md`
