# バージョン履歴

`SKILL.md` から分離。version 更新時はここへ追記する。


| バージョン | 日付 | 変更内容 |
|------------|------|----------|
| 3.1.0 | 2026-09-25 | **Astro 7.1〜7.3 追補・依存のセキュリティ勧告**: 観点 13 と `[Deps]` ラベルを新設し、Step 1 で package.json と lockfile を読むよう変更。lockfile の astro 解決版 < 7.2.8 を GHSA-26w7-cxv4-gfx2 として Critical、sharp 直接依存の 0.35.4 未満と `@astrojs/markdown-remark` と astro の peer 要件の不一致を Warning、Starlight の peer 不一致を Info で検出。remark 系設定の記述を「Sätteri と互換でない可能性」という旧記述から「7.0 から非推奨・`@astrojs/markdown-remark` 必須」へ訂正し、修正例を `processor: unified({...})` に差し替え。dev / preview の自動バックグラウンド化（運用注記）、`glob()` の `deferRender`・CSP の `kind`・`session: false`（Info）を追記。eval 用に test-case-5 を追加 |
| 3.0.0 | 2026-07-05 | **Astro 7 / adapter v14 基準へ全面改修**: レガシー検出（5→6）と Astro 7 移行チェック（6→7）の二層化、Rust コンパイラ HTML 厳格化・Sätteri・src/fetch.ts・compressHTML・Vite 8・@astrojs/db 削除・astro:transitions 内部 API の検出を追加、Cloudflare Pages 廃止反映（Workers 一本化・platformProxy/main 旧値/.assetsignore の残骸検出・Route Caching 活用）、CSP を `security.csp` に是正、参照ドキュメントを `docs.astro.build`（v7 current）へ更新 |
| 2.0.0 | 2026-01-18 | **Astro 6.0+ 専用版**: Cloudflare メインデプロイ対応、新カテゴリ（Astro 6.0 Migration, Cloudflare）追加、削除API検出ルール追加、参照ドキュメントを v6.docs.astro.build に更新 |
| 1.1.0 | 2026-01-17 | 実行フロー詳細化、自動修正モード追加、CI/CD統合ガイド追加 |
| 1.0.0 | 2026-01-17 | 初版リリース |
