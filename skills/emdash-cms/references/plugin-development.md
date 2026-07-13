# EmDash プラグイン開発 リファレンス

> [!note] 基準
> 本リファレンスは emdash 0.29.0（2026-07-10 リリース）/ 2026-07-13 検証を基準とする。作業開始前に `pnpm view emdash version` と公式ドキュメント（`docs/src/content/docs/plugins/` 配下）で現行仕様を確認する。特にプラグインのファイル構成・登録記法は資料間で揺れが出やすい箇所なので、`your-first-plugin.mdx` / `your-first-native-plugin.mdx` の現行チュートリアルを正とする。大きな乖離があれば公式 docs を優先する。

## 概要

EmDash のプラグインには 2 つの形式がある ─ **sandboxed**（既定・マーケットプレイス配布用）と **native**（trusted・エスケープハッチ）。両者は実行環境・登録先の配列・できることが異なり、混同すると容量オーバーやビルド失敗の原因になる。

| 項目 | sandboxed（標準形式） | native |
|---|---|---|
| 実行環境 | Worker isolate（Dynamic Worker Loader）で隔離実行 | サイトと同一プロセス（in-process） |
| 登録先 | `sandboxed: []`（`plugins: []` でも動く） | `plugins: []` のみ |
| インストール | マーケットプレイスから 1 クリック | npm install + `astro.config` 手動編集 |
| リソース制限 | あり（CPU / サブリクエスト / 壁時間 / メモリ） | なし |
| capabilities | 実行時に強制（enforced） | 宣言はドキュメント目的のみ、実際は無制限アクセス |
| React 管理 UI・Portable Text コンポーネント・page fragments | 不可 | 可 |
| Cloudflare 以外のプラットフォーム要件 | sandbox runner が必要（無ければ起動時にスキップ） | プラットフォーム非依存 |

判断基準（公式ドキュメント `choosing-a-format.mdx` より）: **迷ったら sandboxed から始める**。次のいずれかが必要なときだけ native を選ぶ。

1. カスタム React 管理画面（フル React ─ 独自 hooks・サードパーティコンポーネント・複雑な state）が要る
2. Portable Text 用の Astro コンポーネント（`componentsEntry`）を提供する必要がある ─ sandboxed はビルド時コンポーネント読み込みのため非対応
3. ページへの生スクリプト・生 HTML 注入（`page:fragments` フック）が必要 ─ sandboxed は `page:metadata`（メタタグ・JSON-LD のみ）までしか提供できない

sandboxed から native への移行は可能だが、逆（native → sandboxed）は難しいとされる。

---

## CLI の混同注意（先に押さえる）

プラグイン開発では名前の似た 2 つの CLI が登場する。混同するとコマンドが見つからずハマる。

| バイナリ | パッケージ | 用途 |
|---|---|---|
| `emdash plugin`（サイト CLI のサブコマンド） | `emdash` 本体 | マーケットプレイス配布のための操作（`init` / `bundle` / `validate` / `publish` / `login` / `logout`） |
| `emdash-plugin`（別バイナリ） | `@emdash-cms/plugin-cli` | プラグイン開発のローカルビルド・検証ツールチェーン（`init` / `build` / `dev` / `bundle` / `validate` / `publish` / `login` / `logout` / `whoami` / `switch` / `search` / `info`） |

本リファレンスで扱うプラグイン開発は主に後者（`emdash-plugin` バイナリ、`@emdash-cms/plugin-cli`）。

```bash
pnpm dlx @emdash-cms/plugin-cli init my-plugin   # 雛形一式を生成
```

`init` は `emdash-plugin.jsonc`・`src/plugin.ts`・`package.json`・`tsconfig.json`・テスト・README・`.gitignore` を生成する。スラッグだけが必須入力で、残りのフィールド（publisher・author・security contact）には `TODO:` コメントが入る。

---

## sandboxed プラグイン

### ファイル構成

```
my-plugin/
├── emdash-plugin.jsonc   # 識別情報 + trust contract + プロフィール（コードなし）
├── src/
│   └── plugin.ts         # フック・ルート ─ サンドボックスランタイムで実行される
├── package.json
└── tsconfig.json
```

`emdash-plugin build` がこの 2 つを読んで `dist/`（`plugin.mjs` ＝ ランタイム本体・`manifest.json` ＝ マニフェスト・`index.mjs` ＝ サイトが import する descriptor）を生成する。

> [!important] `src/index.ts` + `src/sandbox-entry.ts` という構成は古い／別文書由来
> 資料によっては sandboxed プラグインを「`src/index.ts`（descriptor）+ `src/sandbox-entry.ts`（`definePlugin({ hooks, routes })`）」の 2 ファイル構成で説明しているものがあるが、現行の公式チュートリアル（`your-first-plugin.mdx`）が示す構成は **`src/plugin.ts` 1 ファイルに `satisfies SandboxedPlugin` で default export する形**。本リファレンスはこちらを正とする。`emdash/plugin` は型のみを提供し、sandboxed プラグインはランタイムで `emdash` 本体に依存しない。

### `emdash-plugin.jsonc` 全フィールド

必須フィールド:

| フィールド | 型 | 説明 |
|---|---|---|
| `slug` | string | URL セーフな ID（`/^[a-z][a-z0-9_-]*$/`、最大 64 文字）。npm パッケージ名ではない。プラグインルート URL（`/_emdash/api/plugins/<slug>/...`）の 1 セグメントおよびストレージインデックスの SQL 識別子の一部になるため、`@` ・`/`・先頭数字・大文字は不可 |
| `publisher` | string | Atmosphere アカウントの DID またはハンドル（例: `did:plc:abc123def456`） |
| `license` | string | SPDX 表現（`"MIT"` 等） |
| `author` または `authors` | object \| array | 単数 `{ name, url?, email? }` または配列（最大 32 件）。両方の同時指定はエラー |
| `security` または `securityContacts` | object \| array | 各連絡先は `email` または `url` が必須。配列は最大 8 件。両方の同時指定はエラー |

任意フィールド（プロフィール）:

| フィールド | 型 | 説明 |
|---|---|---|
| `version` | string | 省略推奨。ビルドが `package.json` から読むため、バージョンの正本を一本化できる |
| `name` | string | 表示名（既定は `slug`） |
| `description` | string | 目安 140 文字程度。長い値は一覧表示で切り詰められることがある |
| `keywords` | array | 最大 5 項目 |
| `repo` | string | ソースリポジトリの `https://` URL |

trust contract（すべて任意・既定は空）:

| フィールド | 型 | 説明 |
|---|---|---|
| `capabilities` | array | 付与する権限。後述の全 12 種から選ぶ |
| `allowedHosts` | array | `network:request` 使用時のホスト許可リスト。`*.cdn.example.com` のようなサブドメインワイルドカードも可 |
| `storage` | object | ストレージコレクションとインデックスの宣言（必須。宣言していないコレクションへのアクセスは実行時エラー） |

管理画面（任意）:

```jsonc
"admin": {
  "pages": [{ "path": "/gallery", "label": "Gallery", "icon": "image" }],
  "widgets": [{ "id": "recent-uploads", "title": "Recent uploads", "size": "half" }]
}
```

> [!note] trust contract の変更にはバージョンアップが要る
> `capabilities` / `allowedHosts` / `storage` を変更するには必ずバージョンを上げる。インストール済みサイトは旧 trust contract に同意した状態のため。

### 最小コード例

```jsonc title="emdash-plugin.jsonc"
{
	"$schema": "./node_modules/@emdash-cms/plugin-cli/schemas/emdash-plugin.schema.json",
	"slug": "plugin-hello",
	"publisher": "did:plc:abc123def456",
	"license": "MIT",
	"author": { "name": "Jane Doe", "url": "https://example.com" },
	"security": { "email": "security@example.com" },
	"capabilities": [],
	"allowedHosts": [],
	"storage": { "events": { "indexes": ["timestamp"] } }
}
```

```typescript title="src/plugin.ts"
import type { SandboxedPlugin } from "emdash/plugin";

export default {
	hooks: {
		"content:afterSave": {
			handler: async (event, ctx) => {
				ctx.log.info("Content saved", {
					collection: event.collection,
					id: event.content.id,
				});
				await ctx.storage.events.put(`save-${Date.now()}`, {
					timestamp: new Date().toISOString(),
					collection: event.collection,
					contentId: event.content.id,
				});
			},
		},
	},
	routes: {
		recent: {
			handler: async (_routeCtx, ctx) => {
				const result = await ctx.storage.events.query({ limit: 10 });
				return { events: result.items };
			},
		},
	},
} satisfies SandboxedPlugin;
```

`satisfies SandboxedPlugin` によりフック名から `event` の型が推論され、ルートハンドラは `(routeCtx, ctx)` の 2 引数を取る（`routeCtx` は `{ input, request, requestMeta? }`）。ルートは `/_emdash/api/plugins/<slug>/<route-name>` で到達可能。`ctx.kv`（プラグインごとの KV ストア）は capability 不要で常に使える。

### astro.config への登録

```typescript title="astro.config.mjs"
import { defineConfig } from "astro/config";
import emdash from "emdash/astro";
import { sandbox } from "@emdash-cms/cloudflare";
import hello from "@my-org/plugin-hello";

export default defineConfig({
	integrations: [
		emdash({
			sandboxed: [hello],
			sandboxRunner: sandbox(),
		}),
	],
});
```

> [!important] `sandboxRunner` は `sandbox()` 関数呼び出しが現行の正しい記法
> `@emdash-cms/cloudflare` パッケージのソース（`packages/cloudflare/src/index.ts`）を確認したところ、`sandbox()` は `"@emdash-cms/cloudflare/sandbox"` という文字列を返すだけの関数。つまり `sandboxRunner` オプション自体は文字列（モジュールパス）を受け取るが、**現行の公式チュートリアルは一貫して `sandboxRunner: sandbox()` という関数呼び出し記法**を使っている。一部の古いリファレンス文書に `sandboxRunner: "@emdash-cms/sandbox-cloudflare"`（別パッケージ名の文字列直書き）という例が残っているが、これは現行のパッケージ構成と一致しない古い記法とみられる。文字列を直書きせず `sandbox()` を使うこと。

`sandboxRunner` が未設定、または設定したランナーが現在のプラットフォームで利用不可の場合、`sandboxed: []` のプラグインは起動時にスキップされる。動かすには `plugins: []` に移す必要があるが、その場合 V8 isolate による隔離もリソース制限も無くなり、native 相当の信頼レベルで動く点に注意する。

Cloudflare 上で sandbox runner を使うには、`wrangler.jsonc` に Dynamic Worker Loader のバインディングが必要。

```jsonc title="wrangler.jsonc"
{
	"worker_loaders": [{ "binding": "LOADER" }]
}
```

> [!important] Dynamic Workers は Open Beta・Workers Paid 必須
> `@emdash-cms/cloudflare` の sandbox runner は Cloudflare Workers の Dynamic Worker Loader を使う。これは Open Beta かつ **Workers Paid プラン必須**の機能で、無料プランでは sandboxed プラグインを実行できない（バインディングが無い/使えないと runner が起動時に unavailable と報告し、sandboxed プラグインはスキップされる）。native プラグインはこの制約を受けない。

---

## native プラグイン

### ファイル構成

sandboxed と異なり、descriptor factory とランタイム（`createPlugin`）は同一プロセスで動くため 1 ファイルにまとめられる。

```
my-native-plugin/
├── src/
│   ├── index.ts          # descriptor factory + createPlugin
│   ├── admin.tsx         # React 管理画面コンポーネント（任意）
│   └── astro/            # Portable Text 描画用 Astro コンポーネント（任意）
│       └── index.ts
├── package.json
└── tsconfig.json
```

### 最小コード例

```typescript title="src/index.ts"
import { definePlugin } from "emdash";
import type { PluginDescriptor } from "emdash";

export interface AnalyticsOptions {
	enabled?: boolean;
	maxEvents?: number;
}

// descriptor factory ─ astro.config.mjs がビルド時に import する
export function analyticsPlugin(options: AnalyticsOptions = {}): PluginDescriptor {
	return {
		id: "analytics",
		version: "0.1.0",
		format: "native",
		entrypoint: "@my-org/plugin-analytics",
		options,
		adminEntry: "@my-org/plugin-analytics/admin",
		adminPages: [{ path: "/dashboard", label: "Dashboard", icon: "chart" }],
	};
}

// ランタイム側 ─ definePlugin() の戻り値を返す
export function createPlugin(options: AnalyticsOptions = {}) {
	return definePlugin({
		id: "analytics",
		version: "0.1.0",
		capabilities: ["network:request"],
		allowedHosts: ["api.analytics.example.com"],
		storage: { events: { indexes: ["type", "createdAt"] } },
		admin: {
			entry: "@my-org/plugin-analytics/admin",
			pages: [{ path: "/dashboard", label: "Dashboard", icon: "chart" }],
		},
		hooks: {
			"content:afterSave": async (event, ctx) => {
				await ctx.storage.events.put(`evt_${Date.now()}`, {
					type: "content:save",
					contentId: event.content.id,
					createdAt: new Date().toISOString(),
				});
			},
		},
		routes: {
			stats: {
				// native のルートハンドラは (ctx) の 1 引数 ─ sandboxed の (routeCtx, ctx) と逆
				handler: async (ctx) => {
					const today = new Date().toISOString().split("T")[0];
					const count = await ctx.storage.events.count({ createdAt: { gte: today } });
					return { today: count };
				},
			},
		},
	});
}

export default createPlugin;
```

> [!important] descriptor と `definePlugin` の `id` / `version` / `capabilities` は一致必須
> `id`・`version`・`capabilities` は descriptor（`astro.config.mjs` がビルド時に見る側）と `definePlugin()`（実行時に動く側）の両方に書く必要があり、値を一致させる。`options` は descriptor → `createPlugin` へそのまま渡される（sandboxed プラグインにはこの経路が無く、設定は KV から読む）。

`id` の命名規則は sandboxed の `slug` と同じ（`/^[a-z][a-z0-9_-]*$/`、先頭は小文字、数字開始不可、ドット不可）。バージョンは semver（`"1.0.0"` は可、`"1.0"` は不可）。

### Portable Text コンポーネントの提供

native プラグインは `componentsEntry`（descriptor 側）が指すモジュールから、固定の export 名 `blockComponents` でブロックコンポーネントを提供できる。

```typescript
// componentsEntry が指すモジュール
export const blockComponents = { youtube: YouTube };
```

ユーザーが `<PortableText components={{ ... }} />` で明示指定したコンポーネントが常に優先される。

### astro.config への登録

```typescript title="astro.config.mjs"
import { defineConfig } from "astro/config";
import emdash from "emdash/astro";
import { analyticsPlugin } from "@my-org/plugin-analytics";

export default defineConfig({
	integrations: [
		emdash({
			plugins: [analyticsPlugin({ enabled: true, maxEvents: 500 })],
		}),
	],
});
```

native プラグインは常に in-process 実行で、`sandboxed: []` には入れられない。

---

## capabilities 全 12 種

`emdash-plugin.jsonc`（sandboxed）または `definePlugin()`（native、ドキュメント目的のみ）で宣言する。

| capability | 付与されるアクセス |
|---|---|
| `content:read` | `ctx.content.get()` / `ctx.content.list()` |
| `content:write` | `ctx.content.create()` / `update()` / `delete()`（`content:read` を暗黙に含む） |
| `taxonomies:read` | `ctx.taxonomies.getAll()` / `getTerms()` / `getEntryTerms()`（`content:read` とは独立） |
| `media:read` | `ctx.media.get()` / `ctx.media.list()` |
| `media:write` | `ctx.media.getUploadUrl()` / `upload()` / `delete()`（`media:read` を暗黙に含む） |
| `network:request` | `ctx.http.fetch()`（`allowedHosts` に限定） |
| `network:request:unrestricted` | `ctx.http.fetch()` を無制限に（`network:request` を暗黙に含む。宛先をユーザーが実行時に指定するプラグイン専用） |
| `users:read` | `ctx.users.get()` / `getByEmail()` / `list()` |
| `email:send` | `ctx.email.send()`（capability 宣言 **かつ** transport プラグインが設定済みのときのみ `ctx.email` が存在する） |
| `hooks.email-transport:register` | exclusive フック `email:deliver` の登録を許可（transport プロバイダ用） |
| `hooks.email-events:register` | `email:beforeSend` / `email:afterSend` フックの登録を許可 |
| `hooks.page-fragments:register` | `page:fragments` フックの登録を許可（native プラグイン専用） |

補足:

- **暗黙の包含**: `content:write` は `content:read` を、`media:write` は `media:read` を、`network:request:unrestricted` は `network:request` を、それぞれ暗黙に含む（両方を書く必要はない）。
- Storage（`ctx.storage`）と KV（`ctx.kv`）は capability 不要で常に使える（自プラグインのスコープに限定）。
- `emdash-plugin bundle` / `publish` は capability の綴りチェック・`network:request` に `allowedHosts` が空でないこと・`network:request:unrestricted` に `allowedHosts` が空であることをビルド時に検証する。

---

## hooks 全 25 種

> [!note] 個数の訂正
> `docs/src/content/docs/reference/hooks.mdx` を直接確認したところ、掲載されているフックは **25 種**（content 系 9・media 系 2・cron 1・email 系 3・comment 系 4・page 系 2・plugin lifecycle 系 4）。

| フック | 発火タイミング | 変更可否 | Exclusive | 必要 capability |
|---|---|---|---|---|
| `content:beforeSave` | コンテンツ保存前 | コンテンツデータ | No | ─ |
| `content:afterSave` | コンテンツ保存後 | なし | No | ─ |
| `content:beforeDelete` | コンテンツ削除前 | 削除をキャンセル可 | No | ─ |
| `content:afterDelete` | コンテンツ削除後 | なし | No | ─ |
| `content:afterPublish` | コンテンツ公開後 | なし | No | ─ |
| `content:afterUnpublish` | コンテンツ非公開化後 | なし | No | ─ |
| `content:afterRestore` | コンテンツ復元後 | なし | No | `content:read` |
| `content:afterSchedule` | コンテンツの公開予約後 | なし | No | `content:read` |
| `content:afterUnschedule` | コンテンツの公開予約解除後 | なし | No | `content:read` |
| `media:beforeUpload` | ファイルアップロード前 | ファイルメタデータ | No | ─ |
| `media:afterUpload` | ファイルアップロード後 | なし | No | ─ |
| `cron` | スケジュールタスク発火時 | なし | No | ─（`ctx.cron.schedule()` で登録） |
| `email:beforeSend` | メール配信前 | メッセージ、送信キャンセル可 | No | `hooks.email-events:register` |
| `email:deliver` | transport 経由でメールを配信 | なし | **Yes** | `hooks.email-transport:register` |
| `email:afterSend` | メール配信成功後 | なし | No | `hooks.email-events:register` |
| `comment:beforeCreate` | コメント保存前 | コメント、拒否可 | No | `users:read` |
| `comment:moderate` | コメントの承認可否を決定 | ステータス | **Yes** | `users:read` |
| `comment:afterCreate` | コメント保存後 | なし | No | `users:read` |
| `comment:afterModerate` | 管理者がコメントステータスを変更後 | なし | No | `users:read` |
| `page:metadata` | 公開ページのヘッド描画時 | メタタグを追加 | No | 不要 |
| `page:fragments` | 公開ページのボディ描画時 | スクリプト注入 | No | `hooks.page-fragments:register`（native 専用） |
| `plugin:install` | プラグイン初回インストール時 | なし | No | ─ |
| `plugin:activate` | プラグイン有効化時 | なし | No | ─ |
| `plugin:deactivate` | プラグイン無効化時 | なし | No | ─ |
| `plugin:uninstall` | プラグイン削除時 | なし | No | ─ |

「必要 capability」列の「─」は、フックの**登録自体**に特別な capability が要らないという意味。ハンドラ内で `ctx.content` 等のデータアクセス API を呼ぶ場合は、別途対応する capability（`content:read` 等）の宣言が要る。

メール系フックの実行順は `email:beforeSend` → `email:deliver` → `email:afterSend`。コメント系は `comment:beforeCreate` → `comment:moderate` → `comment:afterCreate`（`comment:afterModerate` は管理者操作時に別途発火）。

hook 設定オブジェクトの共通オプション（`priority` / `timeout` / `dependencies` / `errorPolicy` / `exclusive`）は `emdash types` 等と同様に公式リファレンス（`reference/hooks.mdx`）を参照する。

---

## トラブルシューティング

| 症状 | 原因 / 対処 |
|---|---|
| `ctx.content` が `undefined` で TypeError | capability 未宣言。`ctx.content` / `ctx.media` / `ctx.http` / `ctx.users` / `ctx.email` は対応する capability を宣言したプラグインにしか生成されない（sandboxed の PluginContext factory がゲートしている） |
| `email:deliver` / `page:fragments` フックを登録したのにビルドが通らない、または動かない | `hooks.email-transport:register` / `hooks.page-fragments:register` の宣言漏れ。`page:fragments` は native プラグイン専用（sandboxed では使えない） |
| `ctx.email` が常に `undefined` | `email:send` capability を宣言していても、`email:deliver` を実装した transport プラグイン（例: `cloudflareEmail()`）が有効化・選択されていないと `ctx.email` は生成されない |
| sandboxed プラグインが起動時に無言でスキップされる | `sandboxRunner` が未設定、または現在のプラットフォームでランナーが unavailable（Cloudflare なら `wrangler.jsonc` の `worker_loaders` バインディング未設定、または無料プランで Dynamic Workers が使えない）。`plugins: []` に移せば動くが native 相当の信頼レベルになる点に注意 |
| 無料プランで sandboxed プラグインが動かない | Dynamic Workers（Worker Loader）は Open Beta・**Workers Paid プラン必須**。native への切り替えを検討する |
| native の descriptor と `definePlugin` で挙動が食い違う | `id` / `version` / `capabilities` が両者で一致しているか確認する（descriptor はビルド時、`definePlugin` はリクエスト時に参照される別々のコピー） |
| `slug` / `id` が拒否される | `/^[a-z][a-z0-9_-]*$/` に反している（大文字・先頭数字・`@`・`/`・ドットは不可）。npm パッケージ名とは別の識別子として設計する |
| `emdash-plugin bundle` が `network:request` でエラー | `allowedHosts` が空。`network:request:unrestricted` を使う場合は逆に `allowedHosts` を空にする |
| sandboxed プラグインが Hyperdrive（Postgres）デプロイで動かない | サンドボックスプラグインブリッジは D1 バインディングに直接依存するため D1 専用。Hyperdrive 構成では sandboxed プラグインが使えない（既知の制約） |

---

## 参照ドキュメント

- プラグイン概要: `docs/src/content/docs/plugins/overview.mdx`
- 形式の選び方: `docs/src/content/docs/plugins/creating-plugins/choosing-a-format.mdx`
- sandboxed チュートリアル: `docs/src/content/docs/plugins/creating-plugins/your-first-plugin.mdx`
- マニフェスト全項目: `docs/src/content/docs/plugins/creating-plugins/manifest.mdx`
- capabilities: `docs/src/content/docs/plugins/creating-plugins/capabilities.mdx`
- hooks 全量: `docs/src/content/docs/reference/hooks.mdx`
- `emdash-plugin` CLI: `docs/src/content/docs/plugins/creating-plugins/cli.mdx`
- native チュートリアル: `docs/src/content/docs/plugins/creating-native-plugins/your-first-native-plugin.mdx`
- Portable Text コンポーネント: `docs/src/content/docs/plugins/creating-native-plugins/portable-text-components.mdx`
- ページフラグメント: `docs/src/content/docs/plugins/creating-native-plugins/page-fragments.mdx`
- React 管理画面: `docs/src/content/docs/plugins/creating-native-plugins/react-admin.mdx`
- 配布・公開: `docs/src/content/docs/plugins/creating-plugins/publishing.mdx`
- メール transport・Forms プラグインは `email-and-forms.md` を参照
