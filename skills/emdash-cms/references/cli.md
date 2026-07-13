# EmDash CLI リファレンス

> [!note] 基準
> 本リファレンスは emdash 0.29.0（2026-07-10 リリース）/ 2026-07-13 検証を基準とする。作業開始前に `pnpm exec emdash --version` と公式 CLI リファレンス（`docs/src/content/docs/reference/cli.mdx`）で現行仕様を確認する。大きな乖離があれば公式 docs を優先する。

## 概要

`emdash` パッケージに CLI が同梱される。`pnpm exec emdash <command>` で実行する（バイナリ名は `emdash` と `em`、`em` は短縮形として同一の実体）。

```bash
pnpm add emdash
pnpm exec emdash --version
```

コマンドは大きく 2 系統に分かれる。

- **ローカル DB 直接操作**: `export-seed` など、実行中のサーバーを介さず SQLite/D1 ファイルを直接読む
- **リモート API 経由**: `content` / `schema` / `media` / `search` / `taxonomy` / `menu` など、稼働中の EmDash インスタンス（ローカル dev サーバーでも本番でも可）に REST でアクセスする

## 認証

リモートコマンドは次の優先順位で認証情報を解決する。

1. `--token` フラグ（コマンドラインで明示指定）
2. `EMDASH_TOKEN` 環境変数
3. `~/.config/emdash/auth.json` の保存済み認証情報（`emdash login` で保存される）
4. dev bypass ─ URL が localhost かつトークンが無い場合、自動的に dev bypass エンドポイントで認証する

ほとんどのリモートコマンドは `--url`（既定 `http://localhost:4321`）と `--token` を受け付ける。ローカル dev サーバー相手ならトークン不要。

## 共通フラグ

| フラグ | 短縮 | 説明 | 既定値 |
|---|---|---|---|
| `--url` | `-u` | EmDash インスタンスの URL | `http://localhost:4321` |
| `--token` | `-t` | 認証トークン | 環境変数 / 保存済み認証情報から取得 |
| `--json` | | JSON 出力（パイプ用） | TTY かどうかで自動判定 |

stdout が TTY のときは consola で整形出力、パイプ時や `--json` 指定時は生の JSON を stdout に出す（`jq` 等と組み合わせやすい）。

## コマンド一覧

| コマンド | 概要 | 主な用途 |
|---|---|---|
| `init` | package.json の `emdash` 設定からテンプレート DB を初期化 | 新規セットアップ |
| `types` | 稼働中インスタンスのスキーマから TypeScript 型を生成 | 型生成・CI |
| `dev` | DB マイグレーション込みで開発サーバーを起動 | ローカル開発 |
| `doctor` | DB 接続・マイグレーション・スキーマ整合性を診断 | トラブルシューティング |
| `seed` | シードファイルを適用 | 初期データ投入 |
| `export-seed` | DB のスキーマ・コンテンツをシードファイルとして書き出し | バックアップ・環境複製 |
| `secrets` | 暗号化キーの生成・fingerprint 確認 | 本番デプロイ準備 |
| `auth`（非推奨エイリアス） | `login` の旧名 | 使わない（`login` を使う） |
| `login` | OAuth Device Flow でログイン | リモート操作の認証 |
| `logout` | 保存済み認証情報を削除 | 認証解除 |
| `whoami` | 現在の認証ユーザーを表示 | 認証確認 |
| `content` | コンテンツ項目の CRUD・公開操作 | コンテンツ運用 |
| `schema` | コレクション・フィールドの管理 | スキーマ変更 |
| `media` | メディア項目の管理 | メディア運用 |
| `search` | 全文検索 | コンテンツ検索 |
| `taxonomy` | タクソノミー・タームの管理 | カテゴリ・タグ運用 |
| `menu` | ナビゲーションメニューの管理 | メニュー運用 |
| `plugin` | マーケットプレイス配布用プラグイン操作（init/bundle/validate/publish/login/logout） | プラグイン公開 |

> [!important] `emdash import:wordpress` や `emdash migrate` は存在しない
> WordPress 移行は CLI コマンドではなく、admin dashboard のインポートウィザードまたは REST `/_emdash/api/import/wordpress/` から行う。詳細は `wordpress-migration.md` を参照。

## 主要コマンドの詳細

### `emdash dev`

```bash
pnpm exec emdash dev [options]
```

| オプション | 短縮 | 説明 | 既定値 |
|---|---|---|---|
| `--database` | `-d` | DB ファイルパス | `./data.db` |
| `--types` | `-t` | 起動前にリモートから型生成 | `false` |
| `--port` | `-p` | dev サーバーのポート | `4321` |
| `--cwd` | | 作業ディレクトリ | カレントディレクトリ |

起動時に保留中のマイグレーションを適用し、`--types` 指定時は `EMDASH_URL`（または `package.json` の `emdash.url`）が指すリモートから型を生成してから Astro dev サーバーを起動する。

### `emdash types`

```bash
pnpm exec emdash types --output src/types/emdash.ts
```

稼働中インスタンスのスキーマから TypeScript 型定義を生成する。既定の出力先は `.emdash/types.ts`。同時に `.emdash/schema.json`（生スキーマの JSON）も書き出す。ローカル dev サーバーだけでなく、`--url` でデプロイ済みサイトを直接指すこともできる（スキーマ進化後の型再生成など。`cloudflare-deploy.md` の「スキーマ進化」参照）。

### `emdash doctor`

DB 接続・マイグレーション適用状況・スキーマ整合性を診断する（正確なオプション体系は公式ドキュメントの記載が薄いため、実行前に `--help` で確認する）。

### `emdash seed` / `emdash export-seed`

`export-seed` はローカルの SQLite ファイルを直接読み、シードファイル（JSON）として書き出す。

```bash
pnpm exec emdash export-seed --with-content > seed.json
```

| オプション | 短縮 | 説明 | 既定値 |
|---|---|---|---|
| `--database` | `-d` | DB ファイルパス | `./data.db` |
| `--cwd` | | 作業ディレクトリ | カレントディレクトリ |
| `--with-content` | | コンテンツも含める（全体または `posts,pages` のようなカンマ区切り指定） | 含めない |
| `--no-pretty` | | JSON 整形を無効化 | `false` |

出力にはサイト設定・コレクション定義・タクソノミー・メニュー・ウィジェットエリアが含まれ、`--with-content` 指定時はエントリ（`$media` 参照・`$ref:` 記法つき）も含まれる。デプロイ済みサイトのスキーマを最新化して repo に取り込む用途にも使う（`cloudflare-deploy.md` の「スキーマ進化」節を参照）。

### `emdash secrets generate`

デプロイ用の `EMDASH_ENCRYPTION_KEY` を生成する。このキーはプラグインの secrets（webhook トークン、Turnstile キー等）を保存時に暗号化するために使う。

```bash
pnpm exec emdash secrets generate
pnpm exec emdash secrets generate --write .env
```

`--write` は既存エントリがあると失敗する（`--force` で上書き）。デプロイ済みの暗号化データがある状態でキーを差し替えると、それらの secrets が復号不能になるため、この保護は意図的な挙動。

### `emdash secrets fingerprint <key>`

キーの値を晒さずに 8 文字の fingerprint（kid）を表示する。CI で「正しいキーがデプロイされたか」を検証するのに使う。

```bash
pnpm exec emdash secrets fingerprint emdash_enc_v1_...
```

### `emdash plugin`

マーケットプレイス配布用プラグインの操作コマンド。サブコマンド: `init` / `bundle` / `validate` / `publish` / `login` / `logout`。

> [!warning] `emdash plugin` と `emdash-plugin` は別物
> `emdash plugin`（本 CLI のサブコマンド）はマーケットプレイス配布のためのビルド・検証・公開を担う。一方 `@emdash-cms/plugin-cli` が提供する別バイナリ `emdash-plugin`（build/dev/validate）はプラグイン開発時のローカルビルド用。混同しないこと。

## `content` / `schema` / `media` / `search` / `taxonomy` / `menu` サブコマンド

これらはリモート API（`EMDashClient` 経由）に対する CRUD 操作群。代表例のみ挙げる（全オプションは公式 CLI リファレンスを参照）。

```bash
# コンテンツ
pnpm exec emdash content list posts --status published --limit 10
pnpm exec emdash content get posts 01ABC123          # レスポンスに _rev トークンを含む
pnpm exec emdash content update posts 01ABC123 --rev <token> --data '{"title":"Updated"}'
pnpm exec emdash content publish posts 01ABC123

# スキーマ
pnpm exec emdash schema list
pnpm exec emdash schema add-field posts subtitle --type string --label "Subtitle"

# メディア
pnpm exec emdash media upload ./photo.jpg --alt "A sunset"

# 検索・タクソノミー・メニュー
pnpm exec emdash search "hello world" --collection posts
pnpm exec emdash taxonomy add-term categories --name "Tech" --slug tech
pnpm exec emdash menu get primary
```

`content update` は直前の `get` で取得した `_rev` トークンを渡す必要がある（未確認の変更を上書きしないための楽観ロック）。サーバー側で変更が検知されると 409 Conflict が返るので、再取得してからやり直す。

## 生成ファイル

| ファイル | 内容 |
|---|---|
| `.emdash/types.ts` | コレクションごとの TypeScript インターフェース（`emdash types` が生成、手動編集しない） |
| `.emdash/schema.json` | ツール向けの生スキーマ書き出し |

## 環境変数

| 変数 | 説明 |
|---|---|
| `EMDASH_DATABASE_URL` | DB URL（`dev` コマンドが自動設定） |
| `EMDASH_TOKEN` | リモート操作用の認証トークン |
| `EMDASH_URL` | `types` / `dev --types` の既定リモート URL |
| `EMDASH_ENCRYPTION_KEY` | プラグイン secrets の暗号化キー（オペレーター提供、DB には保存されない。`emdash secrets generate` で生成） |
| `EMDASH_PREVIEW_SECRET` | プレビュー HMAC シークレットの上書き（未設定時は options テーブルに自動生成・永続化） |
| `EMDASH_IP_SALT` | コメント投稿者 IP ハッシュ用ソルトの上書き |
| `EMDASH_AUTH_SECRET` | レガシー。設定されていれば IP ソルトのソースとして使われる（既存インストールの互換性維持用）。新規インストールでは設定しない |

## package.json スクリプト例

```json title="package.json"
{
  "scripts": {
    "dev": "emdash dev",
    "types": "emdash types",
    "export-seed": "emdash export-seed",
    "db:reset": "rm -f data.db"
  }
}
```

## Exit Code

| コード | 意味 |
|---|---|
| `0` | 成功 |
| `1` | エラー（設定・ネットワーク・DB のいずれか） |

## 参照ドキュメント

- 公式 CLI リファレンス: `docs/src/content/docs/reference/cli.mdx`（`init` / `doctor` / `seed` / `plugin` の 4 コマンドは実装 `packages/core/src/cli/index.ts` には存在するが、この公式ドキュメントページには記載が無い。正確なオプションが必要な場合は `--help` で確認する）
