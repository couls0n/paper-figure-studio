---
name: figureforge
description: Create and revise scientific paper figures using a self-contained FigureForge workflow, its complete reference gallery, original prompts, layout analysis, SVG or bitmap generation, and native editable exports. Use for FigureForge-style paper diagrams, reference-guided figures, figure sets, revisions, or bitmap-to-editable reconstruction.
---

# FigureForge

Use the complete, independent engine and resources shipped inside this skill. The active agent performs the AI reasoning and supplies image generation through its available image tool. The bundled engine handles retrieval, prompt construction, response parsing, geometry checks, revision history, reconstruction, rendering, and exports.

Everything needed from the original project is in `assets/figureforge/`: the entire 3,784-file source/resource snapshot, all 3,449 indexed reference images, metadata, CLIP text model, text/image embeddings, tokenizer, WASM runtime, PDF reader, templates, original workflow modules, examples, licenses, and attribution. The browser driver is vendored in `scripts/vendor/`. Resolve paths relative to this skill directory. Do not look for the original checkout, start its server, fetch missing gallery resources, or require a Codex CLI login/API key.

## Start a figure project

Use Node.js 20+ and an installed Chrome/Chromium. These are platform prerequisites; the drawing engine, driver, model weights and gallery are bundled. `FIGUREFORGE_BROWSER` can specify a browser executable when automatic discovery cannot find it.

```bash
node <skill-directory>/scripts/figureforge.mjs doctor
node <skill-directory>/scripts/figureforge.mjs verify
node <skill-directory>/scripts/figureforge.mjs start <project-directory>
```

The launcher creates a private headless browser and loopback transport owned by this skill. It does not attach to the user's existing browser or require them to operate a webpage. Keep generated projects outside the installed skill. For a figure set, create one project per figure and a shared brief describing the common vocabulary, palette and storyline.

Read [the command and agent-response protocol](references/commands.md) before first use. Read [workflow fidelity](references/workflow.md) when choosing modes, modifying figures, reconstructing bitmaps, or interpreting checks.

## Execute the original workflow

1. **Establish the drawing brief.** Read the user's source material and identify the claim, required entities and relationships, desired figure type, language, and deliverables. Preserve the user's scientific storyline. Keep supplied facts separate from illustrative examples. An uploaded paper can use the engine's `parse-pdf` operation. Use the original target values: `overview`, `architecture`, `pipeline`, `results`, or `custom` with `targetDescription`.
2. **Retrieve and inspect references.** Run `search`; it uses the bundled CLIP + BM25 pipeline. Inspect the actual `imagePath` files returned, then `select` relevant IDs. User references can be added with `upload-references`. Preserve reference identity and ordering. The original two-pass mode requires at least four references and allows ten total; its analysis selects 2–4 representative SVG references and 1–3 bitmap anchors. The engine enforces these rules.
3. **Configure the output route.** Default to `mode: "svg"`, `pass: "two"` when the request calls for editable diagrams and no bitmap route is specified. Honor an explicit bitmap request. SVG inference is performed by the active agent. Bitmap inference requires an actual image-generation/editing tool. Choose a bitmap size/profile the available tool can return; the original ratio and resolution checks remain active. If that capability is absent, explain the missing capability and ask before changing the requested route.
4. **Generate through the engine.** Run `generate`. In two-pass mode it queues reference analysis, constructs the measured design contract, then queues generation. Respond to every queued request using the protocol below. Let the existing engine perform its SVG checks and bounded repairs, or automatic bitmap reconstruction. A finished Step 3 bitmap can coexist with an unfinished Step 4; wait for the job's final status before claiming editable output is ready.
5. **Inspect the result.** Export a PNG preview and inspect it. Check factual fidelity, reading order, text, grouping and arrows against the brief. Keep the engine's quality status. A schema-valid reconstruction with `qualityState: "not-run"` has not passed a visual fidelity test. Use `revise` for requested corrections; preserve the original review/confirmation gate and version history.
6. **Export and deliver.** Use the original SVG, PPTX, draw.io and VSDX exporters; PNG is a raster preview of the SVG. Read the export job's artifact list and show the preview plus requested files. Do not represent a PNG preview as a separately generated bitmap or a flattened slide as editable shapes. Stop the project's runtime when its jobs and reviews have finished.

## Act as the model without changing the workflow

`requests PROJECT` lists the exact pending model operations. For each request:

- Read its `prompt.md` and inspect **all** entries in `attachments.json` in order. The readable request preserves the original roles, text, parameters and attachment positions; the original wire payload is also archived.
- Follow the original requested output schema. For analysis, return the requested JSON. For SVG generation/modification/repair, return a complete SVG. For reconstruction, inspect the supplied bitmap and return the requested scene nodes in original pixel coordinates. Do not invent a different intermediate format or bypass a queued stage.
- For an image request, pass its original prompt and every reference image to the host's image tool, preserving the requested composition, ratio and resolution. Return the actual resulting image file. Read any provider-specific native request structure rather than assuming every image request has a top-level `prompt`.
- Save the response in the project and submit it with `respond`. Continue until the job completes, fails, or reaches the original revision review gate. `status` and `requests` do not initiate extra inference.
- Requested model names are transport/profile labels, not proof of which host model ran. The Codex-compatible SVG profile requests `max`; use the host's strongest authorized reasoning setting when selectable. Report actual model/effort only when known. A skill cannot forcibly change the enclosing agent's model or reasoning setting. Never fabricate usage or execution metadata.

The bundled generation code is authoritative. Do not replace its prompts with generic diagram instructions, omit attached references, introduce new repair/retry loops, or turn every paper into a fixed panel template. For an explicit failure, use `fail` so the engine can apply its original error behavior.

## Revisions and continuation

The project stores source inputs, exact inference requests and replies, analysis, scenes, figure versions and exported artifacts. `start` restores the last completed project snapshot, including uploaded references and history. In-flight HTTP requests cannot survive a stopped browser: inspect their recorded status and resume at the failed operation, retaining existing artifacts.

`revise` uses the original revision implementation and presents a candidate for review. Use `review` to obtain the candidate and source files, show the comparison to the user, and use `accept-review` only when the user confirms it. Then run `activate-version` to make the accepted version the export source. Rejected candidates preserve the original figure and modification input.

## Maintain independence and fidelity

The source snapshot is pinned to commit `a9b7c3a8c4e783278a935e7744f688a7a2eece90`; all original files are byte-identical and checked by `scripts/verify.mjs`. Normal drawing tasks write only to the chosen project. The skill's standalone adapter is separate from that frozen snapshot. An update to the skill engine is a separate code-maintenance task.

See [the validation record](references/validation.md) for tested behavior, relocation checks, and full-resource ZIP packaging.

The current executable Step 4 is **one whole-image recognition call**, with its original parsing/recovery and native conversion; its legacy region/inventory/repair implementations are still bundled, but are not the active default. Follow the current executable behavior described in [workflow fidelity](references/workflow.md), not older descriptive documents in the source snapshot.

Original code/image attribution is preserved in `assets/figureforge/LICENSE`, `NOTICE.md`, and `IMAGES_POLICY.md`; Playwright's notices are in its vendored directory. Do not redistribute generated projects, private paper inputs, or credentials as part of the skill package.
