# 対話でのパラメータ収集（AskUserQuestion の質問表・モデル別フォローアップ・ワークフロー別パターン）

`SKILL.md`（gen-nanobanana-images）から分離。該当する場面でこのファイルを Read する。実行するスクリプトは `scripts/generate_image.py` のまま。

### Standard Parameter Collection (Text-to-Image)

After understanding the image description, collect missing parameters with **one AskUserQuestion call** containing up to 3 questions:

**Question 1: Model (header: "Model")**

| Option | Label | Description |
|--------|-------|-------------|
| 1 | Flash2 (Recommended) | 高速＋高機能（マルチターン・4K・検索連携対応）。最もバランスが良い |
| 2 | Pro | 最高品質・テキスト描画精度最高。本番の重要な制作物向け |
| 3 | Lite | 最速・最安（$0.0336/枚）。1K 専用・検索連携なし。ドラフトや大量生成向け |

**Question 2: Aspect Ratio (header: "Ratio")**

| Option | Label | Description |
|--------|-------|-------------|
| 1 | 1:1 Square | SNS 投稿、アイコン、プロフィール画像 |
| 2 | 16:9 Landscape | YouTube サムネイル、プレゼン、バナー |
| 3 | 9:16 Portrait | スマホ壁紙、Instagram/TikTok ストーリーズ |

User can select "Other" to type custom ratios like 3:2, 4:3, 2:3, 4:5, 5:4, 21:9, 1:4, 4:1, 1:8, 8:1 (ultra-wide/tall ratios are flash2 only).

**Question 3: Style (header: "Style")**

| Option | Label | Description |
|--------|-------|-------------|
| 1 | Photorealistic | 写真のようなリアルな描写、スタジオ撮影風 |
| 2 | Illustration | デジタルアート、アニメ、手描き風イラスト |
| 3 | 3D Render | CGI、プロダクトビジュアライゼーション |

User can select "Other" to type custom styles like watercolor, oil painting, pixel art, etc.

**Optional: Number of Variations** — If the user wants multiple variations (e.g., "3パターン出して"), set `-N` accordingly (max 10). Default is 1 if not mentioned.

### Model Follow-Up (Conditional)

Branch the follow-up on the selected model so you never offer a resolution or grounding option the model rejects at runtime.

**If the user selects Lite**: skip the resolution question (Lite is 1K only) and skip Google/Image Search (unsupported); only ask the text-rendering option if relevant.

**If the user selects Flash2**: ask a **second AskUserQuestion** with up to 2 questions:

*Question 1: Resolution (header: "Resolution")*

| Option | Label | Description |
|--------|-------|-------------|
| 1 | 1K (Recommended) | 標準解像度。速度とコストのバランスが良い |
| 2 | 2K | 高解像度。印刷や大画面表示向け |
| 3 | 4K | 最高解像度。生成に最大6分かかる場合あり |
| 4 | 512px | アイコン・サムネイル用の小サイズ |

*Question 2: Options (header: "Options", multiSelect: true)*

| Option | Label | Description |
|--------|-------|-------------|
| 1 | テキスト描画あり | 画像内にテキストを正確に描画する |
| 2 | Google Search 連携 | 事実に基づく正確な図解・インフォグラフィック |
| 3 | Image Search 連携 | 画像検索ベースの正確な写実表現（flash2 のみ） |

**If the user selects Pro**: ask a **second AskUserQuestion** with up to 2 questions. Pro has no 512px tier and no Image Search — do not offer them:

*Question 1: Resolution (header: "Resolution")*

| Option | Label | Description |
|--------|-------|-------------|
| 1 | 1K (Recommended) | 標準解像度。速度とコストのバランスが良い |
| 2 | 2K | 高解像度。印刷や大画面表示向け |
| 3 | 4K | 最高解像度。生成に最大6分かかる場合あり |

*Question 2: Options (header: "Options", multiSelect: true)*

| Option | Label | Description |
|--------|-------|-------------|
| 1 | テキスト描画あり | 画像内にテキストを正確に描画する |
| 2 | Google Search 連携 | 事実に基づく正確な図解・インフォグラフィック |

User may select none, one, or multiple.

### Workflow-Specific Collection Patterns

**Style Reference**: If the user provides reference images for style/composition guidance, collect the reference image paths and add them with `-r`.

**Text-to-Image**: Description → AskUserQuestion (Model, Ratio, Style) → [Flash2/Pro: follow-up] → Generate

**Image Editing**: Confirm input image path → Describe changes → AskUserQuestion (Model only; Ratio and Style inherit from original image) → Generate

**Multi-Turn Editing**: Ask new or continue → If new: same as Text-to-Image flow → If continue: ask only for next prompt, then execute with existing session
