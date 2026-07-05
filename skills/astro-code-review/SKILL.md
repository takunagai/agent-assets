---
name: astro-code-review
version: "3.0.0"
astro: "^7.0.0"
cloudflare: "@astrojs/cloudflare ^14.0.0"
description: "Astro 7+ コードレビュースキル。Astroプロジェクト（Cloudflare Workers デプロイ対応）のコードを体系的にレビューし、ベストプラクティス違反・パフォーマンス問題・アクセシビリティ欠陥・型安全性の欠如・レガシー API（Astro 5/6 時代の削除済みパターン）・Astro 7 移行問題（Rust コンパイラの HTML 厳格化・Sätteri・src/fetch.ts 予約名）を検出して改善提案を行う。『Astroのコードをレビューして』『このAstroコンポーネントをチェックして』『Astroプロジェクトの品質を確認して』『Astro review』などのリクエストで発動。"
---

# Astro Code Review Skill

**Astro 7+（GA）専用** のコードレビュースキル。Cloudflare Workers をメインデプロイ先として想定（Cloudflare Pages サポートはアダプター v13 で廃止済み ─ デプロイ先は static assets 付き Workers 一本）。

> **注意**: このスキルは Astro 7 以降を対象としています。Astro 5.x / 6.x 時代の削除済み API（レガシー API）はレガシー検出として、6 → 7 の破壊的変更は Astro 7 移行チェックとして、二層で検出します。

## 対応環境

| 項目 | バージョン |
|------|-----------|
| Astro | 7.0.0 以上（GA） |
| Node.js | 22.12.0 以上（`astro@7` の engines は `>=22.12.0`。奇数メジャー非対応） |
| デプロイ先 | Cloudflare Workers（static assets 付き。Pages は非対応） |
| アダプター | @astrojs/cloudflare v14+ |
| wrangler | ^4.83.0 以上（adapter v14 の peer 要件） |
| Zod | 4.x（`import { z } from 'astro/zod'`。v7 で変更なし） |

## 目的

- Astro固有のベストプラクティス違反を検出
- パフォーマンス問題の早期発見
- アクセシビリティ・SEOの品質確保
- 型安全性の向上
- **レガシー API（Astro 5/6 で削除済みパターン）の検出と修正ガイダンス**
- **Astro 7 移行問題の検出（Rust コンパイラの HTML 厳格化・Sätteri・src/fetch.ts 予約名ほか）**
- **Cloudflare Workers デプロイの最適化**

## 発動条件（優先順位順）

1. **明示的呼び出し**: `/astro-code-review` コマンド
2. **Astroキーワード + レビュー意図**: 「Astroのコードをチェック」「Astroコンポーネントをレビュー」
3. **`.astro`ファイル指定 + レビュー意図**: 「src/pages/index.astro をレビュー」
4. **プロジェクト判定**: `astro.config.mjs` 存在 + 「コードレビューして」

## 使用方法

```bash
/astro-code-review                              # カレントディレクトリの全.astroファイル
/astro-code-review src/pages/                   # 指定ディレクトリ配下
/astro-code-review src/components/Header.astro  # 特定ファイル
/astro-code-review --severity=critical          # Criticalのみ検出
/astro-code-review --fix                        # 安全な自動修正を適用
```

## レビュー観点（12カテゴリ）

観点 1〜9 はバージョン非依存の普遍的なベストプラクティス。観点 10 は Astro 5 → 6 で削除されたレガシー API 検出、観点 11 は Astro 6 → 7 の移行問題、観点 12 は Cloudflare Workers デプロイ検証。

### 1. Islandアーキテクチャ検証

**検出対象:**
- `client:*` ディレクティブの不適切な選択
- 不要なJavaScriptハイドレーション
- `server:defer` の未活用

**ルール:**
| ディレクティブ | 適切な使用場面 | 不適切な例 |
|---------------|---------------|-----------|
| `client:load` | 即時必要なインタラクション（ナビゲーション、認証UI） | 重いチャートコンポーネント |
| `client:visible` | ビューポート外のコンポーネント | Above-the-foldのCTA |
| `client:idle` | 低優先度（ニュースレター、フィードバック） | 重要な入力フォーム |
| `client:only` | SSR不要・クライアント専用 | SEO重要なコンテンツ |

**修正例:**
```astro
// Before: 不適切
<HeavyChart client:load />

// After: 適切
<HeavyChart client:visible />
```

詳細 → `references/island-architecture.md`

---

### 2. TypeScript型安全性

**検出対象:**
- `interface Props` / `type Props` の未定義
- `HTMLAttributes<"element">` 型の未活用
- Content Collections のスキーマ型定義欠如
- `astro/types` からの型インポート欠如

**修正例:**
```astro
// Before: 型定義なし
---
const { title, description } = Astro.props;
---

// After: 型定義あり
---
interface Props {
  title: string;
  description?: string;
}
const { title, description } = Astro.props;
---
```

詳細 → `references/typescript-patterns.md`

---

### 3. 画像・アセット最適化

**検出対象:**
- `<img>` タグの直接使用（`<Image />` 未使用）
- `alt` 属性の欠如
- `loading="lazy"` / `decoding="async"` の欠如
- 最適化されていない画像フォーマット

**修正例:**
```astro
// Before: 最適化なし
<img src="/hero.png">

// After: 最適化あり
---
import { Image } from 'astro:assets';
import heroImage from '../assets/hero.png';
---
<Image src={heroImage} alt="Hero section background" />
```

詳細 → `references/image-optimization.md`

---

### 4. コンポーネント設計

**検出対象:**
- レイアウトコンポーネントの不適切な構造
- `<slot />` の非効率な使用
- 単一責任原則違反
- 名前付きスロットの未活用

**ベストプラクティス:**
```astro
// Layout コンポーネント
---
interface Props {
  title: string;
  description?: string;
}
const { title, description } = Astro.props;
---
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width" />
    <meta name="description" content={description} />
    <title>{title}</title>
    <slot name="head" />
  </head>
  <body>
    <header><slot name="header" /></header>
    <main><slot /></main>
    <footer><slot name="footer" /></footer>
  </body>
</html>
```

---

### 5. データ取得パターン

**検出対象:**
- `getCollection()` / `getEntry()` の不適切な使用
- エラーハンドリングの欠如
- SSR/SSG モードの不整合
- 404リダイレクト処理の欠如

**修正例:**
```astro
// Before: エラーハンドリングなし
---
import { getEntry, render } from 'astro:content';
const post = await getEntry('blog', Astro.params.slug);
const { Content } = await render(post);
---

// After: 適切なエラーハンドリング
---
import { getEntry, render } from 'astro:content';

const { slug } = Astro.params;
if (!slug) {
  return Astro.redirect('/404');
}

const post = await getEntry('blog', slug);
if (!post) {
  return Astro.redirect('/404');
}

const { Content } = await render(post);
---
```

詳細 → `references/data-fetching.md`

---

### 6. SEO・メタデータ

**検出対象:**
- `<title>` の欠如
- `<meta name="description">` の欠如
- Open Graph タグの欠如
- canonical URL の未設定
- 構造化データ（JSON-LD）の欠如

**推奨構成:**
```astro
<head>
  <title>{title} | サイト名</title>
  <meta name="description" content={description} />
  <link rel="canonical" href={canonicalURL} />

  <!-- Open Graph -->
  <meta property="og:title" content={title} />
  <meta property="og:description" content={description} />
  <meta property="og:type" content="website" />
  <meta property="og:url" content={canonicalURL} />
  <meta property="og:image" content={ogImage} />

  <!-- Twitter -->
  <meta name="twitter:card" content="summary_large_image" />

  <!-- JSON-LD -->
  <script type="application/ld+json" set:html={JSON.stringify(structuredData)} />
</head>
```

---

### 7. アクセシビリティ（a11y）

**検出対象:**
- セマンティックHTML要素の未使用
- `<html lang="...">` の欠如
- ARIA属性の誤用
- キーボードナビゲーション非対応
- フォームラベルの欠如

**チェックリスト:**
- [ ] `<html lang="ja">` が設定されている
- [ ] 見出し階層（h1→h2→h3）が適切
- [ ] `<main>`, `<nav>`, `<article>`, `<aside>` を使用
- [ ] 画像に意味のある `alt` テキスト
- [ ] フォーム要素に `<label>` が関連付け
- [ ] インタラクティブ要素がキーボードアクセス可能

---

### 8. セキュリティ

**検出対象:**
- `set:html` の安全でない使用
- 外部データの未サニタイズ
- 環境変数の不適切な使用
- クライアントへの機密情報漏洩

**危険パターン:**
```astro
// DANGER: 未サニタイズの外部データ
<div set:html={userInput} />

// DANGER: クライアント露出
<script>
  const apiKey = "{import.meta.env.SECRET_API_KEY}";
</script>
```

**安全パターン:**
```astro
// サーバーサイドのみで使用
---
const secretKey = import.meta.env.SECRET_API_KEY;
const data = await fetchWithAuth(secretKey);
---
<div>{data.safeContent}</div>

// クライアント公開用は PUBLIC_ プレフィックス
<script>
  const publicKey = "{import.meta.env.PUBLIC_ANALYTICS_ID}";
</script>
```

詳細 → `references/seo-a11y-security.md`

---

### 9. パフォーマンス

**検出対象:**
- 不要なクライアントサイドJS
- Content Collections の非効率なクエリ
- 大きなバンドルサイズ
- レンダリングブロッキングリソース

**最適化ポイント:**
- 可能な限り静的レンダリング（SSG）を優先
- `client:*` は必要最小限に
- 画像は `astro:assets` で自動最適化
- CSS は `<style>` タグでスコープ化

---

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

詳細 → `references/cloudflare-deployment.md`

---

## 重要度分類

| レベル | 説明 | 対応 |
|--------|------|------|
| **Critical** | セキュリティ脆弱性、必須a11y違反 | 即時修正必須 |
| **Warning** | パフォーマンス問題、推奨パターン逸脱 | 優先的に修正 |
| **Info** | ベストプラクティス提案、最適化機会 | 検討推奨 |

ラベル体系: **[Legacy]** = Astro 5 → 6 で削除された API（観点 10）。**[Astro 7]** = Astro 6 → 7 の移行問題（観点 11）。**[Cloudflare]** = Workers デプロイ検証（観点 12）。

### Critical（即時対応必須）
- `set:html` での未サニタイズデータ使用
- `alt` 属性の欠如
- `<html lang>` の欠如
- `getEntry()` / `getCollection()` の null チェック欠如
- クライアントへの機密情報漏洩
- **[Legacy]** `Astro.glob()` の使用
- **[Legacy]** `<ViewTransitions />` の使用
- **[Astro 7]** 未クローズタグ・不正ネスト（Rust コンパイラでビルド不能）
- **[Cloudflare]** `Astro.locals.runtime` の使用
- **[Cloudflare]** Node.js 専用API の使用

### Warning（改善推奨）
- 不適切な `client:*` ディレクティブ選択
- Props 型定義の欠如
- `<Image />` コンポーネント未使用
- `<title>` / `<meta description>` の欠如
- エラーハンドリングの不足
- **[Legacy]** legacy Content Collections API の使用
- **[Legacy]** `import { z } from 'astro:content'`
- **[Astro 7]** `markdown.remarkPlugins` / `rehypePlugins` 使用（Sätteri 非互換の可能性）
- **[Astro 7]** `src/fetch.ts` の予約名衝突
- **[Astro 7]** `getContainerRenderer` の旧 import 経路 / `@astrojs/db` / `astro:transitions` 内部 API
- **[Cloudflare]** `platformProxy` の残骸・`main` 旧値・`.assetsignore` の残骸
- **[Cloudflare]** `prerender` 設定の最適化不足

### Info（ベストプラクティス提案）
- セマンティックHTML要素の活用
- Open Graph タグの追加
- 構造化データの追加
- コンポーネント分割の提案
- パフォーマンス最適化の機会
- **[Astro 7]** `compressHTML: 'jsx'` 既定化による表示差の可能性 / Vite 8 プラグイン対応
- **[Cloudflare]** CSP（`security.csp` ─ stable）設定の推奨
- **[Cloudflare]** Live Collections（stable）の活用機会
- **[Cloudflare]** KV / R2 / D1 / Route Caching（`cacheCloudflare()`）の活用機会

---

## 実行フロー【必須遵守】

### Step 1: 対象ファイル特定

**ツール使用: Glob**

```
パターン: **/*.astro
パス: 指定されたディレクトリ、または カレントディレクトリ
```

**判断ロジック:**
- 引数がファイルパス（`.astro`で終わる）→ そのファイルのみ対象
- 引数がディレクトリ → そのディレクトリ配下の全`.astro`ファイル
- 引数なし → カレントディレクトリから再帰検索

**ファイル数による分岐:**
- 0件 → エラー処理へ（Step 5参照）
- 1-20件 → 全ファイルを解析
- 21件以上 → ユーザーに確認（「{N}件のファイルが見つかりました。全て解析しますか？ディレクトリを絞り込むことも可能です。」）

---

### Step 2: 静的解析【並列実行可】

**ツール使用: Read（各ファイルに対して）**

各`.astro`ファイルに対し、以下のチェック項目を検査:

#### Critical チェック（必須）
- [ ] `set:html` に未サニタイズのユーザー入力がないか
- [ ] `<img>` タグに `alt` 属性があるか
- [ ] `<html>` タグに `lang` 属性があるか
- [ ] `getEntry()` / `getCollection()` の戻り値に null チェックがあるか
- [ ] `SECRET_*` 環境変数がクライアントスクリプト内で使用されていないか
- [ ] **[Legacy]** `Astro.glob()` が使用されていないか
- [ ] **[Legacy]** `<ViewTransitions />` が使用されていないか
- [ ] **[Astro 7]** 未クローズタグ・不正ネスト（`<p>` 内 `<div>` 等）がないか（v7 Rust コンパイラでビルド不能）
- [ ] **[Cloudflare]** `Astro.locals.runtime` が使用されていないか
- [ ] **[Cloudflare]** `fs`, `path`, `child_process` 等の Node.js 専用API が使用されていないか

#### Warning チェック
- [ ] `client:load` が不適切に使用されていないか（重いコンポーネント、Below-the-fold）
- [ ] `interface Props` または `type Props` が定義されているか
- [ ] `<img>` の代わりに `<Image />` コンポーネントを使用しているか
- [ ] `<title>` と `<meta name="description">` が存在するか（ページファイルのみ）
- [ ] `getEntry()` の結果に対する 404 リダイレクト処理があるか
- [ ] **[Legacy]** `src/content/config.ts` ではなく `src/content.config.ts` を使用しているか
- [ ] **[Legacy]** `type: 'content'` / `type: 'data'` が使用されていないか
- [ ] **[Legacy]** `entry.slug` ではなく `entry.id` を使用しているか
- [ ] **[Legacy]** `entry.render()` ではなく `render(entry)` を使用しているか
- [ ] **[Legacy]** `import { z } from 'astro/zod'` を使用しているか（`astro:content` からの z import は不可）
- [ ] **[Astro 7]** `astro.config` の `markdown.remarkPlugins` / `rehypePlugins` が Sätteri 移行 or `@astrojs/markdown-remark` 切り戻し済みか
- [ ] **[Astro 7]** `src/fetch.ts` が advanced routing 目的か（意図しない予約名衝突がないか）
- [ ] **[Astro 7]** `@astrojs/db` / `astro:db`・`astro:transitions` 内部 API・旧 `getContainerRenderer` import が残っていないか
- [ ] **[Cloudflare]** `platformProxy` の残骸・`main` 旧値（`dist/_worker.js/index.js`）・`public/.assetsignore` の残骸がないか

#### Info チェック
- [ ] セマンティックHTML要素（`<main>`, `<nav>`, `<article>`）を使用しているか
- [ ] Open Graph タグが設定されているか
- [ ] 構造化データ（JSON-LD）が含まれているか
- [ ] 名前付きスロット `<slot name="...">` を活用しているか
- [ ] **[Astro 7]** `compressHTML` 既定変更（`'jsx'`）でインラインレイアウトに表示差が出ていないか / Vite 固有プラグインが Vite 8 対応か
- [ ] **[Cloudflare]** CSP が `security.csp` で有効化されているか（stable）
- [ ] **[Cloudflare]** 静的ページに `export const prerender = true` が設定されているか

---

### Step 3: レポート生成【必須フォーマット】

検出した問題を以下の形式で整理。**このフォーマットを厳守すること。**

```markdown
# Astro Code Review Report

## 📁 対象ファイル
- `src/pages/index.astro`
- `src/components/Header.astro`
（実際の対象ファイルを列挙）

---

## 🚨 Critical Issues (即時対応必須)

### [C-001] alt属性の欠如
- **ファイル**: `src/components/Hero.astro:15`
- **カテゴリ**: Image Optimization / Accessibility
- **問題**: `<img>` タグに alt 属性がありません。スクリーンリーダーユーザーが画像の内容を理解できません。
- **修正前**:
  ```astro
  <img src={heroImage} />
  ```
- **修正後**:
  ```astro
  <img src={heroImage} alt="メインビジュアル: 製品の特徴を示す図解" />
  ```
- **参照**: [Astro Image Guide](https://docs.astro.build/en/guides/images/)

（問題がない場合は「Critical Issues はありません ✅」と明記）

---

## ⚠️ Warnings (改善推奨)

### [W-001] Props型定義の欠如
- **ファイル**: `src/components/Card.astro:1-5`
- **カテゴリ**: TypeScript
- **問題**: Props の型定義がありません。型安全性が低下し、IDE の補完も効きません。
- **推奨**: `interface Props` を frontmatter 内で定義してください。
- **修正例**:
  ```astro
  ---
  interface Props {
    title: string;
    description?: string;
  }
  const { title, description } = Astro.props;
  ---
  ```
- **参照**: [Astro TypeScript Guide](https://docs.astro.build/en/guides/typescript/)

（問題がない場合は「Warnings はありません ✅」と明記）

---

## 💡 Info (ベストプラクティス提案)

### [I-001] Open Graphタグの追加推奨
- **ファイル**: `src/pages/index.astro`
- **カテゴリ**: SEO
- **提案**: SNSでシェアされた際の表示を改善するため、OGPタグの追加を推奨します。
- **メリット**: Twitter/Facebook等でのシェア時にリッチなプレビューが表示されます。
- **実装例**:
  ```astro
  <meta property="og:title" content={title} />
  <meta property="og:description" content={description} />
  <meta property="og:image" content={ogImage} />
  ```
- **参照**: [Astro SEO Guide](https://docs.astro.build/en/guides/seo/)

（提案がない場合は「追加の提案はありません」と明記）

---

## ✅ Good Practices Found

以下の良い実装パターンが確認されました：

- **TypeScript活用**: `src/components/Button.astro` で Props インターフェースが適切に定義されています
- **画像最適化**: `src/components/Gallery.astro` で `<Image />` コンポーネントが使用されています
- **アクセシビリティ**: `src/layouts/Base.astro` で `<html lang="ja">` が設定されています

（良い実装がない場合もこのセクションは省略せず、「特筆すべき Good Practices は見つかりませんでした」と記載）

---

## 📊 サマリー

### 問題数集計

| カテゴリ | Critical | Warning | Info |
|----------|----------|---------|------|
| Island Architecture | 0 | 1 | 0 |
| TypeScript | 0 | 2 | 0 |
| Image Optimization | 1 | 1 | 0 |
| Component Design | 0 | 0 | 1 |
| Data Fetching | 1 | 0 | 0 |
| SEO | 0 | 1 | 1 |
| Accessibility | 1 | 0 | 0 |
| Security | 0 | 0 | 0 |
| Performance | 0 | 0 | 1 |
| **Legacy API (5→6)** | 0 | 0 | 0 |
| **Astro 7 Migration (6→7)** | 0 | 0 | 0 |
| **Cloudflare** | 0 | 0 | 0 |
| **合計** | **3** | **5** | **3** |

### 総合評価

| 評価項目 | 状態 |
|----------|------|
| セキュリティ | ✅ 良好 |
| アクセシビリティ | 🚨 要対応（Critical 1件） |
| パフォーマンス | ⚠️ 要改善 |
| 型安全性 | ⚠️ 要改善 |
| SEO | ⚠️ 要改善 |
| レガシー API (5→6) | ✅ 良好 |
| Astro 7 移行 (6→7) | ✅ 良好 |
| Cloudflare 対応 | ✅ 良好 |

---

## 📚 参考資料

### Astro 7
- [Astro 公式ドキュメント](https://docs.astro.build/)
- [Astro 7 リリース記事](https://astro.build/blog/astro-7/)
- [Astro v7 Upgrade Guide](https://docs.astro.build/en/guides/upgrade-to/v7/)
- [Astro v6 Upgrade Guide（5→6 レガシー検出の出典）](https://docs.astro.build/en/guides/upgrade-to/v6/)
- [Island Architecture](https://docs.astro.build/en/concepts/islands/)
- [TypeScript Guide](https://docs.astro.build/en/guides/typescript/)
- [Image Guide](https://docs.astro.build/en/guides/images/)
- [Content Collections](https://docs.astro.build/en/guides/content-collections/)
- [CSP Configuration (security.csp)](https://docs.astro.build/en/reference/configuration-reference/#securitycsp)

### Cloudflare
- [Cloudflare Adapter](https://docs.astro.build/en/guides/integrations-guide/cloudflare/)
- [Route Caching](https://docs.astro.build/en/guides/caching/)
- [Cloudflare Workers](https://developers.cloudflare.com/workers/)
- [Wrangler Configuration](https://developers.cloudflare.com/workers/wrangler/configuration/)

---

*Generated by astro-code-review skill*
```

---

### Step 4: サマリー出力

レポート末尾のサマリーで以下を必ず含める:
- カテゴリ別の問題数集計テーブル
- 総合評価（✅良好 / ⚠️要改善 / 🚨要対応）
- 優先的に対応すべき項目のハイライト

---

### Step 5: エラー処理

| 状況 | 対応 |
|------|------|
| `.astro` ファイルが見つからない | 「指定されたパスに .astro ファイルが見つかりませんでした。パスを確認してください。」と通知 |
| ファイル読み取り権限エラー | Warning として報告し、該当ファイルをスキップして続行 |
| 構文解析不能なファイル | Warning として「{ファイル名} は解析できませんでした（構文エラーの可能性）」と報告し、続行 |
| Astroプロジェクトでない | 「このディレクトリは Astro プロジェクトではないようです。astro.config.mjs が見つかりません。続行しますか？」と確認

---

## 自動修正モード（--fix）

`--fix` オプション指定時、以下の安全な修正を自動適用:

### 自動修正対象（確認なしで適用）
| 問題 | 修正内容 |
|------|----------|
| `alt` 属性の欠如 | `alt="TODO: 画像の説明を追加"` を挿入 |
| `<html lang>` の欠如 | `<html lang="ja">` に変更 |
| `loading` 属性の欠如 | `loading="lazy"` を追加（Above-the-fold以外） |

### 確認後に適用
| 問題 | 修正内容 |
|------|----------|
| Props 型定義の欠如 | スケルトンの `interface Props {}` を生成（ユーザー確認後） |
| `<img>` → `<Image>` 変換 | import文追加と置換（ユーザー確認後） |

### 自動修正しない
- `set:html` のサニタイズ（ロジック変更が必要）
- `client:*` ディレクティブの変更（意図の確認が必要）
- null チェックの追加（ロジック変更が必要）

**注意**: 自動修正後は必ず `git diff` で変更内容を確認するよう促すこと

---

## 参考資料

### 内部リファレンス（詳細ガイド）
- `references/island-architecture.md` - Islandアーキテクチャ詳細・選択フローチャート
- `references/typescript-patterns.md` - TypeScript型パターン・Props定義
- `references/image-optimization.md` - 画像最適化・`<Image />`コンポーネント
- `references/data-fetching.md` - データ取得・エラーハンドリング
- `references/seo-a11y-security.md` - SEO/アクセシビリティ/セキュリティ
- `references/cloudflare-deployment.md` - Cloudflare Workers デプロイ・bindings・v14 移行検出

### 外部リファレンス
- [Astro公式ドキュメント](https://docs.astro.build/)
- [Astro 7 リリース記事](https://astro.build/blog/astro-7/)
- [Astro v7 Upgrade Guide](https://docs.astro.build/en/guides/upgrade-to/v7/)
- [Astro v6 Upgrade Guide（5→6 レガシー検出の出典）](https://docs.astro.build/en/guides/upgrade-to/v6/)
- [Astro Island Architecture](https://docs.astro.build/en/concepts/islands/)
- [Astro TypeScript Guide](https://docs.astro.build/en/guides/typescript/)
- [Astro Image Guide](https://docs.astro.build/en/guides/images/)
- [Content Collections](https://docs.astro.build/en/guides/content-collections/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

---

## CI/CD 統合ガイド

### GitHub Actions での使用例

```yaml
# .github/workflows/astro-review.yml
name: Astro Code Review

on:
  pull_request:
    paths:
      - 'src/**/*.astro'

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Astro Code Review
        # Claude Code CLI または MCP を使用
        run: |
          echo "Changed .astro files:"
          git diff --name-only ${{ github.event.pull_request.base.sha }} | grep '\.astro$' || true
```

### Pre-commit フック

```bash
#!/bin/bash
# .git/hooks/pre-commit

# 変更された .astro ファイルを検出
ASTRO_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.astro$')

if [ -n "$ASTRO_FILES" ]; then
  echo "🔍 Astro files changed, consider running: /astro-code-review"
  echo "$ASTRO_FILES"
fi
```

---

## バージョン履歴

| バージョン | 日付 | 変更内容 |
|------------|------|----------|
| 3.0.0 | 2026-07-05 | **Astro 7 / adapter v14 基準へ全面改修**: レガシー検出（5→6）と Astro 7 移行チェック（6→7）の二層化、Rust コンパイラ HTML 厳格化・Sätteri・src/fetch.ts・compressHTML・Vite 8・@astrojs/db 削除・astro:transitions 内部 API の検出を追加、Cloudflare Pages 廃止反映（Workers 一本化・platformProxy/main 旧値/.assetsignore の残骸検出・Route Caching 活用）、CSP を `security.csp` に是正、参照ドキュメントを `docs.astro.build`（v7 current）へ更新 |
| 2.0.0 | 2026-01-18 | **Astro 6.0+ 専用版**: Cloudflare メインデプロイ対応、新カテゴリ（Astro 6.0 Migration, Cloudflare）追加、削除API検出ルール追加、参照ドキュメントを v6.docs.astro.build に更新 |
| 1.1.0 | 2026-01-17 | 実行フロー詳細化、自動修正モード追加、CI/CD統合ガイド追加 |
| 1.0.0 | 2026-01-17 | 初版リリース |
