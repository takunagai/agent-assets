# マルチターン編集（-c / --session）と Google / 画像検索グラウンディング

`SKILL.md`（gen-nanobanana-images）から分離。該当する場面でこのファイルを Read する。実行するスクリプトは `scripts/generate_image.py` のまま。

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
