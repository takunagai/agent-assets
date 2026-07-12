# deploy-nextjs-cloudflare

**Next.js + OpenNext 構成専用**の Cloudflare Workers デプロイ自動化スキルです。OpenNext 公式 CLI（`opennextjs-cloudflare deploy` / `upload`）で Next.js アプリをビルド・デプロイし、Wrangler 経由で Cloudflare Workers へ反映する一連の流れ（プリフライト → 状態確認 → ビルド確認 → プッシュ → デプロイ → 確認）を自動実行します。本番環境（production）と Preview URL 発行（preview）に対応します。

> **適用範囲の注意**: Astro 構成のデプロイには別スキル **deploy-astro-cloudflare** を使用してください。両者ともトリガー語が近いため、対象プロジェクトのフレームワークを必ず確認してから実行します（`scripts/deploy.sh` がプリフライトで自動判定します）。

---

## 対応構成

| 項目 | 内容 |
|------|------|
| フレームワーク | Next.js |
| アダプター | `@opennextjs/cloudflare`（OpenNext） |
| デプロイ先 | Cloudflare Workers |
| デプロイコマンド | OpenNext 公式サブコマンド（`opennextjs-cloudflare deploy` / `upload`） |
| 設定ファイル | `wrangler.jsonc`（`wrangler.toml` も後方互換で動作） |
| 対応環境 | production（即時反映） / preview（Preview URL 発行） |

---

## インストール

このリポジトリを clone し、スキル本体（`skills/deploy-nextjs-cloudflare`）を各エージェントのスキルディレクトリへ symlink します。実体は 1 つ、参照を複数張る方式です。当環境では「実体 → `~/.agents` → `~/.claude`」の 2 段 symlink で統一しています。

```bash
git clone git@github.com:takunagai/agent-assets.git ~/Projects/agent-assets
ln -s /Users/$USER/Projects/agent-assets/skills/deploy-nextjs-cloudflare ~/.agents/skills/deploy-nextjs-cloudflare
ln -s ../../.agents/skills/deploy-nextjs-cloudflare ~/.claude/skills/deploy-nextjs-cloudflare
```

> Codex など他のエージェントは `~/.agents/skills/deploy-nextjs-cloudflare` を直接読みます。Claude Code は `~/.claude/skills/` を経由して同じ実体を参照します。

スキル本体の構成は次の通りです（人間用マニュアルである本ファイルは、スキル本体の外＝`docs/` に置いています）。

```
skills/deploy-nextjs-cloudflare/
├── SKILL.md                       # スキル定義（Claude がトリガー時に読む）
├── references/
│   ├── setup-checklist.md         # 初期セットアップ手順（wrangler.jsonc / R2 / package.json 雛形）
│   └── troubleshooting.md         # proxy.ts 問題・頻出トラブル・ロールバック手順
└── scripts/
    └── deploy.sh                  # デプロイ自動化スクリプト（プリフライト〜デプロイ〜確認）
```

---

## クイックスタート

```bash
# 本番環境にデプロイ（デフォルト）
/deploy-nextjs-cloudflare
/deploy-nextjs-cloudflare production

# プレビュー環境にデプロイ（Preview URL 発行）
/deploy-nextjs-cloudflare preview

# ビルドチェックを省略（緊急時のみ）
/deploy-nextjs-cloudflare production --skip-build

# main/master 以外のブランチから本番デプロイを許可
/deploy-nextjs-cloudflare production --allow-branch
```

自然言語でも発動します。「Next.js をデプロイして」「本番に反映」「Cloudflare にデプロイ」「プレビューにデプロイ」など。

---

## 使い方

### 本番 / プレビューの切り替え

第 1 引数で環境を指定します。省略時は `production` です。

| コマンド | 動作 |
|----------|------|
| `/deploy-nextjs-cloudflare` または `/deploy-nextjs-cloudflare production` | 本番環境にデプロイ（`opennextjs-cloudflare deploy` → `wrangler deploy` で即時反映） |
| `/deploy-nextjs-cloudflare preview` | プレビュー環境にデプロイ（`opennextjs-cloudflare upload` → `wrangler versions upload` で Preview URL 発行。トラフィックには乗らない） |

### `--skip-build` オプション

事前ビルドチェック（`build` スクリプト）を省略します。デプロイコマンド自体が内部で再ビルドするため、この事前ビルドはあくまで早期にエラーを検知するための確認です。急ぎの再デプロイなど、ビルドが通ることが分かっている場面でのみ使用してください。

### `--allow-branch` オプション

本番デプロイ（production）は既定で現在のブランチが `main` または `master` であることを要求します。それ以外のブランチから本番デプロイする必要がある場合にこのオプションを指定します。

### ワークフロー

```
0. プリフライト → Git リポジトリ確認・フレームワーク検出・パッケージマネージャ検出・
                  デプロイスクリプト検出・wrangler 認証確認・ブランチ確認
1. 状態確認    → 未コミット変更・未プッシュコミットを確認
2. コミット    → 未コミット変更があれば /commit スキルでコミット
3. ビルド確認  → build スクリプトで事前ビルドチェック（--skip-build で省略可）
4. プッシュ    → 現在のブランチをリモートにプッシュ
5. デプロイ    → deploy（production）または upload（preview）を実行
6. 確認       → ブラウザで本番/プレビュー URL の動作を目視確認
```

未コミットの変更がある場合はプリフライトの時点でデプロイを中止します。`/commit` スキルで先にコミットを済ませてから再実行してください。

## MCP 連携（接続済みなら優先。CLI が実行骨格）

公式プラグイン `cloudflare` の MCP サーバーが接続済み（OAuth 認証済み）なら、次を CLI コマンドの代わりに使ってよい。未接続・未認証の場合は従来どおり CLI で続行する。

- **デプロイ状態確認** ─ `cloudflare-builds`（Workers Builds のビルド・デプロイ状態）。未接続時は `wrangler deployments list`。
- **本番ログ確認** ─ `cloudflare-observability`（本番 Workers ログ・分析）。未接続時は `wrangler tail`。
- **ドキュメント疑問点の確認** ─ `cloudflare-docs`（認証不要・常時使用可）。ドキュメント参照の第一手段としてよい。
- **R2 バケット等のバインディング管理** ─ `cloudflare-bindings`。未接続時は `wrangler r2 bucket create` 等の CLI。

---

## 前提要件

- **`package.json` に公式推奨のスクリプトが定義されていること**

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

  旧形式（`deploy:production` / `deploy:preview` + `wrangler deploy --env`）のプロジェクトでも `scripts/deploy.sh` はフォールバックで動作しますが、新形式への移行を推奨します（`references/setup-checklist.md` 参照）。populateCache（リモートキャッシュ投入）を `deploy` / `upload` サブコマンドが暗黙実行するため、`wrangler deploy` を直接叩く旧方式では ISR/SSG キャッシュ投入が抜ける点に注意してください。

- **`wrangler.jsonc`**（公式推奨。`wrangler.toml` も後方互換で動作するが新機能は jsonc 限定）に R2 バケット・Worker 自己参照バインディング等が設定されていること。雛形は `references/setup-checklist.md` を参照
- **Wrangler でのログインが済んでいること**（`wrangler login`。`npx wrangler whoami` で確認可能）
- Git リポジトリであること（リモート `origin` の存在が前提。ブランチは `main`/`master` を推奨）

---

## 環境変数

`scripts/deploy.sh` は環境変数で挙動を上書きできます。いずれも未指定でそのまま動作します。

| 環境変数 | 説明 | デフォルト |
|----------|------|-----------|
| `DEPLOY_PROJECT_DIR` | デプロイ対象プロジェクトのルートディレクトリ。スクリプトはここに `cd` してから処理を実行する | 実行時のカレントディレクトリ（`$(pwd)`） |
| `PRODUCTION_URL` | デプロイ完了時に表示する本番サイト URL（任意）。未指定の場合は `wrangler.jsonc` の routes / workers.dev 設定を確認するようメッセージが出る | 空 |

```bash
# 例: プロジェクトルートと本番 URL を明示して実行
DEPLOY_PROJECT_DIR=~/Projects/my-next-app PRODUCTION_URL=https://example.com \
  bash ~/.agents/skills/deploy-nextjs-cloudflare/scripts/deploy.sh production
```

---

## バージョン方針

このスキルは**常に最新版を基準**にします。実行前に以下で latest を確認し、対象プロジェクトの依存が古ければアップデートを提案します。

```bash
npm view next version
npm view @opennextjs/cloudflare version
```

| パッケージ | 2026-07-05 確認時点の latest | 備考 |
|---|---|---|
| `next` | 16.2.10 | 16.3 系は canary/preview 段階 |
| `@opennextjs/cloudflare` | 1.20.1 | peerDependencies: `next ">=15.5.18 <16 \|\| >=16.2.6"` / `wrangler ^4.86.0` |

Next 16 系を使う場合は **16.2.6 以上が peer 要件で必須**です。OpenNext の対応状況の最新確認は、上記 `npm view` に加え、接続済みなら `cloudflare-docs` MCP 検索も併用する（認証不要・常時使用可）。

---

## 注意点

### proxy.ts / Node Middleware 問題（2026-07-05 時点）

`@opennextjs/cloudflare` は Next.js の `proxy.ts`（Node Middleware 扱い）を未サポートです。バンドル生成時に `File server/middleware.js does not exist` のようなエラーが出ることがあります。

- 追跡 issue [#1082](https://github.com/opennextjs/opennextjs-cloudflare/issues/1082) は **closed（SWR 対応完了が理由）だが、proxy.ts 問題自体は未解決**です。「#1082 が閉じた = 解決済み」ではありません
- 正しい追跡先は [opennextjs/adapters-api#20](https://github.com/opennextjs/adapters-api/issues/20)（open）と [opennextjs-cloudflare#1277](https://github.com/opennextjs/opennextjs-cloudflare/issues/1277)（open）
- 回避策: `proxy.ts` → `middleware.ts` にリネームし、`export proxy` → `export middleware` に変更（2026-06-18 時点でも必要）
- `middleware.ts` はビルド時に非推奨警告が出ますが、メンテナが **Next 17 までのサポート継続**を明言しています
- 解消条件は adapters-api#20 のクローズ後の再確認です

詳細は `references/troubleshooting.md` を参照してください。

### `keep_vars: true`

`wrangler deploy` はデフォルトで Cloudflare ダッシュボードに設定した環境変数を上書き・削除します。`wrangler.jsonc` に `keep_vars: true` を設定することで、ダッシュボードの環境変数が保持されます（deploy-astro-cloudflare スキルと同じ注意点）。**これが設定されていないと、デプロイ後にサイトが動作しなくなる場合があります**。

### secrets の扱い

機密情報は `wrangler.jsonc` の `vars` に書かず、`wrangler secret put <KEY>` で登録してください。`.dev.vars` / `.env` はコミット禁止です。

### deploy-astro-cloudflare との使い分け

| 対象構成 | 使うスキル |
|----------|-----------|
| Next.js + OpenNext | **deploy-nextjs-cloudflare**（本スキル） |
| Astro + Cloudflare Workers | **deploy-astro-cloudflare** |

トリガー語（「デプロイして」「Cloudflare にデプロイ」など）が両スキルで近いため、誤発動を避ける目的で本スキルは Next.js + OpenNext 構成専用であることを明示しています。`scripts/deploy.sh` はプリフライトで `package.json` の依存を検査し、Astro 構成を検出した場合は deploy-astro-cloudflare への切り替えを案内します。

### その他

- デプロイコマンド（`deploy` / `upload`）は内部で再ビルド・リモートキャッシュ投入（populateCache）を行います。事前の `build` はあくまで早期エラー検知のためのチェックです
- 既知の無害警告: `assets.exclude`、`duplicate key "options"`（floating-ui 由来）
- アセットのアップロードに時間がかかることがあるため、デプロイのタイムアウトは 10 分（600000ms）程度に設定することを推奨します
- デプロイ後は `npx wrangler deployments list` / `npx wrangler rollback` / `npx wrangler tail` で履歴確認・ロールバック・ログ確認ができます。**ロールバックしても KV / R2 / D1 / Durable Object のデータは戻りません**
- 接続済みなら `cloudflare-observability` MCP でも本番ログ・分析を確認できます（同時接続 10 の制約を受けない選択肢として有効）

---

## 詳細

詳細な仕様・プリフライトの各ステップ・エラー対応表は、スキル本体の `SKILL.md` および `scripts/deploy.sh` を参照してください。初期セットアップの手順は `references/setup-checklist.md`、トラブルシューティングの詳細は `references/troubleshooting.md` を参照してください。

## 外部リファレンス

- [OpenNext for Cloudflare](https://opennext.js.org/cloudflare)
- [OpenNext CLI リファレンス](https://opennext.js.org/cloudflare/cli)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/)
- [Cloudflare Workers Preview URL](https://developers.cloudflare.com/workers/configuration/previews/)
