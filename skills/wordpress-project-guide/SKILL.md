---
name: wordpress-project-guide
description: "WordPress 案件の基盤ガイド + 品質ツール一括セットアップ。WPCS 準拠の規約ガイダンスと、WPCS 3.x + PHP_CodeSniffer / PHPStan（phpstan-wordpress）の導入ランブック。トリガー: 「WP セットアップして」「WordPress 案件に品質ツールを入れて」「WPCS を設定」「PHPStan を WordPress に導入」「WordPress の静的解析」、および wp-content / wp-config.php を含むプロジェクトで PHP 規約が問われる場面（php-project-guide の PSR より本スキル優先）。NOT for: Laravel / Symfony、テーマ・プラグインの機能開発、デプロイ。"
---

# WordPress Project Guide

WordPress 案件で「規約の判断」と「品質ツールの導入」を担う基盤スキル。
汎用 PHP スキル（PSR/PER 前提）のガイダンスは WordPress と衝突するため、WP 案件では本スキルを優先する。

## なぜ汎用 PHP ガイダンスを上書きするのか

| 観点 | PSR/PER（汎用） | WordPress（本スキル） |
|---|---|---|
| インデント | 4 スペース | **タブ** |
| 命名 | camelCase | **snake_case** |
| strict_types | 全ファイル必須 | 使わない（コアが緩い型で呼ぶ） |
| global | 禁止・DI 推奨 | `global $post` / `$wpdb` は正規パターン |
| 条件式 | 通常順 | **Yoda 条件**（`if ( 'value' === $var )`） |

## コーディング規約の要点（WPCS）

コード生成・レビュー時に常に適用する:

1. **エスケープ**: 出力は `esc_html()` / `esc_attr()` / `esc_url()` / `wp_kses_post()` を通す
2. **サニタイズ**: 入力は `sanitize_text_field()` 等で受ける
3. **DB**: 直接クエリは `$wpdb->prepare()` 必須
4. **nonce**: フォーム・AJAX は `wp_nonce_field()` / `check_ajax_referer()` で検証
5. **i18n**: 表示文字列は `__()` / `_e()` + text domain
6. インデントはタブ、関数・変数は snake_case、比較は Yoda 条件
7. フック中心設計（直接改変せず `add_action` / `add_filter`）

## 品質ツール セットアップ ランブック

### 前提（マシン共通・初回のみ）

```bash
# WPCS はグローバル 1 回で全案件に効く（phpcs は自己完結ツール）
composer global config allow-plugins.dealerdirect/phpcodesniffer-composer-installer true
composer global require --dev wp-coding-standards/wpcs:"^3.0"
# 確認: WordPress 系標準が登録されているか
$(composer global config bin-dir --absolute)/phpcs -i
```

共通ルールセット（日本語コメント対応版）を `~/Projects/php-standards/wordpress-ja.phpcs.xml` に置く。
無ければ `references/wordpress-ja.phpcs.xml` をコピーして作成する。

### 案件ごと（PHPStan は per-project が正解）

phpstan.neon の `paths`（解析対象）が案件ごとに違うため、グローバル化の節約効果はない。

**手順 1 ─ レイアウト検出**: wp-content の場所を特定する。パターンは 2 系統。

- 標準: `<root>/wp-content/`
- コア分離型: `<root>/<サブディレクトリ>/wp-content/`（サブディレクトリ名は `wp/` `wpd/` など案件により様々。`find <root> -maxdepth 3 -name wp-config.php` と themes ディレクトリの位置で判定）

**手順 2 ─ 自作コード特定**:

- `git ls-files <wp-content>/themes/` ─ git 追跡されているテーマが自作
- style.css の `Author:` 行・`Template:` 行（親テーマ特定）を確認
- git 管理外の案件は Author 行で判定
- 市販テーマ（TCD 等）+ WP デフォルトのみで自作コードゼロなら導入不要と報告して終了

**手順 3 ─ composer 導入**（composer.json が無い classic WP でも require-dev 専用に作ってよい。本番コードは composer 非依存のまま）:

```bash
cd <root> && composer require --dev szepeviktor/phpstan-wordpress
```

wordpress-stubs は自動依存で入る（別途 require 不要）。

**手順 4 ─ phpstan.neon 生成**（`<root>` 直下）:

```neon
includes:
    - vendor/szepeviktor/phpstan-wordpress/extension.neon

parameters:
    level: 1
    paths:
        - <自作テーマ/プラグインの相対パス>
    excludePaths:
        - <paths 配下の dev/・node_modules/ を「パス (?)」形式で除外>
    # 親テーマ等をシンボル解決の対象にする（解析対象にはしない）
    scanDirectories:
        - <親テーマの相対パス>
        - <カスタムフィールド系プラグイン>
```

- **excludePaths は必ず確認**: テーマ内の `dev/`（gulp/webpack 作業場）に node_modules が入っていると OOM クラッシュする。`(?)` は不存在でもエラーにしない optional 記法
- **カスタムフィールド系の判別**: `get_field()` 使用時、提供元は advanced-custom-fields / advanced-custom-fields-pro / **secure-custom-fields**（ACF の WordPress.org フォーク）のいずれか。plugins/ を実際に見て判定
- level は 1 から開始（既存コードベース前提）。新規開発なら 5

**手順 5 ─ 実行と調整（最大 2 反復）**:

```bash
cd <root> && vendor/bin/phpstan analyse --no-progress --memory-limit=2G
```

- メモリは **2G を既定**にする（ACF 系の scanDirectories が重い案件は 1G で OOM する）
- `function.notFound` / `constant.notFound` が大量 → 提供元プラグインを grep で特定し scanDirectories に追加して再実行
- 2 反復で解消しない残りは**死んだ参照の可能性（検出成果）**としてそのまま報告する。ゼロ件を目指さない。典型例: 削除済みプラグインの関数呼び出し、PHP 8 で削除された `create_function`、スターターテーマ改名の残骸
- 死んだ参照を見つけたら「本当にロードされているか」を require チェーン（functions.php の require → テンプレート階層）で確認してから報告する。未ロードなら実害なし・削除候補

**手順 6 ─ .gitignore**: `/vendor/` が無ければ追記。composer.json / composer.lock / phpstan.neon は追跡推奨（コミットはユーザー判断）。

### PhpStorm 連携

GUI 設定手順と実地で判明した罠（設定が既存プロジェクトに共有されない等）は `references/phpstorm-setup.md` を参照。

## トラブルシュート早見表

| 症状 | 原因 | 対処 |
|---|---|---|
| PHPStan OOM クラッシュ | テーマ内 node_modules / ACF scan | excludePaths 確認 → `--memory-limit=2G` |
| `get_field not found` 大量 | フィールド系プラグイン未 scan | ACF / SCF を scanDirectories へ |
| 素の WordPress 標準で日本語コメントに警告 | full-stop / 末尾文字 sniff | `wordpress-ja.phpcs.xml`（references/ に雛形）を Custom 指定 |
| phpcs -i に WordPress が出ない | composer-installer プラグイン未許可 | `allow-plugins` 設定後に再 require |
| notFound がゼロにならない | 死んだ参照 | 消さずに報告（検出成果）。ロード有無を require チェーンで裏取り |
