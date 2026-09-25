// テストケース5: Astro 7.x の依存・セキュリティ勧告（観点 13）と非推奨設定（観点 11）
// 同じフォルダの package.json / pnpm-lock.yaml と組で読む。
// 期待される検出:
// - [C][Deps] lockfile の astro が 7.2.5 に解決（package.json は ^7.0.0）─ 7.2.8 未満のため GHSA-26w7-cxv4-gfx2
// - [W][Deps] package.json の sharp 直接依存 ^0.34.3 が 0.35.4 未満を許す ─ astro 7.2.8 以降は自分の依存（^0.35.4）を使うので、直接依存は削除か ^0.35.4 以上へ（src で sharp を直接 import していないので削除を勧めてよい）
// - [W][Astro 7] markdown.remarkPlugins（7.0 から非推奨。警告は出るが動く）─ 修正例は markdown: { processor: unified({ remarkPlugins: [...] }) }
// - [W][Deps] @astrojs/markdown-remark 7.2.1 ─ astro 7.2.5 の optional peer（7.2.4 の完全一致）を満たさず、astro を 7.3 系へ上げると ^7.3.0 からも外れる。astro の peer が指す版に揃える
//
// 検出しないもの:
// - dev / preview の自動バックグラウンド化は運用上の注記で、欠陥として挙げない
// - package.json の範囲指定（^7.0.0）だけを根拠に Critical にしない（根拠は lockfile の解決版）
import { defineConfig } from 'astro/config';
import remarkToc from 'remark-toc';

export default defineConfig({
  markdown: {
    remarkPlugins: [remarkToc],
  },
});
