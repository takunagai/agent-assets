# 画像編集（-i）とスタイル参照（-r）

`SKILL.md`（gen-nanobanana-images）から分離。該当する場面でこのファイルを Read する。実行するスクリプトは `scripts/generate_image.py` のまま。

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
