# stack-web.md ─ p5.js + Web Audio + Strudel 実装ガイド

ウェブ版の実装ガイド。参照実装: `~/Projects/Game/heartburst`（`web/src/**`）。計画正本: `docs/web-port-plan.md`。ネイティブ版（`stack-native.md`）の 1:1 移植として始まり、OSC は廃止して同一ページ内の関数呼び出しに置き換えた。Phase 9 以降の改良（解放の 2 段化・楽器・物語・声・日英）はウェブ版だけに入っており、ネイティブ版は初版の仕様のまま。

## 構成

```
main.ts（状態機械・ポインタ入力・p5 インスタンスモード）
  ├─ tuning.ts        （定数一元管理。ネイティブ版 .pde の定数とコメントで対応）
  ├─ visuals.ts        （Particle / Shockwave / buildVignette。p5 描画）
  ├─ music.ts          （音程・色・コード進行の共通定義。音響と視覚の両方が参照）─ Phase 9-3
  ├─ scenes.ts         （場面 = 配色と一文）─ Phase 9-4
  ├─ i18n.ts / manual.ts（日英の辞書と切り替え / 遊び方の説明カード）─ Phase 11
  └─ audio/
      ├─ engine.ts      （AudioEngine 契約 + createAudioEngine ファクトリ）
      ├─ heartburst-engine.ts（Web Audio 実装。sc/main.scd の写像）
      └─ pattern.ts      （Strudel パターン層。オプショナル）
```

- **AudioEngine 契約**（`web/src/audio/engine.ts:34-56`）: 視覚と音響をこのインターフェースだけで分離する。`main.ts` はこのインターフェース越しにしか音響を触らない（差し替え時に main.ts を変更しないため）。最小構成は `start / chargeStart / chargeLevel / release / pop / setEnergy / getAmp` の 7 メソッドで、`templates/web/audio-engine-contract.ts` はこの形。参照実装は改良で 21 メソッドに増えた（`release()` が着弾時刻 `ReleaseTiming` を返す、段階チャージの `tierUp`・心拍の位相・小節の位置の取得、診断用の `getDiagnostics` 等）。機能を足すときも契約を拡張し、main.ts から Web Audio を直接触らない。`?mute` クエリで `NoopAudioEngine` に切り替え可能（`engine.ts:111-116`）─ 視覚のみのスモークテストに使える
- **エンジン**（`heartburst-engine.ts`）: `fxIn`（全音源の合流点、SC の `~fxBus` 相当）→ dry/wet 分岐 → `ConvolverNode`（生成インパルス応答のリバーブ、外部 IR ファイル不要）→ `DynamicsCompressor`（Limiter 代用）→ `AnalyserNode` → `destination`。`start()` は `resume()` を待たずに配線まで済ませ、配線完了フラグ `isReady` を立てる。KS プラックは使う音域だけを MIDI 番号をキーに、使う順に 1 音ずつオフライン合成してバンク化する（`heartburst-engine.ts:236-251`、`buildPluckBank()` / `ensurePluck()`）。音声の解錠は `installUnlockListeners()` が指を離した時・タップ時に行う（`pitfalls.md` の autoplay ゲート）
- **パターン層**（`pattern.ts`）: `@strudel/web` を動的 import（導入画面の表示中に先読みし、初期化はクリックゲート後）。`setAudioContext(ctx)` で音響エンジンと同一 `AudioContext` を共有し、`controlSignals`（`heartburst-engine.ts:121`）を `globalThis.__heartburst` 経由で `signal(() => __heartburst.charge)` として注入する（`pattern.ts:10,33-48,95-97`）。ctx が running になってから起動し、出力はエンジンのマスター系統へ付け替える。失敗しても本体（視覚+音響）は継続する設計（`pattern.ts:61-64`）

## 実装順序（`docs/web-port-plan.md` フェーズ計画に対応）

1. Vite+TS scaffold、粒子システム移植（無音）、状態機械 ─ ブラウザで溜め→解放の視覚が60fpsで動く状態が到達点
2. Web Audio 音響エンジン（charge/drop/shock/shimmer/pop + master）─ Fable 主導（音響設計の質が核）
3. Strudel パターン層 + charge/energy 注入 ─ Fable 主導
4. タッチ対応・クリックゲート・粒子数自動調整・磨き ─ サブエージェント委譲可
5. `wrangler deploy`・OGP・ライセンス表記

Phase 1-2 は並行実装可能（AudioEngine 契約で視覚と音響が分離されているため）。並行させる場合は `engine.ts` のインターフェースを先に固定してから委譲する。

## ウェブ固有の落とし穴（詳細な症状/原因/対処は pitfalls.md 参照）

- **p5 v2 の FES 偽陽性**: HSB 4引数 `stroke()` を誤検知し fps を殺す → `p5.disableFriendlyErrors = true` を本番必須に（`main.ts:38-40`）
- **p5 2.3.3 は型定義が入っていない**: `types` の指す `.d.ts` が配布物に無い → `"p5": "2.3.2"` に固定するか、使う API だけの型定義ファイルで補う。`@types/p5`（v1 用）は入れない
- **pixelDensity(1) は createCanvas の後**: p5 v2 では前に呼ぶと無効。`canvas.width` の実測で検証する（`main.ts:1519-1520`）
- **DelayNode フィードバックループは最小128サンプル**: 高音域の Karplus-Strong が組めない → 起動時にオフライン合成して `AudioBuffer` バンク化（`heartburst-engine.ts:1020-1061`）
- **p5.noise はネイティブより桁違いに遅い**: 粒子ごとに4フレームに1回の再計算（スロット分散）+ lerp 平滑化（`visuals.ts:302,317-320`）
- **getAmp（analyser 読み出し）の巻き上げ**: 粒子ループの外、フレームあたり1回に集約する（`main.ts:1654`、`heartburst-engine.ts:1101`）
- **Strudel worklet は initAudioOnFirstClick では間に合わない**: ゲートのクリックは消費済み。ユーザー操作後なら `initAudio()` を明示 await（`pattern.ts:44-46`）
- **autoplay ゲート**: 初回ユーザー操作まで音が出せない制約を導入演出に変換する（`main.ts:1028-1062`）。**タッチは `pointerdown` では解錠できず、指を離した時に初めて解錠できる** ─ `resume()` を待たずに配線し、`pointerup` / `touchend` / `click` / `keydown` で再開する常駐リスナーを置く
- **resume() が解決しない環境**: 未配線のノードへ connect して例外になり、描画ループごと止まる → ctx の有無でなく配線完了フラグ `isReady` で守る
- **起動時の一括処理**: KS の一括合成・Strudel の読み込み・画素単位の p5 関数が長いタスクになる → 使う順に小分け + 要求時フォールバック、先読み、canvas グラデーション・色の表引き
- **グロー**: 本体キャンバスへの加算はトレイルと帰還ループになり白飽和する → 縮小キャンバスを別 DOM レイヤーにして `mix-blend-mode: screen`
- **p5 v2 の fill/stroke キャッシュ**: 2D context へ直接描いたら `ctx.save()` / `ctx.restore()` で囲む
- **iOS**: セキュアコンテキスト限定 API（`DeviceMotionEvent` 等）は http で消える → `typeof` で守り、音声の起動を先に置く。消音スイッチ対策（`audioSession = "playback"`）はマイクと両立しない。振る操作と入力欄の同居は Shake to Undo と衝突する
- **AGPLv3（Strudel のライセンス）**: 組込側もソース公開必須。公開計画の質問時に自動で告知し、ユーザー承認を実装前に取る（`web/LICENSE`、`docs/web-port-plan.md:62-66`）

## Strudel 固有の技術メモ（`docs/web-port-plan.md` 裏取り結果）

- 外部値注入は `signal(() => value)`。クエリごとにコールバックが再実行されるため再評価は不要（`mouseX` と同実装）
- 音源はサンプル（`bd` 等）が既定で外部 CDN 依存になる → 使わず**内蔵シンセ**（sawtooth/square/sine/triangle/noise系/FM）のみで全レイヤーを構成し、オフライン動作を保つ
- 文法差: `#` → メソッドチェーン、`cF` → `signal()`。`fast`/`degradeBy`/`segment`/`euclid`/`arp`/`gain`/`lpf`/`room` はほぼ同名でネイティブ版 `.tidal` から移植しやすい
- 拍位置は公開 API に無い → repl の `scheduler` の内部フィールドから換算し、欠損時は自前クロックへ退避する（`pitfalls.md`）
- Strudel の出力は `ctx.destination` 直結 → エンジンのマスター系統へ付け替えると、ダッキング・ポンピング・`getAmp()` が Strudel 層にも効く
- コード進行に合わせるときは、コードごとにパターン文字列を生成して `evaluate()` し直す（`pattern.ts` の `setPatternChord()`）

## パフォーマンス自動調整（Phase 4・委譲時の仕様化ポイント）

粒子数自動調整は「fps 低下」と「フレーム間隔の変動係数」の両方で判定する（`main.ts:448-496`、`tuning.ts:159-163`）。macOS/Chrome の省エネモードによる rAF 30Hz 制限を実負荷と誤認しないための二重基準（詳細は `verification.md`・`pitfalls.md` の fps 判別の罠を参照）。サブエージェントに委譲する際はこの判定ロジックの落とし穴を仕様に明記しておくと手戻りを防げる。

参照実装は粒子を画面より大きい真円に住まわせているため、粒子数 8000（削減の段は 8000 / 5000 / 3000）で、画面外（余白 `OFFSCREEN_CULL_MARGIN` = 80px の外）の粒子は計算だけして描画を省く。

## UI 層（説明カード・日英）

作品の外側の UI を足すときの型（参照実装 Phase 11）:

- 日英の辞書は `satisfies Record<string, Record<Lang, string>>` で型付けし、訳し漏れを型チェックで検出する。HTML の固定文字は `data-i18n` / `data-i18n-attr` で辞書を指し、一括で差し替える（`i18n.ts`）
- 言語の決定は、端末に記憶した選択 → `navigator.languages` の順
- 説明カードはネイティブ `<dialog>` + `showModal()`（Esc・フォーカスの閉じ込めを標準に任せる）（`manual.ts`）
- 導入画面の上に置くボタン（説明・言語切り替え）は `pointerdown` の伝播を止め、押しても作品が始まらないようにする
- 溜め〜着弾の間は `body.is-charging` で UI を薄くする。DOM は状態が変わったときだけ触る

## 参照実装への誘導

フルコードは常に `web/src/**` を読む。本ファイルは構成・順序・落とし穴の地図であり、実装の写経元ではない。
