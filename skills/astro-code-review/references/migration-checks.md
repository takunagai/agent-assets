# レビュー観点 10〜12: レガシー API（5→6）/ Astro 7 移行 / Cloudflare Workers

`SKILL.md` の「レビュー観点（12カテゴリ）」から分離。`[Legacy]` `[Astro 7]` `[Cloudflare]` ラベルの検出はこのファイルを Read してから行う。観点 1〜9 は `review-criteria.md`。

## Contents

- 10. レガシー API 検出（Astro 5 → 6 で削除）
- 11. Astro 7 移行チェック（6 → 7）
- 12. Cloudflare Workers デプロイ検証

### 10. レガシー API 検出（Astro 5 → 6 で削除）

Astro 5.x 時代のコードパターンを検出。これらは Astro 6 で削除済みで、v7 でも当然に非対応 ─ v7 プロジェクトに残っていれば移行が必須の負債。

**検出対象 (Critical):**
- `Astro.glob()` の使用 → `import.meta.glob()` へ移行必須
- `<ViewTransitions />` → `<ClientRouter />` へ移行必須
- `src/content/config.ts` → `src/content.config.ts` へ移行必須

**検出対象 (Warning):**
- `type: 'content'` / `type: 'data'` → loader API へ移行
- `entry.slug` → `entry.id` へ移行
- `entry.render()` → `render(entry)` へ移行
- `import { z } from 'astro:content'` → `import { z } from 'astro/zod'`
- `getEntryBySlug()` → `getEntry()` へ移行

**修正例:**
```astro
// Before: Astro 5.x (削除済み)
---
import { ViewTransitions } from 'astro:transitions';
const posts = await Astro.glob('./posts/*.md');
---
<ViewTransitions />

// After: Astro 6+/7
---
import { ClientRouter } from 'astro:transitions';
const posts = Object.values(import.meta.glob('./posts/*.md', { eager: true }));
---
<ClientRouter />
```

**Zod 4 移行 (Warning):**
```typescript
// Before: Zod 3
z.string().email()
{ message: "エラー" }

// After: Zod 4（v7 でも Zod 4.x のまま。import は 'astro/zod'）
z.email()
{ error: "エラー" }
```

詳細 → [Astro 6 Upgrade Guide](https://docs.astro.build/en/guides/upgrade-to/v6/)

---

### 11. Astro 7 移行チェック（6 → 7）

Astro 7（GA / 2026-06-22）で入った破壊的変更のうち、**ソースコードから検出可能なもの**を検出（`experimental` フラグの卒業など astro.config だけで完結する変更は検出対象外）。出典: [Astro v7 Upgrade Guide](https://docs.astro.build/en/guides/upgrade-to/v7/) / [Astro 7 リリース記事](https://astro.build/blog/astro-7/)。

**検出対象 (Critical) ─ Rust コンパイラの HTML 厳格化:**
- 未クローズタグ（void 要素以外に閉じタグがない）→ v7 の Rust 製 `.astro` コンパイラでは**ビルド不能**
- セマンティックに不正なネスト（`<p>` 内の `<div>`、`<ul>` 直下の非 `<li>` 等）→ 自動補正が廃止されビルドエラー

```astro
<!-- Before: Go コンパイラは黙認していた -->
<p>説明文<div>ブロック</div></p>
<ul><section>...</section></ul>
<div><span>未クローズ

<!-- After: v7 で通る正しい HTML -->
<div>説明文<div>ブロック</div></div>
<ul><li>...</li></ul>
<div><span>閉じる</span></div>
```

**検出対象 (Warning):**
- `astro.config` の `markdown.remarkPlugins` / `rehypePlugins` 使用 → v7 は **Sätteri**（Rust 製）がデフォルト Markdown/MDX プロセッサで、`@astrojs/markdown-remark` は既定で未インストール。既存の remark/rehype プラグインは Sätteri へ移行するか `@astrojs/markdown-remark` を明示インストールして `unified()` へ切り戻す
- `src/fetch.ts` の存在 → v7 では advanced routing の**予約ファイル名**（自動 import される）。routing 目的でない同名ファイルは衝突するため、リネームするか `astro.config` の `fetchFile` で回避
- `getContainerRenderer` の旧 import 経路 → `@astrojs/react` 等から直接ではなく `@astrojs/react/container-renderer`（preact / solid-js / svelte / vue / mdx も同様のサブパスへ）
- `@astrojs/db` / `astro:db` の使用 → v7 で**パッケージ削除**。`node:sqlite`（Node 22.5+）・Drizzle ORM 等の代替へ
- `astro:transitions` の内部 API（`TRANSITION_BEFORE_PREPARATION` 等の定数・`createAnimationScope()`・`isTransitionBeforePreparationEvent()` 等）→ v7 で削除。ライフサイクルイベント名の文字列（`'astro:before-preparation'` 等）を直接使う

**検出対象 (Info):**
- `compressHTML` 未指定 + 改行に依存したインライン要素レイアウト → v7 で `compressHTML` 既定が `true` → `'jsx'` に変更。JSX ルールでの空白除去になり、インライン要素間の改行が空白として保持されなくなる（表示差の可能性）。必要なら要素間に明示的な `{" "}` を入れる
- Vite 固有プラグイン使用時 → v7 は **Vite 8（Rolldown バンドラ）**。Vite 内部に依存するプラグイン/インテグレーションは Vite 8 対応の確認が必要

**修正例（Sätteri / remark プラグイン）:**
```javascript
// Before: v6 まで（@astrojs/markdown-remark がデフォルト）
export default defineConfig({
  markdown: {
    remarkPlugins: [remarkToc],
    rehypePlugins: [rehypeSlug],
  },
});

// After: v7 ─ 方針を決める
// (a) Sätteri（デフォルト）で同等機能が賄えるか確認して移行する、または
// (b) @astrojs/markdown-remark を明示インストールして unified() 相当へ切り戻す
```

> **Zod / CSP / Live Collections の v7 状態**（誤検出防止のためのメモ）:
> - Zod は v7 でも **4.x**（`import { z } from 'astro/zod'`）。v7 で import 経路もバージョンも変わらない ─ これらを「移行対象」として誤検出しない
> - CSP は `security.csp` として **stable**（`astro@6.0.0` 追加）。Live Collections も **stable**（Astro 6 で安定化）。どちらも v7 で削除・変更なし。活用は Info（観点 8 / 12）で扱い、欠如を欠陥として扱わない

---

### 12. Cloudflare Workers デプロイ検証

Cloudflare **Workers**（static assets 付き）へのデプロイ問題を検出。**Cloudflare Pages サポートはアダプター v13 で廃止済み**なので、Pages 前提の構成は移行負債として検出する。デプロイの実行手順そのものは姉妹スキル `deploy-astro-cloudflare`（Astro 7 / adapter v14 対応）の担当。本スキルはコードとデプロイ設定の**検出**に徹する。

**検出対象 (Critical):**
- `Astro.locals.runtime` の使用 → v13/Astro 6 で削除済み。`import { env } from 'cloudflare:workers'`（または `astro:env/server`）へ移行必須
- `Astro.locals.runtime.env` → `import { env } from 'cloudflare:workers'`
- Node.js 専用API（`fs`, `path`, `child_process` 等）の使用 → Cloudflare Workers 非互換（`crypto` は Web Crypto の `crypto.subtle` へ）

**検出対象 (Warning):**
- `@astrojs/cloudflare` アダプター未設定、または v13 以前（v14+ / wrangler `^4.83.0` が要件）
- `adapter: cloudflare({ platformProxy: {...} })` の残骸 → **`platformProxy` オプションは v14 に存在しない**（`astro dev`/`preview` が workerd 上で動くことで代替）。設定から除去
- `wrangler` 設定の `main` 旧値（`dist/_worker.js/index.js`）→ v14 は `"@astrojs/cloudflare/entrypoints/server"`。旧値は移行漏れ
- `public/.assetsignore` の残骸 → v14 では不要（旧構成の残骸）
- 静的ページで `prerender: false` が設定されている

**修正例:**
```astro
// Before: Astro 5.x Cloudflare (削除済み)
---
const runtime = Astro.locals.runtime;
const kv = runtime.env.MY_KV;
---

// After: Astro 6+/7 Cloudflare
---
import { env } from 'cloudflare:workers';
const kv = env.MY_KV;
await kv.put('key', 'value');
const value = await kv.get('key');
---
```

**ベストプラクティス (Info):**
- KV / R2 / D1 / Durable Objects の適切な使用
- 静的ページには `export const prerender = true` を設定
- Edge Runtime の制限事項を考慮したコード設計
- **Route Caching の活用機会**: v7 で route caching が stable 化。`@astrojs/cloudflare/cache` の `cacheCloudflare()` を cache provider に設定すると、`Cloudflare-CDN-Cache-Control` / `Cache-Tag` ヘッダを付与し Worker caching が自動有効化される（experimental CDN cache providers として Netlify / Vercel / Cloudflare を提供）。SSR ルートで再利用可能なレスポンスに有効

詳細 → `cloudflare-deployment.md`
