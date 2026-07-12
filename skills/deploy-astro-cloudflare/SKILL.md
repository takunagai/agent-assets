---
name: deploy-astro-cloudflare
description: "Astro 7 + @astrojs/cloudflare v14 構成専用の Cloudflare Workers デプロイスキル。Workers Builds（GitHub 連携）・ローカル wrangler deploy・プレビューデプロイの 3 モード。プリフライト検証（バージョン・wrangler.jsonc・認証）、デプロイ完了確認、ロールバックに対応。『デプロイして』『本番に反映』『Cloudflare にデプロイ』『プレビューにデプロイ』などのリクエストで、対象プロジェクトが Astro のとき発動。Next.js + OpenNext 構成は deploy-nextjs-cloudflare を使用。"
---

# Astro 7 + Cloudflare Workers デプロイ Skill

## 概要・適用範囲

Astro アプリケーションを `@astrojs/cloudflare` アダプタ + wrangler 経由で Cloudflare Workers にデプロイする。Workers Builds（GitHub 連携の自動デプロイ）・ローカル `wrangler deploy`・プレビューデプロイの 3 モードに対応し、デプロイ前のプリフライト検証、デプロイ完了確認、ロールバックまでを扱う。

> [!important] このスキルは Astro 7 以降 / `@astrojs/cloudflare` v14 以降の構成専用
> `astro >= 7` かつ `@astrojs/cloudflare >= 14` を前提とする。プリフライト（Step 0）で旧バージョン（`astro < 7` または `@astrojs/cloudflare < 14`）を検出したら**デプロイせず停止**し、次の公式移行ガイドを案内する。
>
> - Astro 6 → 7: https://docs.astro.build/en/guides/upgrade-to/v7/
> - Astro 5 → 6（v5 系からは先にこちらを経由）: https://docs.astro.build/en/guides/upgrade-to/v6/
>
> 旧バージョン向けのデプロイ手順は提供しない（既存プロジェクトも v7 へ更新する方針のため）。

> [!note] Next.js との使い分け
> Next.js + OpenNext 構成のデプロイは別スキル `deploy-nextjs-cloudflare`（`@opennextjs/cloudflare` 前提。設定・ビルド成果物が異なる）を使う。「デプロイして」だけではトリガーが衝突しうるため、`astro.config.*` があり `@astrojs/cloudflare` を使う構成のときに本スキルを選ぶ。

### 技術スタックの前提

- **フレームワーク**: Astro 7+
- **アダプタ**: `@astrojs/cloudflare` v14+（`main: "@astrojs/cloudflare/entrypoints/server"` の統一エントリポイント）
- **デプロイ先**: Cloudflare Workers（static assets 付き。Cloudflare Pages は廃止済み）
- **デプロイツール**: wrangler（`wrangler.jsonc`）
- **CI/CD**: Workers Builds（Cloudflare の GitHub 連携）
- **Node.js**: v22.12.0 以上（奇数メジャーは非対応）

## 使い方

- `/deploy-astro-cloudflare` → Workers Builds 経由でデプロイ（デフォルト = モード A）
- `/deploy-astro-cloudflare --local` → ローカルから `wrangler deploy`（モード B）
- `/deploy-astro-cloudflare --preview` → プレビューデプロイ（モード C。本番トラフィックに載せない）
- `/deploy-astro-cloudflare --skip-build` → ビルド事前チェックを省略（緊急時のみ。モード B と併用）

自然言語でも発動する。「デプロイして」「本番に反映」「Cloudflare にデプロイ」「プレビューにデプロイ」など。

---

## Step 0: プリフライト（全モード共通）

デプロイ前に必ず実行する。詳細な実行コマンド・期待結果・失敗時対処は `references/preflight-checklist.md` に委譲する。要点は以下。

1. **バージョン検出** ─ `package.json` の `astro` が `>= 7`、`@astrojs/cloudflare` が `>= 14` であることを確認する。満たさない場合は**停止**し、上記の移行ガイドを案内する（デプロイしない）。
2. **パッケージマネージャ検出** ─ lockfile で判定する（`pnpm-lock.yaml` → pnpm / `bun.lockb` または `bun.lock` → bun / `package-lock.json` → npm）。以降のコマンドを検出結果に合わせる。
3. **wrangler 設定検証** ─ `wrangler.jsonc`（または `.json` / `.toml`）で次を確認する。
   - `main` が `"@astrojs/cloudflare/entrypoints/server"`
   - `assets.directory`（通常 `"./dist"`）と `assets.binding`（通常 `"ASSETS"`）
   - `compatibility_date` が設定済み（Node.js API 利用時は `compatibility_flags: ["nodejs_compat"]`）
   - 設定ファイルが無い場合 ─ シンプルな構成では Astro が自動生成する運用も許容し、その旨を報告する。
4. **認証・Node 確認（モード B / C のみ）** ─ `wrangler whoami` で Cloudflare 認証を確認し、Node.js が v22.12.0 以上であることを確認する。
5. **`keep_vars` 確認** ─ ダッシュボードで環境変数を管理する運用のプロジェクトでは、`wrangler.jsonc` に `"keep_vars": true` があることを確認する（無いとデプロイ後に環境変数が消える。次節参照）。

最小構成の `wrangler.jsonc` の例:

```jsonc
{
  "name": "my-astro-app",
  "main": "@astrojs/cloudflare/entrypoints/server",
  "compatibility_date": "2025-05-21",
  "assets": { "directory": "./dist", "binding": "ASSETS" }
}
```

---

## モード A: Workers Builds 経由（デフォルト）

GitHub 連携が設定済みなら、`git push` で Cloudflare 側が自動ビルド・デプロイする。

### ワークフロー

```
1. プリフライト → Step 0
2. 状態確認    → git status / 未プッシュコミット確認
3. コミット    → 未コミット変更があれば /commit スキルで処理
4. プッシュ    → git push origin main
5. 完了確認    → デプロイ完了を確認してから報告（push 直後は未完了）
```

### 重要: デプロイ完了確認

`git push` はビルド・デプロイのトリガーにすぎない。**push 直後を「デプロイ完了」と報告しない**。次のいずれかで実際の反映を確認してから完了を報告する。

- `wrangler deployments list` で新しいデプロイ（新 Version ID）が Active になったことを確認する
- 本番 URL に `curl -sI https://<worker>.workers.dev` で疎通し、更新が反映されたことを確認する
- ダッシュボードの Worker → Deployments → View build history でビルドログの成功を確認する

### Workers Builds 未設定の場合

1. Cloudflare ダッシュボードで GitHub 連携と Workers Builds をセットアップする（プロジェクト固有のデプロイ引き継ぎ書・セットアップ手順ノートがあれば参照する）。
2. セットアップ完了まではモード B（ローカルデプロイ）を使う。

---

## モード B: ローカルデプロイ（`--local`）

Workers Builds 未設定時、または手元から直接デプロイしたい場合。

### ワークフロー

```
1. プリフライト → Step 0（認証・Node 確認を含む）
2. 状態確認    → git status 確認
3. コミット    → 未コミット変更があれば /commit スキルで処理
4. ビルド確認  → ビルド事前チェック（--skip-build で省略可）
5. デプロイ    → deploy スクリプト優先、なければフォールバック（タイムアウト 10 分）
6. プッシュ    → git push origin main（未プッシュがあれば）
7. 完了確認    → デプロイログの成功 + 本番 URL 疎通
```

### デプロイコマンドの決定

`package.json` に `deploy` スクリプトがあればそれを優先する。無ければ次のフォールバックを使う（パッケージマネージャは Step 0 の検出結果に合わせる）。

```bash
# フォールバック（npm の例）
npx astro build && npx wrangler deploy
```

**タイムアウトは 600000ms（10 分）** に設定する。ビルドが失敗したらデプロイを中止しエラーを報告する（`--skip-build` 指定時はビルド事前チェックをスキップ。ただしデプロイ内部のビルドは走る）。

> [!warning] 二重デプロイに注意
> Workers Builds が設定済みのリポジトリで `--local` デプロイ後に `git push` すると、ローカルデプロイと Workers Builds の自動デプロイで**二重にデプロイ**が走る。Workers Builds 運用中は原則モード A（push のみ）を使い、`--local` は Workers Builds 未設定時か緊急時に限る。

---

## モード C: プレビューデプロイ（`--preview`）

本番トラフィックに影響を与えずにプレビュー URL を発行して検証する。

### ローカル起点（推奨）

ビルド済み Worker をプレビューとしてアップロードする。本番の Active Deployment は変わらない。

```bash
# エイリアス付きプレビュー URL を発行
npx wrangler versions upload --preview-alias staging
# → staging-<WORKER_NAME>.<SUBDOMAIN>.workers.dev
```

- 前提: workers.dev サブドメインが有効であること（`workers_dev` 有効時はプレビュー URL がデフォルト有効）。
- `--preview-alias` を省略しても version 固有のプレビュー URL は発行される（ダッシュボードの Version ID 配下に表示）。
- エイリアスは英小文字始まり・英小文字/数字/ハイフンのみ。

### Workers Builds 利用時

非本番ブランチへの push でプレビューを出せるが、**デフォルトでは無効**。ダッシュボードで「Builds for non-production branches」を有効化する必要がある。有効化すると、非本番ブランチの deploy コマンドが既定で `npx wrangler versions upload` となり、プレビュー URL が version 配下に表示される。

---

## デプロイ後確認・ロールバック

- **履歴確認**: `wrangler deployments list` で直近のデプロイ・Version ID・Active 状態を確認する。
- **疎通確認**: 本番 URL に `curl -sI` で疎通し、想定どおり更新されたことを確認する。
- **ロールバック**: 異常時は `wrangler rollback` で直前のデプロイへ戻す。`wrangler deployments list` で戻し先の Version ID を確認してから実行する。

---

## MCP 連携（接続済みなら優先。CLI が実行骨格）

公式プラグイン `cloudflare` の MCP サーバーが接続済み（OAuth 認証済み）なら、次を CLI コマンドの代わりに使ってよい。未接続・未認証の場合は従来どおり CLI で続行する。

- **デプロイ状態確認** ─ `cloudflare-builds`（Workers Builds のビルド・デプロイ状態）。未接続時は `wrangler deployments list`。
- **本番ログ確認** ─ `cloudflare-observability`（本番 Workers ログ・分析）。未接続時は `wrangler tail`。
- **ドキュメント疑問点の確認** ─ `cloudflare-docs`（認証不要・常時使用可）。ドキュメント参照の第一手段としてよい。
- 汎用的な wrangler の作法・ベストプラクティスは、公式プラグイン同梱スキル `wrangler` / `workers-best-practices` を参照する。

---

## 環境変数・secrets の要点

詳細は `references/secrets-and-env.md` に委譲する。要点のみ。

- **ランタイム値の読み取り**: サーバーコードでは `import { env } from 'cloudflare:workers';` で環境変数・バインディング（`env.MY_KV` 等）に直接アクセスする。型安全にするなら `astro.config` でスキーマ定義し `import { MY_VAR } from 'astro:env/server';` を使う。
- **`import.meta.env` の罠**: `import.meta.env` はビルド時にインライン化されるため、**ランタイム値（ダッシュボードの vars / secrets）は読めない**。サーバーで動的な値が必要なら必ず `cloudflare:workers` の `env` を使う。
- **secrets**: 本番は `wrangler secret put <KEY>`、ローカル開発は `.dev.vars`（gitignore 必須）。公開してよい値は `wrangler.jsonc` の `vars`。
- **`keep_vars: true`**: `wrangler deploy` はデフォルトでダッシュボード設定の環境変数を上書き・削除する。ダッシュボード管理の vars を使う運用では必須。
- **機密値をレスポンス・コミットに載せない**。参照（`ファイル名:行番号`）かマスク表示で代替する。

> [!note] `Astro.locals.runtime` は削除済み
> 旧構成（Astro 5 / 6・adapter v13 以前）の `Astro.locals.runtime.env` は削除済み API。移行対象であり、新規コードでは使わない（`cloudflare:workers` の `env` へ移行する）。

---

## エラー対応（要約）

頻出のみ。全量と v7 / v14 固有の落とし穴は `references/troubleshooting.md` を参照。

| エラー | 対応 |
|--------|------|
| ビルド失敗 | エラー内容を確認し修正。v7 更新直後は Rust コンパイラの HTML 厳格化 / Markdown プロセッサ変更が原因になりやすい（troubleshooting 参照） |
| wrangler 認証切れ | `wrangler login` で再認証（CI は API トークン） |
| デプロイ後に環境変数が消えた | `wrangler.jsonc` の `"keep_vars": true` を確認 |
| サーバーで `Astro.locals.runtime` が undefined | 旧 API。`cloudflare:workers` の `env` へ移行 |
| Workers Builds 失敗 | ダッシュボードの View build history でビルドログを確認 |
| 二重デプロイ | Workers Builds 設定済みで `--local` + push を併用していないか確認 |

---

## 参照ドキュメント

- `references/preflight-checklist.md` ─ プリフライト各項目の実行コマンド・期待結果・失敗時対処
- `references/secrets-and-env.md` ─ 環境変数の 4 層整理・`keep_vars`・`astro:env` と `cloudflare:workers` の使い分け・環境別ビルド
- `references/troubleshooting.md` ─ エラー対応表（v7 / v14 固有の落とし穴を含む）
- プロジェクト固有のデプロイ引き継ぎ書・知見ノート（Workers Builds セットアップ手順、環境変数設定、過去のエラー事例集など）があれば参照する

## 注意事項

- デプロイ（モード B）のタイムアウトは 10 分（600000ms）に設定する。
- `astro dev` / `astro preview` は Cloudflare Vite plugin 経由で本物の Workers ランタイム（workerd）上で動くため、`wrangler dev` を別途使う必要はない。
- 環境はビルド時に確定する。環境別デプロイは `CLOUDFLARE_ENV=<env名> astro build && wrangler deploy` のように環境ごとに別ビルドする。
