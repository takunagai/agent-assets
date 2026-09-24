// ============================================================
// audio-engine-skeleton.ts ─ Web Audio 音響エンジンの骨格
//
// 置換ガイド（新規作品を作るとき）:
//   - このファイルは src/audio/{{artwork-slug}}-engine.ts にリネームする
//   - クラス名 ArtworkAudioEngine → {{ARTWORK_NAME}}AudioEngine 等に改名し、
//     audio-engine-contract.ts（engine.ts）側の import も合わせて書き換える
//   - 「ここに作品の音を実装」の各メソッド本体を作品のジェスチャーに合わせて書く
//   - ネイティブ版（SuperCollider）と対で作る場合、チューニング定数と
//     main-skeleton.scd 側の対応する定数を両方更新して質感を揃える
//
// マスターチェーン（fxIn → dry/wet リバーブ → limiter → analyser）・生成 IR・
// ノイズバッファ・tanh カーブ・KS プラックバンク・getAmp は汎用インフラとして
// そのまま使える。作品固有の音（chargeStart/chargeLevel/release/pop の中身）
// だけを差し替えるのがこの骨格の使い方。
// ============================================================

import type { AudioEngine } from "./audio-engine-contract";

// ---- チューニング定数 ----
const MASTER_VOLUME = 0.9;
const REVERB_MIX = 0.33; // ドライ/ウェット比（0=ドライ 1=ウェット）
const REVERB_SECONDS = 2.6; // 生成 IR の減衰時間

// パターン層（Strudel 等・オプショナル）と共有する連続値。
// charge/energy 以外の値が要る作品はここに追加する
export const controlSignals = { charge: 0, energy: 0 };

export class ArtworkAudioEngine implements AudioEngine {
  private ctx!: AudioContext;
  private fxIn!: GainNode; // 全音源の合流点（このノードに繋げばマスターへ流れる）
  private analyser!: AnalyserNode;
  private analyserBuf!: Float32Array<ArrayBuffer>;
  private noiseBuf!: AudioBuffer; // 使い回すホワイトノイズ（インパクト系の音に）
  private tanhCurve!: Float32Array<ArrayBuffer>; // ソフトクリップ用カーブ（WaveShaperNode.curve に使う）

  async start(): Promise<void> {
    if (this.ctx) {
      await this.ctx.resume();
      return;
    }
    this.ctx = new AudioContext();
    await this.ctx.resume();

    // ---- master: fxIn → [dry, convolver reverb] → limiter → destination ----
    this.fxIn = this.ctx.createGain();
    const dry = this.ctx.createGain();
    dry.gain.value = 1 - REVERB_MIX;
    const wet = this.ctx.createGain();
    wet.gain.value = REVERB_MIX;
    const reverb = this.ctx.createConvolver();
    reverb.buffer = this.buildImpulseResponse(REVERB_SECONDS);

    const limiter = this.ctx.createDynamicsCompressor();
    limiter.threshold.value = -3;
    limiter.knee.value = 0;
    limiter.ratio.value = 20;
    limiter.attack.value = 0.003;
    limiter.release.value = 0.25;

    const master = this.ctx.createGain();
    master.gain.value = MASTER_VOLUME;

    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 512;
    this.analyserBuf = new Float32Array(this.analyser.fftSize);

    this.fxIn.connect(dry).connect(master);
    this.fxIn.connect(reverb).connect(wet).connect(master);
    master.connect(limiter);
    limiter.connect(this.analyser);
    this.analyser.connect(this.ctx.destination);

    // ---- 使い回し素材 ----
    this.noiseBuf = this.buildNoiseBuffer(2.0);
    this.tanhCurve = this.buildTanhCurve(2048);
    this.buildPluckBank(); // KS プラックが要らない作品はこの行と pluckBank 系を削除してよい

    // ---- パターン層（Strudel・オプショナル）─ 失敗しても本体は動く ----
    // 要らなければこのブロックごと削除する。使う場合は pattern-skeleton.ts を参照
    // const { startPatternLayer } = await import("./pattern");
    // void startPatternLayer(this.ctx);
  }

  // ============ ここに作品の音を実装 ============
  //
  // 元実装（Heartburst）では chargeStart/chargeLevel で溜めドローンを
  // 起動・追従させ、release で複数の音源（ドロップ・衝撃波・シャワー）を
  // 一斉発火していた。ジェスチャーの意味に合わせて書き換える。
  // 下記は KS プラックバンクだけを使った最小の動作例。

  chargeStart(_x: number, _y: number): void {
    if (!this.ctx) return;
    // 例: 継続的に鳴る音（オシレーター等）をここで起動する
  }

  chargeLevel(level: number): void {
    if (!this.ctx) return;
    const l = Math.min(Math.max(level, 0), 1);
    controlSignals.charge = l;
    // 例: 起動済みの継続音の周波数・音量・フィルタを l に追従させる
  }

  release(level: number, x: number, _y: number): void {
    if (!this.ctx) return;
    const l = Math.min(Math.max(level, 0), 1);
    controlSignals.charge = 0;
    controlSignals.energy = 1;
    // 例: ノイズ + tanh ソフトクリップの「衝撃」を 1 発鳴らす
    this.impact(l, (x * 2 - 1) * 0.5);
  }

  pop(x: number, _y: number): void {
    if (!this.ctx) return;
    // 短いクリック/タップ用の軽い一発（KS プラックバンクの例）
    this.pluck(880, 0.3, (x * 2 - 1) * 0.6, 0.28);
  }

  // 例: ノイズバッファ → バンドパスで帯域を絞る → tanh カーブでソフトクリップ
  // → 短いエンベロープ、という「衝撃」系の音の作り方（release 用の最小例）
  private impact(amp: number, pan: number): void {
    const t = this.ctx.currentTime;
    const src = this.ctx.createBufferSource();
    src.buffer = this.noiseBuf;

    const bpf = this.ctx.createBiquadFilter();
    bpf.type = "bandpass";
    bpf.Q.value = 1.5;
    bpf.frequency.setValueAtTime(6000, t);
    bpf.frequency.exponentialRampToValueAtTime(200, t + 0.4);

    const shaper = this.ctx.createWaveShaper();
    shaper.curve = this.tanhCurve; // ソフトクリップで倍音を付与

    const env = this.ctx.createGain();
    env.gain.setValueAtTime(0.0001, t);
    env.gain.exponentialRampToValueAtTime(0.2 + amp * 0.5, t + 0.004);
    env.gain.exponentialRampToValueAtTime(0.0001, t + 0.4);

    const panner = this.ctx.createStereoPanner();
    panner.pan.value = pan;

    src.connect(bpf).connect(shaper).connect(env).connect(panner).connect(this.fxIn);
    src.start(t);
    src.stop(t + 0.5);
  }

  // ============ KS（Karplus-Strong）プラックバンク ============
  //
  // DelayNode のフィードバックループは Web Audio の最小遅延 128 サンプル制約
  // により高い音程が作れないうえ、ループ内 BiquadFilter が不安定警告を出す。
  // そこで起動時に JS でオフライン合成し AudioBuffer バンクとして保持する
  // （発音は再生のみ・音程正確・再生コスト極小）。
  private pluckBank = new Map<string, AudioBuffer>();

  private pluckKey(freq: number, decaySec: number): string {
    return `${freq.toFixed(2)}:${decaySec}`;
  }

  // 使う周波数群をここで登録する（例: ペンタトニック等の音列を作品に合わせて選ぶ）
  private buildPluckBank(): void {
    this.pluckBank.set(this.pluckKey(440, 0.6), this.renderKarplusStrong(440, 0.6));
    this.pluckBank.set(this.pluckKey(880, 0.28), this.renderKarplusStrong(880, 0.28));
  }

  // 古典 KS: ノイズ 1 周期のリングバッファを「隣接平均 × フィードバック」で巡回
  private renderKarplusStrong(freq: number, decaySec: number): AudioBuffer {
    const sr = this.ctx.sampleRate;
    const len = Math.floor(sr * (decaySec + 0.3));
    const buf = this.ctx.createBuffer(1, len, sr);
    const out = buf.getChannelData(0);
    const period = Math.max(2, Math.round(sr / freq));
    const ring = new Float32Array(period);
    for (let i = 0; i < period; i++) ring[i] = Math.random() * 2 - 1;
    const feedback = Math.pow(0.001, period / sr / decaySec); // decaySec 後 -60dB
    let idx = 0;
    for (let i = 0; i < len; i++) {
      const cur = ring[idx];
      const next = ring[(idx + 1) % period];
      out[i] = cur;
      ring[idx] = feedback * 0.5 * (cur + next); // 平均 = 1 次 LPF（弦の高域減衰）
      idx = (idx + 1) % period;
    }
    return buf;
  }

  private pluck(freq: number, amp: number, pan: number, decaySec: number): void {
    const buf = this.pluckBank.get(this.pluckKey(freq, decaySec));
    if (!buf) return; // buildPluckBank に登録していない (freq, decaySec) の組は鳴らない
    const t = this.ctx.currentTime;
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    const gain = this.ctx.createGain();
    gain.gain.value = amp;
    const panner = this.ctx.createStereoPanner();
    panner.pan.value = pan;
    src.connect(gain).connect(panner).connect(this.fxIn);
    src.start(t);
  }

  // ============ 視覚フィードバック用 ============

  setEnergy(energy: number): void {
    controlSignals.energy = Math.min(Math.max(energy, 0), 1);
  }

  getAmp(): number {
    if (!this.analyser) return 0;
    this.analyser.getFloatTimeDomainData(this.analyserBuf);
    let sum = 0;
    for (let i = 0; i < this.analyserBuf.length; i++) sum += this.analyserBuf[i] ** 2;
    const rms = Math.sqrt(sum / this.analyserBuf.length);
    return Math.min(rms * 2.5, 1); // 係数は聴感・演出に合わせて調整する
  }

  // ============ 素材生成（汎用・変更不要） ============

  private buildNoiseBuffer(seconds: number): AudioBuffer {
    const len = Math.floor(this.ctx.sampleRate * seconds);
    const buf = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
    const ch = buf.getChannelData(0);
    for (let i = 0; i < len; i++) ch[i] = Math.random() * 2 - 1;
    return buf;
  }

  // 生成 IR: 指数減衰するデコリレートしたステレオノイズ（外部ファイル不要のリバーブ）
  private buildImpulseResponse(seconds: number): AudioBuffer {
    const len = Math.floor(this.ctx.sampleRate * seconds);
    const buf = this.ctx.createBuffer(2, len, this.ctx.sampleRate);
    for (let c = 0; c < 2; c++) {
      const ch = buf.getChannelData(c);
      for (let i = 0; i < len; i++) {
        ch[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.4);
      }
    }
    return buf;
  }

  private buildTanhCurve(n: number): Float32Array<ArrayBuffer> {
    const curve = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1)) * 8 - 4; // -4..4
      curve[i] = Math.tanh(x);
    }
    return curve;
  }
}
