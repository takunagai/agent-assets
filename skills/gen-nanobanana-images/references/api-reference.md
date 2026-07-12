# Nano Banana API Reference

## Model Specifications

GA models (Flash2 / Pro released 2026-05-28, Lite released 2026-06-30):

| Feature | Flash2 / NB2 (推奨) | Pro (最高品質) | Lite (最速最安) |
|---------|---------------------|---------------|----------------|
| Model ID | `gemini-3.1-flash-image` | `gemini-3-pro-image` | `gemini-3.1-flash-lite-image` |
| Max Input Tokens | 32,768 | 65,536 | 65,536 |
| Max Output Tokens | 8,192 | 32,768 | 4,096 |
| Max Images/Prompt | 14 (10 obj + 4 person) | 14 (6 obj + 5 person + 3 style) | 14 (object only) |
| Image Sizes | 512px, 1K, 2K, 4K | 1K, 2K, 4K | 1K only |
| Text Rendering | Good | High accuracy | Basic |
| Google Search | Yes | Yes | No |
| Image Search | Yes (exclusive) | No | No |
| Thinking Levels | minimal, high | low, high | minimal, high |
| Multi-Turn Editing | Yes | Yes | Yes |
| Aspect Ratios | 10 + 4 ultra | 10 standard | 10 standard |
| Speed | Fast (~5-15s) | Slower (~15-60s, 4K: ~180-360s) | Fastest (sub-2s) |
| Cost | Low | Higher | Lowest |

### 旧モデル（廃止）

- `gemini-2.5-flash-image`（旧 Flash）: 公式で「レガシー。移行を強く推奨」。本スキルからは削除済み。ドラフト用途は Lite を使う。
- `gemini-3.1-flash-image-preview` / `gemini-3-pro-image-preview`（preview ID）: 2026-05-28 に deprecated 告知、**2026-06-25 shutdown**。GA ID（`gemini-3.1-flash-image` / `gemini-3-pro-image`）へ移行済み。`--list-models` には preview ID がまだ列挙されることがあるが常用してはならない。

## Pricing（画像 1 枚あたり, Standard tier, 2026-07-12, 出典 https://ai.google.dev/gemini-api/docs/pricing）

| Model | 512px | 1K | 2K | 4K |
|-------|-------|-----|-----|-----|
| Lite | — | $0.0336 | — | — |
| Flash2 | $0.045 | $0.067 | $0.101 | $0.151 |
| Pro | — | $0.134 | $0.134 | $0.24 |

（Pro は 512px 帯なし。Lite は 1K のみ。）

## Aspect Ratios

**Standard (all models)**: `1:1`, `3:2`, `2:3`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`

**Extended (flash2 only)**: `1:4`, `4:1`, `1:8`, `8:1`

## Interactions API

The skill calls the **Interactions API** (`client.interactions.create`). Google's official image-generation samples have fully moved to it; the older `generate_content` path still exists as the Core API (not deprecated) but is treated here as legacy.

### Request

```python
from google import genai
import base64

client = genai.Client(api_key=api_key)

interaction = client.interactions.create(
    model="gemini-3.1-flash-image",
    input=input_blocks,                 # str, or list[dict] (see below)
    response_format={"type": "image", "aspect_ratio": "16:9", "image_size": "2K"},
    # optional, only when needed:
    tools=[{"type": "google_search", "search_types": ["web_search"]}],
    generation_config={"thinking_level": "high"},   # lowercase: minimal | low | high
    previous_interaction_id=prev_id,    # multi-turn continuation
    store=store,                        # single-shot: False; multi-turn: omit (server default true)
)
```

All arguments are flat keyword arguments — there is **no** `config=GenerateContentConfig(...)` wrapper. `response_modalities`, and `mime_type`/`delivery` on `response_format`, are not passed (the server default is used; the 2.10–2.11 `mime_type` Literal only accepts `image/jpeg`, so it is omitted and PNG is produced locally).

### Input blocks

`input` is either a plain string (text-only) or a list of typed blocks. Images **must** be explicit base64 strings — raw `bytes` are not auto-converted (only PathLike/IO are):

```python
input_blocks = [
    {"type": "image", "data": base64.b64encode(img_bytes).decode("ascii"), "mime_type": "image/png"},
    # ... more -i / -r images ...
    {"type": "text", "text": full_prompt},   # text goes last
]
```

Supported image MIME types: `image/png`, `image/jpeg`, `image/webp`, `image/heic`, `image/heif`.

### response_format

```python
response_format = {"type": "image", "aspect_ratio": aspect_ratio}
if image_size:
    response_format["image_size"] = SIZE_MAP[image_size]   # "512px" -> "512", others unchanged
```

### tools (search grounding)

```python
# -g only:             search_types = ["web_search"]
# --image-search only: search_types = ["image_search"]
# both:                search_types = ["web_search", "image_search"]
tools = [{"type": "google_search", "search_types": search_types}]
```

Validation is unchanged: Lite supports no grounding, `image_search` is flash2 only. The old typed `types.Tool(googleSearch=...)` / `types.SearchTypes` classes are no longer used.

### thinking

Pass `generation_config={"thinking_level": level}` with a **lowercase** value. Allowed values are model-specific: flash2 `minimal`/`high`, pro `low`/`high`, lite `minimal`/`high`. (There is no `MEDIUM` for these image models.)

### Response parsing

```python
interaction.id            # continuation key for multi-turn — always capture it

for step in interaction.steps:
    if step.type == "model_output":
        for block in step.content:
            if block.type == "image":
                data = block.data          # base64 string
                mime = block.mime_type
            elif block.type == "text":
                text = block.text

# convenience fallbacks if the steps walk yields no image:
interaction.output_image   # first image block
interaction.output_text    # concatenated text
```

Saving: `base64.b64decode(data)` → open with PIL → save as PNG (falls back to writing raw bytes with a mime-derived extension if PIL cannot open it). If no image block is present, the prompt was likely filtered — the script warns and exits 2.

**Note**: The `interaction.outputs[-1]` pattern seen in some older external write-ups is a retired schema (removed 2026-06-08). Use the `steps` walk plus the `output_image`/`output_text` convenience properties shown above.

### Multi-turn and store

- Capture `interaction.id` each turn; the next turn sets `previous_interaction_id` to the previous id.
- **store**: single-shot generations send `store=False` (no retention needed). Multi-turn (`-c`/`--session`) **omits** `store` and relies on the server default — `store` is **true** by default — which retains the interaction so the `previous_interaction_id` chain works. No local history rebuild is needed; `-i`/`-r` may be sent on continuation turns.
- **Retention**: stored interactions are kept for **55 days (Paid Tier)** or **1 day (Free Tier)**; Paid can change this to 7/14/28/55 days in AI Studio. Session continuation is valid only within that window — an expired session fails to continue, so restart it with `-c`.

### Error hierarchy

Interactions API exceptions live on a **separate hierarchy** from `google.genai.errors.APIError` (an internal compat-errors path). Do **not** import from that private path. Classify by duck-typing on `status_code`:

- `status_code == 429` or `>= 500` → retry with exponential backoff (max 3).
- `status_code is None` (network / timeout) → retry.
- other 4xx → raise immediately.

Substring matching on the message (`"400" in str(e)`) is not used anywhere.

## Legacy (generate_content era)

Earlier builds used `client.models.generate_content` with `types.GenerateContentConfig(imageConfig=..., thinkingConfig=..., tools=[types.Tool(googleSearch=...)])`, parsed `response.candidates[0].content.parts`, and threaded **thought signatures** (base64-stored raw bytes, key `thought_signature_b64`) through session files for Pro multi-turn. The Interactions API removes all of that: server-side `previous_interaction_id` replaces thought signatures, so sessions created that way (a `history` key, no `version`) cannot be continued. `generate_content` remains available as the Core API but is not used by this skill.

## Error Codes

| HTTP Code | Cause | Resolution |
|-----------|-------|------------|
| 400 | Invalid request (bad params) | Check parameters |
| 403 | Invalid API key or quota exceeded | Verify API key at aistudio.google.com |
| 404 | Model not found | Check model ID spelling |
| 429 | Rate limit exceeded | Wait and retry with exponential backoff |
| 500 | Internal server error | Retry after delay |
| 503 | Service temporarily unavailable | Retry with exponential backoff |

### Content Filtering

If the response contains no image parts, the prompt was likely filtered by safety settings. Try:
- Removing potentially sensitive content from the prompt
- Using more neutral language
- Avoiding copyrighted characters or real persons

## Constraints Summary

| Constraint | Value |
|-----------|-------|
| Max inline file size | 7 MB |
| Max Cloud Storage file size | 30 MB |
| Max images per prompt (all models) | 14 |
| Image sizes (Flash2) | 512px, 1K, 2K, 4K |
| Image sizes (Pro) | 1K, 2K, 4K |
| Image sizes (Lite) | 1K only |
| Temperature range | 0.0 - 2.0 |
| topP default | 0.95 |
| topK | 64 (fixed) |
| Knowledge cutoff | January 2025 |
