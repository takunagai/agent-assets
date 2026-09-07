---
name: image-gen-handoff
description: "Create handoff artifacts after Codex image_gen or GPT Image 2 batch generation: audit saved images, extract final prompts from Codex session JSONL, pair images with prompts, build a manifest (JSON/Markdown), validate sha256 / dimensions / missing prompts / duplicates, optionally extract unsaved JSONL images or archive JSONL. Never moves images or deletes JSONL by default."
---

# Image Gen Handoff

## Overview

Use this skill after image generation is already done. It turns saved images plus a Codex session JSONL into durable project artifacts: `manifest.json`, `manifest.md`, and an optional handoff note.

This skill is not an image generator. Default operation is read-only for existing images and JSONL: do not move, rename, compress, or delete anything unless the user explicitly asks for an optional operation. JSONL deletion is not implemented.

## Workflow

1. Identify the project root, image directory, batch name, and Codex session JSONL.
2. Run a dry run first:

   ```bash
   python3 <SKILL_DIR>/scripts/build_manifest.py \
     --project-root <PROJECT_ROOT> \
     --image-dir <IMAGE_DIR> \
     --jsonl <CODEX_SESSION_JSONL> \
     --batch-name <BATCH_NAME> \
     --out-json <IMAGE_DIR>/<BATCH_NAME>-manifest.json \
     --out-md <IMAGE_DIR>/<BATCH_NAME>-manifest.md \
     --handoff-md '作業記録/<BATCH_NAME>_引き継ぎ.md' \
     --dry-run
   ```

3. If the dry-run counts look right, rerun without `--dry-run`.
4. Validate the resulting manifest:

   ```bash
   python3 <SKILL_DIR>/scripts/validate_manifest.py \
     --manifest <PROJECT_ROOT>/<IMAGE_DIR>/<BATCH_NAME>-manifest.json
   ```

5. Inspect all `confidence=low`, `confidence=missing`, or `needs_review=true` items before treating the handoff as complete.

## Scripts

### Build manifest

`scripts/build_manifest.py` scans saved images, streams Codex JSONL, extracts `image_generation_call` events, pairs images with final prompts, records sha256 and dimensions, and writes artifacts.

Important options:

- `--dry-run`: print the summary only.
- `--expected-count`, `--expected-width`, `--expected-height`: add validation expectations.
- `--no-jsonl`: create an image-only manifest when the session JSONL is unavailable.
- `--copy-to`: optional non-default copy operation.
- `--rename-format`: optional copied filename format. Use only with `--copy-to`; prefer copying over renaming.

### Extract events

Use `scripts/extract_imagegen_events.py` when you need to inspect JSONL event extraction separately:

```bash
python3 <SKILL_DIR>/scripts/extract_imagegen_events.py \
  --jsonl <CODEX_SESSION_JSONL> \
  --limit-events 5
```

Optional image extraction is explicit:

```bash
python3 <SKILL_DIR>/scripts/extract_imagegen_events.py \
  --jsonl <CODEX_SESSION_JSONL> \
  --extract-images \
  --extract-dir <OUTPUT_DIR>
```

The extractor never emits base64 payloads into JSON output. It only writes decoded image files when `--extract-images` is set.

### Validate manifest

`scripts/validate_manifest.py` recalculates sha256, checks file existence, dimensions, and duplicate hashes. Use it after manifest creation and after any image copying step.

### Archive JSONL

`scripts/archive_jsonl.py` is optional and explicit. It creates a compressed copy only after a manifest exists. It never deletes the original JSONL.

```bash
python3 <SKILL_DIR>/scripts/archive_jsonl.py \
  --jsonl <CODEX_SESSION_JSONL> \
  --manifest <PROJECT_ROOT>/<IMAGE_DIR>/<BATCH_NAME>-manifest.json \
  --archive-dir <ARCHIVE_DIR> \
  --format gz
```

## Provider Adapter Boundary

Initial support is Codex-only via `scripts/providers.py`. Keep JSONL event parsing inside the `CodexAdapter`; do not spread Codex transcript-shape assumptions into manifest rendering. Future providers should expose the same event fields rather than changing the manifest schema.

## Confidence Rules

Record uncertainty instead of hiding it:

- `high`: filename number and generation order align, or filename number, generation order, and prompt number align.
- `medium`: image count and event count match, but filename or prompt-number evidence is weak.
- `low`: paired by order while counts differ; human review required.
- `missing`: no final prompt could be matched; human review required.

Do not invent missing prompts. Leave `final_image_prompt` null and set `needs_review=true`.

## Safety Rules

- Do not move or rename existing images by default.
- Do not compress, move, or delete JSONL by default.
- Do not implement or simulate JSONL deletion.
- Do not write base64 image payloads into manifests.
- Stream large JSONL line by line.
- Keep local machine paths out of public examples; use placeholders in documentation.
- Use temporary directories or uncommitted fixtures for live data tests.

## Reference

Read `references/manifest_schema.md` when modifying manifest fields, writing downstream consumers, or reviewing compatibility.
