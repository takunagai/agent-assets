# トラブルシューティング（deploy-astro-cloudflare / Astro 7 + adapter v14）

デプロイ・ビルド・ランタイムのエラー対応。まず一般エラー、続いて v7 / v14 固有の落とし穴。

## 一般エラー

| 症状 | 原因・対処 |
|---|---|
| `wrangler: command not found` | wrangler 未インストール。`npm install -D wrangler` か PM 経由で用意（`npx` / `pnpm dlx` / `bunx` で実行してもよい） |
| 認証エラー | `wrangler login` で再認証。CI は `CLOUDFLARE_API_TOKEN` を設定 |
| デプロイ後に環境変数が消えた | `wrangler.jsonc` に `"keep_vars": true` があるか確認（`secrets-and-env.md` 参照） |
| Workers Builds が失敗 | ダッシュボードの Worker → Deployments → View build history でビルドログを確認 |
| 本番でエラーが再現するがログを追いたい | 接続済みなら `cloudflare-observability` MCP で本番ログ・分析を確認。未接続時は `wrangler tail` |
| `git push` が失敗 | リモートとの差分を確認。`git pull --rebase` を検討 |
| 二重デプロイ | Workers Builds 設定済みで `--local` デプロイ後に push すると自動デプロイと重複。Workers Builds 運用中はモード A（push のみ）を使う |
| Node バージョン不一致 | Astro 7 は Node v22.12.0 以上が必須（奇数メジャー v23 等は非対応）。nvm / Volta で切り替え |
| アセットアップロード遅延 | タイムアウトを延長して再試行（デプロイは 10 分に設定） |

## ランタイム（環境変数・バインディング）

| 症状 | 原因・対処 |
|---|---|
| サーバーで `Astro.locals.runtime` が undefined | `Astro.locals.runtime` は削除済み API（v5 / v6 コードの残骸）。`import { env } from 'cloudflare:workers';` へ移行 |
| サーバーで `import.meta.env` の値が undefined | `import.meta.env` はビルド時インライン化されランタイム値を読めない。`cloudflare:workers` の `env` を使う |
| ビルドは通るが本番で 500 エラー | 上記いずれかの環境変数移行漏れが最有力。サーバーコードの値取得方法を確認 |
| Sessions が効かない / KV エラー | Sessions 利用時、adapter が KV を自動設定する。デフォルト binding 名は `SESSION`。`sessionKVBindingName` の指定と KV 名前空間を確認 |
| 画像変換が失敗 | `imageService` のデフォルトは `'cloudflare-binding'`（Images binding を自動プロビジョン）。用途に応じ `'cloudflare'` / `'compile'` / `'passthrough'` を検討 |

## v7 アップデート後にビルドが落ちる（新しい典型原因）

Astro 7 は Rust 製コンパイラ・Rust 製 Markdown プロセッサ（Sätteri）・Vite 8（Rolldown）がデフォルト。v6 まで通っていたビルドが v7 で落ちる新しい原因がある。

| 症状 | 原因・対処 |
|---|---|
| HTML 構文エラーでビルド失敗 | Rust コンパイラで HTML 構文が厳格化。未クローズタグはエラー、不正ネストの自動補正は廃止。該当箇所の HTML を修正する |
| remark / rehype プラグインが動かない | Markdown 処理が Sätteri（Rust 製）デフォルトに。既存プラグインは移行するか、暫定的に `@astrojs/markdown-remark` へ切り戻す |
| `src/fetch.ts` 関連の衝突 | `src/fetch.ts` が advanced routing の予約ファイル名に。同名ファイルがあると衝突する。adapter の `fetchFile` オプションで回避可 |
| Vite プラグインが動かない | Vite 8（Rolldown）ベースに。Vite 固有プラグインは Vite 8 対応を確認 |
| 改行由来の空白で表示が崩れる | `compressHTML` のデフォルトが `true` → `'jsx'` に変更。空白の扱いが変わったための表示差を確認 |

## v14 固有

| 症状 | 原因・対処 |
|---|---|
| サードパーティ統合（Sentry 等）のサーバーラップが壊れる | v14 で内部の仮想エントリ名が変わり、旧エントリ名に依存する統合が機能しなくなる事例がある（統合側が観測した新名は `virtual:cloudflare/worker-entry`。adapter CHANGELOG には明記されず、統合側 issue での観測）。統合側を v14 対応バージョンへ更新する |
| `astro dev` が OOM でクラッシュ | advanced routing（`src/fetch.ts`）+ 大規模アプリで dev server が OOM する事例（withastro/astro #17181、"unable to reproduce" でクローズ）。最新アダプタ（v14.1.1 以上）へ更新のうえ、再現時は issue を参照 |
| ランタイムキャッシュがレスポンスをブロック | v14 は `ExecutionContext.waitUntil` をキャッシュプロバイダへ転送し、stale-while-revalidate 等をバックグラウンド化する。ブロックが見られる場合はアダプタ更新を確認 |

## 旧バージョンの残骸

| 症状 | 原因・対処 |
|---|---|
| `_worker.js as an asset` エラー | 旧構成（Astro 5 / pre-v13）の名残。v14 は `main: "@astrojs/cloudflare/entrypoints/server"` の統一エントリポイントで `_worker.js` を静的アセットとして出力しないため、`public/.assetsignore` は不要。`main` が旧値（`dist/_worker.js/index.js` 等）のままなら統一エントリポイントへ直す |
| `platformProxy` 関連の警告/エラー | `platformProxy` は v14 に存在しない。`astro.config` から削除する（ローカルランタイムは `astro dev` / `astro preview` が workerd 上で動くことで代替） |
| Cloudflare Pages 前提の設定・エラー | Cloudflare Pages サポートは廃止。Workers（static assets 付き）一本。Pages 固有設定（`_routes.json` 等）は不要 |
