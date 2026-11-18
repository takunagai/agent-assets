# 技術スタック別の手掛かり

網羅より「何を見て決めるか」を優先する。ここに無いスタックも、同じ観点（ロックファイル → install、gitignore 済みで dev に要るもの → 複製、dev とポート）で決める。コマンドは代表例。プロジェクトの README・CI の手順があればそちらを優先する。

## 依存関係

| 手掛かり | install の定番 | 注意 |
|---|---|---|
| `pnpm-lock.yaml` | `pnpm install --frozen-lockfile` | `package.json` の `packageManager` で版を固定していれば corepack か mise の版を使う |
| `package-lock.json` | `npm ci` | `node_modules` を消してから入れ直す。速さが要るなら `npm install` との違いを説明して選んでもらう |
| `yarn.lock` | v1: `yarn install --frozen-lockfile` / Berry: `yarn install --immutable` | `.yarnrc.yml` があれば Berry |
| `bun.lock` / `bun.lockb` | `bun install --frozen-lockfile` | |
| `mise.toml` / `.mise.toml` / `.tool-versions` | `mise install`、以降のコマンドは `mise exec -- <cmd>` | `[tools]` だけなら `mise trust` は不要（pitfalls 11） |
| `.tool-versions`（asdf） | `asdf install` | mise があれば mise でも読める |
| `uv.lock` | `uv sync --frozen` | `.venv` はワークスペースごとに作られる |
| `poetry.lock` | `poetry install` | 仮想環境の置き場（`virtualenvs.in-project`）を確かめる |
| `requirements.txt` | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` | 1 行にせず `setup.sh` の中で書く |
| `Gemfile.lock` | `bundle install` | |
| `go.sum` | `go mod download` | |
| `Cargo.lock` | `cargo fetch` | ビルドは重い。毎回要らなければ setup に入れない |
| `composer.lock` | `composer install` | |

## gitignore 済みで dev に要るもの

`git ls-files --others --ignored --exclude-standard --directory` で名前だけを出し、その中から選ぶ。中身は読まない。

| 種類 | よくある名前 | 扱い |
|---|---|---|
| 秘密ファイル | `.env`・`.env.local`・`.env.development.local`・`.dev.vars`（Wrangler）・`config/master.key`（Rails）・`*.pem` | `SECRET_FILES` に入れて複製する。メインに無ければ skip を表示する。`.env.example` から自動で作らない（値が要るので、ユーザーに任せる） |
| ローカル DB・ストレージ | `.wrangler/state`（D1・R2・KV は SQLite）・`*.sqlite`・`*.sqlite3`・`db.sqlite3`（Django）・`database/database.sqlite`（Laravel）・`prisma/dev.db`・`storage/` | 状態をコピーするか、空で始めてマイグレーションとシードを流すかを尋ねる。コピーなら `STATE_DIRS` に入れる。単独の SQLite ファイルは、その親フォルダを指定するか、雛形の関数を 1 ファイル用に直す |
| 生成物 | `node_modules`・`.venv`・`dist`・`.next`・`.astro` | 複製しない。install やビルドで作る |

空で始める場合のマイグレーションやシードを `setup.sh` に入れるかは、ユーザーに尋ねる（ワークスペースごとのローカル DB だけが対象で、共有の DB に向いていないことを確かめる）。

## サービス

| 手掛かり | 定番 | 注意 |
|---|---|---|
| `compose.yaml` / `docker-compose.yml` | `docker compose up -d` | プロジェクト名はフォルダ名から決まるので、ワークスペースごとに別のコンテナになる。ホスト側のポートは衝突するので、メインと同時に動かすなら上書きが要る。止めるのは `teardown`（`config.toml` なら `[archive]`）に `docker compose down` |

## dev とポート（確認で使う）

| フレームワーク | 別ポートの指定 | 注意 |
|---|---|---|
| Vite | `vite --port 5174 --strictPort` | `--strictPort` が無いと、使用中なら黙って次の番号へずれる |
| Astro | `astro dev --port 4322` | Astro 7 の `astro dev` はバックグラウンド化して即終了する。止めるのは `astro dev stop`（pitfalls 9） |
| Next.js | `next dev -p 3001` | |
| Wrangler | `wrangler dev --port 8788` | |
| Rails | `bin/rails server -p 3001` | |
| Django | `python manage.py runserver 8001` | |
| Laravel | `php artisan serve --port=8001` | |

パッケージマネージャー経由で引数を渡すとき: `pnpm dev --port 4322`、`npm run dev -- --port 4322`。

## モノレポ

| 手掛かり | 扱い |
|---|---|
| `pnpm-workspace.yaml`・`turbo.json`・`nx.json`・`package.json` の `workspaces` | install はルートで 1 回。秘密ファイルは各 app のフォルダにあることが多い（`apps/web/.env` 等）。`SECRET_FILES` にはルートからの相対パスで書く |
| app ごとに作業フォルダが違うコマンド | `setup.sh` の中で `(cd apps/web && <cmd>)` のようにサブシェルで移動する。設定側の `cwd` は公式の形式に従う |
