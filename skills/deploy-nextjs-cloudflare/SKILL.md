---
name: deploy-nextjs-cloudflare
description: "Next.js + OpenNext 構成専用の Cloudflare Workers デプロイスキル。OpenNext 公式 CLI（opennextjs-cloudflare deploy / upload）で本番デプロイと Preview URL 発行を自動実行。未コミット変更の処理、ビルド確認、プッシュ、フレームワーク検出・認証確認などのプリフライトを含む。『Next.js をデプロイして』『本番に反映』『Cloudflareにデプロイ』『プレビューにデプロイ』などのリクエストで発動。Astro 構成のデプロイには deploy-astro-cloudflare を使用する。"
---

# Cloudflare デプロイ Skill（Next.js + OpenNext 構成専用）

> [!note] 適用範囲
> このスキルは **Next.js + OpenNext（`@opennextjs/cloudflare`）構成専用**です。
> Astro 構成のデプロイには別スキル **deploy-astro-cloudflare** を使用してください。
> 両者ともトリガー語が近いため、**実行前に対象プロジェクトの `package.json` を確認**すること。
> `dependencies` / `devDependencies` に `@opennextjs/cloudflare` があれば本スキル、`astro` が見つかれば deploy-astro-cloudflare に切り替える（`scripts/deploy.sh` はこの判定を自動で行う）。

## 概要

Next.js アプリケーションを OpenNext 公式 CLI 経由で Cloudflare Workers にデプロイする。

- **production**: `opennextjs-cloudflare deploy` ─ リモートキャッシュ投入 → `wrangler deploy` で即時本番反映
- **preview**: `opennextjs-cloudflare upload` ─ リモートキャッシュ投入 → `wrangler versions upload` で Preview URL を発行（トラフィックには乗らない。固定エイリアスは `--preview-alias`）

## 使い方

- `/deploy-nextjs-cloudflare` or `/deploy-nextjs-cloudflare production` → 本番環境にデプロイ（デフォルト）
- `/deploy-nextjs-cloudflare preview` → プレビュー環境にデプロイ（Preview URL 発行）
- `/deploy-nextjs-cloudflare production --skip-build` → ビルドチェックを省略（緊急時のみ）
- `/deploy-nextjs-cloudflare production --allow-branch` → main/master 以外のブランチからの本番デプロイを許可

## 実行方法

Claude は `scripts/deploy.sh` を正式なエントリポイントとして実行する。

```bash
bash <スキルパス>/scripts/deploy.sh <production|preview> [--skip-build] [--allow-branch]
```

- タイムアウトは **600000ms（10 分）** を指定する
- スクリプトはプリフライト（Git リポジトリ確認・フレームワーク検出・パッケージマネージャ検出・デプロイスクリプト検出・wrangler 認証確認・ブランチ確認）を通過してからビルド・デプロイに進む
- プリフライトが失敗した場合はエラーメッセージの指示に従う（「エラー対応」節を参照）
- 未コミット変更でスクリプトが止まった場合は `/commit` スキルでコミットしてから再実行する

## 前提条件

- `package.json` に公式推奨のスクリプトが定義されていること

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

- **`wrangler.jsonc`**（公式推奨。`wrangler.toml` も後方互換で動作するが、新機能は jsonc 限定で提供される）
- `wrangler login` 済み（`npx wrangler whoami` で確認できる）
- R2 バケット作成・`open-next.config.ts` などの初期セットアップは `references/setup-checklist.md` を参照
- **旧 I/F（`deploy:production` / `deploy:preview` + `wrangler deploy --env`）のプロジェクトを検出した場合**、`scripts/deploy.sh` はフォールバックで動作を続けるが、新形式（`deploy` / `upload`）への package.json 更新を提案する（手順は `references/setup-checklist.md` を参照）

## バージョン方針

**常に最新版を採用する。** 実行前に以下で latest を確認し、対象プロジェクトの依存が古ければアップデートを提案する。

```bash
npm view next version
npm view @opennextjs/cloudflare version
```

| パッケージ | 2026-07-05 確認時点の latest | 備考 |
|---|---|---|
| `next` | 16.2.10 | 16.3 系は canary/preview 段階 |
| `@opennextjs/cloudflare` | 1.20.1 | peerDependencies: `next ">=15.5.18 <16 \|\| >=16.2.6"` / `wrangler ^4.86.0` |

Next 16 系を使う場合は **16.2.6 以上が peer 要件で必須**。OpenNext の対応状況の最新確認は、上記 `npm view` に加え、接続済みなら `cloudflare-docs` MCP 検索も併用する（認証不要・常時使用可）。

## OpenNext 互換性（proxy.ts / Node Middleware）

- issue #1082 は **closed（2026-04-09、SWR 対応完了が理由）だが、proxy.ts 問題自体は未解決**。「#1082 が閉じた = 解決済み」と読むのは誤り
- 正しい追跡先: [opennextjs/adapters-api#20](https://github.com/opennextjs/adapters-api/issues/20)（open）、[opennextjs-cloudflare#1277](https://github.com/opennextjs/opennextjs-cloudflare/issues/1277)（open）
- 回避策（2026-06-18 時点のコメントでも依然必要）: `proxy.ts` → `middleware.ts` にリネームし、`export proxy` → `export middleware` に変更
- `middleware.ts` はビルド時に非推奨警告が出るが、メンテナ（conico974、2026-04-28）により **Next 17 まではサポート継続**と明言されている
- 根本原因: Next.js の `proxy.ts` は Node Middleware（Next 15.2 導入）扱いで、OpenNext は Node Middleware 自体を未対応
- 解消条件: adapters-api#20 のクローズ後に再確認する

## デプロイ後の確認とロールバック

- ブラウザで本番 / プレビュー URL にアクセスし、主要な変更点を確認する
- `npx wrangler deployments list` / `npx wrangler versions list` ─ 直近 100 件の履歴を確認
- `npx wrangler rollback` ─ 指定バージョンへ即時ロールバック（**KV / R2 / D1 / DO のデータは戻らない**点に注意）
- `npx wrangler tail` ─ リアルタイムログを確認
- 詳細・制約は `references/troubleshooting.md` を参照

## MCP 連携（接続済みなら優先。CLI が実行骨格）

公式プラグイン `cloudflare` の MCP サーバーが接続済み（OAuth 認証済み）なら、次を CLI コマンドの代わりに使ってよい。未接続・未認証の場合は従来どおり CLI で続行する。

- **デプロイ状態確認** ─ `cloudflare-builds`（Workers Builds のビルド・デプロイ状態）。未接続時は `wrangler deployments list`。
- **本番ログ確認** ─ `cloudflare-observability`（本番 Workers ログ・分析）。未接続時は `wrangler tail`。
- **ドキュメント疑問点の確認** ─ `cloudflare-docs`（認証不要・常時使用可）。ドキュメント参照の第一手段としてよい。
- 汎用的な wrangler の作法・ベストプラクティスは、公式プラグイン同梱スキル `wrangler` / `workers-best-practices` を参照する。

## エラー対応

| エラー | 対応 |
|--------|------|
| `wrangler whoami` 失敗（認証切れ） | `wrangler login` を実行 |
| フレームワーク不一致（`astro` を検出） | deploy-astro-cloudflare スキルを使用 |
| デプロイスクリプト未定義 | package.json に `deploy` / `upload` スクリプトを追加（前提条件・`references/setup-checklist.md` を参照） |
| ビルド失敗 | エラー内容を確認し修正。`/error-diagnostic` を活用 |
| プッシュ失敗 | リモートとの差分を確認。`git pull --rebase` を検討 |
| その他（Worker サイズ超過・キャッシュ投入失敗・ISR 不安定 等） | `references/troubleshooting.md` を参照 |

## 注意事項

- `wrangler.jsonc` に `keep_vars: true` を設定する（デプロイでダッシュボード側の環境変数が消えるのを防ぐ。deploy-astro-cloudflare と同趣旨）
- 機密情報は `vars` に書かず `wrangler secret put` で登録する。`.dev.vars` はコミット禁止
- 既知の無害警告: `assets.exclude`、`duplicate key "options"`（floating-ui 由来）
- デプロイのタイムアウトは 600000ms（10 分）に設定すること
