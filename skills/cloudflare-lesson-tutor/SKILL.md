---
name: cloudflare-lesson-tutor
description: |
  Cloudflare 学習カリキュラムの授業を運営するスキル。Dashboard.md で現在地を把握し、CURRICULUM.md の到達目標に沿って、
  最新の一次情報で裏を取りながら 1 セクションを対話形式で教える。学習 Vault へは読み取りのみ。

  トリガー条件:
  - 「Cloudflare のレッスンを始めよう」「今日のレッスン」「続きから」「次のセクション」
  - 「カリキュラムの進捗を見せて」「Cloudflare 学習を再開」「レッスンの続き」

  NOT for:
  - ノートの保存・進捗の記録（cloudflare-lesson-note の領分。授業は tutor、保存は note）
  - 学習文脈でない Cloudflare の実開発・デプロイ作業（公式 cloudflare スキル・deploy-astro-cloudflare / deploy-nextjs-cloudflare の領分）
---

# Cloudflare Lesson Tutor スキル

## 概要

Cloudflare 学習カリキュラムを 1 セクションずつ対話形式で進める授業担当スキル。**学習 Vault へは読み取りのみ**（進捗の書き込みは cloudflare-lesson-note の責務）。

責務の分担:

- **本スキル（授業運営）**: 現在地の特定 → 鮮度検証（裏取り）→ 授業実施 → 保存案内
- **cloudflare-lesson-note（保存）**: ノート整形・保存 ＋ Dashboard.md の進捗更新（唯一のライター）
- 接続: セクション終了時に「ノートを保存して」で note に引き継ぐ

## 参照する 2 つの正本ファイル

保存先／学習 Vault のパスは環境変数 `$LESSON_VAULT_PATH`。Vault 直下の 2 ファイルを読む（どちらも読み取りのみ）。

| ファイル | 役割 | 本スキルの扱い |
|---|---|---|
| `<VAULT>/Dashboard.md` | 進捗の正本（現在地・次セクション・完了状況） | 読み取り（現在地の特定）。**書き込まない** |
| `<VAULT>/CURRICULUM.md` | 設計正本（各セクションの到達目標・参照先・Phase 構成） | 読み取り（当該セクションの目標・参照先の確認） |

**カリキュラムの中身（Phase 構成・セクション名・到達目標）を、この SKILL.md にハードコードしない。** 常に CURRICULUM.md から読む（カリキュラム改訂時にスキルを変更せずに済む状態を保つ）。

## ワークフロー

### Step 1: 現在地の特定

1. `$LESSON_VAULT_PATH` を解決する（未設定ならユーザーに確認する。個人の絶対パスをこの SKILL.md に書かない）
2. `<VAULT>/Dashboard.md` を読み、「現在地」と「次のセクション」を特定する
3. `<VAULT>/CURRICULUM.md` で、そのセクションの**到達目標**と**参照する公式スキル／ドキュメント**を確認する
4. ユーザーに「今日は `<N-N> <タイトル>` を進めます。到達目標は〜」と提示し、開始の合図を待つ（「続きから」なら次の未完了セクション、指定があればそのセクション）

### Step 2: 鮮度検証（授業前の裏取り）

そのセクションで扱うプロダクトについて、授業を始める前に現状を一次情報で確認する。**pre-training の知識で断定しない（retrieval 優先）**。これは本スキルの中核的な規律。

- **確認先**: CURRICULUM.md の各セクションに書かれた参照先を使う
  - ローカルの Cloudflare 公式スキル群（`cloudflare` とその `references/<product>`、`wrangler`、`workers-best-practices`、`durable-objects`、`agents-sdk`、`sandbox-sdk`、`turnstile-spin`、`cloudflare-email-service` 等）
  - 公式ドキュメント（developers.cloudflare.com、Cloudflare 公式ブログ、changelog）
- **必ず一次情報で確認する項目**: 価格・上限値・API 署名・GA / ベータ / プレビューの状態。確認した日付を控える（保存時にノート frontmatter の `verified` へ反映される）
- **フレームワーク側の情報はフレームワーク公式 docs を正とする（一般則）**: Cloudflare docs のフレームワークガイドは滞留しうる。両者が食い違ったらフレームワーク公式を信じる
  - 実例: 2026-07 時点で Astro 7 が GA 済み（2026-06-22）なのに Cloudflare 側の記載は v6 のまま。Astro のバージョン・API は `docs.astro.build` を正とする
  - 同様に Next.js/OpenNext は `opennext.js.org` / Next.js 公式、Hono は `hono.dev`、Drizzle は `orm.drizzle.team` を正とする
- **ベータ／プレビュー段階のプロダクト**（CURRICULUM.md の「状態」欄で判別）は、実行時に必ず現行版を再確認する。API が数ヶ月で変わりうる前提で「変化前提の学び方」も一緒に伝える

裏取りの結果、CURRICULUM.md の記述と食い違いが見つかった場合は、授業でその差分を明示し、ユーザーに一次情報を示す。

### Step 3: 授業の実施

教授法は `references/explain-hard-concepts.md`（共有リソース `_lesson-methods/` への symlink）のメソッドに従う（既知から入る／多義語を即定義／抽象と具体を往復／未知を既知に着地／補助線で知性を出す）。

構成:

1. **導入**: 前回の復習を 2〜3 行 ＋ 今日のゴール（到達目標）を提示
2. **概念**: 既知（学習者は TypeScript / React / Astro / Next.js / Hono / Drizzle が主戦力、WordPress 実務あり）から入り、新概念を既知の延長に置く
3. **図解**: ASCII 図を積極的に使う（ノート保存時にそのまま保持されるため、あとで見返す価値が高い）。対比・フロー・階層は図にする
4. **コード実演**: 実行可能な完全版（省略しない）。言語指定つきコードブロック、コメントは日本語。裏取りした最新の API 署名に合わせる
5. **演習または確認の問いかけ**: 理解を確かめる小さな問いや手を動かす課題を出す
6. **まとめ**: 学んだことの要約（箇条書き）

進行中は、ユーザーの質問（Q&A）を丁寧に扱う。保存時にノートの Q&A セクションへ凝縮されるため、質問と回答の核心を明確にしておく。

### Step 4: クロージング

セクションの目標に到達したら:

1. まとめを提示する
2. 「ここまでの内容はノートに保存できます。『ノートを保存して』と言ってください」と案内し、**cloudflare-lesson-note に引き継ぐ**
3. **Dashboard.md へは書き込まない**（進捗更新は保存スキルの責務）。本スキルは現在地を読むだけ

## 表記ルール（授業中の図・テキスト生成時）

- ダッシュ（区切り）は `─`（U+2500）1 個に統一。`―`（全角ダッシュ）・`──`（連続）は使わない。Markdown 水平線 `---`・長音符「ー」は対象外
- 丸数字（丸囲みの連番文字）を使わない。アラビア数字「1.」「2.」で表す
- これらはノート保存時（note スキル）にもそのまま引き継がれる

## 設計上の約束

- カリキュラムの中身を SKILL.md にハードコードしない（常に CURRICULUM.md から読む）
- 個人の Vault 絶対パスを書かない（`$LESSON_VAULT_PATH` のみ）
- 学習 Vault へは読み取り専用。書き込みは一切しない（保存・進捗記録は cloudflare-lesson-note に委ねる）
