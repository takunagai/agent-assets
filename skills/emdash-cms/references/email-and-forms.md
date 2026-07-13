# EmDash メール & フォーム リファレンス

> [!note] 基準
> 本リファレンスは emdash 0.29.0（2026-07-10 リリース）/ 2026-07-13 検証を基準とする。`@emdash-cms/cloudflare` と `@emdash-cms/plugin-forms` も同じく 0.29.0 系。作業開始前に `pnpm view emdash version` で現行版を確認する。Cloudflare Email Service は 2026-07-13 時点で public beta（GA 未達）のため、料金・上限・提供状況は公式ドキュメント（`https://developers.cloudflare.com/email-service/`）で都度確認する。

## 全体構成図

```
                    ctx.email.send()
Forms プラグイン等  ───────────────────▶  EmDash メールパイプライン
（email:send 消費）                        email:beforeSend
                                              → email:deliver（exclusive・1 個だけ）
                                              → email:afterSend
                                                   │
                                                   ▼
                              transport プラグイン（hooks.email-transport:register）
                              ─ 公式一択: cloudflareEmail()（@emdash-cms/cloudflare/plugins）
                                                   │
                                                   ▼
                              Cloudflare Email Service（send_email Worker binding）
                                                   │
                                                   ▼
                                            実際のメール送信
```

magic link ログイン・チーム招待・コメント通知など EmDash コア機能のメールも、すべてこの `email:deliver` transport 経由で配信される。**transport が設定されていない Cloudflare 上のデプロイでは、開発コンソール向けのスタブしか無く、これらのメール依存フローは "Email is not configured" で失敗する。**

---

## Cloudflare Email Service のセットアップ

EmDash 側の設定に入る前に、Cloudflare 側でメール送信を有効化する。

### 1. 送信ドメインをオンボードする

Cloudflare ダッシュボードの **Email** → **Email Sending** から、送信元にしたいドメイン（またはアドレス）を検証する。未検証の送信元からのメールは Email Sending 側で拒否される。CLI からも有効化できる。

```bash
pnpm exec wrangler email sending enable <domain>
```

DNS レコードの反映には数分かかる（目安 5〜15 分）。

### 2. `send_email` バインディングを追加する

```jsonc title="wrangler.jsonc"
{
	"send_email": [{ "name": "EMAIL", "remote": true }]
}
```

Worker コード側からは `env.EMAIL.send({ to, from, subject, html, text })` で送信する（EmDash 経由で使う場合はこの呼び出しを後述の `cloudflareEmail()` プラグインが代行するため、自前で書く必要はない）。

> [!important] Public Beta・Workers Paid・上限
> Cloudflare Email Sending（送信側）は 2026-04-16 から public beta（2026-07-13 時点で GA 未達）。**Workers Paid プラン必須**。ただし認証済み宛先（同一アカウントで検証済みのドメイン・アドレス）への送信は全プランで無料。1 通あたりの上限は 5 MiB。

---

## EmDash 公式メール機構 ─ capability 3 分類

`skills/creating-plugins/SKILL.md`（191〜210 行付近）と `reference/capabilities.mdx` が定義する、メール関連の 3 つの capability。

| capability | 役割 | 対応するフック |
|---|---|---|
| `email:send` | **消費側** ─ メールを送りたいプラグイン（例: Forms プラグイン） | ─（`ctx.email.send()` を呼ぶだけ） |
| `hooks.email-transport:register` | **配信側** ─ 実際に送信するプロバイダを実装するプラグイン | `email:deliver`（exclusive ─ 有効化できる transport は常に 1 個だけ） |
| `hooks.email-events:register` | **観察・変換側** ─ ミドルウェア的にメールを見る/変えるプラグイン | `email:beforeSend` / `email:afterSend` |

`email:send` を宣言していても、`ctx.email` は「capability 宣言」**かつ**「`email:deliver` を実装した transport プラグインが有効化・選択されている」ときにのみ存在する。どちらか片方が欠けていると `ctx.email` は `undefined` のまま。

---

## 公式ファーストパーティ transport: `cloudflareEmail()`

> [!important] 自作する前に確認 ─ 公式プラグインが既に存在する
> `@emdash-cms/cloudflare` パッケージ（D1 / R2 アダプタと同じパッケージ）に、Cloudflare Email Service へ繋ぐ **ファーストパーティの transport プラグインが同梱されている**。`packages/cloudflare/src/plugins/cloudflare-email.ts` として実装され、`@emdash-cms/cloudflare/plugins` からエクスポートされる公開 API（`package.json` の `exports` で確認済み）。ゼロから自作する前に、まずこちらの導入を検討する。

### 導入（4 ステップ）

前段の Cloudflare Email Service セットアップ（ドメインオンボード + `send_email` バインディング）が済んでいる前提。

1. **プラグインを登録する**

   ```js title="astro.config.mjs"
   import { d1, r2 } from "@emdash-cms/cloudflare";
   import { cloudflareEmail } from "@emdash-cms/cloudflare/plugins";

   emdash({
   	database: d1({ binding: "DB" }),
   	storage: r2({ binding: "MEDIA" }),
   	plugins: [
   		cloudflareEmail({
   			from: { email: "cms@mails.example.com", name: "My Site CMS" },
   			replyTo: "hello@example.com", // 任意
   			binding: "EMAIL", // 任意。既定 "EMAIL"
   		}),
   	],
   });
   ```

2. **デプロイする**（Cloudflare Workers へのデプロイ手順自体は `deploy-astro-cloudflare` スキルに委譲）

3. **Admin → Extensions でプラグインを有効化する**

4. **Settings → Email で provider として選択する** ─ 有効化しただけでは自動選択されない。明示的な選択が必須。

### オプション

| オプション | 型 | 既定値 | 説明 |
|---|---|---|---|
| `from` | `string \| { email, name? }` | ─（必須） | Email Sending にオンボード済みドメインの送信元アドレス |
| `replyTo` | `string` | ─ | Reply-To アドレス（`from` を no-reply 系サブドメインにする場合に便利） |
| `binding` | `string` | `"EMAIL"` | `wrangler.jsonc` の `send_email` バインディング名 |

BCC・添付ファイルは EmDash の `EmailMessage` の型に含まれていないため非対応。

### 代替: 自作トランスポートプラグイン（他プロバイダ・カスタム挙動が要る場合）

Cloudflare Email Service 以外のプロバイダ（Resend・SMTP 等）に繋ぎたい場合や、送信ロジックを独自にカスタムしたい場合は、`hooks.email-transport:register` capability + `email:deliver` exclusive hook を自分で実装した native プラグインを書く。Cloudflare Email Service だけで足りるなら、上記の `cloudflareEmail()` を使えばこの節は不要。

`cloudflareEmail()` 自体が native プラグインとして実装されているので、その実装を雛形として読むとよい。id/version が descriptor 側と `definePlugin` 側で一致している実例、および capability 宣言の実例にもなっている。

```typescript
// packages/cloudflare/src/plugins/cloudflare-email.ts（要約・実装の骨格）
import type { PluginContext, PluginDescriptor, ResolvedPlugin } from "emdash";
import { definePlugin } from "emdash";
import type { EmailDeliverEvent } from "emdash/plugin";

export interface CloudflareEmailConfig {
	binding?: string; // 既定 "EMAIL"
	from: string | { email: string; name?: string };
	replyTo?: string;
}

// フックはリクエストコンテキスト無しで実行されるため、
// Astro.locals.runtime ではなく cloudflare:workers の env から
// バインディングを取得する（astro dev でも Cloudflare アダプタ経由で動く）
async function loadWorkerEnv() {
	const mod = await import("cloudflare:workers");
	return mod.env as Record<string, unknown>;
}

export function createPlugin(config: CloudflareEmailConfig): ResolvedPlugin {
	return definePlugin({
		id: "cloudflare-email",
		version: "1.0.0",
		capabilities: ["hooks.email-transport:register"],
		hooks: {
			"email:deliver": {
				exclusive: true,
				handler: async (event: EmailDeliverEvent, ctx: PluginContext) => {
					const env = await loadWorkerEnv();
					const binding = env[config.binding ?? "EMAIL"] as {
						send: (msg: unknown) => Promise<{ messageId?: string }>;
					};
					const result = await binding.send({
						from: typeof config.from === "string" ? { email: config.from } : config.from,
						to: event.message.to,
						subject: event.message.subject,
						text: event.message.text,
						...(event.message.html ? { html: event.message.html } : {}),
						...(config.replyTo ? { replyTo: config.replyTo } : {}),
					});
					ctx.log.info("email delivered via Cloudflare Email Sending", {
						messageId: result?.messageId,
					});
				},
			},
		},
	});
}

export function cloudflareEmail(config: CloudflareEmailConfig): PluginDescriptor<CloudflareEmailConfig> {
	return {
		id: "cloudflare-email",
		version: "1.0.0",
		entrypoint: "@emdash-cms/cloudflare/plugins/cloudflare-email",
		format: "native",
		options: config,
		capabilities: ["hooks.email-transport:register"],
	};
}
```

自作する場合の要点はこの実装から読み取れる ─ `email:deliver` フックは `exclusive: true` にする、`send_email` バインディングは `cloudflare:workers` の `env` から動的 import で取得する（フックはリクエストスコープを持たないため `Astro.locals.runtime` は使えない）、送信失敗時はエラーを投げて呼び出し側（Forms プラグイン等）の catch に委ねる。SMTP・Resend 等の別サービスに繋ぐ transport を書く場合も、この `email:deliver` exclusive hook を実装する構造は同じ。

---

## 参考掲載: サードパーティ `emdash-plugin-cloudflare-email`

> [!warning] 動作未検証・導入前に capability エラーを確認すること
> `emdash-plugin-cloudflare-email@0.1.0`（Velvee 社、https://github.com/velvee-ai/emdash-plugin-cloudflare-email）というサードパーティプラグインも存在する。peer dependency が `emdash >= 0.5.0` と古く、binding 名は `EMAIL` 固定（設定不可）、`plugins: [cloudflareEmail()]` に登録する native 形式という設計は上記の公式プラグインと似ているが、**3 ヶ月以上更新が無く、現行 0.29 系での capability 体系（本リファレンスの 3 分類）との整合が未確認**。
>
> **公式ファーストパーティ `cloudflareEmail()` の登場で、このプラグインの存在意義はほぼ無くなっている。** 同等の機能を公式パッケージが提供するため、新規導入では検討する理由が無い。既存プロジェクトで既にこれを使っている場合のみ、移行前提で挙動を把握する目的で参照し、導入・継続利用する場合は capability 宣言のエラーが出ないか実機で確認すること。

---

## Forms プラグイン（公式・`@emdash-cms/plugin-forms`）

### 導入

native 形式。peer dependency: `astro >=6.0.0-beta.0`・`emdash >=0.11.0`・`react ^18||^19`・`@phosphor-icons/react`・`@cloudflare/kumo`（2026-07-13 に `pnpm view @emdash-cms/plugin-forms peerDependencies` で実測）。

```bash
pnpm add @emdash-cms/plugin-forms
```

```js title="astro.config.mjs"
import { formsPlugin } from "@emdash-cms/plugin-forms";

emdash({
	plugins: [
		formsPlugin({
			defaultSpamProtection: "turnstile", // "none" | "honeypot" | "turnstile"
		}),
	],
});
```

capabilities: `email:send` / `media:write` / `network:request`（Turnstile 検証・添付ファイル保存・Webhook 送信のため）。

### スパム対策 3 種

フォームごとに `settings.spamProtection` で選ぶ。既定値は `formsPlugin()` の `defaultSpamProtection` オプション。

- `"none"` ─ 対策なし
- `"honeypot"` ─ 隠しフィールド方式（設定不要）
- `"turnstile"` ─ Cloudflare Turnstile。Admin の設定画面で **Turnstile Site Key** と **Turnstile Secret Key**（`type: "secret"`、暗号化保存）を入力する。フロントエンドの検証ウィジェット表示は別途 `settings/turnstile-status` ルートでキー設定状況を確認できる

### 通知メール（フォーム設定 `FormSettings`）

| フィールド | 型 | 説明 |
|---|---|---|
| `notifyEmails` | `string[]` | 送信ごとに通知するメールアドレスの一覧 |
| `digestEnabled` | `boolean` | `true` で個別通知の代わりに日次ダイジェストにする |
| `digestHour` | `number`（0〜23） | ダイジェスト送信時刻（サイトのタイムゾーン基準） |
| `autoresponder` | `{ subject, body }` | 送信者本人への自動返信メール |
| `webhookUrl` | `string` | 送信のたびに POST する Webhook URL |
| `retentionDays` | `number` | 送信データの保持日数（`0` で無期限） |

> [!important] transport 未設定だと通知は無言でスキップされる
> 実装（`packages/plugins/forms/src/handlers/submit.ts`）を確認したところ、通知送信の条件は次のとおり。
>
> ```typescript
> if (settings.notifyEmails.length > 0 && !settings.digestEnabled && ctx.email) {
>   // 送信処理
> }
> ```
>
> `ctx.email` が `undefined`（＝ transport 未設定）のときはこの条件が単に成立せず、**エラーもログも出ないまま通知だけが送られない**。オートレスポンダーも同様に `if (settings.autoresponder && ctx.email)` でガードされている。フォームを作る前に、まず transport（前段の `cloudflareEmail()` 等）を有効化・選択しておくこと。

日次ダイジェストと週次クリーンアップは `plugin:activate` フックで `ctx.cron.schedule("cleanup", { schedule: "@weekly" })` を登録し、`cron` フックの `event.name` が `"cleanup"` または `"digest:<formId>"` かで処理を分岐する仕組み。

### Portable Text への埋め込み

Forms プラグインは `admin.portableTextBlocks` でブロック型 `emdash-form` を提供する。管理画面の本文エディタから「Form」ブロックを挿入し、`formId` フィールド（`forms/list` ルートから選択肢を取得する `select` 型）でフォームを選ぶと、本文中に埋め込まれる。

---

## 問い合わせフォーム構築のエンドツーエンド手順

1. Cloudflare ダッシュボードで送信ドメインを Email Sending にオンボードする（または `pnpm exec wrangler email sending enable <domain>`）
2. `wrangler.jsonc` に `send_email` バインディングを追加する
3. `astro.config.mjs` に `cloudflareEmail()`（transport）と `formsPlugin()`（フォーム本体）を両方 `plugins: []` に登録する
4. デプロイする
5. Admin → Extensions で両プラグインを有効化する
6. Settings → Email で `cloudflareEmail` を provider として選択する
7. Admin でフォームを作成し、`notifyEmails` に問い合わせ受付用アドレスを設定する。必要なら `autoresponder`（自動返信）・`spamProtection: "turnstile"`（Turnstile キー設定込み）も設定する
8. 本文（Portable Text）にフォームブロックを埋め込む
9. 実際にフォームを送信してテストする ─ 通知メールが届くか、Turnstile 設定時は検証が機能するか、`submissions/list` ルートで送信データが保存されているかを確認する
10. 届かない場合はまず「Settings → Email で provider が選択されているか」（ステップ 6 の抜け漏れが最頻出の原因）を疑う

---

## 参照ドキュメント

- Cloudflare Email 設定手順（EmDash 公式）: `docs/src/content/docs/deployment/cloudflare.mdx`（「Email」節）
- capability 3 分類の正本: `skills/creating-plugins/SKILL.md`（191〜210 行付近）・`docs/src/content/docs/plugins/creating-plugins/capabilities.mdx`
- hooks 全量（`email:*` 含む）: `docs/src/content/docs/reference/hooks.mdx`
- Cloudflare Email Service 公式ドキュメント: https://developers.cloudflare.com/email-service/
- Cloudflare Email Sending（旧 Email Routing send-email-workers）: https://developers.cloudflare.com/email-routing/email-workers/send-email-workers/
- `@emdash-cms/cloudflare` ソース: `packages/cloudflare/src/plugins/cloudflare-email.ts`
- `@emdash-cms/plugin-forms` ソース: `packages/plugins/forms/src/`（`index.ts` / `types.ts` / `handlers/submit.ts` / `handlers/cron.ts`）
- サードパーティ参考: https://github.com/velvee-ai/emdash-plugin-cloudflare-email
- プラグイン開発全般（capabilities・hooks 全量・sandboxed/native の使い分け）: `plugin-development.md`
