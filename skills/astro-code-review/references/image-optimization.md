# 画像最適化 ガイド

Astro 7 における画像最適化のベストプラクティス。Content Layer API に対応した画像スキーマとパフォーマンス最適化を解説。

> **対応バージョン**: Astro 7+

---

## astro:assets の基本

### Image コンポーネント

```astro
---
import { Image } from 'astro:assets';
import myImage from '../assets/hero.png';
---

<Image src={myImage} alt="Hero section image" />
```

**自動最適化:**
- WebP/AVIF への変換
- 適切なサイズへのリサイズ
- width/height の自動設定（CLS防止）
- loading="lazy" のデフォルト適用
- decoding="async" のデフォルト適用

---

## ローカル画像 vs リモート画像

### ローカル画像（推奨）

```astro
---
import { Image } from 'astro:assets';
import heroImage from '../assets/hero.png';
---

<!-- ビルド時に最適化 -->
<Image src={heroImage} alt="Hero" />
```

**メリット:**
- ビルド時に最適化
- 自動的な幅/高さ設定
- 型安全なインポート

### リモート画像

```astro
---
import { Image } from 'astro:assets';
---

<!-- 許可されたドメインが必要 -->
<Image
  src="https://example.com/image.png"
  alt="Remote image"
  width={800}
  height={600}
/>
```

**astro.config.mjs の設定:**
```javascript
export default defineConfig({
  image: {
    domains: ['example.com', 'cdn.example.com'],
    remotePatterns: [
      { protocol: 'https', hostname: '**.amazonaws.com' }
    ],
  },
});
```

---

## 必須属性

### alt 属性（Critical）

```astro
<!-- BAD: alt なし -->
<Image src={image} />

<!-- BAD: 空の alt（装飾画像以外では不適切） -->
<Image src={image} alt="" />

<!-- GOOD: 意味のある alt -->
<Image src={image} alt="赤いスニーカーを履いた人が公園を走っている" />

<!-- GOOD: 装飾画像の場合のみ空 alt -->
<Image src={decorativePattern} alt="" role="presentation" />
```

**alt テキストのガイドライン:**
- 画像の内容を具体的に説明
- 「画像」「写真」などの冗長な表現を避ける
- コンテキストに応じた説明
- 装飾画像は `alt=""` と `role="presentation"`

---

## サイズ指定

### 固定サイズ

```astro
<Image
  src={image}
  alt="Product thumbnail"
  width={300}
  height={200}
/>
```

### アスペクト比維持

```astro
<!-- ローカル画像の場合：width/height は自動推論される -->
<Image
  src={localImage}
  alt="Hero banner"
/>

<!-- リモート画像の場合：width のみ指定すればアスペクト比を維持 -->
<Image
  src="https://example.com/image.png"
  alt="Hero banner"
  width={1200}
  inferSize={true}
/>

<!-- または widthとheightを両方指定 -->
<Image
  src="https://example.com/image.png"
  alt="Hero banner"
  width={1200}
  height={675}
/>
```

### レスポンシブ画像

```astro
<Image
  src={image}
  alt="Responsive image"
  widths={[320, 640, 1280]}
  sizes="(max-width: 640px) 100vw, 50vw"
/>
```

---

## Picture コンポーネント

複数フォーマットやアートディレクション用。

```astro
---
import { Picture } from 'astro:assets';
import hero from '../assets/hero.png';
---

<Picture
  src={hero}
  alt="Hero image"
  formats={['avif', 'webp', 'png']}
  widths={[400, 800, 1200]}
  sizes="(max-width: 800px) 100vw, 50vw"
/>
```

**生成されるHTML:**
```html
<picture>
  <source type="image/avif" srcset="..." sizes="..." />
  <source type="image/webp" srcset="..." sizes="..." />
  <img src="..." alt="Hero image" ... />
</picture>
```

---

## getImage() 関数

プログラマティックな画像処理。

```astro
---
import { getImage } from 'astro:assets';
import background from '../assets/bg.png';

const optimizedBg = await getImage({
  src: background,
  width: 1920,
  format: 'webp',
  quality: 80,
});
---

<div style={`background-image: url(${optimizedBg.src})`}>
  <!-- コンテンツ -->
</div>
```

---

## パフォーマンス設定

### loading 属性

```astro
<!-- Above-the-fold: 即座に読み込み -->
<Image src={hero} alt="Hero" loading="eager" />

<!-- Below-the-fold: 遅延読み込み（デフォルト） -->
<Image src={card} alt="Card" loading="lazy" />
```

### decoding 属性

```astro
<!-- 非同期デコード（デフォルト、推奨） -->
<Image src={image} alt="Image" decoding="async" />

<!-- 同期デコード（Critical画像のみ） -->
<Image src={lcp} alt="LCP Image" decoding="sync" />
```

### fetchpriority 属性

```astro
<!-- LCP画像に高優先度 -->
<Image
  src={hero}
  alt="Hero"
  loading="eager"
  fetchpriority="high"
/>
```

---

## 画像フォーマット比較

| フォーマット | 圧縮率 | ブラウザサポート | 推奨用途 |
|-------------|--------|-----------------|---------|
| AVIF | 最高 | 限定的 | 最新ブラウザ向け |
| WebP | 高 | 広い | 一般的な画像 |
| PNG | 低 | 完全 | 透過画像 |
| JPEG | 中 | 完全 | 写真 |

---

## Content Layer API での画像

### スキーマ定義（Astro 7）

```typescript
// src/content.config.ts（旧 src/content/config.ts は 5→6 で廃止）
import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';  // ← astro:content ではなく astro/zod

const blog = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/blog' }),
  schema: ({ image }) => z.object({
    title: z.string(),
    cover: image().refine((img) => img.width >= 1080, {
      error: 'Cover image must be at least 1080px wide',  // Zod 4: message → error
    }),
    thumbnail: image().optional(),
  }),
});

export const collections = { blog };
```

### 使用例

```astro
---
import { Image } from 'astro:assets';
import { getEntry } from 'astro:content';

const post = await getEntry('blog', 'my-post');
---

<Image src={post.data.cover} alt={post.data.title} />
```

---

## アンチパターン

### 1. <img> タグの直接使用

```astro
<!-- BAD -->
<img src="/images/hero.png" alt="Hero" />

<!-- GOOD -->
<Image src={heroImage} alt="Hero" />
```

### 2. alt 属性の省略

```astro
<!-- BAD: a11y 違反 -->
<Image src={image} />

<!-- GOOD -->
<Image src={image} alt="Descriptive text" />
```

### 3. 過度に大きな画像

```astro
<!-- BAD: 4000px幅の画像を300pxで表示 -->
<Image src={hugeImage} alt="Thumbnail" width={300} />

<!-- GOOD: 適切なソース画像を使用 -->
<Image src={thumbnailImage} alt="Thumbnail" width={300} />
```

### 4. LCP画像に lazy loading

```astro
<!-- BAD: LCP が遅延 -->
<Image src={hero} alt="Hero" loading="lazy" />

<!-- GOOD: LCP は eager -->
<Image src={hero} alt="Hero" loading="eager" fetchpriority="high" />
```

---

## 参考リンク

- [Astro Images Guide](https://docs.astro.build/en/guides/images/)
- [Image Component Reference](https://docs.astro.build/en/reference/components-reference/#image)
- [astro:assets API](https://docs.astro.build/en/reference/modules/astro-assets/)
