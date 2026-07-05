# SEO・アクセシビリティ・セキュリティ ガイド

Astro 7 における SEO、アクセシビリティ（a11y）、セキュリティのベストプラクティス。組み込み CSP 機能（`security.csp`）と Cloudflare 連携を解説。

> **対応バージョン**: Astro 7+, @astrojs/cloudflare v14+

---

## SEO（検索エンジン最適化）

### 必須メタタグ

```astro
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} | サイト名</title>
  <meta name="description" content={description} />
  <link rel="canonical" href={canonicalURL} />
</head>
```

### Open Graph タグ

```astro
<head>
  <!-- 基本 OGP -->
  <meta property="og:title" content={title} />
  <meta property="og:description" content={description} />
  <meta property="og:type" content="website" />
  <meta property="og:url" content={canonicalURL} />
  <meta property="og:image" content={ogImage} />
  <meta property="og:site_name" content="サイト名" />
  <meta property="og:locale" content="ja_JP" />

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:site" content="@username" />
  <meta name="twitter:title" content={title} />
  <meta name="twitter:description" content={description} />
  <meta name="twitter:image" content={ogImage} />
</head>
```

### 構造化データ（JSON-LD）

```astro
---
const structuredData = {
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": title,
  "description": description,
  "author": {
    "@type": "Person",
    "name": authorName,
  },
  "datePublished": publishDate,
  "dateModified": updatedDate,
  "image": ogImage,
};
---

<script type="application/ld+json" set:html={JSON.stringify(structuredData)} />
```

### サイトマップ

```javascript
// astro.config.mjs
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://example.com',
  integrations: [sitemap()],
});
```

### robots.txt

```
// public/robots.txt
User-agent: *
Allow: /

Sitemap: https://example.com/sitemap-index.xml
```

---

## アクセシビリティ（a11y）

### 必須要件

#### 1. 言語設定

```astro
<!-- Critical: lang 属性必須 -->
<html lang="ja">
```

#### 2. セマンティックHTML

```astro
<!-- BAD: div だらけ -->
<div class="header">
  <div class="nav">...</div>
</div>
<div class="content">...</div>
<div class="footer">...</div>

<!-- GOOD: セマンティック要素 -->
<header>
  <nav>...</nav>
</header>
<main>
  <article>...</article>
</main>
<footer>...</footer>
```

#### 3. 見出し階層

```astro
<!-- BAD: 階層が飛んでいる -->
<h1>タイトル</h1>
<h3>サブセクション</h3>  <!-- h2 をスキップ -->

<!-- GOOD: 適切な階層 -->
<h1>タイトル</h1>
<h2>セクション</h2>
<h3>サブセクション</h3>
```

#### 4. 画像の alt テキスト

```astro
<!-- Critical: alt 必須 -->
<Image src={photo} alt="東京タワーの夜景" />

<!-- 装飾画像の場合 -->
<Image src={decoration} alt="" role="presentation" />
```

#### 5. フォームラベル

```astro
<!-- BAD: ラベルなし -->
<input type="email" placeholder="メールアドレス" />

<!-- GOOD: ラベルあり -->
<label for="email">メールアドレス</label>
<input type="email" id="email" name="email" />

<!-- または -->
<label>
  メールアドレス
  <input type="email" name="email" />
</label>
```

#### 6. キーボードナビゲーション

```astro
<!-- インタラクティブ要素にはフォーカス可能に -->
<button type="button" onclick="handleClick()">
  クリック
</button>

<!-- カスタム要素の場合 -->
<div
  role="button"
  tabindex="0"
  onkeydown="handleKeyPress(event)"
  onclick="handleClick()"
>
  カスタムボタン
</div>
```

### ARIA 属性

```astro
<!-- モーダル -->
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby="modal-title"
>
  <h2 id="modal-title">確認</h2>
</div>

<!-- 展開/折りたたみ -->
<button
  aria-expanded={isOpen}
  aria-controls="panel-id"
>
  詳細を見る
</button>
<div id="panel-id" hidden={!isOpen}>
  詳細内容
</div>

<!-- ライブリージョン -->
<div role="alert" aria-live="polite">
  保存しました
</div>
```

### スキップリンク

```astro
<body>
  <a href="#main-content" class="skip-link">
    メインコンテンツへスキップ
  </a>
  <header>...</header>
  <main id="main-content">...</main>
</body>

<style>
  .skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    padding: 8px;
    background: #000;
    color: #fff;
    z-index: 100;
  }
  .skip-link:focus {
    top: 0;
  }
</style>
```

---

## セキュリティ

### set:html の安全な使用

```astro
<!-- DANGER: 未サニタイズのユーザー入力 -->
<div set:html={userInput} />

<!-- SAFE: 信頼できるソースからのみ -->
---
import { marked } from 'marked';
import DOMPurify from 'isomorphic-dompurify';

// Markdown をパースしてサニタイズ
const rawHtml = marked(trustedMarkdown);
const safeHtml = DOMPurify.sanitize(rawHtml);
---
<div set:html={safeHtml} />
```

### 環境変数

```astro
---
// SAFE: サーバーサイドで使用
const apiKey = import.meta.env.SECRET_API_KEY;
const data = await fetchWithAuth(apiKey);
---

<!-- DANGER: クライアントに露出 -->
<script>
  // NG: 機密情報がクライアントに漏洩
  const key = "{import.meta.env.SECRET_API_KEY}";
</script>

<!-- SAFE: 公開用の環境変数 -->
<script>
  const analyticsId = "{import.meta.env.PUBLIC_ANALYTICS_ID}";
</script>
```

**命名規則:**
- `SECRET_*` または プレフィックスなし → サーバーのみ
- `PUBLIC_*` → クライアント公開OK

### Content Security Policy（`security.csp` ─ 組み込み機能・stable）

CSP は `security.csp` として提供される組み込み機能（`astro@6.0.0` で追加、`Default: false`、v7 でも stable）。**設定パスは `security.csp`**（トップレベルの `csp:` ではない）。`directives` は文字列の配列で指定する。

#### 基本設定

```javascript
// astro.config.mjs
import { defineConfig } from 'astro/config';

export default defineConfig({
  security: {
    csp: {
      directives: [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' https://cdn.example.com",
        "font-src 'self' https://fonts.gstatic.com",
        "connect-src 'self' https://api.example.com",
      ],
    },
  },
});
```

#### ハッシュ自動生成

Astro はインラインスクリプト/スタイルのハッシュを**自動生成**する。`scriptDirective` / `styleDirective` で追加のハッシュ・リソースを指定できる。

```javascript
// astro.config.mjs
export default defineConfig({
  security: {
    csp: {
      algorithm: 'SHA-256',
      // インラインスクリプト/スタイルのハッシュは自動生成される
      scriptDirective: { strictDynamic: false },
      styleDirective: { resources: ["'self'"] },
    },
  },
});
```

#### Cloudflare 連携

```javascript
// astro.config.mjs
import cloudflare from '@astrojs/cloudflare';

export default defineConfig({
  output: 'server',
  adapter: cloudflare(),
  security: {
    csp: {
      directives: [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        // Cloudflare Analytics
        "connect-src 'self' https://cloudflareinsights.com",
      ],
    },
  },
});
```

#### 従来の middleware 方式（非推奨）

```typescript
// src/middleware.ts（組み込みの security.csp を推奨）
import { defineMiddleware } from 'astro:middleware';

export const onRequest = defineMiddleware(async (context, next) => {
  const response = await next();

  // ❌ 非推奨: 手動での CSP ヘッダー設定
  response.headers.set(
    'Content-Security-Policy',
    "default-src 'self';"
  );

  return response;
});
```

### XSS 防止

```astro
<!-- Astro はデフォルトでエスケープ -->
<p>{userInput}</p>  <!-- 安全: 自動エスケープ -->

<!-- 危険: set:html はエスケープしない -->
<p set:html={userInput} />  <!-- 危険! -->

<!-- 安全: サニタイズ後に使用 -->
<p set:html={DOMPurify.sanitize(userInput)} />
```

### CSRF 対策（フォーム）

```astro
---
// トークン生成
const csrfToken = crypto.randomUUID();
Astro.cookies.set('csrf', csrfToken, {
  httpOnly: true,
  secure: true,
  sameSite: 'strict',
});
---

<form method="POST" action="/api/submit">
  <input type="hidden" name="csrf" value={csrfToken} />
  <!-- フォーム内容 -->
</form>
```

### セキュリティヘッダー

```typescript
// src/middleware.ts
export const onRequest = defineMiddleware(async (context, next) => {
  const response = await next();

  // セキュリティヘッダー
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');

  return response;
});
```

---

## チェックリスト

### SEO チェックリスト
- [ ] `<title>` が設定されている
- [ ] `<meta name="description">` が設定されている
- [ ] `<link rel="canonical">` が設定されている
- [ ] Open Graph タグが設定されている
- [ ] 構造化データ（JSON-LD）が設定されている
- [ ] サイトマップが生成されている
- [ ] robots.txt が配置されている

### a11y チェックリスト
- [ ] `<html lang="ja">` が設定されている
- [ ] 見出し階層が適切（h1→h2→h3）
- [ ] セマンティックHTML要素を使用
- [ ] 全画像に意味のある alt テキスト
- [ ] フォーム要素にラベルが関連付け
- [ ] キーボードでナビゲーション可能
- [ ] コントラスト比が十分（4.5:1 以上）
- [ ] フォーカス状態が視覚的に明確

### セキュリティ チェックリスト
- [ ] `set:html` にユーザー入力を直接渡していない
- [ ] 機密情報を `PUBLIC_*` 以外の環境変数で管理
- [ ] フォームに CSRF トークンを使用
- [ ] セキュリティヘッダーを設定
- [ ] 外部スクリプトの整合性を検証（SRI）

---

## 参考リンク

### SEO
- [Astro SEO Guide](https://docs.astro.build/en/guides/seo/)
- [Google Search Central](https://developers.google.com/search)

### アクセシビリティ
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)

### セキュリティ
- [Astro CSP Configuration (security.csp)](https://docs.astro.build/en/reference/configuration-reference/#securitycsp)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [MDN Web Security](https://developer.mozilla.org/en-US/docs/Web/Security)
- [Cloudflare Workers Security](https://developers.cloudflare.com/workers/configuration/security/)
