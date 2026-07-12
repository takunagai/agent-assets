# セットアップチェックリスト（Next.js + OpenNext + Cloudflare Workers）

`deploy-nextjs-cloudflare` スキルを使う前の初期セットアップ手順。新規プロジェクト・既存プロジェクトの変換・設定ファイルの雛形をまとめる。

## 1. プロジェクト作成 / 変換

- 新規プロジェクト: `npm create cloudflare@latest -- <app名> --framework=next`
- 既存プロジェクトを OpenNext 構成へ変換: `opennextjs-cloudflare migrate`（公式の変換コマンド）

## 2. `wrangler.jsonc` 雛形

設定ファイルは **wrangler.jsonc が公式推奨**。`wrangler.toml` は後方互換だが、新しい Wrangler 機能は JSON 設定ファイル限定で提供される。

```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "main": ".open-next/worker.js",
  "name": "<WORKER_NAME>",
  "compatibility_date": "<当日の日付を推奨。最低 2025-05-05>",
  "compatibility_flags": ["nodejs_compat", "global_fetch_strictly_public"],
  "assets": { "directory": ".open-next/assets", "binding": "ASSETS" },
  "services": [
    { "binding": "WORKER_SELF_REFERENCE", "service": "<WORKER_NAME>" }
  ],
  "r2_buckets": [
    { "binding": "NEXT_INC_CACHE_R2_BUCKET", "bucket_name": "<WORKER_NAME>-opennext-cache" }
  ],
  "images": { "binding": "IMAGES" },
  "keep_vars": true
}
```

各キーの意味:

| キー | 説明 |
|---|---|
| `main` | OpenNext がビルドした Worker エントリポイント（固定パス） |
| `name` | Worker 名（Cloudflare 上の識別子） |
| `compatibility_date` | Workers ランタイムの互換性日付。下記「根拠」参照 |
| `compatibility_flags` | `nodejs_compat`（Node.js API 互換）と `global_fetch_strictly_public`（Cloudflare 推奨のセキュリティフラグ） |
| `assets` | 静的アセットのディレクトリとバインディング名 |
| `services` | Worker 自己参照バインディング（ISR/SSG のリクエスト内挙動に必要） |
| `r2_buckets` | インクリメンタルキャッシュ（ISR/SSG）用の R2 バケット |
| `images` | Next.js Image Optimization 用バインディング |
| `keep_vars` | `wrangler deploy` によるダッシュボード環境変数の上書き・削除を防ぐ（**必須級の推奨設定**） |

### `compatibility_date` の根拠

1. `nodejs_compat` を有効化するには 2024-09-23 以降の日付が必須
2. `FinalizationRegistry is not defined` エラーを避けるには 2025-05-05 以降が必要
3. Cloudflare 公式ガイドの実例は「デプロイ当日の日付」を使う運用

## 3. `open-next.config.ts` 雛形とキャッシュ戦略

```ts
import { defineCloudflareConfig } from "@opennextjs/cloudflare";
import r2IncrementalCache from "@opennextjs/cloudflare/overrides/incremental-cache/r2-incremental-cache";

export default defineCloudflareConfig({
  incrementalCache: r2IncrementalCache,
});
```

規模別の推奨構成:

| 規模 | 推奨構成 |
|---|---|
| 小規模 | R2 + Durable Object Queue + D1 Tag Cache |
| 大規模 | R2 + `ShardedDOTagCache`（DO タグキャッシュのコスト膨張対策） |
| 静的のみ | Workers Static Assets（revalidation 非対応） |

Regional cache オプション（エッジ近傍でのキャッシュ）も規模・レイテンシ要件に応じて検討する。

## 4. R2 バケットの事前作成

```bash
wrangler r2 bucket create <WORKER_NAME>-opennext-cache
```

`wrangler.jsonc` の `r2_buckets[].bucket_name` と一致させる。

接続済みなら `cloudflare-bindings` MCP でも作成・確認可。

## 5. ローカル開発設定

- `next.config.ts` に以下を追記し、`next dev` でも Cloudflare バインディングにアクセスできるようにする

  ```ts
  import('@opennextjs/cloudflare').then(m => m.initOpenNextCloudflareForDev());
  ```

- `.dev.vars` にローカル用の環境変数を設定する（例: `NEXTJS_ENV=development`）
- `.dev.vars` / `.env` は **コミット禁止**
- 本番シークレットは `wrangler secret put <KEY>` で登録する（`vars` に機密値を書かない）

## 6. package.json スクリプト（公式推奨形）

```json
{
  "scripts": {
    "build": "next build",
    "preview": "opennextjs-cloudflare build && opennextjs-cloudflare preview",
    "deploy": "opennextjs-cloudflare build && opennextjs-cloudflare deploy",
    "upload": "opennextjs-cloudflare build && opennextjs-cloudflare upload"
  }
}
```

旧形式（`deploy:production` / `deploy:preview` + `wrangler deploy --env`）を使っているプロジェクトは、上記 4 スクリプトへの移行を推奨する。移行後は `opennextjs-cloudflare deploy` / `upload` が populateCache（リモートキャッシュ投入）を暗黙実行するため、`wrangler deploy` を直接叩く必要はない。

## 7. セットアップ検証チェックリスト

- [ ] `next` のバージョンが `@opennextjs/cloudflare` の peerDependencies 要件（`>=15.5.18 <16` または `>=16.2.6`）を満たしている
- [ ] `wrangler.jsonc` に `main` / `name` / `compatibility_date` / `assets` の必須キーが揃っている
- [ ] R2 バケットが作成済みで `wrangler.jsonc` の `bucket_name` と一致している
- [ ] `npx wrangler whoami` が成功する（ログイン済み）
- [ ] `npm run preview`（`opennextjs-cloudflare build && opennextjs-cloudflare preview`）でローカル起動を確認できる
