# emdash-cms

**EmDash**（Cloudflare 発の TypeScript / Astro ベース CMS。WordPress の精神的後継・MIT ライセンス）のセットアップ・構成・運用スキルです。管理画面（Portable Text エディタ・スキーマビルダー・メディア管理）と、Astro プロジェクトへのコンテンツ配信を 1 パッケージで担う CMS を対象に、新規サイト作成から既存 Astro への統合、コンテンツモデリング、プラグイン開発、メール・フォーム、WordPress 移行までを扱います。

---

## 適用範囲と鮮度に関する注意

本スキルは **emdash 0.29.0（2026-07-10 リリース）/ 2026-07-13 検証**を基準としています。EmDash は **v0.x の早期ベータ**で、API・CLI・設定が数ヶ月単位で大きく変わります。作業前に必ず次を実行し、基準バージョンとのズレを確認してください。

```bash
pnpm view emdash version          # 現行の最新版を確認
pnpm view create-emdash version   # スキャフォールダも同時に確認
```

GitHub の releases（https://github.com/emdash-cms/emdash/releases）でメジャーな変更も確認します。基準（0.29.x）とメジャー／マイナーがずれている場合、スキルのコード例をそのまま使わず、公式ドキュメント（https://docs.emdashcms.com）で該当 API を裏取りしてから進める運用です。

> デプロイの実行自体は Astro + Cloudflare Workers 構成なので、既存スキル `deploy-astro-cloudflare` に委譲します。本スキルは構成まで、デプロイ操作はそちらが担当します。

---

## 発動トリガー

自然言語で以下のような依頼をすると発動します。

- 「EmDash をセットアップして」「EmDash で新規サイトを作って」
- 「EmDash でコンテンツタイプを作って」「フィールドの型は何がある？」
- 「EmDash プラグインを作って」「sandboxed と native、どっちがいい？」
- 「WordPress から EmDash に移行して」
- 「EmDash に問い合わせフォームを追加して」「メール通知を設定して」
- 「EmDash の認証（passkey / OAuth）を組み込んで」

---

## できること一覧

| カテゴリ | 内容 |
|---|---|
| セットアップ | `pnpm create emdash@latest` での新規サイト作成、既存 Astro プロジェクトへの `emdash()` integration 統合 |
| コンテンツモデリング | 管理 UI でのスキーマ定義、`pnpm exec emdash types` での型生成、16 種のフィールド型 |
| クエリと Portable Text | `getEmDashCollection` / `getEmDashEntry` でのデータ取得、`<PortableText />`（`emdash/ui`）でのレンダリング |
| 認証 | `Astro.locals.user` によるユーザー判定、5 段階ロール、passkey-first（WebAuthn）・OAuth・magic link |
| プラグイン開発（2 形式） | sandboxed（Dynamic Workers 隔離・マーケットプレイス配布向け）／ native（trusted・管理 UI 拡張向け）の使い分けと実装 |
| メール | 公式ファーストパーティ `cloudflareEmail()` を主軸に、Cloudflare Email Service との連携・自作 transport |
| フォーム | 公式 `@emdash-cms/plugin-forms`（スパム対策・CSV エクスポート・メール通知） |
| WordPress 移行 | 管理ダッシュボードのインポートウィザード、`emdash-exporter` プラグイン、Gutenberg → Portable Text 変換 |
| MCP サーバー | サイト管理用（45 ツール・8 ドメイン）とドキュメント検索用（`search_docs` のみ）の 2 種 |
| デプロイ連携 | `deploy-astro-cloudflare` への委譲、D1 マイグレーション・`worker_loaders` を含む構成の注意点 |

---

## 技術スタック前提

| パッケージ / ツール | 基準バージョン | 備考 |
|---|---|---|
| emdash / create-emdash | 0.29.0 | npm の `1.0.0` は誤公開 deprecated。無視する |
| astro | 7.x | v7 GA（2026-06-22）。emdash の peer は `astro >=6.0.0-beta.0` |
| vite | 8.x | Astro 7 同梱。Rolldown 統合済み |
| @astrojs/cloudflare | 14.x | Cloudflare デプロイ時のアダプタ |
| @emdash-cms/cloudflare | 0.29 系 | D1 / R2 / KV / Hyperdrive / Cloudflare Email 用の別パッケージ |
| tailwindcss / @tailwindcss/vite | 4.x | CSS-first。`tailwind.config.js` 不要 |
| @biomejs/biome | 2.x | `.astro` は実験的サポート（2.3.0+） |
| pnpm | 11.x | パッケージマネージャーの基準 |
| wrangler | 4.x | Cloudflare デプロイ用 |

Cloudflare 構成では D1（DB）・R2（メディア）が既定。KV はオブジェクトキャッシュ用（任意）、Worker Loaders は sandboxed プラグイン実行時のみ必要です。

---

## ファイル構成

```
skills/emdash-cms/
├── SKILL.md                        # スキル定義（動作の正本。本ファイルはこの写像）
└── references/                     # SKILL.md から参照する詳細資料
    ├── cli.md                      # emdash CLI 全コマンド・環境変数・Exit Code
    ├── plugin-development.md       # sandboxed / native 両形式の実装・capabilities 12 種・hooks 25 種
    ├── email-and-forms.md          # メールパイプライン・cloudflareEmail() 導入・Forms プラグイン
    ├── wordpress-migration.md      # WXR 変換仕様・概念対応表・移行後チェックリスト
    └── cloudflare-deploy.md        # wrangler.jsonc 完全例・D1/Hyperdrive/KV・Dynamic Workers
```

各 references は SKILL.md 本文からトピック単位で参照されます。人間が個別に読む場合も、まず SKILL.md で全体像を掴んでから該当ファイルに入ると迷いません。

---

## 制約・注意

- **Dynamic Workers（sandboxed プラグイン実行）は Open Beta・Workers Paid プラン必須**（Open Beta 開始は 2026-03-24 ─ Cloudflare changelog）。無料プランでは sandboxed プラグインを実行できず、native（trusted）プラグインのみに構成を絞る必要があります。料金は月 1,000 個までの unique Dynamic Worker 作成が無料枠、超過は 1 個・1 日あたり $0.002。
- **Cloudflare Email Sending（送信側）は public beta**（2026-04-16 開始、2026-07-13 時点で GA 未達）。Workers Paid プラン必須ですが、認証済み宛先への送信は全プランで無料。1 通あたり上限 5 MiB。
- **サードパーティ `emdash-plugin-cloudflare-email` は非推奨扱い**にしています。peer dependency が古く（`emdash >= 0.5.0`）、3 ヶ月以上更新が無く現行 0.29 系の capability 体系との整合が未確認のため。公式ファーストパーティ `cloudflareEmail()` の登場で存在意義がほぼ無くなっており、新規導入では検討する理由がありません。既存プロジェクトで使用中の場合のみ、移行前提で参照します。
- **EmDash docs と実装の食い違いが残っている領域**があります。具体的には、古いドキュメントに残る `sandboxRunner` の文字列直書き記法（現行は `sandbox()` 関数呼び出しが正）、sandboxed プラグインが Hyperdrive（Postgres）構成では D1 バインディング依存のため動作しないという既知の制約、`requireAuth` / `getUser` のようなガード関数が実際には存在せずページ側の自前チェックが必要な点など。ドキュメントの記述をそのまま信じず、コード例は実機で確認する前提で扱ってください。
- WordPress 移行に専用 CLI コマンドは無く、管理ダッシュボードのインポートウィザード経由のみです（`emdash import:wordpress` 等は存在しません）。

---

## 関連スキル

| スキル | 関係 |
|---|---|
| `deploy-astro-cloudflare` | 本スキルはコンテンツ・プラグイン等の構成までを担当し、Cloudflare Workers への実デプロイ操作はこちらに委譲する |
| `astro-code-review` | EmDash 統合後の Astro コード（integration 設定・コンポーネント）のレビューに使う |

---

## 外部リファレンス

- [EmDash リポジトリ / releases](https://github.com/emdash-cms/emdash)
- [EmDash ドキュメント](https://docs.emdashcms.com)（ドキュメント検索 MCP: `https://docs.emdashcms.com/mcp`）
- [WordPress エクスポーター（emdash-exporter）](https://github.com/emdash-cms/wp-emdash)
- [Cloudflare Email Service](https://developers.cloudflare.com/email-service/)
