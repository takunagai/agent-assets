# データ取得パターン ガイド

Astro 7 におけるデータ取得のベストプラクティス。Content Layer API と Live Collections を活用した最新パターンを解説。

> **対応バージョン**: Astro 7+, @astrojs/cloudflare v14+

---

## Content Layer API

Astro の Content Collections は **Content Layer API**（loader ベース）で定義する。設定ファイルは `src/content.config.ts`（旧 `src/content/config.ts` は 5→6 で廃止済み）。

```typescript
// src/content.config.ts
import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    pubDate: z.coerce.date(),
    draft: z.boolean().default(false),
  }),
});

export const collections = { blog };
```

---

## Content Collections

### getCollection()

**コレクション全体の取得**

```astro
---
import { getCollection } from 'astro:content';

// 全記事を取得
const allPosts = await getCollection('blog');

// フィルタリング付き
const publishedPosts = await getCollection('blog', ({ data }) => {
  return !data.draft && data.publishDate <= new Date();
});

// ソート
const sortedPosts = publishedPosts.sort(
  (a, b) => b.data.publishDate.valueOf() - a.data.publishDate.valueOf()
);
---
```

### getEntry()

**単一エントリの取得**

```astro
---
import { getEntry, render } from 'astro:content';

const post = await getEntry('blog', 'my-first-post');

// Critical: null チェック必須
if (!post) {
  return Astro.redirect('/404');
}

const { Content, headings } = await render(post);
---

<article>
  <h1>{post.data.title}</h1>
  <Content />
</article>
```

---

## SSG vs SSR

### 静的生成（SSG）

```astro
---
// src/pages/blog/[slug].astro
import { getCollection, render } from 'astro:content';

export async function getStaticPaths() {
  const posts = await getCollection('blog');
  return posts.map((post) => ({
    params: { slug: post.id },
    props: { post },
  }));
}

const { post } = Astro.props;
const { Content } = await render(post);
---
```

### サーバーサイドレンダリング（SSR）

```astro
---
// src/pages/blog/[slug].astro
export const prerender = false;

import { getEntry, render } from 'astro:content';

const { slug } = Astro.params;

// パラメータチェック
if (!slug) {
  return Astro.redirect('/404');
}

const post = await getEntry('blog', slug);

// エントリチェック
if (!post) {
  return Astro.redirect('/404');
}

const { Content } = await render(post);
---
```

---

## エラーハンドリング

### パターン1: 404リダイレクト

```astro
---
const post = await getEntry('blog', slug);

if (!post) {
  return Astro.redirect('/404');
}
---
```

### パターン2: カスタムエラーページ

```astro
---
const post = await getEntry('blog', slug);

if (!post) {
  Astro.response.status = 404;
  return Astro.redirect('/404', 404);
}
---
```

### パターン3: インラインエラー表示

```astro
---
let post;
let error;

try {
  post = await getEntry('blog', slug);
  if (!post) {
    error = 'Post not found';
  }
} catch (e) {
  error = 'Failed to load post';
}
---

{error ? (
  <div class="error">{error}</div>
) : (
  <article>
    <Content />
  </article>
)}
```

---

## Live Collections（stable）

Live Collections は Astro 6 で**安定版**になり（5.10 で experimental 導入）、v7 でも stable。CMS やデータベースからリアルタイムにデータを取得する際に使用します。

### defineLiveCollection()

```typescript
// src/content.config.ts
import { defineCollection, defineLiveCollection } from 'astro:content';
import { z } from 'astro/zod';

// 外部 CMS からのライブデータ
const products = defineLiveCollection({
  schema: z.object({
    id: z.string(),
    name: z.string(),
    price: z.number(),
    description: z.string().optional(),
  }),
  load: async () => {
    const response = await fetch('https://api.example.com/products');
    return response.json();
  },
});

export const collections = { products };
```

### getLiveEntry()

```astro
---
// src/pages/products/[id].astro
export const prerender = false;

import { getLiveEntry } from 'astro:content';

const { id } = Astro.params;
const { entry, error } = await getLiveEntry('products', id);

if (error) {
  return Astro.redirect('/404');
}
---

<h1>{entry.data.name}</h1>
<p>価格: ¥{entry.data.price.toLocaleString()}</p>
```

### getLiveCollection()

```astro
---
export const prerender = false;

import { getLiveCollection } from 'astro:content';

const { entries, error } = await getLiveCollection('products');

if (error) {
  console.error('Failed to load products:', error);
}
---

<ul>
  {entries?.map((product) => (
    <li>
      <a href={`/products/${product.id}`}>{product.data.name}</a>
    </li>
  ))}
</ul>
```

### LiveEntryNotFoundError

```astro
---
export const prerender = false;

import { getLiveEntry, LiveEntryNotFoundError } from 'astro:content';

const { entry, error } = await getLiveEntry('products', Astro.params.id);

if (error) {
  if (LiveEntryNotFoundError.is(error)) {
    console.error(`Product not found: ${error.message}`);
    Astro.response.status = 404;
  } else {
    console.error(`Error loading product: ${error.message}`);
    return Astro.redirect('/500');
  }
}
---
```

---

## Cloudflare Bindings 連携

Cloudflare Workers でのデータ取得パターン。

### KV からのデータ取得

```astro
---
export const prerender = false;

import { env } from 'cloudflare:workers';

const slug = Astro.params.slug;
const cached = await env.MY_KV.get(`post:${slug}`, { type: 'json' });

if (cached) {
  // キャッシュヒット
  var post = cached;
} else {
  // フォールバック: Content Collections から取得
  const { getEntry } = await import('astro:content');
  post = await getEntry('blog', slug);

  // KV にキャッシュ（1時間）
  if (post) {
    await env.MY_KV.put(`post:${slug}`, JSON.stringify(post), {
      expirationTtl: 3600,
    });
  }
}
---
```

### D1 Database クエリ

```astro
---
export const prerender = false;

import { env } from 'cloudflare:workers';

const { slug } = Astro.params;

const result = await env.MY_DB
  .prepare('SELECT * FROM posts WHERE slug = ? AND published = 1')
  .bind(slug)
  .first();

if (!result) {
  return Astro.redirect('/404');
}
---

<article>
  <h1>{result.title}</h1>
  <div set:html={result.content} />
</article>
```

### R2 からファイル取得

```astro
---
export const prerender = false;

import { env } from 'cloudflare:workers';

const { key } = Astro.params;
const object = await env.MY_BUCKET.get(key);

if (!object) {
  return new Response('Not Found', { status: 404 });
}

const content = await object.text();
---
```

---

## 外部API フェッチ

### 基本パターン

```astro
---
const response = await fetch('https://api.example.com/data');

if (!response.ok) {
  throw new Error(`HTTP error! status: ${response.status}`);
}

const data = await response.json();
---
```

### 型安全なフェッチ

```astro
---
interface ApiResponse {
  id: number;
  title: string;
  content: string;
}

const response = await fetch('https://api.example.com/posts/1');
const post: ApiResponse = await response.json();
---
```

### エラーハンドリング付き

```astro
---
interface Post {
  id: number;
  title: string;
}

let posts: Post[] = [];
let error: string | null = null;

try {
  const response = await fetch('https://api.example.com/posts');
  if (!response.ok) {
    throw new Error(`Failed to fetch: ${response.status}`);
  }
  posts = await response.json();
} catch (e) {
  error = e instanceof Error ? e.message : 'Unknown error';
  console.error('Fetch error:', e);
}
---

{error ? (
  <p class="error">{error}</p>
) : (
  <ul>
    {posts.map((post) => (
      <li key={post.id}>{post.title}</li>
    ))}
  </ul>
)}
```

---

## データ取得の最適化

### 並列フェッチ

```astro
---
// BAD: 直列実行
const posts = await getCollection('blog');
const authors = await getCollection('authors');
const categories = await getCollection('categories');

// GOOD: 並列実行
const [posts, authors, categories] = await Promise.all([
  getCollection('blog'),
  getCollection('authors'),
  getCollection('categories'),
]);
---
```

### 参照の解決

```astro
---
import { getCollection, getEntry } from 'astro:content';

const posts = await getCollection('blog');

// 著者情報を並列で取得
const postsWithAuthors = await Promise.all(
  posts.map(async (post) => {
    const author = await getEntry(post.data.author);
    return { ...post, author };
  })
);
---
```

---

## キャッシュ戦略

### レスポンスヘッダー（SSR）

```astro
---
export const prerender = false;

// キャッシュヘッダーを設定
Astro.response.headers.set(
  'Cache-Control',
  'public, max-age=3600, s-maxage=86400'
);

const data = await fetchData();
---
```

### Stale-While-Revalidate

```astro
---
Astro.response.headers.set(
  'Cache-Control',
  'public, max-age=60, stale-while-revalidate=3600'
);
---
```

---

## アンチパターン

### 1. null チェックの欠如

```astro
// BAD: post が undefined の可能性
---
const post = await getEntry('blog', slug);
const { Content } = await render(post); // エラー!
---

// GOOD
---
const post = await getEntry('blog', slug);
if (!post) {
  return Astro.redirect('/404');
}
const { Content } = await render(post);
---
```

### 2. 直列フェッチ（独立データ）

```astro
// BAD: 不必要に遅い
---
const posts = await getCollection('blog');
const products = await getCollection('products');
---

// GOOD: 並列実行
---
const [posts, products] = await Promise.all([
  getCollection('blog'),
  getCollection('products'),
]);
---
```

### 3. クライアントサイドでの機密データフェッチ

```astro
// BAD: クライアントに露出
<script>
  const response = await fetch('/api/data', {
    headers: { 'Authorization': 'Bearer secret-token' }
  });
</script>

// GOOD: サーバーサイドでフェッチ
---
const data = await fetch('https://api.example.com/data', {
  headers: { 'Authorization': `Bearer ${import.meta.env.SECRET_API_KEY}` }
}).then(r => r.json());
---
<div>{JSON.stringify(data)}</div>
```

### 4. エラー状態の無視

```astro
// BAD: エラーを無視
---
const response = await fetch(url);
const data = await response.json();
---

// GOOD: エラーハンドリング
---
const response = await fetch(url);
if (!response.ok) {
  console.error(`Fetch failed: ${response.status}`);
  return Astro.redirect('/error');
}
const data = await response.json();
---
```

---

## 参考リンク

- [Content Layer API](https://docs.astro.build/en/guides/content-collections/)
- [Data Fetching](https://docs.astro.build/en/guides/data-fetching/)
- [SSR Adapters](https://docs.astro.build/en/guides/on-demand-rendering/)
- [Cloudflare Adapter](https://docs.astro.build/en/guides/integrations-guide/cloudflare/)
- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)
