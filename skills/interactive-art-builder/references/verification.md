# 検証ハーネス

「動いた気がする」を禁止する（`docs/skill-plan.md` 設計原則 5）。すべての検証は数値・ログ・画像データという再現可能な証拠を残す。Heartburst（旧称 CatharsisField）では Phase 5〜7 と Phase 9〜11（`docs/process-log.md`）で以下の手法を実測している。

**ブラウザの使い分け**: 状態を変える検証（再読み込み・モバイル表示の模擬・CPU スロットル）は、自前の Chrome for Testing を使う agent-browser で行う。chrome-devtools MCP を普段使いの Chrome に繋いだままだと、選択中タブがユーザーのタブへ移って誤操作する（`pitfalls.md` 検証節）。下の 1 節は chrome-devtools の例だが、同じ合成は agent-browser の eval でもできる。

## 1. chrome-devtools MCP での PointerEvent 合成 E2E

ウェブ版はマウス・タッチ操作が入力の起点。初版の状態機械は `idle → pointerdown → charging → pointerup → releasing →(1frame)→ decay →(約3秒)→ idle`。参照実装は Phase 9-1 で解放を 2 段に分け、`idle → charging → inhale（吸い込み。着弾時刻まで待つ）→ impact（ヒットストップ）→ decay → idle` になった（`web/src/main.ts:7`、`game-feel.md`）。自動実行するのは「ゲート突破・pop 連打・溜め→解放」の一連で、人手なしで再現する（`docs/process-log.md:121`）。

**到達状態**: コンソールエラー 0 件で idle → charging →（解放の状態）→ decay → idle まで遷移し、各段階でスクリーンショット・amp 値が取得できること。

マウスの合成イベントだけでは、タッチ固有の不具合（指を離すまで音声を解錠できない等）を見逃す。スマホ対応の作品は 7 節のタッチ検証も必ず回す。

構造:

1. `mcp__chrome-devtools__navigate_page` でページを開く
2. 初回操作は**導入オーバーレイのゲート**を経由する。`#overlay` 要素への `pointerdown` が `AudioContext` 起動を兼ねる（`web/src/main.ts:1032-1062`）。`mcp__chrome-devtools__evaluate_script` でこの要素に対して合成 `PointerEvent` を dispatch するか、`mcp__chrome-devtools__click` で直接クリックする
3. 以降の操作は canvas 要素（`sketch-container` 配下、`web/src/main.ts:1548-1549,1556-1563`）に対する `pointerdown` → 一定時間の `pointermove` なし待機（charging） → `pointerup`（release）のシーケンスを合成する
4. pop 連打は `pointerdown` → 即 `pointerup` を短間隔で複数回

実証済みの合成イベント骨格（Heartburst で使用。座標・待機は作品の状態機械に合わせて調整）:

```js
// evaluate_script 内。bubbles/cancelable/pointerId/isPrimary/buttons を揃えないと拾われない
const fire = (target, type, x, y) => target.dispatchEvent(new PointerEvent(type, {
  bubbles: true, cancelable: true, clientX: x, clientY: y,
  pointerId: 1, isPrimary: true, button: 0, buttons: type === 'pointerdown' ? 1 : 0 }));
// ゲート → 溜め → 解放: fire(overlay,'pointerdown') → sleep(2500 ─ worklet 読込待ち)
// → fire(canvas,'pointerdown') → sleep(チャージ時間+α) → fire(window,'pointerup')
// pointerup/pointercancel は window 側でリッスンされがち ─ dispatch 先に注意
```

## 2. 音響の数値検証

**Web**: `window.__heartburstAudio`（`web/src/main.ts:114`）経由で `getAmp()` を呼び出し、RMS 振幅をサンプリングする。実装は `AnalyserNode.getFloatTimeDomainData` → 二乗平均平方根（`web/src/audio/heartburst-engine.ts:1101-1106`）。実測値（`docs/process-log.md:122`）: pop 0.83 / charge 0.18 / release 0.59 / 減衰後 0.003。

**到達状態**: 各状態遷移の直後に `getAmp()` を呼び、無音期待の状態（idle・decay 後）で 0 に近い値、release 直後にピークが出ることを数値で確認する。

**ネイティブ (SC)**: SC 側は `SendReply.kr` で 30Hz（`~ampSendRate`, `sc/main.scd:13`）ごとにマスター振幅を計測し、`OSCdef(\ampForward, ...)` が `/sc/ampReply` を `/sc/amp` として Processing へ転送する（`sc/main.scd:160-163`）。`bin/test-osc.scd` でシーケンスを注入した実測（`docs/process-log.md:74`）: `/sc/amp` 919 パケット・最大振幅 0.606・エラー 0。

リスナー実装（実証済み ─ Processing 未起動時に UDP:12000 を代理受信して集計する方法）:

```bash
nc -ul 12000 > /tmp/amp.raw &   # OSC バイナリを貯める（テスト完了後に kill）
python3 - <<'EOF'
import struct
data = open('/tmp/amp.raw','rb').read()
vals, i = [], 0
while (i := data.find(b'/sc/amp', i)) >= 0:
    # OSC: "/sc/amp\0"(8B) + ",f\0\0"(4B) + big-endian float
    if i + 16 <= len(data): vals.append(struct.unpack('>f', data[i+12:i+16])[0])
    i += 8
print(f"packets={len(vals)} nonzero={sum(v>0.01 for v in vals)} max={max(vals):.3f}")
EOF
```

## 3. fps 判別

**罠**: 全状態でぴったり 30.0fps + long task ゼロ + フレーム間隔 33.3ms 均一 = 描画が重いのではなく **macOS/Chrome の省エネモードによる rAF 30Hz 制限**（`docs/process-log.md:117`）。60fps 目標のはずが 30fps に見えても、これだけでは「重い」と断定できない。

**判定基準**:

- フレーム間隔が完全に均一（分散ほぼ 0）→ 上限に張り付いている＝制限。フレーム間隔が変動（変動係数が高い）→ 実負荷でコマ落ちしている
- long task（メインスレッドブロック）の有無を合わせて見る。long task ゼロ + 均一 30fps は制限、long task あり + 不均一は真の負荷
- ネイティブ (Processing) 側は `draw()` 内で 120 フレームごとに `[perf] fps=... state=...` を `println` し、ログを状態別に grep して定量確認する運用（`docs/process-log.md:98`）
- ウェブ版の粒子数自動調整は「fps 低下」と「フレーム間隔の変動係数」の両方で判定するよう仕様化されている（`docs/process-log.md:127`）。判定ロジックを新規作品に流用する際もこの二重基準を踏襲する
- fps が rAF 制限で頭打ちのときは、fps ではなく **draw 1 回の処理時間**で負荷を見る。`draw()` 内で指数移動平均を取り、開発用ハンドルで読む（参照実装: `main.ts` の `drawMsAverage` を `window.__heartburstDebug()` で取得）。実測: M2 Max・4000 粒子で 3.6〜5.3ms（表示は 30fps でも余裕がある）。rAF をラップして測る方法は p5 では効かない

## 4. OSC 注入テスト

`bin/test-osc.scd` は Processing の代わりに溜め→解放シーケンスを SC(57120) と Tidal(6010) へ直接送信するスタンドアロン検証スクリプト。Processing のマウス操作を経由せず音側だけを単体検証できる。

使い方: `sc/main.scd` と Tidal（起動していれば）を先に立ち上げた状態で、別プロセスとして `sclang bin/test-osc.scd` を実行する。

内容（`bin/test-osc.scd:1-37`）: `/pop` を 0.25 秒間隔で3回 → 1秒待機 → `/charge/start` 後 90 フレーム（30fps 相当）かけて `/charge/level` を 0→1 に上げつつ `/ctrl charge` を Tidal にも送信 → `/release 1.0` 発火と同時に `/ctrl charge 0.0` → 90 フレームかけて `/ctrl energy` を 1→0 に下げる → 8 秒待って `0.exit`。

**到達状態**: SC 側でエラーログ 0、`/sc/amp` 転送パケットが送出され続けている（音が鳴っている証拠）、Tidal 側で `/ctrl` 受信によるパターン変化が確認できること。

## 5. 決定的瞬間の撮影

MCP のスクリーンショットツールはツール呼び出し間のレイテンシがあり、「解放直後のピーク」のような狙った瞬間を外しやすい（`docs/process-log.md:128`）。

**対処**: `mcp__chrome-devtools__evaluate_script` でページ内 JS を実行し、`canvas.toDataURL()` を呼んで**同期的・原子的に**その瞬間のフレームをキャプチャする。狙ったタイミングが厳密でない場合は、`base64` 文字列の長さ（データ量）を継続的にプローブし、描画が最も密になる瞬間（= データ量ピーク）を特定してから撮影する、という手法が実証済み（OG 画像撮影、`docs/process-log.md:128`）。

**到達状態**: `toDataURL()` の呼び出しとキャプチャしたい状態変化（release 発火など）が同一の `evaluate_script` 呼び出し内、またはポーリングで数十ms単位の粒度に収まっている。

## 6. 成果物提示規約

生成物（スクリーンショット・OG画像・動作確認用の画面）は **Read ツールで表示しただけでは Claude 側からしか見えない**。ユーザーに確認を求める前に、`open <path>` でローカルビューアに橋渡しするか、Artifact（data URI 埋め込みで publish）で提示する（`docs/process-log.md:85`、`docs/skill-plan.md` Phase 5）。承認は提示の後。

デプロイ後の本番確認は URL が確定してから改めて E2E を回す（`docs/process-log.md:129-130`: 本番 `wrangler deploy` 後にゲート→溜め→解放・amp 0.45・コンソールエラー 0 まで確認、OGP の絶対URL化のため再ビルド・再デプロイの2段構成が必要だった）。表示された URL と OGP の URL が一致しているかも見る（workers.dev のサブドメインは外部要因で変わる。`pitfalls.md` 公開・デプロイ節）。

## 7. タッチの検証（CDP で本物のタッチを送る）

`dispatchEvent` で作った PointerEvent はマウス相当の経路しか通らず、タッチ固有の制約（`pointerdown` では音声を解錠できず、指を離した時に初めて解錠できる）を再現できない。Heartburst ではマウスの E2E が全部通ったまま、スマホで完全に無音だった。

手順（agent-browser が起動した Chrome の CDP に直接つなぐ）:

1. `Emulation.setTouchEmulationEnabled`（`enabled: true`）でタッチ端末として振る舞わせる
2. `Input.dispatchTouchEvent` で `touchStart` → 待機 → `touchEnd` を送る（ブラウザが本物のタッチとして扱う）
3. 各段階で `AudioContext` の状態と振幅を読む（`__heartburstAudio.getDiagnostics()` / `getAmp()` 相当）

**到達状態**: `touchStart` の後は suspended のままでよく、`touchEnd` の後に running になり、パターン層が起動し、溜め・解放で振幅が出る（Heartburst の実測: 溜め 0.166 / 解放 0.310）。マウス経路では押下の時点で running になること（回帰なし）も合わせて確かめる。

## 8. 起動時間の計測（長いタスク）

「起動が重い」は体感で探さない。CPU を絞った状態で、読み込み直後から長いタスク（50ms 超のメインスレッド占有）を記録する。

1. `Emulation.setCPUThrottlingRate`（4 倍）で低速端末を模擬する
2. `Page.addScriptToEvaluateOnNewDocument` で、ページのスクリプトより先に `PerformanceObserver`（`longtask`）を仕込む
3. 再読み込み → 7 節の本物のタッチで導入ゲートを押し、読み込み直後とタップ直後の長いタスクを分けて集計する

**到達状態**: 読み込み直後・タップ直後とも、長いタスクが体感できない長さに分散している（Heartburst の実測: 読み込み 377 → 69ms、タップ後は最大 69ms）。音・色・見た目に回帰が無いこと。対処の型は `pitfalls.md` の「事前合成・事前読み込みを一括で行うとタップ直後に固まる」「起動時の画素単位・粒子単位の p5 関数が長いタスクになる」。

## 9. 実機診断表示

実機（特に iPhone）でしか起きない不具合は、推測の修正を重ねる前に、画面に診断を出してユーザーに見てもらう。

- `?debug` のようなクエリで、音声の状態（`AudioContext.state` / 未生成）・`isSecureContext`・消音スイッチ対策の有無・配線完了フラグ・直近のエラーを画面に表示する（参照実装: `AudioEngine.getDiagnostics()`）
- LAN の http とデプロイ後の https では、使える API が違う（`DeviceMotionEvent`・`AudioWorklet`・`navigator.audioSession`・マイク）。両方で見る

**到達状態**: ユーザーから診断表示のスクショ 1 枚を受け取れば、真因の候補が 1 つに絞れる。

## 10. 見た目の評価ループ

数値が正しくても、見た目が良いとは限らない。演出を足したら「スクショ → 判断 → 修正」を複数周回す（Heartburst Phase 9-2 は 5 周）。

- 状態ごと（idle・溜め・満充填・着弾直後・余韻の後半）に撮る。余韻の後半・満充填の保持中のような「長く続く状態」ほど空虚になりやすい
- 狭い画面（390×844 等）でも撮り、UI の重なりを見る
- 撮った画像はユーザーに見える形で提示してから判断を仰ぐ（6 節）

何を見るかは `game-feel.md` の「見た目の評価ループで直したもの」を参照。

## 11. UI・多言語の検証

説明画面・言語切り替えのような DOM の UI は、画面サイズ × 言語の組み合わせで機械的に確かめる。

- 説明カードがスクロール無しで収まるか: `scrollHeight === clientHeight` を、画面サイズ 5 通り × 日英で見る
- 条件が効いているかを先に確かめる。全ケースで同じ値が出たら、計測スクリプトに条件（画面サイズ等）が渡っていない疑いを潰す（zsh の単語分割で実際に起きた。`pitfalls.md` 検証節）
- ブラウザの言語設定での自動選択は、`--lang=en-US` 等で起動したブラウザで確かめる
- UI のボタン（説明・言語切り替え）を押しても作品が始まらないこと（導入ゲートの `pointerdown` に伝播しないこと）を確かめる
