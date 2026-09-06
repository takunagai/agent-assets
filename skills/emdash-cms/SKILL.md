---
name: emdash-cms
description: "EmDash（Cloudflare 発の TypeScript/Astro ベース CMS、emdash 0.29 基準）のセットアップ・構成・運用。新規作成（pnpm create emdash）、既存 Astro 統合、Cloudflare D1/R2/KV と Node/SQLite、コンテンツモデルと getEmDashCollection、Portable Text、認証、プラグイン開発、メール・フォーム、WordPress 移行、MCP、CLI。トリガー: 『EmDash をセットアップして』『EmDash でコンテンツタイプを作って』『EmDash プラグインを作って』『WordPress から EmDash に移行して』『EmDash に問い合わせフォームを追加して』。デプロイは /deploy-astro-cloudflare を案内する。"
---

# EmDash CMS Skill

## 概要・適用範囲

EmDash は Cloudflare 発の CMS で、WordPress の精神的後継として設計されている。全編 TypeScript・Astro integration として動作し、ライセンスは MIT。管理画面（Portable Text エディタ・スキーマビルダー・メディア管理）と、Astro プロジェクトへのコンテンツ配信を 1 パッケージで担う。

このスキルは次を扱う ─ 新規サイトの作成、既存 Astro プロジェクトへの統合、Cloudflare（D1 / R2 / KV）および Node / SQLite でのデータベース・ストレージ設定、コンテンツモデル定義とクエリ、Portable Text レンダリング、認証、プラグイン開発、メール・フォーム、WordPress 移行、MCP サーバー、CLI。**デプロイの実行自体**は Astro + Cloudflare Workers 構成なので、既存スキル `deploy-astro-cloudflare` の担当（本スキルは構成まで。同スキルは手動起動専用なので、ユーザーに `/deploy-astro-cloudflare` の起動を案内する）。

> [!important] EmDash は v0.x の早期ベータ ─ 作業開始前に必ず鮮度検証する
> 本スキルは **emdash 0.29.0（2026-07-10 リリース）/ 2026-07-13 検証**を基準とする。EmDash は v0.x のため API・CLI・設定が数ヶ月単位で大きく変わる。作業を始める前に必ず次を実行し、乖離があれば公式ドキュメントを優先すること。
>
> ```bash
> pnpm view emdash version          # 現行の最新版を確認
> pnpm view create-emdash version   # スキャフォールダも同時に確認
> ```
>
> GitHub の releases（https://github.com/emdash-cms/emdash/releases）でメジャーな変更を確認する。基準（0.29.x）とメジャー／マイナーがずれていたら、本スキルのコード例をそのまま使わず、公式ドキュメント（下記）で該当 API を裏取りしてから進める。
>
> **モデル・エフォートの再判定（Stop And Ask）**: 基準 0.29 系とメジャー／マイナーがずれていたら、API・CLI の破綻を公式ドキュメントで裏取りしながら適応する「調査・判断」が発生する。Sonnet など軽量モデルで起動している場合は、その場で作業を止め、ユーザーに **Opus 4.8 / high エフォートでの再起動**を促す（セッションは自身のモデルを変更できないため、自動昇格ではなく停止して申告する）。ズレが無ければそのまま続行する。
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

対話は 2 段階 ─ プラットフォーム（`node` / `cloudflare`）→ テンプレート（`blog` / `starter` / `marketing` / `portfolio`）。非対話で作るなら `--yes`（既定は cloudflare + blog + `my-site`）。テンプレート実体は `emdash-cms/templates` リポジトリから取得される。生成されるプロジェクトには `astro.config.mjs`・`wrangler.jsonc`（Cloudflare 時）・`src/worker.ts` のほか、`EMDASH_ENCRYPTION_KEY` を自動生成した `.env`、AI エージェント向けの `AGENTS.md`（`CLAUDE.md` は symlink）・`.mcp.json` が含まれる（2026-07-14 実機確認）。

> [!note] テンプレートの依存 pin は最新版より古いことがある（実機確認: emdash `^0.28.1` が入った）
> スキャフォールド直後に `pnpm list emdash` で実際に入った版を確認し、最新に上げる場合は `pnpm add emdash@latest @emdash-cms/cloudflare@latest` を実行してから動作確認する。0.x 系はマイナー間で破壊的変更がありうるため、上げた直後にビルドと管理画面を必ず確認する。

初回起動は `pnpm dev`（テンプレートの scripts は `astro dev`）。`http://localhost:4321/_emdash/admin` へアクセスすると `/setup` へリダイレクトされ、セットアップウィザードで最初の管理者アカウントを作成する（実機確認）。

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

統合時の補足:

- **マイグレーション**: 保留中のマイグレーションは `pnpm exec emdash dev` の初回起動時に自動適用される（本番は初回ブートストラップで自動。詳細は `references/cloudflare-deploy.md`）。
- **パス衝突**: EmDash は `/_emdash/` 配下（admin・API・media）を占有する。既存ルートとの衝突が無いか統合前に確認する。
- **Cloudflare 構成で統合する場合**: 後方の「設定（Cloudflare 既定）」節のテンプレート準拠形（素の `d1()` / `r2()`。ローカルは `astro dev` の miniflare エミュレーションで動く）を使う。

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

> [!important] 素の `d1()` / `r2()` がテンプレート既定 ─ ローカルは miniflare がエミュレートする（2026-07-14 実機確認）
> 公式テンプレートの `astro.config.mjs` は環境出し分けの無い素の `d1({ binding: "DB", session: "auto" })` + `r2({ binding: "MEDIA" })`。ローカル開発は `pnpm dev`（= `astro dev`）で、`@astrojs/cloudflare` が **miniflare によるローカル D1 / R2 エミュレーション**（`.wrangler/state/` 配下）を提供するため、wrangler へのログインなしでそのまま動く。**この形を既定とする**。
> `import.meta.env.PROD` で SQLite に出し分けるパターン（公式 database.mdx 記載）は、CLI ツール群（`emdash dev` / `seed` / `doctor` ─ 素の SQLite `data.db` を使う別世界）で開発したい場合の代替。詳細は後述「ローカル開発の 2 系統」。

```js
// astro.config.mjs（テンプレート準拠の既定形）
import { defineConfig } from "astro/config";
import cloudflare from "@astrojs/cloudflare";
import emdash from "emdash/astro";
import { d1, r2 } from "@emdash-cms/cloudflare";

export default defineConfig({
  output: "server",
  adapter: cloudflare(),
  integrations: [
    emdash({
      database: d1({ binding: "DB", session: "auto" }),
      storage: r2({ binding: "MEDIA" }), // 公開 URL を使う場合は publicUrl: "https://pub-xxxx.r2.dev"（R2 の Public access 有効化後に取得）を追加
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
    // database_id は `pnpm exec wrangler d1 create <name>` の出力から転記する
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

### ローカル開発の 2 系統（2026-07-14 実機確認）

Cloudflare 構成のローカル開発には**互いに DB を共有しない 2 つの系統**がある。混同するとデータが見えず混乱する。

| | 系統 A: `pnpm dev`（= `astro dev`。テンプレート既定） | 系統 B: CLI（`emdash dev` / `seed` / `doctor` / `init`） |
|---|---|---|
| DB の実体 | miniflare のローカル D1（`.wrangler/state/` 配下） | 素の SQLite `./data.db` |
| 必要な設定 | 素の `d1()` のままで動く（wrangler ログイン不要） | `import.meta.env.PROD` での `sqlite()` 出し分け + better-sqlite3 のビルド許可 |
| 用途 | 通常の開発・管理画面・プレビュー | シード適用・スキーマ診断・Node 系ワークフロー |

- 系統 A で `emdash seed` / `emdash doctor` を打っても **`data.db` が無いのでエラーになる**（doctor は「run "emdash init"」と言う）。miniflare 側 D1 へのコンテンツ投入は管理画面（初回は `/_emdash/admin` → セットアップウィザード）から行う
- 系統 B を使うには、テンプレートの `pnpm-workspace.yaml` が **`allowBuilds: better-sqlite3: false` で意図的にネイティブビルドを止めている**ため、`true` に変更して `pnpm rebuild better-sqlite3` を実行してから `emdash init` する（しないと "Failed to create database" で全滅）
- どちらの系統の DB も本番 D1 とは別物。本番へのシードは `references/cloudflare-deploy.md` を参照

### Node プラットフォームを選ぶ場合

Cloudflare を使わない構成（Node.js サーバーへのデプロイ）では、本番でも `sqlite({ url: "file:./data.db" })` + `local()` ストレージで動く。外部 DB は `libsql`（Turso）・`postgres`（いずれも `emdash/db`）、S3 互換ストレージは `s3()`（`emdash/astro`、`@aws-sdk/client-s3` の追加インストールが必要）が選べる。CLI ツール群（`emdash dev` / `seed` / `doctor`）はこの SQLite をそのまま見るため、Cloudflare 構成のような 2 系統の分離は起きない。

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

// 一覧（公開済みを新しい順に 10 件）。戻り値は分割代入で受ける
const { entries: posts } = await getEmDashCollection("posts", {
  status: "published",
  orderBy: { published_at: "desc" },
  limit: 10,
});

// ページネーション（offset ベースが基本）
const { entries: page2 } = await getEmDashCollection("posts", {
  limit: 10,
  offset: 10,
});
// 大量データは nextCursor / hasMore でカーソル継続もできる（前回の nextCursor を cursor オプションに渡す）

// タクソノミー・フィールドで絞り込み（where はフィールド名→値。ネスト演算子は無い）
const { entries: tagged } = await getEmDashCollection("posts", {
  where: { tags: "astro" },
});

// 単体（slug または ID で 1 件）。第 2 引数は文字列
const { entry: post } = await getEmDashEntry("posts", "hello-world");
```

`getEmDashCollection(name, options)` の options は `status?`（トップレベル、`"published"` 等）・`where?: Record<string, string | string[]>`（フィールド／タクソノミー絞り込み）・`orderBy?: { [field]: "asc" | "desc" }`（複数指定可。フィールド名は snake_case、例 `published_at`）・`limit?` / `offset?` / `cursor?`。戻り値は `{ entries, error, nextCursor, hasMore }`。`getEmDashEntry(collection, slugOrId)` の第 2 引数は文字列で、戻り値は `{ entry, error, isPreview }`。

フィールド型は 16 種 ─ `string` / `text` / `url` / `number` / `integer` / `boolean` / `datetime` / `select` / `multiSelect` / `portableText` / `image` / `file` / `reference` / `json` / `slug` / `repeater`。正本は `docs/src/content/docs/reference/field-types.mdx`。

## Portable Text レンダリング

本文（`portableText` フィールド）は `<PortableText />`（`emdash/ui`）で描画する。**コンポーネント方式**で、`renderPortableText` のような関数は存在しない。

```astro
---
import { PortableText } from "emdash/ui";
import CustomImage from "../components/CustomImage.astro";
const { entry: post } = await getEmDashEntry("posts", Astro.params.slug);
if (!post) return Astro.redirect("/404");
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

判断基準 ─ **フル React 管理画面 / Portable Text レンダリングコンポーネント / page fragments が要るなら native、それ以外は sandboxed 推奨**（sandboxed でも manifest の `admin.pages` / `admin.widgets` で簡易な管理ページは提供できる）。capabilities・hooks・manifest スキーマ・最小テンプレートの詳細は `references/plugin-development.md` を参照する。

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
| `doctor` | DB 接続・マイグレーション・スキーマ整合性を診断（対象は `data.db` の系統 B のみ ─ 「ローカル開発の 2 系統」参照） |
| `seed` / `export-seed` | シードの適用 / 書き出し |
| `content` / `schema` / `media` / `search` / `taxonomy` / `menu` | 各ドメインの操作 |
| `login` / `logout` / `whoami` | 認証（`auth` は非推奨エイリアス） |
| `plugin` | プラグインの `init` / `bundle` / `validate` / `publish` |

プラグイン開発用の別バイナリ `emdash-plugin`（`@emdash-cms/plugin-cli` の `build` / `dev` / `validate`）と混同しない。全コマンドの詳細は `references/cli.md` を参照する。

## デプロイ・トラブルシューティング

Cloudflare Workers へのデプロイは Astro + `@astrojs/cloudflare` 構成なので、**デプロイ操作は既存スキル `deploy-astro-cloudflare` の担当**（Workers Builds / ローカル wrangler / プレビューの 3 モード、プリフライト、ロールバックを持つ）。同スキルは手動起動専用（`disable-model-invocation: true`）なので、Claude から Skill ツールで呼ばず、ユーザーに `/deploy-astro-cloudflare` の起動を案内する。EmDash 固有の注意点（D1 マイグレーション適用、`worker_loaders` を含む場合のプラン要件、`src/worker.ts` の PluginBridge エクスポート）は `references/cloudflare-deploy.md` にまとめる。`pnpm exec emdash doctor` での事前診断は SQLite（系統 B）を設定済みの場合のみ有効 ─ テンプレート既定（系統 A）のままでは `data.db` が無くエラーになるので、代わりにローカルの `pnpm build` 成功とプレビューデプロイでの動作確認を事前チェックとする。

## x402（マイクロペイメント）

`@emdash-cms/x402` は EmDash 本体と疎結合の独立した Astro integration で、HTTP 402 ベースのマイクロペイメントを提供する。Cloudflare Bot Management と連携する bot-only 課金モード（人間は無料、ボットからのアクセスに課金）が目玉。有料コンテンツ・API 課金を組み込む場合に検討する。詳細 API は導入前に公式ドキュメントで裏取りする。

## 関連リソース（一次情報）

- リポジトリ / releases: https://github.com/emdash-cms/emdash ・ https://github.com/emdash-cms/emdash/releases
- ドキュメント: https://docs.emdashcms.com （docs 検索 MCP: `https://docs.emdashcms.com/mcp`）
- docs ソース: `docs/src/content/docs/`（reference/ ・ deployment/ ・ plugins/ ・ migration/）
- WordPress エクスポーター: https://github.com/emdash-cms/wp-emdash
- Cloudflare Email Service: https://developers.cloudflare.com/email-service/
- 本スキルの詳細ドキュメント: `references/cli.md` ・ `references/plugin-development.md` ・ `references/email-and-forms.md` ・ `references/wordpress-migration.md` ・ `references/cloudflare-deploy.md`
