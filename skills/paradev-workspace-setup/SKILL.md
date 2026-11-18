---
name: paradev-workspace-setup
description: "Paradev（旧 Superset）でワークスペースを作るたびに走るセットアップ（setup.sh と設定の 1 行）をリポジトリに合わせて作り、使い捨てワークスペースで dev 起動まで確かめて片付ける。公式 superset:setup の形式・手順の上に、設定画面の「1 行 = 1 コマンド」の落とし穴、秘密ファイルを値を読まずに複製する規律、ローカル DB 等の状態の入れ替えコピーと検査、skip 表示、.superset/ から .paradev/ への移行提案、日本語での案内と最後の説明を足す。トリガー: 「Paradev のセットアップスクリプトを作って」「ワークスペース作成時に自動で準備したい」「ライフサイクルスクリプト」「setup 欄に入れるスクリプト」「Superset の setup.sh」「新しいワークスペースで .env が無い・dev が動かない」。NOT for: クラウド環境（superset:environment）、config の形式だけの質問（superset:setup）、Paradev 以外のツールの worktree 設定。"
---

# Paradev ワークスペースのセットアップ作成

新しいワークスペース（git worktree）が、依存関係・秘密ファイル・ローカルの状態がそろった状態で立ち上がるようにする。本体は `setup.sh` に置き、設定には呼び出しの 1 行だけを書く。dev を起動して主要ページがメインと同じ中身で出るところまで確かめる。

## 役割分担（公式が正本）

| 公式 `superset:setup` と実物の CLI が正本 | このスキルが足す |
|---|---|
| 設定の置き場・形式（`config.json` / `config.toml`）・キーとテーブル・環境変数・形式変換・コミットの流れ | 設定画面の判定と「1 行だけ書く」方針、壊れにくい `setup.sh`（秘密ファイル・状態コピー・検査・skip 表示）、dev 起動までの確認と片付け、`.superset/` → `.paradev/` 移行の提案、日本語の案内と最後の説明 |

形式の仕様はこのスキルに書き写さない（公式は移行中で、すぐ古くなる）。公式とこのスキルが食い違ったら公式と実物を優先し、食い違いをユーザーに伝える。

## 進め方の約束

- ユーザーとは日本語で話す。各段階の前に何をするかを 1 文で言う
- 選択肢は AskUserQuestion で出し、推奨案を先頭にして `(Recommended)` を付ける。事実を尋ねる質問（どちらの画面か等）には推奨を付けない
- ファイルの書き込み、ワークスペースの作成、フォルダの移行、コミットは、内容を示して承認を得てから行う
- **秘密ファイル（`.env` 系・`.dev.vars` 系・鍵ファイル等）は存在と名前だけを確かめる。** 中身を表示・Read・grep・cat しない。検索の対象からも外す。複製は `setup.sh` の中でファイルごと行い、値を会話・config・コミット・ログに書かない。ユーザーのグローバル指示に秘密の扱いの規律があれば、それを優先する

## 0. 公式を読み込む

1. 公式スキルを読む: `~/.claude/skills/superset/skills/setup/SKILL.md`（Paradev デスクトップアプリが起動時に配る）。無ければ Skill ツールで `superset:setup` を呼ぶ。どちらも無ければ、Paradev アプリが未起動か未導入とユーザーに伝えて止める
2. `superset --version` と `superset workspaces create --help` で CLI を確かめる（`paradev` でも同じ）
3. 公式から読み取るのは、形式・置き場・環境変数・規則。進め方（尋ね方・確認の範囲・コミットの扱い）はこのスキルに従う

## 1. リポジトリを調べる（変更しない）

| 見るもの | 見方 | 決まること |
|---|---|---|
| ロックファイル・ランタイムの版管理 | ルートの一覧。`references/stack-recipes.md` の表 | install のコマンド、PATH の保険 |
| gitignore 済みで dev に要るもの | `git ls-files --others --ignored --exclude-standard --directory`（名前だけ出る） | 複製する秘密ファイル・状態フォルダの候補 |
| ローカルの状態 | 上の結果のうち DB・ストレージのフォルダ（例: `.wrangler/state`、`*.sqlite`） | 状態をコピーするか空で始めるか |
| サービス | `compose.yaml` / `docker-compose.yml` 等 | setup で起動するか、`teardown` で止めるか |
| dev コマンドとポート | `package.json` の scripts、フレームワークの設定 | 確認で使うコマンドと別ポートの指定方法 |
| モノレポ | `pnpm-workspace.yaml`・`turbo.json`・各 app の秘密ファイル | 作業フォルダ、複製するパス |
| 既存の設定フォルダ | `.paradev/`・`.superset/` の中身、各ファイルの `git ls-files` / `git check-ignore -v` | 設定の形式、共有かマシンだけか、移行の要否 |
| 既存の setup の中身 | 設定の `setup` に複数の要素があるか | 本体を `setup.sh` へ移す必要 |

## 1.5 `.superset/` なら `.paradev/` への移行を提案する

設定フォルダが改名前の `.superset/` だけのとき、`.paradev/` への移行を提案する。Paradev は `.superset/` も読み続けるので移行は任意。承認されたら、セットアップの作成より先に移行だけを行い、確認を 1 回挟む。手順・分岐・確認は `references/migrate-superset-to-paradev.md`。断られたら `.superset/` のまま進め、以降の `.paradev/` を読み替える。

## 2. 決めることを尋ねる

AskUserQuestion でまとめて尋ねる。

1. **どちらの設定画面か**（事実の確認）
   - タブ式: 設定 → プロジェクト →「プロジェクトのライフサイクルスクリプト」に、セットアップ・ティアダウン・実行の 3 タブと入力欄 1 つ
   - ファイル全体を編集する「Workspace config」
   - 画面は使っていない・分からない（タブ式として扱い、ファイルで確かめる）
2. **書く場所**。既存の設定フォルダの管理状態に合わせた方を推奨にする。新規なら、共同作業者がいればチームで共有、1 人ならこのマシンだけを推奨にする
   - チームで共有: 設定と `setup.sh` をコミットする。ブランチごとに版が付いてくる。公開リポジトリなら `setup.sh` も公開される
   - このマシンだけ: 設定フォルダごと gitignore するか、個人用の `config.local.*` に書く。`setup.sh` もメインにだけ置く
3. **複製するもの**（multiSelect）: 1 で見つけた秘密ファイルと状態フォルダを名前で並べる
4. **判断が要る所**（あれば）: 状態をメインからコピーするか空で始めるか、サービスを setup で起動するか等

## 3. `setup.sh` と設定の 1 行を書く

1. `references/setup-template.sh` を元に、「要編集」の箇所を埋め、使わない節を消す。既存の setup に複数のコマンドがあれば、それを `setup.sh` へ移す
2. 設定に入れる 1 行を決める

   | 書く場所 | `setup.sh` の場所 | 設定の 1 行 |
   |---|---|---|
   | チームで共有 | `.paradev/setup.sh`（コミット） | `bash ./.paradev/setup.sh` |
   | このマシンだけ | `.paradev/setup.sh`（gitignore 済み。メインにだけある） | `bash "$SUPERSET_ROOT_PATH/.paradev/setup.sh"` |

   共有の設定にマシンだけの手順を足すときは、`setup.local.sh` 等の別名にして `.git/info/exclude` で無視し、`config.local.*` から呼ぶ。
3. 書き先を画面に合わせる
   - **タブ式**: 中身は設定フォルダの `config.json`（セットアップ = `setup` 配列、1 行 = 1 要素）。画面に 1 行を貼ってもらうか、`setup` を 1 要素の配列にしてファイルに書く（どちらでも画面とファイルは同じものになる）。**`setup.sh` の本体や複数行を欄に直接貼らせない**（`references/pitfalls.md` の 1）
   - **Workspace config・ファイルだけ**: 公式の形式で書く
   - 既存の形式を保つ。`config.json` があるのに `config.toml` を新しく足さない（両方あると `config.json` が無視され、タブ式画面の中身が効かなくなる）。形式変換は公式の手順にあり、望まれたら別の変更として行う
   - 1 行の中の引用符は形式に合わせる。JSON は `\"` でエスケープ、TOML はシングルクォートの文字列にすると楽
4. このマシンだけなら、設定フォルダか `setup.sh` が無視されていることを `git check-ignore -v` で確かめる。無視されていなければ `.gitignore` に足すか `.git/info/exclude` に足すかを尋ねる
5. `setup.sh` 全文・設定の差分・置き場所を示し、承認を得てから書く

## 4. 構文を確かめる

- `bash -n <setup.sh>`。`shellcheck` があれば走らせ、警告を読んで直すか理由を残す
- `config.json` は `python3 -m json.tool <file> >/dev/null`。`config.toml` は Python 3.11 以上の `tomllib` で読めるかを確かめる（無ければ次の確認で代える）

## 5. 確かめる（dev 起動まで）

詳細と CLI は `references/verify.md`。

1. 作るもの（ワークスペース名・ブランチ名・起点のブランチ・終わったら消すこと）を示し、作成の承認を取る。チームで共有なら、新しいワークスペースは自分のブランチの設定を読むので、先にブランチへのコミットが要る（コミットも別に承認を取る）
2. 使い捨てワークスペースを作り、「Workspace Setup」端末を `setup done` か `setup failed` が出るまで読む。失敗したら直して作り直す
3. ワークスペース側で dev を別ポートで起動する。起動の判定は終了コードではなく、ポートの LISTEN と HTTP 応答で行う
4. 主要ページの応答と中身（件数・見出し等）をメインと比べる。メインの dev が動いていなければ、自分で起動して比べ、終わったら止める
5. 状態をコピーする構成なら、メインの dev を動かしたままもう一度作成し、検査が通るかを確かめる。ユーザーが起動した dev には触らない
6. 片付け: 自分で起動したプロセスを止めてポートの解放を確かめる → `superset workspaces archive --local <id>` → `git branch -D <ブランチ>` → `git worktree list` が作成前と同じかを確かめる

## 6. 説明して報告する

最後に、次をユーザーに説明する。

- `setup.sh` の各ステップが何をするか
- ファイルの場所と、設定に入れた 1 行（タブ式なら、どのタブに何が入っているか）
- コミットされるものか、このマシンだけのものか
- 注意点: ワークスペースの状態は作成時点でメインから分かれる（以後の変更は互いに届かない）。秘密ファイルを複製している（ワークスペースを archive すると worktree ごと消える）。メインの dev が書き込み中に作ると検査で止まることがあり、そのときはメインの dev を止めて作り直す
- 後から変える方法: `setup.sh` を直す（設定の 1 行はそのまま）。複製するものを増やすときは配列に足す。形式変換や `.paradev/` への移行は別の変更として行う
- 確認の結果（何を比べて何が一致したか）と、確かめていないこと

チームで共有の場合は、コミットとプルリクエストを提案する（push は承認を得てから）。

## 参考資料

- `references/setup-template.sh` ─ 雛形
- `references/pitfalls.md` ─ 落とし穴と根拠
- `references/stack-recipes.md` ─ 技術スタック別の手掛かりと定番コマンド
- `references/verify.md` ─ 確認の手順と CLI
- `references/migrate-superset-to-paradev.md` ─ `.superset/` からの移行
