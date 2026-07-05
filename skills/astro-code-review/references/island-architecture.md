# Islandアーキテクチャ ガイド

Astro 7 の核となる Island アーキテクチャの詳細ガイド。Server Islands (`server:defer`) が**安定版**として利用可能。

> **対応バージョン**: Astro 7+

---

## 概要

Astroは「Islands Architecture」を採用し、ページの大部分を静的HTMLとして配信しつつ、必要な部分のみをインタラクティブな「島（Island）」として動的に動作させる。

## client:* ディレクティブ一覧

### client:load

**即座にハイドレーション**

```astro
<InteractiveNav client:load />
```

**適切な使用場面:**
- ナビゲーションメニュー
- 認証UI（ログイン/ログアウトボタン）
- 即時に操作が必要なフォーム
- Above-the-fold のインタラクティブ要素

**不適切な使用例:**
- 重いチャート/グラフコンポーネント
- フッター付近のニュースレター登録
- モーダル/ダイアログ（トリガー前は不要）

---

### client:visible

**ビューポートに入ったらハイドレーション**

```astro
<HeavyChart client:visible />
<ImageGallery client:visible />
```

**適切な使用場面:**
- スクロール位置より下のコンポーネント
- 重いビジュアライゼーション
- 画像ギャラリー
- コメントセクション

**内部動作:**
- IntersectionObserver API を使用
- rootMargin でプリロードタイミング調整可能

```astro
<HeavyChart client:visible={{rootMargin: "200px"}} />
```

---

### client:idle

**ブラウザがアイドル状態になったらハイドレーション**

```astro
<Newsletter client:idle />
<FeedbackWidget client:idle />
```

**適切な使用場面:**
- ニュースレター登録フォーム
- フィードバックウィジェット
- ソーシャルシェアボタン
- アナリティクストラッカー

**内部動作:**
- `requestIdleCallback` API を使用
- フォールバック: 200ms タイムアウト

---

### client:only="framework"

**サーバーでレンダリングせず、クライアントのみ**

```astro
<ClientOnlyComponent client:only="react" />
<VueComponent client:only="vue" />
```

**適切な使用場面:**
- ブラウザAPIに依存するコンポーネント（localStorage, window）
- SSRが困難なサードパーティライブラリ
- SEOが不要なインタラクティブ要素

**注意:**
- SEOに影響するコンテンツには使用禁止
- 初期表示でちらつきが発生する可能性

---

### client:media

**メディアクエリ条件でハイドレーション**

```astro
<MobileMenu client:media="(max-width: 768px)" />
<DesktopSidebar client:media="(min-width: 769px)" />
```

**適切な使用場面:**
- モバイル専用メニュー
- レスポンシブ対応のインタラクティブ要素
- 特定デバイスサイズでのみ必要な機能

---

## server:defer（Server Islands）- stable

**サーバーサイドでの遅延レンダリング**

> **Astro 6 で安定版になりました（v7 でも stable）。** 実験的フラグなしで使用可能です。

```astro
<UserAvatar server:defer />
<PersonalizedContent server:defer />
```

**適切な使用場面:**
- ユーザー固有のコンテンツ（アバター、名前）
- パーソナライズされたレコメンデーション
- Cookie/セッションに依存するコンテンツ
- 動的だがクライアントJSが不要な要素
- **Cloudflare Workers でのパーソナライズ**

**メリット:**
- クライアントJSなしで動的コンテンツ
- 初期ページロードをブロックしない
- キャッシュとの相性が良い
- **Cloudflare KV/D1 と組み合わせて高速パーソナライズ**

### Cloudflare での活用例

```astro
---
// src/components/UserGreeting.astro
import { env } from 'cloudflare:workers';

const userId = Astro.cookies.get('userId')?.value;
const userName = userId
  ? await env.MY_KV.get(`user:${userId}:name`)
  : null;
---

<div>
  {userName ? `ようこそ、${userName}さん` : 'ゲストさん'}
</div>
```

```astro
---
// src/pages/index.astro
import UserGreeting from '../components/UserGreeting.astro';
---

<html>
  <body>
    <!-- 静的コンテンツはすぐに配信 -->
    <h1>Welcome</h1>

    <!-- ユーザー情報は遅延取得 -->
    <UserGreeting server:defer />
  </body>
</html>
```

---

## 選択フローチャート

```
コンポーネントはインタラクティブ?
├─ No → 静的コンポーネントとしてレンダリング
└─ Yes
    ├─ サーバーでレンダリング可能?
    │   └─ No → client:only="framework"
    └─ Yes
        ├─ 即座に操作が必要?
        │   └─ Yes → client:load
        └─ No
            ├─ ビューポート外?
            │   └─ Yes → client:visible
            └─ No
                ├─ 低優先度?
                │   └─ Yes → client:idle
                └─ No
                    └─ 特定メディアクエリ? → client:media
```

---

## パフォーマンス比較

| ディレクティブ | 初期JSロード | ハイドレーションタイミング | 推奨度 |
|---------------|-------------|-------------------------|-------|
| なし（静的） | 0 KB | なし | 最高 |
| client:visible | 遅延 | スクロール時 | 高 |
| client:idle | 遅延 | アイドル時 | 高 |
| client:media | 条件付き | 条件一致時 | 中 |
| client:load | 即座 | ページロード時 | 低 |
| client:only | 即座 | ページロード時 | 最低 |

---

## アンチパターン

### 1. すべてに client:load を使用

```astro
// BAD: パフォーマンス低下
<Header client:load />
<Sidebar client:load />
<Footer client:load />
<Newsletter client:load />
```

### 2. 静的コンテンツの不必要なハイドレーション

```astro
// BAD: このコンポーネントにインタラクションがない場合
<StaticCard client:load />

// GOOD: 静的コンポーネントはディレクティブ不要
<StaticCard />
```

### 3. SEO重要コンテンツに client:only

```astro
// BAD: 検索エンジンがコンテンツを認識できない
<BlogContent client:only="react" />

// GOOD: SSRで配信
<BlogContent />
```

---

## 参考リンク

- [Astro Islands](https://docs.astro.build/en/concepts/islands/)
- [Client Directives](https://docs.astro.build/en/reference/directives-reference/#client-directives)
- [Server Islands](https://docs.astro.build/en/guides/server-islands/)
- [Cloudflare Adapter](https://docs.astro.build/en/guides/integrations-guide/cloudflare/)
