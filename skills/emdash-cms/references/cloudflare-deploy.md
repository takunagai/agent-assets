# EmDash の Cloudflare Workers デプロイ

> [!note] 基準
> 本リファレンスは emdash 0.29.0（2026-07-10 リリース）/ 2026-07-13 検証を基準とする。作業開始前に公式デプロイガイド（`docs/src/content/docs/deployment/cloudflare.mdx` ほか同ディレクトリ配下）で現行仕様を確認する。

> [!important] デプロイ実行そのものは `deploy-astro-cloudflare` スキルに委譲する
> `wrangler deploy` の実行・Workers Builds 経由の自動デプロイ・プレビューデプロイ・ロールバックの手順は既存スキル `deploy-astro-cloudflare` が担う（Astro 7 + `@astrojs/cloudflare` v14 前提）。本ファイルは **EmDash 固有のバインディング設定・DB/ストレージ選択・スキーマ運用・メール・Dynamic Workers** に絞る。

## 前提

- Cloudflare アカウント
- wrangler CLI（`wrangler login` で認証済み）
- D1 をデータベースに、R2 をメディアストレージに使う構成が基本（PostgreSQL 資産がある場合は Hyperdrive も選べる）

## wrangler.jsonc 完全例

```jsonc title="wrangler.jsonc"
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "my-emdash-site",
  "main": "@astrojs/cloudflare/entrypoints/server",
  "compatibility_date": "2026-07-13", // 生成時点の日付を使う（固定推奨値は無い）
  "compatibility_flags": ["nodejs_compat"],
  "assets": { "directory": "./dist", "binding": "ASSETS" },

  "d1_databases": [
    { "binding": "DB", "database_name": "emdash-db" }
  ],

  "r2_buckets": [
    { "binding": "MEDIA", "bucket_name": "emdash-media" }
  ],

  "kv_namespaces": [
    { "binding": "CACHE", "id": "<namespace-id>" }
  ],

  "send_email": [
    { "name": "EMAIL" }
  ],

  "triggers": {
    "crons": ["* * * * *"]
  }
}
```

- `d1_databases` / `r2_buckets` は初回デプロイ時に存在しなければ wrangler が自動プロビジョニングする
- `kv_namespaces` は Object Cache（後述）を使う場合のみ必要。事前に `pnpm exec wrangler kv namespace create CACHE` でネームスペースを作成し、返ってきた `id` を設定する
- `send_email` は EmDash 公式メールプラグイン `cloudflareEmail()` を使う場合のみ必要（後述）
- `triggers.crons` はスケジュール公開・プラグイン cron を使う場合に必須（後述）
- `worker_loaders`（Dynamic Workers）は sandboxed プラグインを使う場合のみ必要。既定構成には含めない（後述）

## astro.config.mjs 設定

```js title="astro.config.mjs"
import { defineConfig } from "astro/config";
import cloudflare from "@astrojs/cloudflare";
import emdash from "emdash/astro";
import { d1, r2, kvCache } from "@emdash-cms/cloudflare";

export default defineConfig({
  output: "server",
  adapter: cloudflare(),
  integrations: [
    emdash({
      database: d1({ binding: "DB" }),
      storage: r2({ binding: "MEDIA" }),
      objectCache: kvCache({ binding: "CACHE" }), // 任意
    }),
  ],
});
```

`d1()` / `r2()` / `kvCache()` / `hyperdrive()` はすべて `@emdash-cms/cloudflare` パッケージからの named export。

## ローカル開発とD1

D1 は Cloudflare Workers 専用のため、ローカル開発では素の SQLite に切り替えるのが公式パターン。`wrangler dev` を別途起動する必要はなく、環境に応じてアダプタを出し分ける。

```js title="astro.config.mjs"
import { sqlite } from "emdash/db";
import { d1 } from "@emdash-cms/cloudflare";

const database = import.meta.env.PROD ? d1({ binding: "DB" }) : sqlite({ url: "file:./data.db" });

export default defineConfig({ integrations: [emdash({ database })] });
```

`pnpm exec emdash dev` コマンド自体もローカル SQLite ファイル（既定 `./data.db`）を直接使う設計になっている（`cli.md` 参照）。

## データベースオプション

| バックエンド | 用途 | 備考 |
|---|---|---|
| **D1**（`d1()`） | Cloudflare Workers 標準構成 | エッジ分散、既定の推奨 |
| **Hyperdrive**（`hyperdrive()`） | 既存 PostgreSQL 資産を Workers から使う | プーリング・高速化はするが DB 自体は別途用意 |

### D1 と Read Replica

```js
database: d1({
  binding: "DB",
  session: "auto", // "disabled"（既定） / "auto" / "primary-first"
}),
```

| モード | 挙動 |
|---|---|
| `"disabled"`（既定） | 全クエリがプライマリに向く。セッション無し |
| `"auto"` | 匿名リクエストは最寄りレプリカから読む。認証済みユーザーは bookmark cookie で read-your-writes 一貫性を確保 |
| `"primary-first"` | `"auto"` と同様だが最初のクエリは常にプライマリへ（書き込み頻度が非常に高いサイト向け） |

D1 自体でも Cloudflare ダッシュボードまたは REST API で read replication を有効化する必要がある（`session` オプションは EmDash 側のクライアント制御のみ）。

> [!warning] `global_fetch_strictly_public` との非互換
> Read replica セッション（`session: "auto"` / `"primary-first"`）は compatibility flag `global_fetch_strictly_public` と併用できない。この flag があると D1 Sessions API がレプリカへルーティングする内部リクエストが静かにブロックされ、ログに何も残らないまま SSR リクエストがハングする（`outcome: "canceled"`）。レプリカのプロビジョニング完了後に症状が出るため、デプロイ直後の疎通確認をすり抜けて数時間後に顕在化することがある（[emdash-cms/emdash#1273](https://github.com/emdash-cms/emdash/issues/1273)）。この flag が必要なワーカーでは `session` を無効のままにする。

### Hyperdrive（PostgreSQL）

```js
import { hyperdrive, r2 } from "@emdash-cms/cloudflare";

database: hyperdrive({ binding: "HYPERDRIVE" }),
storage: r2({ binding: "MEDIA" }),
```

要件: `pg >= 8.16.3` を依存に追加、`compatibility_flags: ["nodejs_compat"]`、`compatibility_date >= "2024-09-23"`。

```bash
wrangler hyperdrive create emdash-db \
  --connection-string "postgres://user:password@host/db?sslmode=verify-full" \
  --caching-disabled
```

> [!warning] プライマリ binding のクエリキャッシュは必ず無効化する
> Hyperdrive のクエリキャッシュは既定で有効だが、EmDash 自身が read-after-write 一貫性に依存している（admin・セットアップウィザードが書き込み直後に読み戻す）ため、キャッシュが有効だと "collection already exists" 等のセットアップ破損を起こす。`--caching-disabled` で作成するか、既存設定に `wrangler hyperdrive update <id> --caching-disabled` を適用する。

匿名の公開読み取りだけキャッシュを許容できる場合は、同一 DB に対しキャッシュ無効/有効の 2 つの Hyperdrive 設定を用意し `cachedBinding` オプションで使い分けられる（two-configuration pattern。詳細は `deployment/database.mdx` を参照）。

> [!note] Sandboxed プラグインは D1 専用
> sandbox プラグインブリッジは D1 binding に直接アクセスするため、Hyperdrive 構成では sandboxed プラグインが使えない。

## ストレージオプション

| バックエンド | 用途 | signed upload |
|---|---|---|
| **R2 binding**（`r2()`） | Cloudflare Workers、ゼロコンフィグ | 非対応 |
| **S3 互換**（`s3()`） | R2 の S3 API・MinIO 等、直接クライアントアップロードが要る場合 | 対応 |

R2 binding は signed upload URL に対応しない。クライアント直接アップロードが必要な場合は R2 の S3 API 用認証情報を発行し `s3()` アダプタを使う。

```js
storage: r2({
  binding: "MEDIA",
  publicUrl: "https://pub-xxxx.r2.dev", // R2 バケットの Public access 有効化後に設定
}),
```

本番ではカスタムドメインを R2 バケットに接続することが推奨される。

## Object Cache（KV）

D1 への読み取り負荷を減らすため、コンテンツ・サイト設定・メニュー・タクソノミータームのクエリ結果を KV にキャッシュできる（既定は無効）。

```js
import { d1, r2, kvCache } from "@emdash-cms/cloudflare";

objectCache: kvCache({ binding: "CACHE" }),
```

| オプション | 既定値 | 説明 |
|---|---|---|
| `binding` | ─（必須） | KV binding 名 |
| `defaultTtl` | `3600`秒 | キャッシュエントリの TTL（KV は 60 秒が下限） |
| `revalidate` | `1000`ms | isolate ローカルの epoch 再利用ウィンドウ |
| `timeout` | `2000`ms | KV 操作待機の上限（超過はキャッシュミス扱い。`0` で無効化） |
| `keyPrefix` | `"em"` | キープレフィックス（1 ネームスペースを複数サイトで共有時に変更） |

admin API・メディアファイル・レンダリング済み HTML は対象外。管理画面での作成・更新・公開・削除は該当コレクションのキャッシュを自動無効化する。プレビューリンク・ビジュアル編集は常にバイパスする。

## スキーマ進化（デプロイ後にスキーマを変更する）

コードのデプロイ（`wrangler deploy`）は Worker のコードだけを置き換え、**DB 側のスキーマ・コンテンツには影響しない**。稼働中サイトのコレクション・フィールド・タクソノミーを変更するのは別の作業系統になる。

| 作業 | 変わるもの | 手段 |
|---|---|---|
| コンテンツ編集 | エントリ・メディア・設定 | admin パネルまたはコンテンツ API |
| コードデプロイ | テンプレート・設定・EmDash バージョン | `wrangler deploy`（スキーマ・コンテンツは不変） |
| 初回ブートストラップ | 空の状態からすべて | マイグレーション + シードファイル + セットアップウィザード（初回起動時に自動） |
| スキーマ進化 | コレクション・フィールド・タクソノミー | admin パネルまたは `emdash schema`（稼働中サイトに対して） |

- admin パネルの **Content Types** から変更するのが基本経路。変更は即座に反映される（API・ローダー・編集 UI がすべて DB から動的にスキーマを読むため）
- スキーマ変更後はテンプレートが使う型を再生成する: `pnpm exec emdash types --url https://example.com`
- CLI からも変更できる。`pnpm exec emdash login --url https://example.com` で認証するか、admin の **設定 → API トークン** で発行したトークンを `--token` / `EMDASH_TOKEN` で渡す（CI 向け）

```bash
pnpm exec emdash schema add-field posts subtitle --type string --label "Subtitle" --url https://example.com
pnpm exec emdash schema remove-field posts legacy_field --url https://example.com
```

> [!warning] フィールド削除は破壊的
> フィールドを削除するとカラムとデータが消える。本番前にプレビュー環境でリハーサルする。

### シードファイルの同期

シードファイルは「空の DB が初回ブート時にどう初期化されるか」を決めるだけで、稼働中の DB には影響しない。本番のスキーマを進化させたら、シードファイルも最新化してリポジトリに戻す。

```bash
pnpm exec wrangler d1 export emdash-db --remote --output=./prod.sql
sqlite3 prod.db < prod.sql
pnpm exec emdash export-seed --database prod.db > .emdash/seed.json
```

更新した `.emdash/seed.json` は、その新スキーマに依存するコードと一緒にコミットする（新しい環境が常に理解可能なモデルでブートストラップされるようにするため）。

### プレビュー環境でのリハーサル

破壊的なスキーマ変更（フィールド削除、コレクション再構成）は使い捨てのプレビュー環境で試す。

```bash
pnpm exec wrangler d1 export emdash-db --remote --output=./prod.sql
pnpm exec wrangler d1 execute emdash-db-preview --remote --file=./prod.sql
pnpm exec wrangler deploy --env preview
pnpm exec emdash schema remove-field posts legacy_field --url https://preview.example.com
```

## メール（Cloudflare Email Sending）

Workers 上では組み込みの `email:deliver` ハンドラが開発コンソール向けスタブのみのため、マジックリンクログイン・チーム招待・コメント通知等は本番で "Email is not configured" となり失敗する。`cloudflareEmail()` プラグインが `send_email` binding 経由で実メール送信を提供する（外部 API キー不要）。

1. Cloudflare ダッシュボードの **Email** で送信元ドメイン（またはアドレス）を検証する（未検証の送信元からのメールは拒否される）
2. `wrangler.jsonc` に binding を追加する: `"send_email": [{ "name": "EMAIL" }]`
3. `astro.config.mjs` にプラグインを登録する

```js
import { d1, r2 } from "@emdash-cms/cloudflare";
import { cloudflareEmail } from "@emdash-cms/cloudflare/plugins";

emdash({
  database: d1({ binding: "DB" }),
  storage: r2({ binding: "MEDIA" }),
  plugins: [
    cloudflareEmail({
      from: { email: "cms@mails.example.com", name: "My Site CMS" },
      replyTo: "hello@example.com", // 任意
      binding: "EMAIL", // 任意、既定 "EMAIL"
    }),
  ],
}),
```

4. デプロイ後、admin の **Extensions** でプラグインを有効化し、**設定 → Email** でプロバイダとして選択する（自動選択はされない）

BCC・添付ファイルは対象外（EmDash の `EmailMessage` モデルに無い）。

## Scheduled Publishing（スケジュール公開・cron）

Cloudflare Workers 上でスケジュール公開・プラグイン cron・メンテナンスタスクを動かすには Worker Cron Trigger が必要。新規テンプレートには自動で組み込まれるが、既存プロジェクトに追加する場合は次の 2 手順を行う。

```ts title="src/worker.ts"
export { default, PluginBridge } from "@emdash-cms/cloudflare/worker";
```

```jsonc title="wrangler.jsonc"
{
  "triggers": { "crons": ["* * * * *"] }
}
```

> [!warning] Cron Trigger が無いと管理画面でスケジュールした公開が動かない
> ローカルの `astro dev` はインプロセスのスケジューラを使うため問題なく動くが、Cloudflare Workers 本番では Cron Trigger が無いとスケジュール公開・プラグイン cron が一切実行されない。

## Dynamic Workers（sandboxed プラグイン専用）

マーケットプレイス配布のプラグイン（sandboxed 形式）を動かすには sandbox runner の設定が要る。現行の正しい記法は `sandbox()` 関数呼び出し（詳細は `plugin-development.md` を参照）。

```js title="astro.config.mjs"
import { sandbox } from "@emdash-cms/cloudflare";

emdash({
  sandboxed: [/* sandboxed プラグイン */],
  sandboxRunner: sandbox(),
}),
```

> [!warning] 一部の古い EmDash ドキュメント（`plugins/installing.mdx` 等）には `sandboxRunner: "@emdash-cms/sandbox-cloudflare"`（文字列直書き）や「追加バインディング不要」という記述が残っているが、現行のパッケージ構成・チュートリアルと一致しない。`sandbox()` 記法 + 明示的な binding 宣言を正とする。

`wrangler.jsonc` には Dynamic Worker Loader のバインディング宣言が必要（`plugin-development.md` および Cloudflare 公式 `developers.cloudflare.com/dynamic-workers/` と同一）。

```jsonc title="wrangler.jsonc"
{
  "worker_loaders": [
    { "binding": "LOADER" }
  ]
}
```

- **Open Beta・Workers Paid プラン必須**（Open Beta 開始は 2026-03-24 ─ Cloudflare changelog。pricing ページでも Paid 必須を確認済み、2026-07-13 時点）
- 料金（Cloudflare 公式 `dynamic-workers/pricing` より）: 月あたり 1,000 個までの unique Dynamic Worker 作成が無料枠に含まれ、超過分は 1 個・1 日あたり $0.002。リクエスト数・CPU 時間は Workers Standard 料金に準じ、既存の Workers 請求に合算される
- **無料プランでは sandboxed プラグインは動かせない**。無料プランで運用する場合は native（trusted）プラグインのみに構成を絞る（`plugins: []` 配列、`sandboxRunner` を設定しない）

## 環境変数・secrets

| 変数 | 用途 |
|---|---|
| `EMDASH_ENCRYPTION_KEY` | プラグイン secrets の暗号化キー。起動時に検証される。毎デプロイで設定しておく（後から設定変更すると既存の暗号化データが復号不能になる） |
| `EMDASH_PREVIEW_SECRET` | プレビュー HMAC シークレットの上書き（複数プロセス間で共有したい場合のみ） |
| `EMDASH_IP_SALT` | コメント投稿者 IP ハッシュソルトの上書き |

```bash
pnpm exec emdash secrets generate
wrangler secret put EMDASH_ENCRYPTION_KEY
```

> [!warning] 暗号化キーをリポジトリにコミットしない
> 平文の値は環境変数としてのみ存在させ、パスワードマネージャー・KMS・チームの secret store にバックアップする。紛失するとそのキーで暗号化された secrets はすべて失われる。

`deploy-astro-cloudflare` の `secrets-and-env.md` にある `keep_vars` の注意点（`wrangler deploy` がダッシュボード管理の環境変数を上書き・削除しうる）は EmDash デプロイでも同様に適用される。

デプロイ実行の詳細な手順・モード選択・完了確認は `deploy-astro-cloudflare` スキルに従う（プレビュー環境用の `wrangler.jsonc` の `env.preview` 設定例は上記「プレビュー環境でのリハーサル」を参照）。

## MCP 連携（接続済みなら優先。CLI が実行骨格）

公式プラグイン `cloudflare` の MCP サーバーが接続済み（OAuth 認証済み）なら、次を CLI コマンドの代わりに使ってよい。未接続・未認証の場合は従来どおり CLI で続行する。

- **D1 / R2 / KV の作成・確認** ─ `cloudflare-bindings`（データベース・バケット・namespace の作成/一覧/取得）。未接続時は `wrangler d1 create <name>` / `wrangler r2 bucket create <name>` / `wrangler kv namespace create <name>`
- **本番ログ確認** ─ `cloudflare-observability`（Worker ログ・分析）。未接続時は `wrangler tail`
- **ドキュメント疑問点の確認** ─ `cloudflare-docs`（認証不要・常時使用可）。Email Service / Dynamic Workers / D1 / Hyperdrive の仕様確認の第一手段としてよい
- **デプロイ状態確認** ─ `cloudflare-builds` は委譲先 `deploy-astro-cloudflare` 側のガイダンスに従う

## トラブルシューティング

| エラー | 対応 |
|---|---|
| "D1 binding not found" | `wrangler.jsonc` の binding 名が `d1({ binding: "DB" })` と一致しているか確認する |
| "R2 binding not found" | `wrangler.jsonc` の binding 名が `r2({ binding: "MEDIA" })` と一致しているか確認する |
| マイグレーションエラー | `wrangler tail` で Worker ログを追い、エラーを再現してメッセージを取得してから対応する |
| スケジュール公開が動かない | `wrangler.jsonc` に `triggers.crons` があるか、`src/worker.ts` が `@emdash-cms/cloudflare/worker` の `PluginBridge` を export しているか確認する |
| メール送信が "Email is not configured" | `cloudflareEmail()` プラグインを有効化し、**設定 → Email** でプロバイダとして選択したか確認する（有効化だけでは自動選択されない） |
| SSR リクエストがハングし、ログに何も出ない | `session: "auto"`（D1 read replica）と compatibility flag `global_fetch_strictly_public` を併用していないか確認する |
| 本番でエラーが再現するがログを追いたい | 接続済みなら `cloudflare-observability` MCP で本番ログ・分析を確認。未接続時は `wrangler tail` |

## 参照ドキュメント

- `docs/src/content/docs/deployment/cloudflare.mdx` ─ 全体のデプロイ手順
- `docs/src/content/docs/deployment/database.mdx` ─ D1 / Hyperdrive / PostgreSQL / libSQL / SQLite の詳細
- `docs/src/content/docs/deployment/storage.mdx` ─ R2 / S3 / ローカルストレージ
- `docs/src/content/docs/deployment/object-cache.mdx` ─ KV Object Cache
- `docs/src/content/docs/deployment/schema-evolution.mdx` ─ デプロイ後のスキーマ変更
- `docs/src/content/docs/plugins/installing.mdx` ─ sandboxed / native プラグインのインストールと sandbox runner 設定
- https://developers.cloudflare.com/dynamic-workers/ ─ Dynamic Worker Loader（Worker Loader API・pricing）
- 既存スキル `deploy-astro-cloudflare` ─ デプロイ実行本体（Workers Builds / ローカル wrangler deploy / プレビューデプロイ）
