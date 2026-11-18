# 確認の手順（使い捨てワークスペースで dev 起動まで）

`superset` は `paradev` でも同じ。フラグは版で変わりうるので、最初に `superset workspaces create --help` 等で現存を確かめる（2026-11-18、CLI 2.0.9 で確認したもの）。

## 0. 作成の前に

1. 作るものをユーザーに示し、承認を取る: ワークスペース名・ブランチ名（例: `setup-test`）・起点のブランチ・終わったら archive してブランチを消すこと・メインの dev には触らないこと
2. 片付け後の比較用に、いまの worktree 一覧を控える: `git worktree list --porcelain`（ユーザーが使っている他のワークスペースを消さないため）
3. ブランチ名が空いているかを確かめる: `git branch --list setup-test`。使われていれば別名にする
4. プロジェクト ID を取る: `superset projects list --json`。リポジトリのパスで照合する
5. 起点のブランチを決める
   - このマシンだけ（設定と `setup.sh` がメインにだけある）: 今のブランチ
   - チームで共有: 設定と `setup.sh` をコミットしたブランチ。新しいワークスペースは自分のブランチの設定を読むので、未コミットのままでは確かめられない（コミットは別に承認を取る）

## 1. 作ってセットアップの完了を待つ

```bash
superset workspaces create --local --project <project-id> --name setup-test \
  --branch setup-test --base-branch <起点のブランチ> --skip-branch-prefix --json
```

- 戻り値の JSON から、ワークスペースの ID と「Workspace Setup」端末の ID を拾う。キー名は版で変わりうるので実物を見る。端末の ID が無ければ `superset terminals list --local --workspace <id> --json` で探す
- 完了を待つ（雛形は最後に `setup done`、失敗時に `setup failed` を出す）:

```bash
superset terminals wait --local --workspace <id> --terminal <terminal-id> \
  --match 'setup (done|failed)' --timeout 900
superset terminals read --local --workspace <id> --terminal <terminal-id> --max-lines 40
```

- 末尾の数十行だけを読む。`copied:` と `skip:` の行が想定どおりかを見る（想定外の `skip:` は理由を確かめる）
- 失敗したら、原因を直して archive → ブランチ削除 → 作り直す
- worktree の場所は `git worktree list` で取る（例: `~/.paradev/worktrees/<repo>/<branch>`）

## 2. ワークスペース側で dev を起動する

1. ポートが空いているかを確かめる: `lsof -nP -iTCP:<port> -sTCP:LISTEN`
2. worktree のフォルダで、メインと違うポートを明示して dev をバックグラウンドで起動する（指定方法は `stack-recipes.md`）。起動したプロセスの PID を控える
3. 起動の判定は終了コードではなく、ポートの LISTEN と HTTP 応答で行う（すぐ戻る dev があるため）
   - `lsof -nP -iTCP:<port> -sTCP:LISTEN` が出るまで数秒おきに待つ（上限を決める）
   - `curl -s -o /dev/null -w '%{http_code}' http://localhost:<port>/` が 200 系か

## 3. メインと比べる

- 主要ページ（トップ、一覧、状態を使うページ）を 2〜4 個選ぶ。ユーザーに聞くか、ルーティングから選ぶ
- メインの dev が動いていればそれと比べる。動いていなければ自分で起動して比べ、終わったら止める（ユーザーに一言伝える）
- 比べるのは HTTP ステータスと、中身の要点（一覧の件数、見出し、`<title>`）。HTML 全体の一致は求めない（dev が差し込むスクリプト・トークン・時刻で必ず違う）。ページ全体を会話に出さない
- 状態をコピーする構成なら、状態に由来する中身（記事の件数等）が一致していることを確かめる

比べ方の例（Python。スクリプトをファイルに書いて実行すると、出力を短く保てる）:

```python
import re, sys, urllib.request

main_port, workspace_port, paths = sys.argv[1], sys.argv[2], sys.argv[3:]
marker = re.compile(r"<article\b")  # 要編集: 件数を数える目印

def summarize(port, path):
    with urllib.request.urlopen(f"http://localhost:{port}{path}", timeout=10) as response:
        body = response.read().decode("utf-8", "replace")
        title = re.search(r"<title>(.*?)</title>", body, re.S)
        return response.status, (title.group(1).strip() if title else ""), len(marker.findall(body))

for path in paths:
    main, workspace = summarize(main_port, path), summarize(workspace_port, path)
    print(path, "一致" if main == workspace else f"不一致 main={main} workspace={workspace}")
```

## 4. 状態をコピーする構成の追加確認

メインの dev を動かしたまま、もう一度ワークスペースを作り（例: `setup-test-2`）、セットアップが検査を通るかを確かめる。

- ユーザーが起動したメインの dev には触らない。動いていなければ自分で起動し、終わったら止める
- 検査で止まったら、メインの dev を止めて作り直す運用になることを説明に含める

## 5. 片付け

1. 自分で起動したプロセスを止める。PID を `kill` するか、フレームワークの停止コマンド（例: `astro dev stop`）を worktree で実行する
2. ポートの解放を確かめる: `lsof -nP -iTCP:<port> -sTCP:LISTEN` が何も出さない
3. `superset workspaces archive --local <id>`。worktree のフォルダは未コミットの変更ごと消え、ブランチは残る。archive の前に、設定の `teardown`（`[archive]`）が走ることも確かめておく
4. `git branch -D setup-test`（作った確認用ブランチだけ。チームで共有の設定をコミットしたブランチは消さない）
5. `git worktree list --porcelain` が、手順 0 で控えた一覧と同じかを確かめる

## 報告に含めること

- 作成から完了までの時間（1 回目と、依存関係のキャッシュが効いた 2 回目があれば両方）
- `copied:` / `skip:` の結果
- 比べたページと一致・不一致
- 状態をコピーする構成なら、メインの dev 稼働中の作成で検査が通ったか
- 片付けの結果（プロセス・ポート・worktree・ブランチ）
- 確かめていないこと
