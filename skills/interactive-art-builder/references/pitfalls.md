# pitfalls.md ─ 統合知識ベース

Heartburst（旧称 CatharsisField）制作工程（`docs/skill-plan.md` 5節・`docs/process-log.md` 全フェーズ。Phase 9〜13 の改良・モバイル対応・改名を含む）で実証済みの落とし穴。同じ罠に二度ハマらないための一覧。各項目は「症状 → 原因 → 対処」の3点セット。

コード位置は、行番号で示した項目（Phase 8 までの初版）と、関数名・定数名で示した項目（Phase 9 以降）がある。行番号は参照実装の改修でずれるので、合わなければ名前で検索する。

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

### Processing のメイン .pde 名はフォルダ名と一致が必須

- **症状**: 作品を改名してフォルダ名だけ変えると、Processing がスケッチとして開けない
- **原因**: Processing はスケッチフォルダ名と同名のメイン `.pde` を要求する
- **対処**: 改名はフォルダとメイン `.pde` を同時に行う（`processing/Heartburst/Heartburst.pde`）。起動スクリプトの `--sketch=` のパスも合わせ、Processing CLI でコンパイルが通る（`Heartburst.class` が生成される）ことで確認する

### グローを本体キャンバスへ加算すると白飽和する

- **症状**: 発光（グロー）を足すと、数フレームで画面全体が白く飽和する
- **原因**: トレイル（前フレームを薄く残す描画）の上に光を加算すると、前フレームの光を毎フレーム再加算する帰還ループになる
- **対処**: 縮小サイズの別キャンバスを別の DOM レイヤーとして重ね、CSS `mix-blend-mode: screen` で合成する（`main.ts` の `glowCanvas`・`GLOW_DOWNSCALE`、`style.css`）。拡大補間そのものがぼかしになるので、`ctx.filter` 非対応環境でも成立する

### p5 v2 は fill/stroke をキャッシュする ─ 2D context の直接描画が漏れる

- **症状**: 2D context へ直接 `fillStyle` を書いた描画の後、次フレームの p5 描画が別の色で塗られる（トレイル消去の矩形が星雲のグラデーションで塗られ、画面全体が飽和した）
- **原因**: p5 v2 は fill/stroke の値をキャッシュし、同じ色なら ctx へ再設定しない。直接書き換えた ctx の状態が p5 から見えない
- **対処**: p5 を経由しない直接描画は必ず `ctx.save()` / `ctx.restore()` で囲む

### 大量粒子は p5 の stroke() を経由せず 2D context に直接描く

- **症状**: 粒子数を増やすと、描画呼び出しそのものが重くなる
- **原因**: p5 の `stroke()` は呼び出しごとに色の解釈・検証が走る
- **対処**: 色を量子化して rgba 文字列をキャッシュし、2D context に直接 `moveTo` / `lineTo` で描く（前項の `save` / `restore` と併用）。長さ 0 の線は描かれない環境があるため、点は 0.01px の線 + `lineCap = "round"` で描く

### rAF をラップしても p5 の draw 時間は測れない

- **症状**: `requestAnimationFrame` を差し替えて計測しても、p5 の描画時間が取れない
- **原因**: p5 は起動時に取得した rAF の参照を使い続ける
- **対処**: `draw()` の中で処理時間の指数移動平均を取り、開発用ハンドルに出す（`main.ts` の `drawMsAverage`、`window.__heartburstDebug()`）

### 暗い背景・低 alpha の橙〜黄緑は泥色に濁る

- **症状**: 夜明けのつもりの星雲が茶色・オリーブに見える
- **原因**: 色相 15〜125° を暗く低 alpha で重ねると濁る。場面の定義で避けても、コード進行による色ずらしや色寄せの結果この帯に入る
- **対処**: 最終的な色相を帯の外へ逃がす関数を描画直前に掛ける（`main.ts` の `avoidMuddyHue`）。金色のような暖色は、背景ではなく粒子・輪など明るい要素で出す

### 起動時の画素単位・粒子単位の p5 関数が長いタスクになる

- **症状**: ページ読み込み直後に数百 ms 固まる（CPU 4 倍スロットルで 377ms）
- **原因**: 画面端を暗くする画像を全ピクセルの `p.map` / `p.constrain` で生成し、粒子ごとに `p.lerpColor` を呼んでいた
- **対処**: 画像は canvas の放射グラデーション（`createRadialGradient`）で作り、描画は `tint` でなく `drawImage` + `globalAlpha`。色の補間は 64 段の表にして引く。計測方法は `verification.md` の起動時間の計測を参照

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

### autoplay ゲート ─ タッチは「指を離した時」にしか解錠できない

- **症状**: PC では鳴るのに、スマホでは音が全く出ない（Strudel 層も起動しない）
- **原因**: ブラウザの autoplay 制約で、初回ユーザー操作までは音が出せない。さらに HTML の user activation は、マウスなら `pointerdown` で成立するが、**タッチでは `pointerup` / `touchend` まで成立しない**。導入ゲートの `pointerdown` で `AudioContext.resume()` を呼び、その解決を `await` していたため、スマホでは ctx が suspended のまま止まっていた
- **対処**:
  - 制約は演出に変換する。「画面に触れて、溜めて、解放する」の導入オーバーレイを置き、最初の操作をそのまま 1 回目の溜めに繋げる（`web/src/main.ts:1028-1062`）
  - `start()` は `resume()` を待たずに配線まで済ませる。`pointerup` / `touchend` / `click` / `keydown` のたびに、止まっていれば `resume()` する常駐リスナーを置く（`heartburst-engine.ts` の `installUnlockListeners()`）。iOS の着信・バックグラウンド復帰で止まった場合もこれで戻る
  - Strudel 層は ctx の `statechange` で running になってから起動する（`whenRunning()`）
  - 音声の起動を待つ間に指が離れていたら、溜めでなくタップとして扱う。離し済みのまま charging に入ると、次のタップまで抜けられない
  - 残る仕様: スマホでは最初の長押しの間は無音で、指を離した瞬間から鳴る
- 検証はマウスの合成イベントだけでは通ってしまう。CDP で本物のタッチを送る（`verification.md` の 7 節）

### resume() が解決しない環境で描画ループごと止まる

- **症状**: 溜めの段階 1 に到達した瞬間に画面が固まる（ヘッドレス検証で発覚）
- **原因**: `resume()` が解決しない環境で、未配線のノードへ `connect` して例外になり、p5 の描画ループごと停止した。エンジンの防御を「ctx があるか」で判定していたため、ctx はあるが配線前という状態を素通りした
- **対処**: 配線と素材の準備が済んだ時点で立てるフラグ（`isReady`）で各メソッドを守る。音声が起動できなくても作品（描画）は続くように、ゲート側でも `start()` の失敗を `catch` する

### 事前合成・事前読み込みを一括で行うとタップ直後に固まる

- **症状**: 導入ゲートを押した直後に数百 ms 止まる（CPU 4 倍スロットルで 353ms + 171ms）
- **原因**: Karplus-Strong 45 音の一括合成と、Strudel の読み込み・パースがタップ直後に集中していた
- **対処**: 事前合成は「使う順に小分け + 要求時フォールバック」にする。KS は `setTimeout(0)` で 1 音ずつ、タップ音 → 和音・シャワー → 種の順に合成し、未合成の音が要求されたらその場で合成する（`heartburst-engine.ts` の `buildPluckBank()` / `ensurePluck()`）。バンクのキーは周波数でなく MIDI 番号にし、使う音域だけ合成する。Strudel は導入画面の表示中に import だけ先読みする（`pattern.ts` の `preloadPatternLayer()`）。結果、タップ後の長いタスクは最大 69ms に分散した

### Strudel の拍位置は公開 API に無い

- **症状**: 音楽の拍に演出（着弾・光の点滅）を合わせたいが、Strudel から現在の拍位置を取る API が無い
- **原因**: 拍の管理は Strudel 内部のスケジューラ（`@strudel/core` の Cyclist）にある
- **対処**: `initStrudel()` の戻り値（repl）の `scheduler` が持つ `num_cycles_at_cps_change` / `seconds_at_cps_change` / `cps` / `latency` から、Cyclist 自身の発音時刻の式 `(cycle - n0) / cps + s0 + latency` で換算する。内部フィールドなので、欠損時は同じ cps の自前クロックへ退避する（`pattern.ts` の `StrudelClock`）。光を音に合わせるときは、出力レイテンシを引いた「聞こえている位置」を使う

### Strudel 層にダッキング・analyser を効かせるには出力を奪う

- **症状**: 着弾前の無音の間（ダッキング）やポンピングを掛けても、Strudel 層だけ鳴り続ける。`getAmp()` にも Strudel の音が乗らない
- **原因**: Strudel（superdough）は自分の出力を `ctx.destination` に直接繋いでいる
- **対処**: `getSuperdoughAudioController().output.destinationGain` を `ctx.destination` から外し、音響エンジンのマスター系統へ繋ぎ直す（`startPatternLayer()` の `destination` 引数）。コード進行に合わせてパターンを変えるときは、`signal` で音程を動かすより、コードごとにパターン文字列を生成して `evaluate()` し直す方が素直（スケジューラは止まらず次のクエリから効く。`setcps` が同値なら cps のリセットも起きない）

### マイク入力で溜めるときの自己発火と音量の潰れ

- **症状**: 自分の爆発音をマイクが拾って、また溜めが始まる。声の強弱が溜めに反映されない
- **原因**: スピーカー出力の回り込みと、ブラウザの自動ゲイン調整
- **対処**: `getUserMedia` で `echoCancellation: true`・`autoGainControl: false` を指定し、爆発後 1.5 秒は声の溜めを受け付けない。マイクの音は出力へ流さず計測だけに使う（ただし未接続ノードを処理しないブラウザがあるため、無音のゲインを経由して出力に繋ぐ）。マイクは https / localhost でしか使えないので、それ以外では入口を表示しない

## モバイル / iOS

タッチの解錠タイミングは上の「autoplay ゲート」を参照。

### セキュアコンテキスト限定の API は LAN の http 検証で消える

- **症状**: iPhone で LAN の http から開くと完全に無音。診断表示には `contextState: not created` と `ReferenceError: Can't find variable: DeviceMotionEvent`
- **原因**: iOS Safari は https でないページに `DeviceMotionEvent` 自体を公開しない。導入ゲートが音声の起動より先に「振って解放」の許可要求を呼び、その中の参照で例外になって、音声の起動が 1 行も実行されていなかった。`AudioWorklet`・`navigator.audioSession`・マイクも同じくセキュアコンテキスト限定
- **対処**: 参照は `typeof DeviceMotionEvent === "undefined"` のように守る。ユーザー操作のハンドラでは、例外が後続を巻き込まないよう重要な処理（音声の起動）を先に置く。実機確認は https（本番デプロイ・トンネル等）でも行う

### モーションセンサーの許可はタッチの touchend で要求する

- **症状**: 「振って解放」が iOS で反応しない
- **原因**: iOS の `DeviceMotionEvent.requestPermission()` はユーザー操作の中でしか通らず、タッチでは `pointerdown` が user activation にならない
- **対処**: 導入ゲートのタッチで `touchend` に一度だけ許可要求を仕掛ける（`main.ts` の `requestMotionPermission`）

### 消音スイッチ対策とマイク入力は両立しない

- **症状**: iPhone の消音スイッチがオンだと Web Audio が鳴らない。対策を入れると、今度は「声で溜める」が「マイクが許可されていません」になる
- **原因**: 消音スイッチを無視させる `navigator.audioSession.type = "playback"`（Safari 16.4+）のままだと、iOS がマイク取得を拒否する（実機での切り分けによる推定）
- **対処**: 普段は `"playback"`、マイクを使う間だけ `"play-and-record"` に切り替え、やめたら戻す。Audio Session API が無い環境（http・古い iOS）では、無音の `<audio>` を鳴らし続けて消音スイッチを回避する（`heartburst-engine.ts` の `createSilentMediaElement()`）

### テキスト入力と「振る」操作が iOS の Shake to Undo と衝突する

- **症状**: 振って解放すると、iOS の「取り消す - 入力」ダイアログが出る
- **原因**: iOS 標準のシェイクで取り消し。入力欄の履歴は、要素を消して新しい要素に差し替えても OS 側に残る
- **対処**: iOS（iPad 含む）だけ、テキスト入力を OS 標準のダイアログ（`window.prompt`）に切り替える。振る操作とページ内の入力欄を同じ画面に置かない

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

### 実機でしか起きない不具合に推測の修正を重ねる

- **症状**: スマホ実機で無音。仮説で直してデプロイしても直らない
- **原因**: 実機の状態（ctx の状態・https か・例外）が開発側から見えないまま推測で直していた。1 回目の修正は仮説が外れていた
- **対処**: 推測の修正を重ねる前に、`?debug` 等で実機の画面に診断を出してユーザーに見てもらう（音声の状態・`isSecureContext`・消音対策の有無・直近のエラー。`AudioEngine.getDiagnostics()`）。Heartburst では診断 1 回で真因に届いた

### 普段使いの Chrome で検証するとユーザーのタブを操作してしまう

- **症状**: 長い検証の途中で、モバイル表示の模擬・CPU スロットル・再読み込みがユーザーの別タブに実行された
- **原因**: chrome-devtools MCP（`--autoConnect` で普段使いの Chrome に接続）の選択中タブが、検証中にユーザーの操作で別タブへ移っていた
- **対処**: 状態を変える操作の前に `location.href` を確かめる。検証の操作は、自前の Chrome for Testing を使う agent-browser へ寄せる

### 計測値が条件を変えても同一なら、条件が効いていない

- **症状**: 5 画面サイズ × 日英の 10 通りで、説明カードが全部「スクロール無しで収まる」と出た
- **原因**: zsh は `set -- $var` で単語分割しないため、画面サイズがスクリプトに渡らず全ケースが同じ寸法で計測されていた
- **対処**: 条件を変えても計測値が同一なら、結果を信じる前に条件が効いているかを確かめる（スクショの実寸を見る等）

### agent-browser の操作の癖

- `--args` 付きの起動は、既存のデーモンがあると「Could not configure browser」で失敗する → `--session <新しい名前>` で別デーモンを立てる
- `press "?"` のような記号キーは押しっぱなしになり、keydown が届き続ける（閉じたダイアログがすぐ開き直す）→ 記号キーは合成イベントで送る
- ヘッドレスの偽マイク（`--use-file-for-fake-audio-capture`）には音声が流れなかった → マイクの接続（トラックが live・analyser 接続）までを確かめ、判定ロジックは声量の取得関数（`getVoiceLevel`）を台本の値に差し替えて状態遷移を追う

## 公開・デプロイ

### workers.dev のサブドメインは外部要因で変わる

- **症状**: 再デプロイしたら公開 URL が変わっており、旧 URL は応答しない（OGP の URL も古いまま）
- **原因**: アカウントの workers.dev サブドメイン自体が変わっていた（同じ Worker のデプロイ履歴は続いていた）
- **対処**: デプロイ前に `wrangler deployments list` で既存 Worker の所在を確かめ、デプロイ後は表示された URL と `og:url` / `og:image` の URL が一致しているかを必ず見る

### wrangler は非対話環境で確認プロンプトを「はい」で通過する

- **症状**: 確認プロンプトの有無を見るつもりで `yes n | wrangler delete` を実行したら、Worker が削除された
- **原因**: wrangler は非対話環境では確認を既定値（はい）で通過する
- **対処**: 破壊的な wrangler コマンドの挙動は `--dry-run` / `--help` で調べる。n をパイプで渡して試さない。削除はユーザー承認と新 URL の確認の後に行う

### 作品の改名で利用者の保存データが消える

- **症状**: 改名に合わせて localStorage のキーを変えると、利用者の設定（言語・案内済み等）が消える
- **原因**: 新しいキーには何も入っていない
- **対処**: 起動時に旧キーから新キーへ値を引き継ぎ、旧キーを削除する。公開 URL を変える場合は、旧 URL の転送が要るかをユーザーに確認する

### タイトルロゴを生成モデルに直接「透過」で頼まない

- **症状**: 透過 PNG を頼むと、市松模様が絵として描き込まれる。光のにじみが切れる
- **原因**: 画像生成モデルは透過を正しく扱えないことが多い
- **対処**: 真っ黒な背景に発光ロゴだけを描かせ、手元で「明るさ = 不透明度」（alpha = max(R, G, B)、色は alpha で割り戻す）に変換して透過 PNG にする。光のにじみが半透明のまま残る。黒に戻して元画像との差を測り（平均 1.3 / 最大 10、0〜255）、市松・作品背景・白の 3 背景に重ねた比較でユーザーに選んでもらう

## ライセンス

### Strudel は AGPLv3

- **症状**: パターン層に Strudel（`@strudel/web`）を組み込むと、作品全体のライセンス方針に波及する
- **原因**: Strudel は AGPLv3（組込側もソース公開必須、SaaS 条項あり）
- **対処**: 公開計画をユーザーに質問する段階で自動的に告知する。Heartburst では「web/ を AGPLv3 でソース公開して Strudel を続行」を実装前にユーザー承認で確定した（`web/LICENSE`）。ソース非公開が必須の案件では Strudel を使わない選択肢も提示する
