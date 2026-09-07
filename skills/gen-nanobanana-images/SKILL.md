---
name: gen-nanobanana-images
description: "Generate and edit images with Google Gemini image models (Nano Banana series): text-to-image, image editing, multi-turn refinement. Models: Flash2 (balanced), Pro (4K / best text accuracy), Lite (fast 1K draft). Use when the user names Gemini / Nano Banana, or needs infographics and multi-turn edits with Gemini. NOT for: requests naming GPT Image 2 / ChatGPT, and generic \"generate an image\" requests with no model specified (both go to gpt-image-2)."
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
2. **Want to edit or modify an existing image?** → Go to [Image Editing](references/editing-and-style-reference.md)
3. **Want to apply a style from reference images?** → Go to [Style Reference](references/editing-and-style-reference.md) (Pro has official style-reference slots; all models accept references)
4. **Want to iteratively refine an image over multiple turns?** → Go to [Multi-Turn Editing](references/multi-turn-and-grounding.md) (flash2/pro/lite)
5. **Need factual/grounded image content?** → Go to [Google Search Grounding](references/multi-turn-and-grounding.md) (flash2/pro)
6. **Need image-based search results?** → Go to [Image Search Grounding](references/multi-turn-and-grounding.md) (flash2 only)

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

**対話で不足パラメータを聞くとき**: [references/parameter-collection.md](references/parameter-collection.md) を Read（AskUserQuestion の質問表・モデル別フォローアップ・ワークフロー別の収集パターン）

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

## Generation Record (生成記録.md) — Mandatory

**After every generation run (single image or batch), write a `生成記録.md` into the output directory.** Do this after Post-Generation Verification so the record can include the verification notes.

Rules:

- **One record file per output directory.** If `生成記録.md` already exists there (follow-up batch, multi-turn continuation), **append a new dated section** — never overwrite past records.
- **Keep the output directory clean**: images + `生成記録.md` (+ `session_*.json` for multi-turn) only. Redirect any execution logs to the scratchpad — never leave per-image `.log` files in the output directory.
- **Multi-turn sessions**: append each turn (prompt + produced file) as a subsection under the same record.
- Write the record **in Japanese**, with this structure:

```markdown
# <内容の短いタイトル> ─ 生成記録

- 生成日: YYYY-MM-DD
- スキル: gen-nanobanana-images
- モデル: <正式名>（`<model ID>`）
- 設定: アスペクト比 ／ 解像度 ／ 実行形態（-N 枚数・並列・マルチターン等）
- 料金目安: **約 $X.XX**（$<単価>/枚 × <枚数>。Cost Guide の表から算出し、tier と価格時点を添える）

## ユーザーの指示（原文）

> （ユーザーの依頼文をそのまま引用。スラッシュコマンド経由ならコマンドごと）

## 各画像の生成プロンプト

### <ファイル名> ─ <日本語の短い内容サマリ>

（実際に API へ送ったプロンプト全文をコードブロックで。入力画像 `-i`・参照画像 `-r` を使った場合はそのパスも記載）

## 検証メモ

（Post-Generation Verification で気づいた点: 破綻・文字化け・再生成推奨など。問題なしならその旨を 1 行）
```

## Text-to-Image Generation

Generate a new image from a text prompt.

### Basic Generation (Flash2 — default)

```bash
python3 scripts/generate_image.py \
  -p "A red apple on a white marble surface. Soft studio lighting. Photorealistic." \
  -o ./output
```

**Pro / テキスト描画 / `-N` 複数生成の実行例、全フラグ・制約・`config.json` の詳細**: [references/cli-and-config.md](references/cli-and-config.md) を Read

## Image Editing / Style Reference

**既存画像の編集（`-i`）や参照画像（`-r`）を使うとき**: [references/editing-and-style-reference.md](references/editing-and-style-reference.md) を Read（入力画像の上限・ロール別枚数・プロンプトの Tips）

## Multi-Turn Editing / Grounding

**`-c` / `--session` の継続編集、`-g` / `--image-search` を使うとき**: [references/multi-turn-and-grounding.md](references/multi-turn-and-grounding.md) を Read

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
