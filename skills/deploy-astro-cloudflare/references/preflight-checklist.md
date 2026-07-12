# プリフライトチェックリスト（deploy-astro-cloudflare）

デプロイ前に確認する項目の実行コマンド例・期待結果・失敗時対処。各項目の正本は「到達状態」であり、コマンドは達成手段の一例。実挙動が違う場合は同じ到達状態を別手段で満たしてよい。

## 1. バージョン検出（全モード必須・最優先）

**到達状態**: `astro >= 7` かつ `@astrojs/cloudflare >= 14` であることを確認済み。満たさなければデプロイせず停止し移行を案内。

```bash
# インストール済みバージョンを確認（PM に合わせて読み替え）
npm ls astro @astrojs/cloudflare 2>/dev/null
# または package.json の宣言を確認
cat package.json | grep -E '"astro"|"@astrojs/cloudflare"'
```

- 期待: `astro@7.x` 以上、`@astrojs/cloudflare@14.x` 以上。
- 失敗時（旧バージョン検出）: **デプロイを中止**し、次を案内する。
  - Astro 6 → 7: https://docs.astro.build/en/guides/upgrade-to/v7/
  - Astro 5 → 6（v5 系は先に経由）: https://docs.astro.build/en/guides/upgrade-to/v6/
- 旧バージョン向けのデプロイ手順は提供しない（既存プロジェクトも v7 へ更新する方針）。
- 移行ガイドの詳細確認は、接続済みなら `cloudflare-docs` MCP（認証不要）を第一手段とする。未接続時は上記 URL を直接参照する。

## 2. パッケージマネージャ検出

**到達状態**: 以降のコマンドで使う PM が確定している。

| lockfile | PM | 実行例 |
|---|---|---|
| `pnpm-lock.yaml` | pnpm | `pnpm build` / `pnpm dlx wrangler ...` |
| `bun.lockb` または `bun.lock` | bun | `bun run build` / `bunx wrangler ...` |
| `package-lock.json` | npm | `npm run build` / `npx wrangler ...` |

```bash
ls pnpm-lock.yaml bun.lockb bun.lock package-lock.json 2>/dev/null
```

- 複数存在する場合は、より限定的なもの（pnpm / bun）を優先し、ユーザーに確認する。

## 3. wrangler 設定検証

**到達状態**: `main` が統一エントリポイントで、`assets` と `compatibility_date` が妥当。設定ファイルが無い場合は自動生成運用として許容し報告する。

```bash
# 設定ファイルの存在と主要キー
cat wrangler.jsonc wrangler.json wrangler.toml 2>/dev/null
```

必須・推奨キー:

- `main`: `"@astrojs/cloudflare/entrypoints/server"`（v14 の統一エントリポイント。`astro dev` と本番デプロイの両方を担う）
- `assets.directory`: 通常 `"./dist"`
- `assets.binding`: 通常 `"ASSETS"`
- `compatibility_date`: 設定済みであること
- Node.js API を使う場合: `compatibility_flags: ["nodejs_compat"]`

最小構成例:

```jsonc
{
  "name": "my-astro-app",
  "main": "@astrojs/cloudflare/entrypoints/server",
  "compatibility_date": "2025-05-21",
  "assets": { "directory": "./dist", "binding": "ASSETS" }
}
```

- 失敗時: `main` が `dist/_worker.js/index.js` 等の旧値ならアダプタ更新後の設定漏れ。統一エントリポイントへ直す。
- 設定ファイルが無い場合: シンプルな構成では Astro が自動生成する運用も許容する。その旨をユーザーに報告し、カスタム設定が必要かを確認する。
- `wrangler types` で設定に一致した型定義を生成できる（`Env` 型のズレの検出に有用）。

## 4. 認証・Node 確認（モード B / C のみ）

**到達状態**: Cloudflare に認証済みで、Node.js が要件を満たす。

```bash
wrangler whoami          # 認証アカウントの確認
wrangler --version       # v4.83.0 以上（@astrojs/cloudflare v14 の peer 要件）
node -v                  # v22.12.0 以上であること（奇数メジャー v23 等は非対応）
```

- 認証切れ: `wrangler login`（CI では `CLOUDFLARE_API_TOKEN` を使用）。
- wrangler が古い: `@astrojs/cloudflare@14` は `wrangler ^4.83.0` を peer 依存に要求する。`npm ls wrangler` で確認し、古ければ更新する。
- Node が古い / 奇数メジャー: 対応バージョンへ切り替える（nvm / Volta 等）。

## 5. `keep_vars` 確認（ダッシュボード vars 運用時）

**到達状態**: ダッシュボードで環境変数を管理するプロジェクトでは `keep_vars: true` を設定済み。

```bash
grep -n "keep_vars" wrangler.jsonc 2>/dev/null
```

- `wrangler deploy` はデフォルトでダッシュボード設定の環境変数を上書き・削除する。`"keep_vars": true` がないとデプロイ後に環境変数が消える。詳細は `secrets-and-env.md`。

## 6. `platformProxy` 残骸の検出（旧構成からの移行時）

**到達状態**: `astro.config` に `platformProxy` オプションが残っていない。

```bash
grep -rn "platformProxy" astro.config.* 2>/dev/null
```

- `platformProxy` は `@astrojs/cloudflare` v14 には存在しない。ローカルランタイムは `astro dev` / `astro preview` が Cloudflare Vite plugin 経由で workerd 上で動くことで代替される。残っていたら削除する（ビルド警告やエラーの原因になりうる）。
