# 検証ハーネス

「動いた気がする」を禁止する（`docs/skill-plan.md` 設計原則 5）。すべての検証は数値・ログ・画像データという再現可能な証拠を残す。Heartburst（旧称 CatharsisField）では Phase 5〜7（`docs/process-log.md`）で以下の手法を実測している。

## 1. chrome-devtools MCP での PointerEvent 合成 E2E

ウェブ版はマウス・タッチ操作が入力の起点（状態機械: `idle → pointerdown → charging → pointerup → releasing →(1frame)→ decay →(約3秒)→ idle`、`web/src/main.ts:7`）。chrome-devtools MCP でこの一連を自動実行し、「ゲート突破・pop 連打・溜め→解放」を人手なしで再現する（`docs/process-log.md:121`）。

**到達状態**: コンソールエラー 0 件で idle → charging → releasing → decay → idle まで遷移し、各段階でスクリーンショット・amp 値が取得できること。

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

デプロイ後の本番確認は URL が確定してから改めて E2E を回す（`docs/process-log.md:129-130`: 本番 `wrangler deploy` 後にゲート→溜め→解放・amp 0.45・コンソールエラー 0 まで確認、OGP の絶対URL化のため再ビルド・再デプロイの2段構成が必要だった）。
