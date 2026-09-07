# CLI フラグ・制約・config.json と実行例（Pro / テキスト描画 / -N）

`SKILL.md`（gen-nanobanana-images）から分離。該当する場面でこのファイルを Read する。実行するスクリプトは `scripts/generate_image.py` のまま。

## Contents

- High-Quality Generation (Pro)
- With Text Rendering (Pro recommended)
- Multiple Variations (-N)
- Script Parameters Reference
- Constraints
- Configuration File
- 設定可能なキー
- 使用例

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
