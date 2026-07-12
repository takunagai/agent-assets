# トラブルシューティング（Next.js + OpenNext + Cloudflare Workers）

`deploy-nextjs-cloudflare` スキルで発生しうる問題の詳細対応集。SKILL.md の「エラー対応」表で扱いきれない事象はここを参照する。

## 1. proxy.ts / Node Middleware 問題

- **状況**: `@opennextjs/cloudflare` は Next.js の `proxy.ts`（Node Middleware 扱い）を未サポート
- **エラー例**: バンドル生成時に `File server/middleware.js does not exist`
- **現状（2026-07-05 確認）**: 追跡 issue [opennextjs/opennextjs-cloudflare#1082](https://github.com/opennextjs/opennextjs-cloudflare/issues/1082) は **closed（2026-04-09、SWR 対応完了が理由）だが、proxy.ts 問題自体は未解決**
- **正しい追跡先**: [opennextjs/adapters-api#20](https://github.com/opennextjs/adapters-api/issues/20)（open）、[opennextjs-cloudflare#1277](https://github.com/opennextjs/opennextjs-cloudflare/issues/1277)（open）
- **回避策**（2026-06-18 時点のコメントでも依然必要）: `proxy.ts` → `middleware.ts` にリネームし、`export proxy` → `export middleware` に変更
- **補足**: `middleware.ts` はビルド時に非推奨警告が出るが、メンテナ（conico974、2026-04-28）が **Next 17 までサポート継続**を明言している
- **根本原因**: Next.js の `proxy.ts` は Node Middleware（Next 15.2 導入）扱いで、OpenNext は Node Middleware 自体が未対応
- **解消条件**: adapters-api#20 のクローズ後に再確認する

## 2. 頻出トラブル対応表

| 症状 | 原因と対処 |
|---|---|
| Worker サイズ超過 | gzip 後 Free プラン 3 MiB / Paid プラン 10 MiB が上限。`.open-next/server-functions/default/handler.mjs.meta.json` を ESBuild Bundle Analyzer（https://esbuild.github.io/analyze/）に読み込ませて大きい依存を特定・削減する |
| npm パッケージ import 失敗 | `nodejs_compat` フラグ欠落、または `compatibility_date` が古い。`.env` に `WRANGLER_BUILD_CONDITIONS=""` / `WRANGLER_BUILD_PLATFORM="node"` を設定して回避 |
| `Cannot perform I/O on behalf of a different request` | DB クライアント等をグローバルスコープで使い回しているのが原因。リクエストハンドラ内で都度生成する |
| `FinalizationRegistry is not defined` | `compatibility_date` を 2025-05-05 以降に更新する |
| R2 キャッシュ投入失敗（populate 15 attempts） | 既知 issue [#1284](https://github.com/opennextjs/opennextjs-cloudflare/issues/1284)（open）。リトライで解消する場合がある。ヘルパー Worker が Cloudflare Access で保護されていると認証エラーになるため、Access 設定の干渉も確認する |
| ISR キャッシュ不安定 | 既知 issue [#1281](https://github.com/opennextjs/opennextjs-cloudflare/issues/1281)（open、1.19.x 系で報告）。`@opennextjs/cloudflare` を最新化する |
| DO タグキャッシュのコスト膨張 | 既知 issue [#1103](https://github.com/opennextjs/opennextjs-cloudflare/issues/1103)。大規模サイトは `ShardedDOTagCache` への切り替えを検討する（`references/setup-checklist.md` の規模別推奨を参照） |
| ダッシュボード設定の環境変数が消えた | `wrangler deploy` はデフォルトでダッシュボードの環境変数を上書きする。`wrangler.jsonc` に `keep_vars: true` を設定する（deploy-astro-cloudflare スキルと同じ注意点） |

## 3. ロールバック手順

```bash
npx wrangler deployments list   # 直近 100 件のデプロイ履歴を確認
npx wrangler versions list      # 直近 100 件のバージョン履歴を確認
npx wrangler rollback           # 指定バージョンへ即時ロールバック
```

制約:

1. ロールバック可能なのは直近 100 バージョンまで
2. KV / R2 / D1 / Durable Object の**データは巻き戻らない**（コードのみ戻る）
3. 対象バージョンとの間でリソース削除・DO マイグレーションがある場合はロールバック不可

## 4. リアルタイムログ

```bash
npx wrangler tail
# JSON 整形して確認する例
npx wrangler tail | jq .
```

- 同時接続クライアントは最大 10（それ以上は拒否される）
- 高トラフィック時はサンプリングされる場合がある
- 接続済みなら `cloudflare-observability` MCP でも本番ログ・分析を確認できる（未接続時は上記の `wrangler tail` を使う）。同時接続 10 の制約を受けない選択肢として有効

## 5. Preview URL が発行されない場合

Preview URL（`upload` コマンド実行時に発行される、workers.dev サブドメイン上の URL）が出力されないときは、以下を確認する。

- Durable Object を実装した Worker には Preview URL が生成されない仕様
- `workers_dev` が無効化されていないか確認する（`workers_dev` 有効時はデフォルトで Preview URL が有効）
- 生成される URL の形式: `<PREFIX>-<WORKER_NAME>.<SUBDOMAIN>.workers.dev`
- Preview URL はカスタムドメインでは発行されない（workers.dev サブドメインのみ）
