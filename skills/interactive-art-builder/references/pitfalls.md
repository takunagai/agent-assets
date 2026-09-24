# pitfalls.md ─ 統合知識ベース

Heartburst（旧称 CatharsisField）制作工程（`docs/skill-plan.md` 5節・`docs/process-log.md` 全フェーズ）で実証済みの落とし穴。同じ罠に二度ハマらないための一覧。各項目は「症状 → 原因 → 対処」の3点セット。

## Processing / p5

### colorMode のレンジは alpha にも効く

- **症状**: 加算合成の粒子・フラッシュ・衝撃波が背景の灰色浮き・白飛び・マゼンタ不明瞭を起こす
- **原因**: `colorMode(HSB, 360, 100, 100, 100)`（`processing/Heartburst/Heartburst.pde:118`）でレンジを 100 に指定しているのに、alpha 値を 255 前提（45〜230）で書いていた → 100 で頭打ち＝ほぼ不透明のまま加算合成が蓄積する
- **対処**: colorMode のレンジ指定と描画時の alpha 値を必ず突き合わせて検査する。alpha を 100 レンジに再設計し、トレイルのフェードを強める（例: `flashAlpha = 100`、`processing/Heartburst/Heartburst.pde:336`）。サブエージェント成果物の頻出バグポイントなので統合時に必ずチェックする

### p5 v2 の FES（Friendly Error System）が偽陽性で fps を殺す

- **症状**: HSB 4引数の `stroke()` を「Invalid input」と誤検知し、毎フレーム数千件のログが出て最大のボトルネックになる
- **原因**: p5 v2 の入力検証が誤検知する（`web/src/main.ts:40` 付近）
- **対処**: 本番ビルドで `p5.disableFriendlyErrors = true` を必須にする（`(p5 as unknown as {...}).disableFriendlyErrors = true`、`web/src/main.ts:40`）

### pixelDensity(1) は createCanvas の後でないと効かない

- **症状**: retina 環境で描画が重く、解放時にアニメーションが停止・スローモーション化する
- **原因**: retina の既定 pixelDensity(2) は 3024x1964 で約2380万ピクセル/フレームの描画になる。p5 v2 では `pixelDensity(1)` を `createCanvas` の**前**に呼ぶと無効
- **対処**: `createCanvas` の後に呼ぶ（ネイティブ Processing: `processing/Heartburst/Heartburst.pde:114`。ウェブ p5: `web/src/main.ts:1519-1520`、`p.createCanvas(...)` の直後に `p.pixelDensity(1)`）。検証は `canvas.width` の実測で行う

### p5.noise はネイティブ Processing の noise() より桁違いに遅い

- **症状**: 4000粒子×60fps で idle が 30fps に落ちる
- **原因**: p5.js（ウェブ版）の `noise()` 実装がネイティブより大幅に重い（`web/src/visuals.ts:302` 付近にコメントあり）
- **対処**: 粒子ごとに4フレームに1回の再計算（スロット分散）+ lerp 平滑化で視覚品質を保ったまま計算量を1/4に削減する（`web/src/visuals.ts:317-320` 付近）

### ループ不変値の巻き上げ（色キャッシュ・getAmp）

- **症状**: 粒子ごとに毎フレーム同じ値を再計算・再取得している（例: analyser 読み出しを粒子ごと4000回呼んでいた）
- **原因**: ループ不変値をループ内に置いている（/simplify の指摘パターンの再発）
- **対処**: `getAmp()` の呼び出しをフレームあたり1回に巻き上げる（`web/src/main.ts:1654`、コメント「analyser 読み出しは1フレーム1回」）。契約：ループ不変値はループ外へ。Particle の色も HSB 分解をコンストラクタで済ませ `display()` では再計算しない

### stroke 状態の描画間漏れ（点描画への切り替え時）

- **症状**: 粒子を `ellipse()` から `stroke + strokeWeight + point()`（GLポイントスプライト、P2D で軽量）へ変更した際、トレイル矩形やフラッシュなど後続の `rect`/`fill` 描画に stroke が意図せず残る
- **原因**: `stroke`/`strokeWeight` はグローバル描画状態であり、`point()` 呼び出し後もクリアされない
- **対処**: トレイル矩形・フラッシュの直前に `noStroke()` を明示する（`processing/Heartburst/Heartburst.pde:121, 171, 212`）。粒子の点描画自体は `Particle.pde:150-151`

### Processing cli の JVM 孤児化

- **症状**: 「クリックしても動かない」─ 起動はしているがウィンドウが無反応
- **原因**: `Processing cli --run` は JVM を debugger 接続（jdwp suspend=y）で起動し、親の CLI runner が死ぬと JVM が孤児化する
- **対処**: 起動スクリプトはフォアグラウンドシェル内 `&` ではなく、永続するバックグラウンド実行で立ち上げる（`bin/start.sh:58`）

## Web Audio

### DelayNode のフィードバックループは最小128サンプル

- **症状**: 約344Hz超の Karplus-Strong プラック音が物理的に組めない（ペンタトニック音列がほぼ全滅）＋ループ内 BiquadFilter が不安定警告を出す
- **原因**: Web Audio の DelayNode フィードバックループの最小遅延が128サンプルという制約がある
- **対処**: KS 合成はリアルタイムのフィードバックループで組まず、起動時に JS で**オフライン合成**して `AudioBuffer` バンク化する（`web/src/audio/heartburst-engine.ts:1020-1061`、`renderKarplusStrong()`）。音程が正確になり再生コストも極小、警告も根絶できる

### analyser 読み出し（getAmp）の巻き上げ

- 上記「Processing/p5」節の「ループ不変値の巻き上げ」と同一事象・同一対処（`web/src/audio/heartburst-engine.ts:1101`, `web/src/main.ts:1654`）。契約はプラットフォーム共通

### Strudel worklet の initAudio タイミング

- **症状**: `initAudioOnFirstClick()` を使うと AudioWorkletNode エラーが出続ける
- **原因**: ゲートのクリックは既に消費済みのため、`initAudioOnFirstClick` は「次のクリック」を待ち続けてしまい間に合わない
- **対処**: ユーザー操作後であれば `initAudio()` を明示的に await する（`web/src/audio/pattern.ts:44-46`）

### autoplay ゲート

- **症状**: ブラウザの autoplay policy により、初回ユーザー操作前は音が出せない
- **原因**: ブラウザ標準の autoplay 制約
- **対処**: 制約を演出に変換する。「画面に触れて、溜めて、解放する」の導入オーバーレイを用意し、初回 `pointerdown` で `AudioContext.resume()` を行いつつそのまま1回目の溜めに繋げる（`web/src/main.ts:1028-1062`）

## SuperCollider

### 入出力サンプルレート不一致

- **症状**: 起動時エラーまたは不安定動作
- **原因**: 出力専用アプリなのに入力バスを開いていると、入出力デバイスのサンプルレート不一致が起きうる
- **対処**: `s.options.numInputBusChannels = 0` を明示する（`sc/main.scd:21`）

### SuperDirt クラス存在ガード

- **症状**: SuperDirt（quark）未導入環境でコンパイルエラーになる
- **原因**: クラス名を直接コード中に書くと、未導入時にクラス未定義エラーで起動全体が落ちる
- **対処**: `\SuperDirt.asClass` で動的にクラスを参照し、`notNil` を確認してから Tier 2 起動を分岐する（`sc/main.scd:169-179`）。未導入でも Tier 1（カスタム SynthDef のみ）で動作を継続する

### SuperDirt quark の headless インストール

- **症状**: なし（正しい手順を知らないと IDE 前提だと誤認しがち）
- **原因（前提の誤り）**: SuperDirt 導入に GUI/IDE が必要だと思い込みやすい
- **対処**: scratchpad の `.scd` を `sclang` に渡すだけで headless 完結する（IDE 不要）

## プロセス運用

### ghci は stdin EOF で終了する

- **症状**: バックグラウンド起動した Tidal が「Connected to SuperDirt」ログ直後に静かに死ぬ。エラーが出ないため気づきにくい
- **原因**: `ghci` は標準入力が EOF になると終了する仕様。バックグラウンド起動時に stdin が閉じられるとこれに該当する
- **対処**: `tail -f /dev/null | ghci ...` で stdin を開きっぱなしにする（`bin/start.sh:44-46`）。プロセス起動後は必ず `pgrep` 等で生存確認まで行う ─ ログが正常でも死んでいることがある

### Processing cli の JVM 孤児化

- 「Processing / p5」節と同一事象。プロセス運用の観点でも重要: 起動スクリプト設計時に「親プロセスが死んでも子が生き残る/生き残らない」の想定を必ず明示する（`bin/start.sh:58`）

### 音出しテスト前後のシステム音量退避・復元

- **症状**: 音出しテストで不意に大音量が出る、あるいは復元し忘れて後続作業に影響する
- **原因**: SynthDef やパターンの初期音量が想定外に大きい場合がある。BT スピーカー・耳の保護が必要
- **対処**: `osascript -e 'set volume output volume 40'` のように事前に音量を絞り、終了後に元音量へ復元する（元音量の退避を忘れない）

## 検証

### fps 判別の罠（省エネモードと実負荷の混同）

- **症状**: 全状態でぴったり30.0fps + long task ゼロ + フレーム間隔33.3ms均一という測定結果が出る
- **原因**: これは描画が重いのではなく、macOS/Chrome の省エネモードによる rAF 30Hz 制限である。真の負荷と誤認しやすい
- **対処**: フレーム予算計測（long task の有無・フレーム間隔分布の分散/変動係数）で「重い」と「絞られてる」を区別する。手法の詳細は `verification.md` 参照

### MCP スクリーンショットは決定的瞬間を外す

- **症状**: 「解放直後のピーク」のような狙った瞬間のスクリーンショットが撮れない
- **原因**: MCP のツール呼び出し間にレイテンシがあり、タイミングがずれる
- **対処**: ページ内 `canvas.toDataURL()` で原子的にキャプチャする。手法の詳細は `verification.md` 参照

### 成果物提示は Read では不可視

- **症状**: Read で画像を表示した・ファイルパスを提示しただけでは、ユーザー側の環境で見えていないことがある
- **原因**: Read ツールの画像表示は Claude 側からしか見えない
- **対処**: `open <path>` でローカルビューアに橋渡しするか、Artifact（data URI 埋め込みで publish）してから承認を求める。承認前に配置しない

## ライセンス

### Strudel は AGPLv3

- **症状**: パターン層に Strudel（`@strudel/web`）を組み込むと、作品全体のライセンス方針に波及する
- **原因**: Strudel は AGPLv3（組込側もソース公開必須、SaaS 条項あり）
- **対処**: 公開計画をユーザーに質問する段階で自動的に告知する。Heartburst では「web/ を AGPLv3 でソース公開して Strudel を続行」を実装前にユーザー承認で確定した（`web/LICENSE`）。ソース非公開が必須の案件では Strudel を使わない選択肢も提示する
