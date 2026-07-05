# TypeScript型パターン ガイド

Astro 7 における TypeScript 活用のベストプラクティス。Content Layer API と Zod 4 に対応した型安全なパターンを解説。

> **対応バージョン**: Astro 7+, Zod 4.x (`import { z } from 'astro/zod'`。v7 で import 経路・バージョンとも変更なし)

---

## Props 型定義

### 基本パターン

```astro
---
interface Props {
  title: string;
  description?: string;
  publishDate: Date;
  tags: string[];
}

const { title, description, publishDate, tags } = Astro.props;
---
```

### type vs interface

```typescript
// interface - 拡張性が高い（推奨）
interface Props {
  title: string;
}

// type - ユニオン型などで有用
type Props = {
  title: string;
} | {
  name: string;
}
```

---

## HTMLAttributes の活用

### 標準HTML属性の継承

```astro
---
import type { HTMLAttributes } from 'astro/types';

interface Props extends HTMLAttributes<'a'> {
  isExternal?: boolean;
}

const { href, isExternal, ...attrs } = Astro.props;
---

<a
  href={href}
  target={isExternal ? '_blank' : undefined}
  rel={isExternal ? 'noopener noreferrer' : undefined}
  {...attrs}
>
  <slot />
</a>
```

### よく使う要素の型

```typescript
import type { HTMLAttributes } from 'astro/types';

// リンク
interface LinkProps extends HTMLAttributes<'a'> {}

// ボタン
interface ButtonProps extends HTMLAttributes<'button'> {}

// 入力
interface InputProps extends HTMLAttributes<'input'> {}

// 画像
interface ImageProps extends HTMLAttributes<'img'> {}

// div
interface ContainerProps extends HTMLAttributes<'div'> {}
```

---

## Content Layer API の型安全性

Astro の Content Collections は **Content Layer API**（loader ベース）で定義する。

### スキーマ定義（Astro 7）

```typescript
// src/content.config.ts（旧 src/content/config.ts は 5→6 で廃止）
import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';  // ← astro:content ではなく astro/zod

const blog = defineCollection({
  // type: 'content' は廃止、loader を使用
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    publishDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    author: z.string().default('Anonymous'),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
    image: z.object({
      src: z.string(),
      alt: z.string(),
    }).optional(),
  }),
});

export const collections = { blog };
```

### Zod 4 の変更点

```typescript
import { z } from 'astro/zod';

// Zod 4 での変更（Astro 6 で Zod 4 導入。v7 でも Zod 4.x のまま）
const schema = z.object({
  // ✅ Zod 4 の新しいバリデーター
  email: z.email(),        // z.string().email() から変更
  url: z.url(),            // z.string().url() から変更
  uuid: z.uuid(),          // z.string().uuid() から変更

  // ✅ エラーメッセージの指定方法
  name: z.string().min(1, { error: "必須項目です" }),  // { message } → { error }
});
```

### 型の活用

```astro
---
import { getCollection, type CollectionEntry } from 'astro:content';

// 型安全なコレクション取得
const posts: CollectionEntry<'blog'>[] = await getCollection('blog',
  ({ data }) => !data.draft
);

// 単一エントリの型
interface Props {
  post: CollectionEntry<'blog'>;
}
---
```

---

## カスタム型の拡張

### グローバルJSX属性の拡張

```typescript
// src/env.d.ts
declare namespace astroHTML.JSX {
  interface HTMLAttributes {
    // カスタムdata属性
    'data-testid'?: string;
    'data-tracking'?: string;

    // HTMX属性
    'hx-get'?: string;
    'hx-post'?: string;
    'hx-trigger'?: string;
    'hx-swap'?: string;
  }

  interface CSSProperties {
    // カスタムCSS変数
    '--primary-color'?: string;
    '--spacing'?: string;
  }
}
```

---

## レイアウト・ページの型

### レイアウトコンポーネント

```astro
---
// src/layouts/BaseLayout.astro
interface Props {
  title: string;
  description?: string;
  image?: string;
  noIndex?: boolean;
}

const {
  title,
  description = 'Default description',
  image = '/og-default.png',
  noIndex = false,
} = Astro.props;
---
```

### ページファイル

```astro
---
// src/pages/blog/[slug].astro
import type { GetStaticPaths, InferGetStaticPropsType } from 'astro';
import { getCollection, render } from 'astro:content';

export const getStaticPaths = (async () => {
  const posts = await getCollection('blog');
  return posts.map((post) => ({
    params: { slug: post.id },
    props: { post },
  }));
}) satisfies GetStaticPaths;

type Props = InferGetStaticPropsType<typeof getStaticPaths>;

const { post } = Astro.props;
const { Content } = await render(post);
---
```

---

## 厳格な型チェック設定

### tsconfig.json

```json
{
  "extends": "astro/tsconfigs/strict",
  "compilerOptions": {
    "strictNullChecks": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

### 推奨設定レベル

| 設定 | base | strict | strictest |
|------|------|--------|-----------|
| strictNullChecks | ❌ | ✅ | ✅ |
| strict | ❌ | ✅ | ✅ |
| noImplicitAny | ❌ | ✅ | ✅ |
| noUncheckedIndexedAccess | ❌ | ❌ | ✅ |
| exactOptionalPropertyTypes | ❌ | ❌ | ✅ |

---

## 型エラー回避パターン

### null/undefined チェック

```astro
---
const post = await getEntry('blog', slug);

// BAD: post が undefined の可能性
const { Content } = await render(post);

// GOOD: nullチェック
if (!post) {
  return Astro.redirect('/404');
}
const { Content } = await render(post);
---
```

### オプショナルチェイン

```astro
---
interface Props {
  user?: {
    name: string;
    avatar?: string;
  };
}

const { user } = Astro.props;
---

<div>
  {user?.name ?? 'Guest'}
  {user?.avatar && <img src={user.avatar} alt={user.name} />}
</div>
```

---

## アンチパターン

### 1. any の使用

```typescript
// BAD
const { data } = Astro.props as any;

// GOOD
interface Props {
  data: DataType;
}
const { data } = Astro.props;
```

### 2. 型アサーションの乱用

```typescript
// BAD
const post = (await getEntry('blog', slug))!;

// GOOD
const post = await getEntry('blog', slug);
if (!post) return Astro.redirect('/404');
```

### 3. 型定義の省略

```astro
---
// BAD: 暗黙のany
const { title, items } = Astro.props;

// GOOD: 明示的な型定義
interface Props {
  title: string;
  items: Item[];
}
const { title, items } = Astro.props;
---
```

---

## 参考リンク

- [Astro TypeScript Guide](https://docs.astro.build/en/guides/typescript/)
- [Content Layer API](https://docs.astro.build/en/guides/content-collections/)
- [TypeScript Configuration](https://docs.astro.build/en/guides/typescript/#type-checking)
- [Zod 4 Changelog](https://zod.dev/v4/changelog)
