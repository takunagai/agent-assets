# _lesson-methods（授業メソッド共有リソース）

Cloudflare 学習の 2 スキル（授業運営 `cloudflare-lesson-tutor` と ノート保存 `cloudflare-lesson-note`）が共通で参照する教授法リソースを置く場所。`_` 始まりのため `SKILL.md` を持たず、スキルとしてはロードされない共有ライブラリ（CLAUDE.md の `_image-styles` と同じ扱い）。

## 収録物

- `explain-hard-concepts.md` ─ 難解な概念を平易な言葉で嫌味なく伝えるための実行ガイド（既知から入る／多義語を即定義／抽象と具体を往復／未知を既知に着地／マウント検査）。授業の解説とノート整形の両方で使う。

## 参照のしかた

各スキルの `references/explain-hard-concepts.md` は、このディレクトリへの**相対 symlink**（`../../_lesson-methods/explain-hard-concepts.md`）。実体はここ 1 箇所のみで、各スキルへコピーしない（定義のズレを防ぐ）。**編集は必ずこの実体に対して行う**。スキル本体の symlink を張れば依存はリポ内相対リンクで解決するため、このディレクトリ自体を個別に symlink 登録する必要はない。
