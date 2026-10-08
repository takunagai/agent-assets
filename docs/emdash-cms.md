# emdash-cms

**EmDash**（Cloudflare 発の TypeScript / Astro ベース CMS。WordPress の精神的後継・MIT ライセンス）のセットアップ・構成・運用スキルです。管理画面（Portable Text エディタ・スキーマビルダー・メディア管理）と、Astro プロジェクトへのコンテンツ配信を 1 パッケージで担う CMS を対象に、新規サイト作成から既存 Astro への統合、コンテンツモデリング、プラグイン開発、メール・フォーム、WordPress 移行までを扱います。

---

## 適用範囲と鮮度に関する注意

本スキルは **emdash 0.29.0（2026-07-10 リリース）/ 2026-07-13 検証**を基準としています。EmDash は **v0.x の早期ベータ**で、API・CLI・設定が数ヶ月単位で大きく変わります。作業前に必ず次を実行し、基準バージョンとのズレを確認してください。

```bash
pnpm view emdash version          # 現行の最新版を確認
pnpm view create-emdash version   # スキャフォールダも同時に確認
```

GitHub の releases（https://github.com/emdash-cms/emdash/releases）でメジャーな変更も確認します。基準（0.29.x）とメジャー／マイナーがずれている場合、スキルのコード例をそのまま使わず、公式ドキュメント（https://docs.emdashcms.com）で該当 API を裏取りしてから進める運用です。

> デプロイの実行自体は Astro + Cloudflare Workers 構成なので、既存スキル `deploy-astro-cloudflare` に委譲します。本スキルは構成まで、デプロイ操作はそちらが担当します。

---

## 発動トリガー

自然言語で依頼すると発動します。ざっくりした依頼でも動きますが、**構成・制約・目的を具体的に添えるほど手戻りが減ります**。以下は実際に使える指示のサンプルです。

### セットアップ・構成

- 「EmDash で新規サイトを作って。Cloudflare 構成、D1 と R2 を使う、テンプレートは blog で」
- 「既存の Astro 7 プロジェクトに EmDash を統合して。DB は D1、メディアは R2、Tailwind 4 と Biome も入れて」
- 「EmDash の wrangler.jsonc を作って。D1・R2・KV キャッシュ・cron トリガーを全部入れて、compatibility_date は今日の日付で」
- 「本番は Hyperdrive 経由で既存の PostgreSQL を使いたい。設定を変更して」
- 「Cloudflare 無料プランで運用したい。sandboxed プラグインを使わない構成にして」

### コンテンツモデリング・クエリ

- 「『実績』コレクションを作りたい。フィールドはタイトル・スラッグ・サムネイル画像・本文（Portable Text）・公開日・クライアント名・タグ。管理画面での作り方を手順で教えて」
- 「投稿一覧ページを作って。公開済みだけ、公開日の降順、1 ページ 10 件でページネーションつき」
- 「タグ『typescript』で絞り込んだ記事一覧を取得するコードを書いて」
- 「スキーマを変更したので型を再生成して、型エラーが出ている箇所を直して」
- 「EmDash のフィールド型は何がある？ ACF のリピーターに相当するものはどれ？」

### Portable Text・レンダリング

- 「記事詳細ページで本文をレンダリングして。見出しに id を振って目次を作れるようにしたい」
- 「Portable Text にカスタムの『注意書き』ブロックを追加して、Astro コンポーネントで描画して」
- 「YouTube 埋め込みブロックを Portable Text に追加したい。プラグインで提供する形にして」

### 認証

- 「管理者だけが見られるダッシュボードページを作って。ロールが Editor 未満ならトップにリダイレクト」
- 「GitHub と Google の OAuth ログインを有効にして」
- 「passkey ログインを試したい。ローカルでの動作確認手順を教えて」

### プラグイン開発

- 「記事が公開されたら Slack に通知する EmDash プラグインを作って。sandboxed と native のどちらが適切か判断してから実装して」
- 「閲覧数カウンターのプラグインを作って。KV に保存、管理画面に集計ページを出す」
- 「このプラグインの hook が発火しない。capability の宣言漏れがないか見て」
- 「sandboxed プラグインをマーケットプレイスに公開したい。manifest の書き方と bundle・publish の手順を教えて」

### メール・フォーム

- 「問い合わせフォームを追加して。Turnstile でスパム対策、送信されたら info@ 宛に通知メール、送信者には自動返信」
- 「Cloudflare Email Service を有効化して、EmDash からメールが送れるところまで設定して」
- 「magic link ログインのメールが届かない。メールトランスポートの設定を確認して」
- 「フォームの送信データを CSV でエクスポートしたい」

### WordPress 移行

- 「この WordPress サイトを EmDash に移行できるか判定して。プラグイン一覧はこれ（貼り付け）」
- 「WXR ファイルをエクスポートしたので、EmDash にインポートする手順を教えて。ACF のフィールドも移行したい」
- 「移行後、旧 URL からのリダイレクトを Cloudflare 側に設定して」
- 「Gutenberg のカスタムブロックが htmlBlock に落ちている。Portable Text コンポーネント化して」

### 運用・トラブルシュート

- 「本番でメール送信が『Email is not configured』になる。原因を調べて直して」
- 「スキーマとコードの整合性を確認して」（構成に応じてスキルが方法を選ぶ ─ `emdash doctor` は CLI 併用構成〔系統 B〕専用。テンプレート既定の構成では型再生成 + ビルド確認で代替）
- 「Claude Desktop から自サイトの EmDash を操作したい。MCP の接続設定を教えて」
- 「EmDash の最新版が出ていないか確認して、このプロジェクトのコードに影響する変更があれば教えて」

> [!tip] 指示に添えると精度が上がる情報
> **プラットフォーム**（Cloudflare / Node）、**プラン**（無料 / Workers Paid ─ sandboxed プラグインと Email Sending の可否が変わる）、**既存プロジェクトか新規か**、**実現したいことの目的**（「フォームがほしい」ではなく「問い合わせを受けてメールで通知したい」）。この 4 つがあると、選択肢の提示ではなく実装に直行できます。

---

## 推奨モデル・エフォート（起動時の目安）

このスキルを別セッション／サブエージェントで無人起動する場合、タスク種別に応じてモデルとエフォートを選ぶと手戻りが少なくなります。判断軸は「手順が確定した機械的作業なら Sonnet、調査・判断・デバッグが残るなら Opus」です。

代表例として「**EmDash で新規サイトを作って。Cloudflare 構成、D1 と R2 を使う、テンプレートは blog で**」の新規スキャフォールドは、プラットフォーム・テンプレート・バインディングまで指定済みで手順がほぼ確定するため、**Sonnet 5 / medium エフォート**が最適です。

| タスク | 推奨モデル | エフォート | 理由 |
|---|---|---|---|
| 新規サイト作成（今回の blog スキャフォールド等、構成が指定済み） | Sonnet 5 ⭐ | medium | scaffold → バインディング作成 → 型生成 → ビルド確認まで手順が確定。判断は導入版の差分確認程度 |
| 既存 Astro への統合 | Sonnet 5 | medium | 既存ルート衝突・アダプタ import 元の確認はあるが定型 |
| プラグイン開発（sandboxed / native 判断込み） | Opus 4.8 | high | capability 宣言・hook 設計・形式選定に設計判断が残る |
| WordPress 移行の可否判定・実行 | Opus 4.8 | high | プラグイン棚卸し・ページビルダー検出・変換の当たり外れ判定に調査と判断が要る |
| メール／フォーム不達などの運用デバッグ | Opus 4.8 | medium〜high | transport 未設定の silent skip など、原因の切り分けが要る |

エスカレーション規則（新規スキャフォールドでも Sonnet から Opus に上げる条件）:

- 起動直後の鮮度チェック（`pnpm view emdash version`）で、基準 0.29 系とメジャー／マイナーがずれている場合。API・CLI の破綻を公式ドキュメントで裏取りしながら適応する「調査・判断」が発生します
- テンプレートが古い版を pin していて最新へ上げた結果、0.x 系のマイナー破壊的変更に当たった場合

> [!important] 昇格は自動ではなく Stop And Ask
> 走行中のセッションは自身のモデルを変更できません。上の条件に該当したら、スキルは**その場で作業を止め、「Opus（現行の最上位）/ high エフォートで再起動してほしい」旨をユーザーに申告して停止**します（黙って続行しない）。この停止挙動は SKILL.md の鮮度検証ブロックにも実装済みです。ズレが無ければそのまま続行します。

思考キーワード（開始プロンプト末尾に付ける）は、スキャフォールドが素直に通る想定なら不要です。上の条件で Opus に再起動する場合は `ultrathink` を付けます。

---

## できること一覧

| カテゴリ | 内容 |
|---|---|
| セットアップ | `pnpm create emdash@latest` での新規サイト作成、既存 Astro プロジェクトへの `emdash()` integration 統合。Cloudflare 構成の既定はテンプレート準拠の素の `d1()` / `r2()`（ローカルは `astro dev` の miniflare エミュレーションで動く ─ 実機確認済み） |
| コンテンツモデリング | 管理 UI でのスキーマ定義、`pnpm exec emdash types` での型生成、16 種のフィールド型 |
| クエリと Portable Text | `getEmDashCollection` / `getEmDashEntry` でのデータ取得、`<PortableText />`（`emdash/ui`）でのレンダリング |
| 認証 | `Astro.locals.user` によるユーザー判定、5 段階ロール、passkey-first（WebAuthn）・OAuth・magic link |
| プラグイン開発（2 形式） | sandboxed（Dynamic Workers 隔離・マーケットプレイス配布向け）／ native（trusted・管理 UI 拡張向け）の使い分けと実装 |
| メール | 公式ファーストパーティ `cloudflareEmail()` を主軸に、Cloudflare Email Service との連携・自作 transport |
| フォーム | 公式 `@emdash-cms/plugin-forms`（スパム対策・CSV エクスポート・メール通知） |
| WordPress 移行 | 管理ダッシュボードのインポートウィザード、`emdash-exporter` プラグイン、Gutenberg → Portable Text 変換 |
| MCP サーバー | サイト管理用（45 ツール・8 ドメイン）とドキュメント検索用（`search_docs` のみ）の 2 種 |
| デプロイ連携 | `deploy-astro-cloudflare` への委譲、D1 マイグレーション・`worker_loaders` を含む構成の注意点 |

---

## 技術スタック前提

| パッケージ / ツール | 基準バージョン | 備考 |
|---|---|---|
| emdash / create-emdash | 0.29.0 | npm の `1.0.0` は誤公開 deprecated。無視する |
| astro | 7.x | v7 GA（2026-06-22）。emdash の peer は `astro >=6.0.0-beta.0` |
| vite | 8.x | Astro 7 同梱。Rolldown 統合済み |
| @astrojs/cloudflare | 14.x | Cloudflare デプロイ時のアダプタ |
| @emdash-cms/cloudflare | 0.29 系 | D1 / R2 / KV / Hyperdrive / Cloudflare Email 用の別パッケージ |
| tailwindcss / @tailwindcss/vite | 4.x | CSS-first。`tailwind.config.js` 不要 |
| @biomejs/biome | 2.x | `.astro` は実験的サポート（2.3.0+） |
| pnpm | 11.x | パッケージマネージャーの基準 |
| wrangler | 4.x | Cloudflare デプロイ用 |

Cloudflare 構成では D1（DB）・R2（メディア）が既定。KV はオブジェクトキャッシュ用（任意）、Worker Loaders は sandboxed プラグイン実行時のみ必要です。

---

## ファイル構成

```
skills/emdash-cms/
├── SKILL.md                        # スキル定義（動作の正本。本ファイルはこの写像）
└── references/                     # SKILL.md から参照する詳細資料
    ├── cli.md                      # emdash CLI 全コマンド・環境変数・Exit Code
    ├── plugin-development.md       # sandboxed / native 両形式の実装・capabilities 12 種・hooks 25 種
    ├── email-and-forms.md          # メールパイプライン・cloudflareEmail() 導入・Forms プラグイン
    ├── wordpress-migration.md      # WXR 変換仕様・概念対応表・移行後チェックリスト
    └── cloudflare-deploy.md        # wrangler.jsonc 完全例・D1/Hyperdrive/KV・Dynamic Workers
```

各 references は SKILL.md 本文からトピック単位で参照されます。人間が個別に読む場合も、まず SKILL.md で全体像を掴んでから該当ファイルに入ると迷いません。

---

## MCP 連携（接続済みなら優先。CLI が実行骨格）

公式プラグイン `cloudflare` の MCP サーバーが接続済み（OAuth 認証済み）なら、次を CLI コマンドの代わりに使います。未接続・未認証の場合は従来どおり CLI で続行します。

- **Cloudflare 側仕様の裏取り** ─ `cloudflare` MCP の `docs` ツール（OAuth 認証が必要。未接続時は developers.cloudflare.com を直接参照）。Email Service / Dynamic Workers / D1 の仕様確認の第一手段。EmDash 本体の仕様は docs 検索 MCP（`https://docs.emdashcms.com/mcp`）か GitHub が正本
- **D1 / R2 / KV の作成・確認** ─ 作成は `wrangler d1 create` 等の CLI。一覧・取得は `cloudflare` MCP の `execute`（GET）でもよい。Read only スコープで認証した場合、MCP からは作成できない
- **本番ログ確認** ─ 第一手段は `wrangler tail`。`cloudflare` MCP の `execute` から Workers Observability API を呼ぶ方法は、Read only スコープで使えるか未検証
- **デプロイ状態確認** ─ 委譲先 `deploy-astro-cloudflare` 側のガイダンスに従う

---

## WordPress 移行の適用範囲（受注前に必ず読む）

**「WordPress から EmDash に移行して」で運べるのはコンテンツ（データ）だけです。サイトそのものは移行できません。** カスタマイズが重いサイトほど、移行後に残る手作業が増えます。案件の見積もりを出す前に、ここで適用範囲を判定してください。

### 移行されるもの / 作り直しになるもの

| | 内容 |
|---|---|
| **自動で移行される** | 投稿・固定ページ・カスタム投稿タイプ、メディア（コンテンツ内 URL の書き換え込み）、カテゴリ / タグ（階層保持）、著者、**ACF などのカスタムフィールド**（型推論つき）、Yoast / Rank Math の SEO メタ、再利用ブロック |
| **作り直し（互換レイヤーなし）** | **テーマ** ─ PHP テンプレートは Astro プロジェクトとして全面書き直し（EmDash のテーマ = Astro サイトそのもの）／**プラグイン** ─ PHP プラグインは 1 行も動かない。EmDash プラグイン（TypeScript）として書き直し／**ショートコード** ─ 変換対象外。Portable Text のカスタムブロックとして手で作る |

### プラグインの種類ごとの難易度

「プラグインが多い」だけでは判定できません。**何をするプラグインか**で難易度が割れます。

| プラグインの種類 | 実態 |
|---|---|
| ACF・SEO 系（コンテンツにデータを足すもの） | **データは自動で運ばれる**。最も移行の旨味が大きいケース |
| フォーム・アナリティクス・管理画面拡張 | 書き直しだが移植しやすい。フォームは公式 `@emdash-cms/plugin-forms` で置換できる |
| カスタム Gutenberg ブロック提供系 | 未知ブロックは `htmlBlock`（生 HTML）に落ちる。表示は残るが、EmDash 側でコンポーネント化しない限り「編集できない塊」になる |
| WooCommerce・マルチサイト・コアにパッチを当てる系 | 公式が「移植に不向き」と明言。事実上ここは移行対象外 |

> [!warning] ページビルダー製サイト（Elementor / Divi / WPBakery）は移行ではなく再構築
> これらのコンテンツは Gutenberg ブロックではなく独自のショートコード・メタに格納されているため、Portable Text へまともに変換されません。「カスタマイズが重い WordPress」の受託案件では最頻出のパターンです。**インポーターに通す前に検出し、移行ではなく再構築として見積もる**必要があります。

### 受注前チェックリスト

1. **エディタの確認** ─ Gutenberg か、Classic Editor か、ページビルダーか。ページビルダーなら移行ではなく再構築として扱う
2. **プラグインの棚卸し** ─ 有効なプラグインを全件リストアップし、上表の 4 分類に振り分ける。「WooCommerce・マルチサイト」系が含まれるなら対象外と判断する
3. **コンテンツ資産と機能の比率** ─ 記事数が多く ACF でフィールドを積んでいる程度なら移行の旨味が大きい。EC・会員制・LP 群が主体なら再構築
4. **テーマの作り込み量を工数化** ─ テーマは必ず Astro で書き直しになるため、ここは移行工数ではなく**新規制作工数**として見積もる
5. **ショートコード・カスタムブロックの洗い出し** ─ 1 種類ごとに Portable Text コンポーネントの実装工数が発生する

**うまくいく典型**: コンテンツ資産は厚いが、機能はブログ / コーポレートサイト相当。
**うまくいかない典型**: EC・会員制・ページビルダー製の LP 群 ─ これは移行ではなく再構築案件です。

この判定フローは実行側にも実装済みです（`skills/emdash-cms/references/wordpress-migration.md` の「移行可否の事前判定」）。エージェントがインポート前に同じ観点で自己判定します。

詳細な変換仕様（Gutenberg ブロック対応表・ステータスマッピング・リダイレクトマップ・WordPress → EmDash 概念対応表）は `skills/emdash-cms/references/wordpress-migration.md` を参照してください。

---

## 制約・注意

- **ローカル開発は 2 系統あり、DB を共有しない**（2026-07-14 実機確認）。`pnpm dev`（astro dev + miniflare ローカル D1）と、CLI 系（`emdash init/seed/doctor/dev` ─ 素の SQLite `data.db`）。Cloudflare テンプレートは CLI 系に必要な `better-sqlite3` のビルドを既定で止めているため、CLI 系を使うには `pnpm-workspace.yaml` の `allowBuilds` 変更 + rebuild が要る。スキルはこの分離を明記済み
- **`pnpm create emdash` のテンプレートは最新版より古い版を pin していることがある**（実機確認: emdash `^0.28.1` が入った）。スキャフォールド後に `pnpm list emdash` で確認し、必要なら最新へ上げる手順をスキルに記載済み
- **Dynamic Workers（sandboxed プラグイン実行）は Open Beta・Workers Paid プラン必須**（Open Beta 開始は 2026-03-24 ─ Cloudflare changelog）。無料プランでは sandboxed プラグインを実行できず、native（trusted）プラグインのみに構成を絞る必要があります。料金は月 1,000 個までの unique Dynamic Worker 作成が無料枠、超過は 1 個・1 日あたり $0.002。
- **Cloudflare Email Sending（送信側）は public beta**（2026-04-16 開始、2026-07-13 時点で GA 未達）。Workers Paid プラン必須ですが、認証済み宛先への送信は全プランで無料。1 通あたり上限 5 MiB。
- **サードパーティ `emdash-plugin-cloudflare-email` は非推奨扱い**にしています。peer dependency が古く（`emdash >= 0.5.0`）、3 ヶ月以上更新が無く現行 0.29 系の capability 体系との整合が未確認のため。公式ファーストパーティ `cloudflareEmail()` の登場で存在意義がほぼ無くなっており、新規導入では検討する理由がありません。既存プロジェクトで使用中の場合のみ、移行前提で参照します。
- **EmDash docs と実装の食い違いが残っている領域**があります。具体的には、古いドキュメントに残る `sandboxRunner` の文字列直書き記法（現行は `sandbox()` 関数呼び出しが正）、sandboxed プラグインが Hyperdrive（Postgres）構成では D1 バインディング依存のため動作しないという既知の制約、`requireAuth` / `getUser` のようなガード関数が実際には存在せずページ側の自前チェックが必要な点など。ドキュメントの記述をそのまま信じず、コード例は実機で確認する前提で扱ってください。
- WordPress 移行に専用 CLI コマンドは無く、管理ダッシュボードのインポートウィザード経由のみです（`emdash import:wordpress` 等は存在しません）。

---

## 関連スキル

| スキル | 関係 |
|---|---|
| `deploy-astro-cloudflare` | 本スキルはコンテンツ・プラグイン等の構成までを担当し、Cloudflare Workers への実デプロイ操作はこちらに委譲する |
| `astro-code-review` | EmDash 統合後の Astro コード（integration 設定・コンポーネント）のレビューに使う |

---

## 外部リファレンス

- [EmDash リポジトリ / releases](https://github.com/emdash-cms/emdash)
- [EmDash ドキュメント](https://docs.emdashcms.com)（ドキュメント検索 MCP: `https://docs.emdashcms.com/mcp`）
- [WordPress エクスポーター（emdash-exporter）](https://github.com/emdash-cms/wp-emdash)
- [Cloudflare Email Service](https://developers.cloudflare.com/email-service/)
