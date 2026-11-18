# `.superset/` から `.paradev/` への移行

改名前の設定フォルダ `.superset/` を `.paradev/` へ移す手順。Paradev は `.superset/` も読み続けるので移行は任意。ユーザーの承認を得てから行い、セットアップの作成とは混ぜない（移行だけで一度確かめる）。

変わらないもの: 環境変数名（`SUPERSET_ROOT_PATH` 等）と CLI 名（`superset`。`paradev` でも同じ）。形式変換（`config.json` → `config.toml`）は同時にしない。

公式 `superset:setup` にも移行の記述がある。食い違ったら公式を優先する。

## 1. 調べる（変更しない）

- `git status`: 無関係の未コミット変更は触らない。混ぜない
- `.superset/` の中身と、各ファイルの管理状態: `git ls-files .superset`、`git check-ignore -v .superset/*`
- `.paradev/` の有無と中身。pdev の `settings.json`・`agents/`・`prompts/` だけなら設定フォルダとして数えない
- `.superset` を含む参照（`node_modules`・`.git`・`dist` は除く。秘密ファイルは検索の対象にしない）
  - git 管理下: `git grep -n -I -e '\.superset' -- . ':!node_modules' ':!dist'`
  - gitignore 済みのファイルは `git grep` に出ない。`.superset/` 内の `config.*` と `*.sh`、`.gitignore`、`.git/info/exclude` を名指しで検索する
  - 見る場所: config のコマンド、`*.sh`、`.gitignore`、README・docs、`package.json` の scripts
- 個人用の上書き設定: `~/.paradev/projects/` 配下で、このリポジトリに当たるフォルダの `config.json`。フォルダの名付け方は版で変わりうるので、一覧で確かめる。中に `.superset` への参照があるか
- 結果を「移すもの / 書き換える箇所 / 変えないもの」の表でユーザーに示し、承認を取る

## 2. 移す

状況で分岐する。

| 状況 | 移し方 |
|---|---|
| `.paradev/` が無く、`.superset/` が git 管理下 | `git mv .superset .paradev` |
| `.paradev/` が無く、`.superset/` が gitignore 済み | `mv .superset .paradev` |
| `.superset/` の中で管理下と gitignore 済みが混ざる | 管理下のファイルは `git mv`、gitignore 済みのファイルは `mv` で 1 つずつ |
| `.paradev/` が pdev のファイルだけで既にある | `.superset/` のファイルを 1 つずつ `.paradev/` へ移す（管理下は `git mv`）。pdev のファイルは残す |
| `.paradev/` にも設定ファイル（`config.*`・`setup.sh` 等）がある | どちらが使われているかが分からないので止めて尋ねる |

- 移した後に `.superset/` を残さない（両方あると読み先が分かりにくい）。空になったフォルダの削除も確認を取ってから行う
- 移した結果、gitignore の効き方が変わらないかを確かめる（`.gitignore` に `.paradev/` 全体を足すと、管理したい config まで隠れないか）

## 3. 参照を書き換える

- `./.superset/` → `./.paradev/`、`$SUPERSET_ROOT_PATH/.superset/` → `$SUPERSET_ROOT_PATH/.paradev/`（config のコマンド、`*.sh`、README・docs、`package.json` の scripts）
- `.gitignore`・`.git/info/exclude` の `.superset/` 行を `.paradev/` に
- 個人用の上書き設定に参照があれば、書き換えるかを尋ねる（リポジトリの外のファイル）
- 環境変数名は変えない（`SUPERSET_ROOT_PATH` のまま）

## 4. 確かめる

- `.superset` の残りを再検索して 0 件。意図して残すもの（変更履歴の記述等）は理由付きで報告する
- `*.sh` は `bash -n`
- 使い捨てワークスペースで、新しいパスのセットアップが最後まで通る（`verify.md` の 0〜1 と 5。dev 起動の確認は、セットアップの作成時に行う）
- タブ式画面なら、セットアップのタブに新しいパスが出ていることをユーザーに画面で確かめてもらう

## 5. コミット

git 管理下の変更があれば、コミットは別に承認を取る。リネームと参照の書き換えを 1 コミットにまとめる（例: `chore: Paradev の設定フォルダを .superset から .paradev へ移す`）。

## 実績

- gitignore 済みの `.superset/`（`config.json` と `setup.sh`）を `mv` で移し、`.gitignore` 1 行・config の 1 行・`setup.sh` のコメントを書き換えた。使い捨てワークスペースで `bash "$SUPERSET_ROOT_PATH/.paradev/setup.sh"` が実行され、最後まで通った（2026-11-18）
- git 管理下の `.superset/` での移行は未実施
