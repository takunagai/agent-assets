# WordPress から EmDash への移行

> [!note] 基準
> 本リファレンスは emdash 0.29.0（2026-07-10 リリース）/ 2026-07-13 検証を基準とする。作業開始前に公式移行ガイド（`docs/src/content/docs/migration/from-wordpress.mdx`、`migration/content-import.mdx`）で現行仕様を確認する。

## 移行経路の全体像

WordPress からの移行は **CLI コマンドではなく、admin dashboard のインポートウィザード**（または REST `/_emdash/api/import/wordpress/`）から行う。全ソース共通で 4 段階のフローを踏む。

```
Connect（接続） → Analyze（解析） → Prepare（スキーマ準備） → Execute（インポート実行）
```

インポート元は 3 種類あり、対応範囲が異なる。

| ソース | 対象 | プローブ | OAuth | 完全インポート |
|---|---|---|---|---|
| `wxr` | WordPress エクスポートファイル（.xml） | 不要 | 不要 | 可 |
| `wordpress-com` | WordPress.com ホスティングサイト | 可 | 要 | 可 |
| `wordpress-rest` | セルフホスト WordPress（汎用 REST プローブ） | 可 | 不要 | **プローブのみ**（公式ドキュメント記載） |

**WXR ファイルアップロードが最も完全な移行方法**として公式に推奨されている。ドラフト・カスタムフィールド・非公開投稿を含め全データを捕捉できる。

> [!warning] emdash-exporter（WordPress 側プラグイン）と docs の記載に差分あり
> WP 側に導入する `emdash-exporter` プラグイン（後述）の README は「ワンクリックでファイルダウンロードなしにインポートできる」「投稿・メディア・タクソノミー・カスタムフィールドを含め全データをエクスポートできる」と謳っており、認証つき REST エンドポイント（`/analyze` `/content` `/media` `/taxonomies` `/options`）を提供する。一方 EmDash 本体の公式ドキュメント（`content-import.mdx`）は「セルフホスト WordPress の REST 経路はプローブのみ（Probe: Yes / Full Import: Probe only）」と明記している。どちらが admin dashboard のインポートウィザードに実際に配線されているかは今回の裏取りでは確認できなかった。**本番移行では WXR ファイルアップロードを主経路とし、`emdash-exporter` 経由の完全インポートを使う場合は事前に EmDash 側の管理画面で実際にフルインポートが選べるか検証してから計画する。**

## WordPress 側の準備（WXR エクスポート）

1. WordPress admin で **ツール → エクスポート → すべてのコンテンツ → エクスポートファイルをダウンロード**
2. EmDash admin で **設定 → インポート → WordPress** を開く
3. `.xml` ファイルをドラッグ&ドロップ、またはクリックして選択（ブラウザ内でパースされる）

再実行は安全（WordPress ID でマッチングされるため重複作成されない）。

## WordPress 側の準備（emdash-exporter プラグイン経由・参考）

`emdash-exporter`（https://github.com/emdash-cms/wp-emdash 内 `plugins/emdash-exporter`、PHP プラグイン、2026-07-13 時点 stable tag 1.0.0）を使うと、WP 側に REST API を追加してファイルダウンロードなしでの連携を狙える。

- 認証: WordPress Application Passwords（WordPress 5.6+ 組み込み機能）。ユーザープロフィールで発行し、ユーザー名 + アプリケーションパスワードで REST 認証する
- エンドポイント: すべて `/wp-json/emdash/v1/` 配下
  - `GET /probe` ─ 認証不要。サイト情報・対応可否を返す
  - `GET /analyze` ─ 要認証。インポート計画用のサイト全体解析
  - `GET /content?post_type=post` ─ 要認証。投稿取得（ページネーションあり）
  - `GET /media` / `GET /media/{id}?include_data=true` ─ 要認証。メディア取得（後者は base64 データを含められる）
  - `GET /taxonomies` ─ 要認証。タクソノミー・タームの取得
  - `GET /options` ─ 要認証。サイトオプションの取得
- 対応データ: 投稿・固定ページ・カスタム投稿タイプ（ドラフト含む）、ACF フィールド、Yoast SEO / Rank Math の SEO メタ、カテゴリ・タグ・カスタムタクソノミー（階層保持）、投稿者情報

導入手順: `emdash-exporter` フォルダを `/wp-content/plugins/` にアップロード → 有効化 → ユーザープロフィールでアプリケーションパスワードを発行 → EmDash 側でサイト URL と認証情報を入力してインポート開始。

## Content Conversion（変換仕様）

### Gutenberg → Portable Text

| Gutenberg ブロック | Portable Text | 備考 |
|---|---|---|
| `core/paragraph` | `block` style="normal" | インラインマーク保持 |
| `core/heading` | `block` style="h1〜h6" | レベルはブロック属性から |
| `core/image` | `image` block | メディア参照を更新 |
| `core/list` | `block` + `listItem` type | 順序・非順序リスト両対応 |
| `core/quote` | `block` style="blockquote" | 引用元を含む |
| `core/code` | `code` block | 言語属性を保持 |
| `core/embed` | `embed` block | URL とプロバイダを保存 |
| `core/gallery` | `gallery` block | 画像参照の配列 |
| `core/columns` | `columns` block | ネスト構造を保持 |
| 未知のブロック | `htmlBlock` | 生 HTML をそのまま保持（要目視確認） |

未知のブロックは `htmlBlock` として元の HTML とブロックメタデータごと保存される。**目視確認すべきもの**は次の 3 種類。

- 埋め込み（`core/embed`）─ プロバイダによっては Portable Text 側にレンダリング用カスタムコンポーネントが必要
- ショートコード ─ Classic Editor 由来のショートコードは変換対象外。カスタムブロックとして手動で Portable Text コンポーネント化する
- カスタムブロック（サードパーティプラグイン提供のブロック）─ 大半は `htmlBlock` に落ちるため、表示崩れが無いか個別確認する

Classic Editor の HTML はインラインスタイル（`<strong>` `<em>` `<a>`）がマークとして変換され、Portable Text ブロックになる。

### ステータスマッピング

| WordPress ステータス | EmDash ステータス |
|---|---|
| `publish` | `published` |
| `draft` | `draft` |
| `pending` | `pending` |
| `private` | `private` |
| `future` | `scheduled` |
| `trash` | `archived` |

## 移行対象データ

- 投稿・固定ページ・カスタム投稿タイプ（新規コレクションとして自動作成、または既存コレクションへフィールド追加）
- メディア（インポートウィザードで別工程として実行。WordPress URL からダウンロード、コンテンツハッシュで重複排除、コンテンツ内 URL を自動書き換え）
- カテゴリ・タグ（階層を保持してタクソノミーとしてインポート）
- 著者（`authorId` によるオーナーシップ設定 + byline 作成。EmDash ユーザーへのマッピングがあればそのユーザーに紐づけ、無ければゲスト byline を作成。複数著者のインポート済みエントリは `primaryBylineId` を先頭クレジットとして設定）
- カスタムフィールド・ACF（型推論つきで解析される。数値文字列→`number`、`"1"/"0"/"true"/"false"`→`boolean`、ISO 日付→`date`、シリアライズされた PHP/JSON→`json`、`_thumbnail_id` のような WordPress ID→`reference`。内部フィールド `_edit_` `_wp_` 始まりは既定で非表示、SEO プラグインのフィールドは `seo` オブジェクトにマッピング）
- 再利用ブロック（`wp_block`）は [Sections](https://docs.emdashcms.com) としてインポートされる
- コメントは今回のリサーチで移行対象としての明記を確認できなかった（記載無し）

> [!note] ACF リピーター・フレキシブルコンテンツ
> JSON としてインポートされる。EmDash 側で対応する Portable Text または配列フィールドを作成してデータを構造化する必要がある。

## URL リダイレクト

インポート後、EmDash はリダイレクトマップを生成する。

```json
{
  "redirects": [
    { "from": "/?p=123", "to": "/posts/hello-world" },
    { "from": "/2024/01/hello-world/", "to": "/posts/hello-world" },
    { "from": "/category/news/", "to": "/categories/news" }
  ],
  "feeds": [
    { "from": "/feed/", "to": "/rss.xml" },
    { "from": "/feed/atom/", "to": "/atom.xml" }
  ]
}
```

このリダイレクトマップを Cloudflare のリダイレクトルール、ホスティング先のリダイレクト設定、または `astro.config.mjs` の `redirects` オプションに適用する。

## 概念対応表（コード移植時の参照用）

| WordPress | EmDash | 備考 |
|---|---|---|
| `register_post_type()` | admin UI でのコレクション作成 | ダッシュボードまたは API 経由 |
| `register_taxonomy()` | タクソノミーまたは配列フィールド | 複雑さに応じて選択 |
| `register_meta()` | コレクションスキーマのフィールド | 型つき、キーバリューではない |
| `WP_Query` | `getEmDashCollection(filters)` | ランタイムクエリ |
| `get_post()` | `getEmDashEntry(collection, id)` | エントリまたは null を返す |
| `wp_insert_post()` | `POST /_emdash/api/content/{type}` | REST API |
| `the_content` | `<PortableText value={...} />` | Portable Text レンダリング（`emdash/ui`） |
| `add_shortcode()` / `register_block_type()` | Portable Text カスタムブロック | カスタムコンポーネントで描画 |
| `wp_options` | `ctx.kv` | キーバリューストア（プラグイン内） |
| `wp_postmeta` | コレクションフィールド | 構造化、キーバリューではない |
| `$wpdb` | `ctx.storage` | 直接ストレージアクセス（プラグイン内） |

## 移行後チェックリスト

- URL 構造 ─ 新旧の URL パターンを比較し、生成されたリダイレクトマップを実サイトのルーティング設定に反映したか
- 画像パス ─ メディアインポート後、コンテンツ内の画像 URL が新ストレージ（R2 等）を指すよう書き換えられているか
- 型生成 ─ スキーマ変更（新規コレクション作成・フィールド追加）後に `pnpm exec emdash types` を再実行したか
- 未知のブロック ─ `htmlBlock` として保存された箇所を目視確認し、埋め込み・ショートコード・カスタムブロックの表示崩れが無いか
- フィールド型の衝突 ─ インポートウィザードが警告した型不一致を解消したか（EmDash 側フィールドのリネーム、マッピング変更、コレクション再作成のいずれかで対応）
- 大容量エクスポートの扱い ─ 100MB を超える WXR は WordPress 側で投稿タイプ別に分割エクスポートし、順次インポートする

> [!warning] 公式ドキュメントの `--resume` 記載について
> `from-wordpress.mdx` は大容量エクスポート対応として「CLI を `--resume` 付きで使う」と言及しているが、現行 CLI の実装（`packages/core/src/cli/index.ts`）には WordPress インポート関連のコマンドが配線されていない（`emdash import:wordpress` は存在しない）。この記載は docs 側が実装に先行しているか、admin dashboard 経由のフローを指した比喩表現の可能性がある。大容量移行を計画する際は、CLI の `--resume` が使える前提を置かず、admin dashboard 経由で投稿タイプ別に分割インポートする方針を基本とする。

## トラブルシューティング

| 症状 | 対応 |
|---|---|
| "XML parsing error" | エクスポートファイルが破損・不完全な可能性。WordPress から再エクスポートする |
| メディアダウンロード失敗 | 認証が必要な画像や移動済み画像が原因。インポート自体は継続し、失敗した URL はログに記録されるので手動対応する |
| フィールド型の衝突 | 既存コレクションに互換性のない型のフィールドがある場合に発生。EmDash 側フィールドのリネーム／WordPress 側フィールドのマッピング変更／コレクションの削除・再作成のいずれかで解消する |
| インポート結果に警告・失敗が混在 | インポート完了後のサマリーで確認できる。失敗した項目はドラフトとして保存され、元コンテンツは `_importError` に記録されるのでレビューする |

## プラグインの移植（参考）

WordPress プラグインを EmDash プラグインとして移植する詳細（フック対応表・ストレージ対応・設定スキーマ・移植プロセス）は公式ドキュメント `migration/porting-plugins.mdx` を参照する。要点のみ:

- WordPress の `add_action()` / `add_filter()`（文字列フック名）に対し、EmDash は型つきフックをプラグイン定義内に宣言する（`content:beforeSave` 等）
- `wp_options` → `ctx.kv`、カスタムテーブル（`$wpdb`）→ ストレージコレクション（`ctx.storage`）
- 良い移植候補: カスタムフィールド・SEO プラグイン・コンテンツ加工・管理画面拡張・アナリティクス・フォーム
- 不向きな候補: マルチサイト機能、WooCommerce/Gutenberg 密結合の統合、WordPress コア内部にパッチを当てるプラグイン

プラグインの実装形式（sandboxed / native の使い分け、capabilities 一覧）は本スキルの別リファレンスまたは公式 `plugins/` docs を参照する（本ファイルの対象範囲外）。

## 参照ドキュメント

- `docs/src/content/docs/migration/from-wordpress.mdx` ─ WXR インポートの手順・変換仕様
- `docs/src/content/docs/migration/content-import.mdx` ─ 3 ソースの詳細・API エンドポイント仕様
- `docs/src/content/docs/migration/porting-plugins.mdx` ─ プラグイン移植
- https://github.com/emdash-cms/wp-emdash（`plugins/emdash-exporter`）─ WP 側エクスポータープラグイン
