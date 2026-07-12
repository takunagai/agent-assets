---
name: gen-nanobanana-images
description: "Generate and edit images using Google Gemini image models (Nano Banana series, GA). Supports text-to-image, image editing, and multi-turn refinement with Flash2 (recommended/balanced), Pro (production/4K/highest text accuracy), and Lite (fastest/cheapest/1K draft) models. Use when users request: (1) AI image generation from text, (2) editing or modifying existing images, (3) iterative multi-turn image refinement, (4) text rendering in images, or (5) infographics and visualizations with Gemini models."
---

# Nano Banana Image Generation

## Overview

Generate and edit images using Google's Nano Banana series (GA): Flash2/Nano Banana 2 (recommended, balanced speed+features) and Pro/Nano Banana Pro (production quality, highest text accuracy) — both released 2026-05-28 — plus Lite/Nano Banana 2 Lite (fastest, cheapest, 1K draft, released 2026-06-30). Supports text-to-image generation, image editing with input images, and multi-turn iterative refinement with session persistence.

### Prerequisites

- **API Key**: `GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variable (get at https://aistudio.google.com/apikey)
- **Dependencies**: `pip install -U "google-genai>=2.11.0" Pillow` (see `requirements.txt`). SDK **>= 2.11.0 required** — the skill uses the Interactions API (`client.interactions.create`), and 2.11.0 is the first release whose interactions transform reliably accepts multiple input blocks (image + text).

## Workflow Decision Tree

Determine which workflow to use:

1. **Want to create a new image from text?** → Go to [Text-to-Image Generation](#text-to-image-generation)
2. **Want to edit or modify an existing image?** → Go to [Image Editing](#image-editing)
3. **Want to apply a style from reference images?** → Go to [Style Reference](#style-reference) (Pro has official style-reference slots; all models accept references)
4. **Want to iteratively refine an image over multiple turns?** → Go to [Multi-Turn Editing](#multi-turn-editing) (flash2/pro/lite)
5. **Need factual/grounded image content?** → Go to [Google Search Grounding](#google-search-grounding) (flash2/pro)
6. **Need image-based search results?** → Go to [Image Search Grounding](#image-search-grounding) (flash2 only)

## Gathering Parameters

Before running the script, collect all required parameters from the user. Follow these principles:

### Non-Interactive Mode (Delegation / Complete Params) — Check This First

**Do NOT use AskUserQuestion when parameters are already sufficient.** Run the script immediately (with sensible defaults for anything unspecified) in these cases:

- **Called as an image-generation engine by another skill** (e.g. `gen-lifestyle-images`, `print-card-comp`). These skills pass a full prompt and flags; never interrupt them with AskUserQuestion.
- **The user's instruction already contains the needed parameters** (subject + any model/ratio/size they cared to specify). Fill unspecified params from defaults (model `flash2`, ratio `1:1`, no `-s` unless requested).

AskUserQuestion is **only** for interactive, brand-new requests where the subject or key parameters are genuinely missing.

### Information Collection Principles

1. **Do not re-ask what's already known** — If the user says "Pro で 16:9 の夕焼け", model (Pro), aspect ratio (16:9), and subject (sunset) are already determined. Only collect missing parameters.
2. **Ask for image description first** — If the user hasn't described what to generate, ask in plain text (AskUserQuestion choices can't express open-ended image descriptions well).
3. **Batch remaining parameters in a single AskUserQuestion** — Collect all missing options in one interaction to minimize back-and-forth.

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

### Prompt Assembly from Collected Parameters

After collecting all parameters, Claude should automatically build a 6-element prompt:

1. **User's description** → Expand into Subject + Action + Environment
2. **Selected Style** → Append as the Style element
3. **Composition and Lighting** → Claude supplements if not specified by the user
4. **Text rendering** → If "テキスト描画あり" is selected, ensure text portions are wrapped in double quotes
5. **Text language default** → 画像内に描画するテキストは、**ユーザーが言語を明示していない場合は日本語をデフォルト**とする。ただし以下の場合は英語または指定言語を使用:
   - ユーザーが英語（または他言語）で明示的に指定した場合（例: `"HELLO WORLD" と書いて`）
   - ブランド名・固有名詞がそのまま使われている場合（例: `"CAFE TOKYO"`）
   - 技術用語・プログラミング関連で英語が自然な場合
   - どちらが適切か判断が難しい場合は、AskUserQuestion でユーザーに確認する

Example: User says "夕焼けの海辺の灯台" + Style: Photorealistic + Ratio: 16:9
→ `"A lighthouse standing on a seaside cliff at sunset. Golden hour light casting long shadows across the rocky shore. Wide 16:9 cinematic framing. Photorealistic photography style."`

Example: User says "セールのバナーを作って" + テキスト描画あり
→ テキスト部分は `"夏のセール開催中"` のように日本語で生成（ユーザーが英語を指定していない限り）

Example: User says "PREMIUM COFFEE のロゴを作って"
→ `"PREMIUM COFFEE"` はブランド名として英語のまま使用

## Model Selection

Choose the right model for your task. All three are GA models (released 2026-05-28 / Lite 2026-06-30):

| Feature | Flash2 (推奨) | Pro (最高品質) | Lite (最速最安) |
|---------|--------------|---------------|----------------|
| Model ID | `gemini-3.1-flash-image` | `gemini-3-pro-image` | `gemini-3.1-flash-lite-image` |
| Speed | Fast (~5-15s) | Slower (~15-60s) | Fastest |
| Resolution | 512px, 1K, 2K, 4K | 1K, 2K, 4K | 1K only |
| Text Rendering | Good | High accuracy | Basic |
| Multi-Turn Editing | Yes | Yes | Yes |
| Google Search | Yes | Yes | No |
| Image Search | Yes (exclusive) | No | No |
| Max Images/Prompt | 14 (10 obj + 4 person) | 14 (6 obj + 5 person + 3 style) | 14 (object only) |
| Aspect Ratios | 10 + 4 ultra (1:4, 4:1, 1:8, 8:1) | 10 standard | 10 standard |
| Thinking Levels | minimal/high | low/high | minimal/high |
| Cost | Low | Higher | Lowest |

**Recommendation**: Use **Flash2** (default) for most tasks — best balance of quality, speed, and features. Use **Pro** when maximum text rendering accuracy is critical. Use **Lite** for the fastest, cheapest drafts and high-volume batches (1K only, no search grounding).

### Cost Guide (per image, Standard tier, 2026-07-12, source: https://ai.google.dev/gemini-api/docs/pricing)

| Model | 512px | 1K | 2K | 4K |
|-------|-------|-----|-----|-----|
| Lite | — | $0.0336 | — | — |
| Flash2 | $0.045 | $0.067 | $0.101 | $0.151 |
| Pro | — | $0.134 | $0.134 | $0.24 |

**Cost guardrail (agent)**: Before running any execution whose estimated cost exceeds **$0.5** (e.g. Pro 4K, `-N` 4+ images, any 4K batch), present the estimate (image count × unit price) to the user and confirm before generating.

## Prompt Construction

Build effective prompts using the **6-element structure**:

1. **Subject** - What to generate
2. **Action** - What it's doing
3. **Environment** - Setting/background
4. **Composition** - Camera angle, framing
5. **Lighting** - Light quality/direction
6. **Style** - Artistic style

**Describe the scene narratively and in the positive (Google official guidance)**: write what you *want* as flowing descriptive sentences, not a keyword list. Prefer "A serene misty forest at dawn with soft golden light" over "forest, mist, dawn, golden, 4k, best quality". If you must exclude something, state it as a positive alternative ("an empty street with no cars" rather than "no cars"). The script no longer auto-appends any negative constraints — add an `Avoid: ...` clause explicitly only when genuinely needed, or opt in via `config.json` (`negative_constraints`).

**Text rendering**: Wrap the exact text in double quotes — `"プレミアム"` — so the model renders it. Keep each text element to **one short string** (a heading + a short label at most; long body text belongs in Figma/Photoshop). Specify a font style when it matters (sans-serif / serif / handwritten). **画像内テキストのデフォルト言語は日本語**。ユーザーが英語や他言語を明示した場合、またはブランド名・固有名詞の場合はそのまま使用。判断が難しい場合はユーザーに確認する。**Always visually verify rendered text after generation** (see [Post-Generation Verification](#post-generation-verification)) — misrendered characters are common, especially in Japanese.

When using AskUserQuestion-collected parameters, incorporate the selected **Style** as the final style element of the prompt. See [Prompt Assembly from Collected Parameters](#prompt-assembly-from-collected-parameters) for the full assembly process.

For industry-specific templates and advanced techniques, see `references/prompt-engineering.md`.

## Post-Generation Verification

**After every generation, open each produced image with the Read tool and verify it.** This is mandatory, not optional. Check:

- **(a) Match** — Does the image match what was requested (subject, composition, ratio)?
- **(b) Text integrity** — Are any in-image text strings free of typos / garbled characters? Japanese text is especially prone to corruption.
- **(c) Breakage** — Any broken hands, faces, letters, or composition artifacts?

If in-image text is garbled, either **regenerate** (wrap the text in `「」`/double quotes, shorten it, specify font) or advise the user to **overlay the text afterward in Figma/Photoshop**. Do not deliver an image with garbled text without flagging it.

## Text-to-Image Generation

Generate a new image from a text prompt.

### Basic Generation (Flash2 — default)

```bash
python3 scripts/generate_image.py \
  -p "A red apple on a white marble surface. Soft studio lighting. Photorealistic." \
  -o ./output
```

### High-Quality Generation (Pro)

```bash
python3 scripts/generate_image.py \
  -p "A futuristic cityscape at sunset with neon lights reflecting on wet streets. Wide shot, 16:9 cinematic framing. Volumetric lighting." \
  -m pro \
  -a 16:9 \
  -s 2K \
  -o ./output
```

### With Text Rendering (Pro recommended)

```bash
python3 scripts/generate_image.py \
  -p 'A coffee shop storefront with a wooden sign reading "BREW & BLOOM" in elegant serif font.' \
  -m pro \
  -o ./output
```

### Multiple Variations (-N)

Generate multiple image variations from the same prompt in one execution:

```bash
python3 scripts/generate_image.py \
  -p "A red apple on a white marble surface. Soft studio lighting. Photorealistic." \
  -N 3 \
  -o ./output
```

Each variation is a separate API call, producing unique results. Files are named with `_v2`, `_v3` suffixes (e.g., `nanobanana_..._1.png`, `nanobanana_..._v2_1.png`, `nanobanana_..._v3_1.png`). With `-n city -N 4`: `city.png`, `city_v2.png`, `city_v3.png`, `city_v4.png`.

**Note**: `-N` is not available with multi-turn mode (`--chat`/`--session`). Max 10 images per execution.

**Note**: The script does **not** append any negative constraints by default. If you need them, write an `Avoid: ...` clause into your prompt, or set `negative_constraints` in `config.json` (opt-in).

## Image Editing

Edit an existing image with a text prompt describing the desired changes.

```bash
python3 scripts/generate_image.py \
  -p "Change the sky to a dramatic sunset with orange and purple clouds" \
  -i original_photo.jpg \
  -o ./output
```

### Multiple Image Editing

Edit or blend multiple images in a single prompt (all models):

```bash
python3 scripts/generate_image.py \
  -p "Create a double exposure blending the portrait with the landscape" \
  -i portrait.jpg landscape.jpg \
  -m pro \
  -o ./output
```

### Tips for Editing Prompts

- Be specific: "Change the sky to sunset orange" rather than "Make it better"
- Reference visible elements: "Add a cat on the windowsill"
- Combine changes: "Add snow on the rooftops and change the sky to overcast gray"

### Input Image Constraints

- Max total file size: 7 MB (all images combined)
- Supported formats: PNG, JPEG, WebP, HEIC, HEIF
- **Total input + reference images: up to 14 for all models**, but the official per-role limits differ:
  - **Lite**: up to 14 object references (no person-consistency or style-reference slots)
  - **Flash2**: up to 10 object references + 4 person-consistency references (no official style-reference slot)
  - **Pro**: up to 6 object references + 5 person-consistency references + 3 style references

## Style Reference

Apply the visual style, color palette, or composition from reference images to new or existing images. **Pro is the first choice for style transfer** — it is the only model with official style-reference slots (up to 3). All models accept up to 14 reference/input images total, so Flash2 and Lite can still take a reference image as an object reference and pick up its look, but without Pro's dedicated style-reference handling.

### Generate with Style Reference

```bash
python3 scripts/generate_image.py \
  -p "A mountain landscape at dawn. Soft pastel colors." \
  -r style_painting.png \
  -o ./output
```

### Edit with Style Reference

Combine input image editing with style reference:

```bash
python3 scripts/generate_image.py \
  -p "Repaint this photograph in the reference artistic style" \
  -i photo.jpg \
  -r style_reference.png \
  -o ./output
```

### Multiple Reference Images

Use multiple references for blending styles:

```bash
python3 scripts/generate_image.py \
  -p "Combine the lighting from the first reference with the color palette from the second" \
  -r lighting_ref.jpg palette_ref.jpg \
  -o ./output
```

### Tips for Reference Prompts

- Explicitly describe which aspects to reference: "color palette", "lighting style", "composition", "brush strokes"
- Combine reference images with detailed text prompts for best results
- All models accept up to 14 input+reference images total; for dedicated style transfer prefer **Pro** (official style-reference slots), while Flash2/Lite treat a reference as an object reference
- See `references/prompt-engineering.md` for detailed style reference techniques

## Multi-Turn Editing

Iteratively refine images through conversational editing. Available with **Flash2** (default), **Pro**, and **Lite** models.

Multi-turn state is handled server-side through the Interactions API: each turn stores its `interaction.id`, and the next turn passes it as `previous_interaction_id` so the model can reference and modify its previous output. Continuation relies on the server default (`store` is true by default), so stored turns persist for the retention window (55 days Paid Tier / 1 day Free Tier). The script records these IDs in a version 2 session file.

### Start a New Chat Session

```bash
python3 scripts/generate_image.py \
  -p "A cozy wooden cabin in a snowy forest. Warm light from windows. Evening atmosphere." \
  -c \
  -o ./output
```

This creates a session file (e.g., `session_20260210_143000.json`) in the output directory.

### Continue the Session

```bash
python3 scripts/generate_image.py \
  -p "Add smoke coming from the chimney and a path of footprints in the snow" \
  --session ./output/session_20260210_143000.json \
  -o ./output
```

You can pass `-i`/`-r` on a continuation turn as well; the images are sent as part of that turn.

### How It Works

1. Each turn saves its prompt, saved image paths, model text, and the returned `interaction.id` to the session JSON (version 2).
2. On continuation the script sends only the new prompt plus `previous_interaction_id` (the last turn's id); `store` is left at the server default (true), so the server retains the prior context and no local history rebuild is needed. (Single-shot generations instead send `store=False`.)
3. The session pins the model chosen on turn 1; continuation reuses it even if `-m` differs. Aspect ratio and image size are likewise locked to the turn-1 settings (`-a`/`-s` on a continuation turn are ignored); `-t`/`-g`/`--image-search` apply per turn.
4. You can continue editing for multiple turns with the same session file.

**Note**: Sessions created by an older build (`generate_content` era, with a `history` key and no `version` field) cannot be continued. Start a fresh session with `-c`. Continuation also works only within the server retention window (55 days Paid Tier / 1 day Free Tier); an expired session must be restarted with `-c`.

## Google Search Grounding

Generate images grounded in real-world data using Google Search. Available with **Flash2** (default) and **Pro** models.

```bash
python3 scripts/generate_image.py \
  -p "Accurate anatomical diagram of the human heart with labeled chambers and valves. Medical illustration style." \
  -g \
  -o ./output
```

Best for: scientific diagrams, factual infographics, current event illustrations.

## Image Search Grounding

Generate images grounded in image search results. Only available with **Flash2** model.

```bash
python3 scripts/generate_image.py \
  -p "Photo of the latest iPhone model on a desk" \
  --image-search \
  -o ./output
```

Combine with Google Search for maximum accuracy:

```bash
python3 scripts/generate_image.py \
  -p "Accurate photo of the latest Tesla Model Y exterior" \
  --image-search -g \
  -o ./output
```

Best for: product photos, real-world object references, current visual trends.

## Script Parameters Reference

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--prompt` | `-p` | **Required** | Text prompt |
| `--list-models` | | False | Query API for available image models |
| `--model` | `-m` | `flash2` | `flash2` (recommended), `pro`, or `lite` |
| `--input-image` | `-i` | None | Input image path(s) for editing (multiple OK) |
| `--reference` | `-r` | None | Style/composition reference image path(s) |
| `--num-images` | `-N` | `1` | 生成する画像の枚数 (max: 10) |
| `--output-dir` | `-o` | `.` | Output directory |
| `--output-name` | `-n` | Auto | Output filename (no extension; existing files are never overwritten — a `_2` suffix is added) |
| `--aspect-ratio` | `-a` | `1:1` | Aspect ratio |
| `--image-size` | `-s` | None | Resolution (flash2: 512px/1K/2K/4K, pro: 1K/2K/4K, lite: 1K only) |
| `--thinking-level` | `-t` | None | Thinking level (flash2/lite: minimal/high, pro: low/high) |
| `--google-search` | `-g` | False | Enable Google Search (flash2/pro) |
| `--image-search` | | False | Enable Image Search grounding (flash2 only; sent as a `google_search` tool `search_types`) |
| `--chat` | `-c` | False | Start new multi-turn session (flash2/pro/lite) |
| `--session` | | None | Continue existing session (version 2 file; older `generate_content`-era sessions cannot be continued) |
| `--timeout` | | 120 | Timeout in seconds for the API request (auto-raised to 420s for 4K) |

## Constraints

- **Aspect ratios**: 1:1, 3:2, 2:3, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9 (all models) + 1:4, 4:1, 1:8, 8:1 (flash2 only)
- **Image sizes**: flash2: 512px/1K/2K/4K, pro: 1K/2K/4K, lite: 1K only
- **Max inline file size**: 7 MB total (all images combined)
- **Thinking levels**: flash2: minimal/high, pro: low/high, lite: minimal/high
- **Max images per execution**: 10 (`-N` flag)
- **Multi-turn**: flash2, pro, lite
- **Google Search**: flash2, pro
- **Image Search**: flash2 only

## Configuration File

デフォルト値は `config.json`（スキルディレクトリ直下、`SKILL.md` と同階層）で変更できます。ファイルが存在しない場合はビルトインデフォルトが使われます。CLI 引数は常に config より優先されます。

### 設定可能なキー

```json
{
  "model": "flash2",
  "aspect_ratio": "1:1",
  "output_dir": ".",
  "num_images": 1,
  "timeout": 120,
  "thinking_level": null,
  "negative_constraints": ""
}
```

| Key | Type | Description |
|-----|------|-------------|
| `model` | `"flash2"` \| `"pro"` \| `"lite"` | デフォルトモデル |
| `aspect_ratio` | string | デフォルトアスペクト比 |
| `output_dir` | string | デフォルト出力ディレクトリ |
| `num_images` | int (1-10) | デフォルト生成枚数 |
| `timeout` | int | デフォルトタイムアウト秒数 |
| `thinking_level` | string \| null | デフォルト思考レベル |
| `negative_constraints` | string | **既定は空文字（付加しない）**。ここに文字列を設定した場合のみ全プロンプト末尾に付加される opt-in 方式。例: `"Avoid: low quality, blurry, deformed hands, watermark."` |

### 使用例

常に Pro モデル・16:9・出力先固定にしたい場合:

```json
{
  "model": "pro",
  "aspect_ratio": "16:9",
  "output_dir": "./output"
}
```

必要なキーだけ記述すれば OK です。未指定のキーはビルトインデフォルトが使われます。

## Error Handling

| Issue | Solution |
|-------|----------|
| No API key | Set `GEMINI_API_KEY` env var |
| Model not found | Model ID may have changed; run `--list-models` to check |
| No images in response | Prompt may be filtered; simplify content (script exits 2) |
| Rate limit / 5xx | Script classifies by `status_code` and auto-retries with backoff (max 3) |
| 4K timeout | Auto-adjusted to 420s when `--image-size 4K` |
| Old-format session cannot be continued | The session predates the Interactions API; start a new one with `-c` |
| Import error | Run `pip install -U "google-genai>=2.11.0" Pillow` |

For detailed error codes and API specifications, see `references/api-reference.md`.

## Dependencies

```bash
pip install -r requirements.txt
# or directly:
pip install -U "google-genai>=2.11.0" Pillow
```
