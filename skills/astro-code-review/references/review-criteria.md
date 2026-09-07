# レビュー観点 1〜9 の検出対象・ルール・修正例

`SKILL.md` の「レビュー観点（12カテゴリ）」から分離。Step 2 の静的解析でこのファイルを Read し、各観点の検出対象と修正例に沿って指摘する。観点 10〜12 は `migration-checks.md`。

## Contents

- 1. Islandアーキテクチャ検証
- 2. TypeScript型安全性
- 3. 画像・アセット最適化
- 4. コンポーネント設計
- 5. データ取得パターン
- 6. SEO・メタデータ
- 7. アクセシビリティ（a11y）
- 8. セキュリティ
- 9. パフォーマンス

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

詳細 → `island-architecture.md`

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

詳細 → `typescript-patterns.md`

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

詳細 → `image-optimization.md`

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

詳細 → `data-fetching.md`

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

詳細 → `seo-a11y-security.md`

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
