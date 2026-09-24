# stack-native.md ─ SuperCollider + Processing + Tidal 実装ガイド

ネイティブ版の実装ガイド。参照実装: `~/Projects/Game/heartburst`（sc/main.scd, processing/Heartburst/*.pde, bin/start.sh, bin/test-osc.scd）。

## 構成

```
Processing (視覚+入力・状態機械の主管) ──OSC :57120──→ SuperCollider (sclang+scsynth, SynthDef+SuperDirt)
                                       ←──OSC :12000── (← /sc/amp のみ)
Processing ──OSC :6010──→ Tidal Cycles (ghci, パターン層)
```

- 状態機械の正本は Processing 側（入力発生源）。SC/Tidal は受けたメッセージに反応するだけ
- Tier 1（Processing + SC カスタム SynthDef のみ）でコア体験が成立、Tier 2（+ SuperDirt + Tidal）はオプショナルな持続層
- OSC アドレス・ポート・引数型の正本は architecture-template.md で確定してから実装に入る（並行実装が破綻しないための契約）

## 環境構築（到達状態ベース。コマンドは達成手段の一例）

導入系は一次情報裏取り必須（P1 ルール）。到達状態 = 各コマンドで実バージョンが確認できること。

1. **SuperCollider / Processing**: `brew install --cask supercollider processing` → `sclang -v` でバージョン確認、Processing.app 配置確認。processing.org は WebFetch で 403 を返すことがある → cask の `.rb` ソースを直接確認すれば代替裏取りできる（両 cask とも公式 GitHub リリースの署名済み DMG を取得しているか確認する）
2. **GHC/cabal/tidal**: `brew install ghc cabal-install` → `cabal update && cabal install tidal --lib`。GHC が最新すぎると tidal 側の依存が対応しておらず失敗することがある → 失敗時は旧版 GHC へフォールバック
3. **SuperDirt quark**: headless インストール（scratchpad の `.scd` を `sclang` に渡すだけで IDE 不要・完結）。到達状態 = SuperDirt + Dirt-Samples + Vowel の取得確認
4. **oscP5**: Processing 4.5 系の公式 CLI は「Processing contributions」経由のライブラリ導入に対応しない（examples のみ）。作者公式 GitHub リリース（`sojamo/oscp5`）の zip を `~/Documents/Processing/libraries/` に手動配置する（netP5 は 2.x で oscP5.jar に同梱）
5. **BootTidal.hs**: 公式配布物は cabal store（`~/.local/state/cabal/store/.../share/...`）配下にある。見つけてリポジトリの `tidal/` にコピーする
6. **Processing CLI**: `Processing cli --sketch=<dir> --run/--build` でビルド検証を自動化できる。sketchbook パスは `Processing sketchbook list` で取得

## 実装構成

### sc/main.scd（`sc/main.scd:1`）

- 冒頭にチューニング定数を集約（マスター音量・リバーブ・`/sc/amp` 送出レート・ポート番号）。ポート契約の正本は architecture.md 側であることをコメントで明示する
- `s.options.numInputBusChannels = 0`（`sc/main.scd:21`）─ 出力専用アプリであることを明示し、入出力デバイスのサンプルレート不一致を回避する
- SynthDef 群（`sc/main.scd:45-93`）: ワンショット/持続音を用途別に分離（例: chargeDrone=持続ドローン、dropBoom/shockwave=ワンショット、shimmer/popPluck=群発生用の軽量プラック）。ドローン系は制御バス（`Bus.control`）経由でレベルを追従させ、`gate` で `EnvGen.kr(Env.asr(...), gate, doneAction: 2)` を使い解放時にフリーズしない
- マスター（`sc/main.scd:96-102`）: 全音源を共有 FX バスに集約 → `FreeVerb2` → `Limiter.ar` でクリップ防止 → `SendReply.kr` で振幅を一定レートで送出。ノードツリーは `Group.after` で音源グループの後段に置き実行順を保証する
- OSCdef 群（`sc/main.scd:113-163`）: 受信メッセージへの反応のみを書く。判断ロジック（状態遷移）は持たせない
- SuperDirt はクラス存在ガード付きで起動（`sc/main.scd:169-179`）。詳細は下記「落とし穴」参照

### Processing（`processing/Heartburst/`）

- `Heartburst.pde` ─ メインスケッチ。状態機械（idle/charging/releasing/decay）・入力ハンドラ（`mousePressed`/`mouseDragged`/`mouseReleased`）・OSC 送信トリガーの主管。チューニング定数を冒頭に一元集約
- `OscBridge.pde` ─ OSC 送受信の集約クラス。送信は SC 向け（`/charge/*`, `/release`, `/pop`）と Tidal 向け（`/ctrl "key" value`）を分離。受信（`/sc/amp`）は生値を保持し `updateSmoothing()` で毎フレーム lerp 平滑化、`getAmp()` で描画側へ渡す。送信失敗（受信側未起動）で例外を投げてスケッチを落とさないよう try-catch で握りつぶす
- `Particle.pde` ─ 粒子 1 個の状態。色は HSB 分解までコンストラクタで済ませ、`display()` では毎フレーム再計算しない（不変値のキャッシュ）
- `Shockwave.pde` ─ 衝撃波リング。配列使い回し（非活性個体を再利用、毎フレーム生成しない）
- `oscEvent(OscMessage)` はメインスケッチ（PApplet）に置く ─ oscP5 はコンストラクタに渡したオブジェクトに対しリフレクションで `oscEvent` を探して呼ぶため

### bin/start.sh・bin/test-osc.scd

- `start.sh` は SuperCollider → (Tidal) → Processing の順で起動し、SC は `sc.log` に "ready" 行が出るまでポーリング待機してから次工程へ進む（到達状態確認してから次を起動する設計）
- Tidal は `tail -f /dev/null | ghci ...` で stdin を開きっぱなしにして起動（理由は下記「落とし穴」）
- Processing は `Processing cli --sketch=<dir> --run` をバックグラウンドで起動（`&` はフォアグラウンドシェル内ではなく永続バックグラウンドで。理由は下記）
- `test-osc.scd` は Processing の代わりに OSC シーケンス（pop×3 → charge 3秒 → release → energy 減衰）を SC(57120) と Tidal(6010) へ直接送る自動検証ハーネス。使い方は verification.md 参照

## ネイティブ固有の落とし穴（詳細な症状/原因/対処は pitfalls.md 参照）

- `numInputBusChannels = 0`（入出力デバイスのサンプルレート不一致回避）
- SuperDirt はクラス名を直接書かず `\SuperDirt.asClass` で存在ガードし、未導入環境でもコンパイルエラーにしない
- `ghci` は stdin が EOF になると（バックグラウンド起動時など）静かに終了する。ログにエラーが出ないため気づきにくい
- `Processing cli --run` の JVM は runner が親プロセス。runner が死ぬと JVM が孤児化してウィンドウが無反応になる
- Processing の `colorMode` のレンジ指定（例: HSB 360/100/100/100）は alpha 引数にも効く。255 前提の値を書くと頭打ちになる
- 音出しテスト前後はシステム音量の退避・復元を忘れない（BT スピーカー・耳の保護）
