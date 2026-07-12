# astro-code-review

**Astro 7+（GA）専用**のコードレビュースキルです。Cloudflare **Workers**（static assets 付き）をメインのデプロイ先として想定し、Astro プロジェクトのコードを体系的にレビューして、ベストプラクティス違反・パフォーマンス問題・アクセシビリティ欠陥・型安全性の欠如・レガシー API（Astro 5/6 で削除済みのパターン）・Astro 7 移行問題（Rust コンパイラの HTML 厳格化・Sätteri・`src/fetch.ts` 予約名ほか）を検出します。

---

## 対応環境

| 項目 | バージョン |
|------|-----------|
| Astro | 7.0.0+（GA） |
| Node.js | 22.12.0+（`astro@7` の engines。奇数メジャー非対応） |
| デプロイ先 | Cloudflare Workers（static assets 付き。Pages は非対応） |
| アダプター | @astrojs/cloudflare v14+ |
| wrangler | ^4.83.0+（adapter v14 の peer 要件） |
| Zod | 4.x（`import { z } from 'astro/zod'`。v7 で変更なし） |

> **注意**: 検出は二層構成です。Astro 5.x/6.x 時代の削除済み API は**レガシー検出**、Astro 6 → 7 の破壊的変更は**Astro 7 移行チェック**として扱います。**Cloudflare Pages サポートはアダプター v13 で廃止済み**（デプロイ先は Workers 一本）。

---

## インストール

このリポジトリを clone し、スキル本体（`skills/astro-code-review`）を各エージェントのスキルディレクトリへ **symlink** します。実体は 1 つ、参照を複数張る方式です。当環境では「実体 → `~/.agents` → `~/.claude`」の 2 段 symlink で統一しています。

```bash
# 1) リポジトリを取得
git clone git@github.com:takunagai/agent-assets.git ~/Projects/agent-assets

# 2) ハブ（~/.agents）から実体へ絶対 symlink
ln -s /Users/$USER/Projects/agent-assets/skills/astro-code-review ~/.agents/skills/astro-code-review

# 3) Claude Code 用に ~/.agents への相対 symlink
ln -s ../../.agents/skills/astro-code-review ~/.claude/skills/astro-code-review
```

> Codex など他のエージェントは `~/.agents/skills/astro-code-review` を直接読みます。Claude Code は `~/.claude/skills/` を経由して同じ実体を参照します。

スキル本体の構成は次の通りです（人間用マニュアルである本ファイルは、スキル本体の外＝`docs/` に置いています）。

```
skills/astro-code-review/
├── SKILL.md          # スキル定義（Claude がトリガー時に読む）
├── references/       # 観点別の詳細リファレンス（progressive disclosure）
│   ├── island-architecture.md
│   ├── typescript-patterns.md
│   ├── image-optimization.md
│   ├── data-fetching.md
│   ├── seo-a11y-security.md
│   └── cloudflare-deployment.md
├── assets/
│   └── review-report-template.md   # レビューレポートの出力テンプレート
└── tests/            # レビュー検証用の .astro フィクスチャ（基本 / Island / データ取得 / Astro 7 移行）
```

---

## クイックスタート

```bash
# カレントディレクトリの全 .astro ファイルをレビュー
/astro-code-review

# 特定ディレクトリをレビュー
/astro-code-review src/pages/

# 特定ファイルをレビュー
/astro-code-review src/components/Header.astro
```

自然言語でも発動します。「Astro のコードをレビューして」「この Astro コンポーネントをチェックして」「Astro プロジェクトの品質を確認して」など。

---

## 主な機能

- **12 カテゴリ**のレビュー観点（Island、TypeScript、画像、SEO、a11y、セキュリティ、**Legacy API (5→6)**、**Astro 7 Migration (6→7)**、**Cloudflare** 等）
- **3 段階の重要度分類**（Critical / Warning / Info）
- **具体的な修正例**付きのレポート出力
- **自動修正モード**（`--fix`）で安全な修正を適用
- **レガシー API 検出（5→6）**: 削除 API（`Astro.glob()`、`<ViewTransitions />`、legacy Content Collections 等）の検出
- **Astro 7 移行チェック（6→7）**: Rust コンパイラの HTML 厳格化（未クローズ・不正ネスト）、Sätteri 非互換の remark/rehype、`src/fetch.ts` 予約名、`compressHTML: 'jsx'`、Vite 8、`@astrojs/db` 削除、`astro:transitions` 内部 API の検出
- **Cloudflare Workers 最適化**: `cloudflare:workers` パターン、Node.js 非互換 API、`platformProxy`/`main` 旧値/`.assetsignore` の残骸、Route Caching（`cacheCloudflare()`）の検出

---

## オプション

| オプション | 説明 |
|------------|------|
| `--severity=critical` | Critical のみ検出 |
| `--fix` | 安全な修正を自動適用 |

---

## レビュー観点

| カテゴリ | 検出例 |
|----------|--------|
| Island Architecture | 不適切な `client:*` 選択 |
| TypeScript | Props 型定義の欠如 |
| Image Optimization | `alt` 属性の欠如、`<img>` 直接使用 |
| Data Fetching | `getEntry()` の null チェック欠如 |
| SEO | `<title>`、OGP タグの欠如 |
| Accessibility | `<html lang>` 欠如、見出し階層 |
| Security | `set:html` の未サニタイズ使用 |
| **Legacy API (5→6)** | `Astro.glob()`、`<ViewTransitions />`、legacy Content Collections |
| **Astro 7 Migration (6→7)** | 未クローズ/不正ネスト、Sätteri 非互換の remark/rehype、`src/fetch.ts` 予約名、`compressHTML: 'jsx'` |
| **Cloudflare** | `Astro.locals.runtime`、Node.js 専用 API、`platformProxy`/`main` 旧値の残骸 |

---

## 詳細

詳細な仕様・実行フロー・観点別リファレンスは、スキル本体の `SKILL.md` および `references/*.md` を参照してください。

## 外部リファレンス

最新仕様の確認は、接続済みなら `cloudflare-docs` MCP 検索（認証不要）を第一手段とする。

- [Astro 7 リリース記事](https://astro.build/blog/astro-7/)
- [Astro v7 Upgrade Guide](https://docs.astro.build/en/guides/upgrade-to/v7/)
- [Astro v6 Upgrade Guide（5→6 レガシー検出の出典）](https://docs.astro.build/en/guides/upgrade-to/v6/)
- [Cloudflare Adapter](https://docs.astro.build/en/guides/integrations-guide/cloudflare/)
