# 状態機械・ポインタ統合・性能自動調整・ゲート処理 ─ 設計ノート

p5.js インスタンスモードで「溜めて解放する」系のインタラクティブアートを書くときの
`main.ts`（スケッチ本体）の型を、抽出元の Heartburst（旧称 CatharsisField）実装から一般化してまとめる。
コードそのものはここに複製しない ─ 実装の参照先は
`/Users/takna/Projects/Game/heartburst/web/src/main.ts`（本スキルの抽出元。実際にこの
パスにアクセスできる環境なら、迷ったらまずこれを読む）。

## 1. 状態機械（4 状態）

```
idle ──pointerdown──→ charging ──pointerup──→ releasing ──(1 frame)──→ decay ──(数秒)──→ idle
```

- **idle**: 何もしていない待機状態。粒子はパーリンノイズ等の自律運動で漂わせる。
- **charging**: ポインタを押している間。経過時間（+ドラッグ量などの追加入力）から
  `level ∈ [0, 1]` を毎フレーム計算し、音響エンジンへ `chargeLevel(level)` を送る。
  レベルの立ち上がりは `easeOutQuad` 等のイージングで加速感を出す。
- **releasing**: 解放の演出を単発で発火するための 1 フレームだけの中継状態。
  実処理（インパルス付与・衝撃波 spawn・フラッシュ・画面シェイク・
  `audio.release()` 呼び出し）は `pointerup` ハンドラ側で「trigger」関数として
  即座に行い、`releasing` 状態はその次のフレームで `decay` へ抜けるだけの薄いゲート。
- **decay**: 解放後の余韻。`energy` を 1→0 へ時間で減衰させ、`audio.setEnergy(energy)`
  で音響エンジンにも伝える。`energy <= 0` で `idle` に戻る。

短いクリック/タップ（保持時間が閾値未満）は `charging` を経由せず「pop」の軽量パスに
分岐させる ─ 溜め演出を経ない小さな反応として、`triggerPop` のような別関数に切り出す。

**拡張（参照実装の Phase 9-1）**: 解放に「来るぞ」という間を作り、着弾を音楽の拍に揃えるなら、
`releasing` を `inhale → impact` の 2 状態に分ける。`audio.release()` が着弾までの秒数を返し、
`inhale` はその時刻まで粒子を吸い込ませて待ち、`impact` でヒットストップ（`timeScale` を
落とし、摩擦は `FRICTION ** timeScale`）を掛けてから `decay` へ抜ける。

```
idle ──pointerdown──→ charging ──pointerup──→ inhale ──着弾時刻──→ impact ──ヒットストップ──→ decay ──→ idle
```

詳細と他の演出は `references/game-feel.md`。

## 2. ポインタ統合（マウス/タッチの一本化）

- Pointer Events（`pointerdown` / `pointermove` / `pointerup` / `pointercancel`）で
  マウスとタッチを同一パスに統合する。個別に `mousedown`/`touchstart` 等を扱わない。
- 座標は `[0,1]` に正規化してから音響エンジンへ渡す（`x / width, y / height`）。
  ピクセル座標のまま音響側に渡さない ─ 画面サイズ非依存にするため。
- ドラッグによる「溜めブースト」を入れる場合、移動距離を累積してレベルに加算する
  （`dragBoost = min(dragBoost + distance * 係数, 上限)`）。上限を必ず設けること。
- `pointerup` 時、保持時間が短ければ pop パスへ、長ければ release パスへ分岐する
  閾値（例: 300ms）を 1 箇所の定数として持つ。

## 3. 性能自動調整（パーティクル数の段階的削減）

重いエフェクト（パーティクル数が多い等）は環境によって fps が落ちる。固定数のまま
出荷すると低スペック環境で破綻するので、起動直後の実測 fps に応じて段階的に間引く。

アルゴリズムの要点:

1. `deltaTime`（前フレームからの経過 ms）を一定フレーム数だけ貯める。
2. 平均 fps としきい値を比較するだけでなく、**変動係数（標準偏差 / 平均）** も見る。
   fps が低くても間隔が一定なら、実際の処理負荷ではなく OS の省エネモードや
   ディスプレイのリフレッシュレート制限（rAF のスロットリング）の可能性が高いので
   間引かない。変動が大きい（＝処理落ちで揺れている）場合のみ実際に間引く。
3. 外れ値（タブ切り替え復帰直後の巨大な deltaTime 等）は計測対象から除外する。
4. 間引きは「配列を切り詰めるだけ」（`particles.length = 次の段の値`）にして、
   新規オブジェクト生成コストをかけない。
5. 間引いた後も、まだ下の段が残っていれば再度同じ手順で評価し、最下段に到達するか
   十分な fps が出たら計測を打ち切る（無限に評価し続けない）。
6. 間引き後にインデックスアクセスする箇所（pop の飛び先計算など）は、削減後の
   `particles.length` を基準にする ─ 元の固定パーティクル数の定数を使わない
   （配列外アクセスを避けるため）。

## 4. 導入オーバーレイ（AudioContext のゲート処理）

ブラウザの自動再生ポリシーにより `AudioContext` はユーザー操作なしに鳴らせない。
最初の操作を「音を起動するためのゲート」と「1 回目の操作」を同時に兼ねさせると、
ユーザーから見て余計なクリックが増えない。

- 全画面オーバーレイ（「タップして始める」等）を用意し、その `pointerdown` で
  `audio.start()` を呼ぶ。
- **タッチでは `pointerdown` で音声を解錠できない**（HTML の user activation はタッチだと
  `pointerup` / `touchend` から）。`start()` は `resume()` を待たずに配線だけ済ませ、
  エンジン側で `pointerup` / `touchend` / `click` / `keydown` のたびに止まっていれば
  `resume()` する常駐リスナーを置く（`audio-engine-skeleton.ts` の `installUnlockListeners()`）。
  `pointerdown` で `resume()` の解決を待つ作りにすると、スマホでは永久に無音になる。
- `start()` の Promise が解決（または失敗）したら、そのまま同じ座標で 1 回目の
  `handlePointerDown` を呼び、charging 状態に入る（ユーザーの最初のジェスチャーを
  無駄にしない）。`start()` の失敗は `catch` し、音が出なくても描画は続ける。
- 起動を待つ間に指が離れていたら（`pointerup` を `{ once: true }` で見張る）、溜めでなく
  タップとして扱う。離し済みのまま charging に入ると、次のタップまで抜けられない。
- iOS の「振って解放」等のモーションセンサー許可（`DeviceMotionEvent.requestPermission()`）も
  ユーザー操作の中でしか通らない。タッチは `touchend` で要求する。http では
  `DeviceMotionEvent` 自体が存在しないので `typeof` で守り、音声の起動より後に置く
  （ここで例外が出ても音声の起動を巻き込まないため）。
- オーバーレイは即座に消さず、トランジション時間だけ待ってから DOM から除去する
  （フェードアウト等の演出を切れさせないため）。

## 5. その他の実装上の注意点（元実装からの教訓）

- p5 v2 系は Friendly Error System が誤検知でログを大量に吐き、それ自体が fps を
  削ることがある。本番ビルドでは `disableFriendlyErrors` を早期に無効化しておく。
- `colorMode(HSB, 360, 100, 100, 100)` のときアルファのレンジは **100**（255 ではない）。
  フラッシュ演出などで `fill(0, 0, 100, 255)` のように 255 を渡すバグは起きやすい。
- 粒子ループの中で毎フレーム再計算しなくてよい値（軌道半径・引力係数など、
  状態遷移時にしか変わらない値）はループの外・フレーム先頭で 1 回だけ算出する。
- `AnalyserNode` からの読み出し（`getFloatTimeDomainData` 等）は 1 フレームに
  1 回に抑える（粒子ごとに読むと無駄にコストがかかる）。
