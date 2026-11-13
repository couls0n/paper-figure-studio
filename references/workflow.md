# Workflow fidelity and source map

This skill contains the complete tracked working tree of FigureForge at `a9b7c3a8c4e783278a935e7744f688a7a2eece90`, plus an independent headless adapter and agent-response transport. The original repository is not imported, linked, read, contacted, or served at runtime. All paths below are inside this skill.

`source-manifest.json` records every original path, size and SHA-256. Run `node scripts/verify.mjs` to verify original bytes, every catalog image, and embedding dimensions. The original readme's headline count is stale: the executable catalog contains **3,449** figures. All of them and the rest of the 3,784 tracked files are included. No Git history, credentials, ignored source PDFs, temporary run logs or original checkout symlinks are needed by the drawing workflow.

## Preserved behavior

| Stage | Authoritative implementation in the snapshot | Preserved decisions |
|---|---|---|
| Paper input | `forge/index.html`: `selectPdfContext`, `callPdfParser` | Original document/text/rendered-page routing, relevance selection, schema and input limits |
| Retrieval | `forge/retrieval.mjs`, `retrieval-boot.mjs`, `retrieval-worker.mjs` | CLIP + BM25 ranking, filters, 512-dimensional embeddings, local WASM/tokenizer/model |
| Reference analysis | `index.html`: `ANALYZE_SYS`, `buildAnalyzePrompt`, `analyzeReferences` | Ordered images, measured density/style, design contract, representatives and bitmap anchors |
| SVG generation | `index.html`: `SVG_SYS`, `buildPrompt`, `genOaiSVG`, `auditAndRepair` | Exact original prompts and parsing; max two geometry repairs; candidate retained only if defects decrease; truncated drafts not polished as complete |
| Bitmap generation | `index.html`: `genOaiImage`; `image-api.mjs`, `image-routes.mjs`, `aspect-ratio.mjs` | Prompt budgets, reference preservation, provider payloads, ratio/resolution checks, original recovery/failover |
| Editable reconstruction | `index.html`: `runReconstruction`, `requestEditableScene` | Current single whole-image recognition, original scene recovery, conversion, and error status |
| Revision | `svg-revision.mjs`, `revision-gallery.mjs`, `revision-scope.mjs`, `revision-layout.mjs` | Full-canvas SVG handling, bitmap local/reflow behavior, screenshots, unchanged-output detection, candidate review and history |
| Export | `index.html` native export handlers; `editable-native.mjs`, `editable-text-layout.mjs`, `pptx-template.json` | Same scene, geometry, editable labels, shape/path conversion, typography and package formats |

All dormant/legacy code is also retained byte-for-byte. Presence in the snapshot does not make it an active workflow stage.

## Current Step 4, specifically

The active `runReconstruction` uses `pipeline: "direct-whole-image-v1"`. It receives the original full bitmap and selected recognition model. The whole-image request carries the original 128,000-output-token setting and one attempt; it keeps the existing no-deadline setting and scene parsing/recovery. It then converts recognized nodes into the editable SVG/native scene.

Its audit explicitly lists inventory, regional recognition, AI acceptance, repair and automatic retry as skipped. It does **not** execute the older multi-tile repair scheme described in `EDITABLE_EXPORT.md`. Successful recognition produces `qualityState: "not-run"`; the native exporter marks that result `draft-unverified`. Do not claim pixel-perfect reconstruction, add an automatic inspection/repair cascade, or replace a failed reconstruction with a raster-wrapped slide.

## Adapter boundary

`scripts/browser-bridge.js` is appended to the copied module in memory to expose existing operations. It sets task fields/model transport configuration, invokes original functions/buttons, and saves/restores state. It does not rewrite source files or replace workflow functions. The immutable asset snapshot can be independently inspected and hashed.

`scripts/runtime.mjs` serves only the skill-local snapshot in its own headless browser, exposes an authenticated local control endpoint, and materializes model requests into files for the active agent. It preserves original prompt text, attachment ordering/bytes, and request parameters. Original provider-specific model requests are intercepted locally; no remote FigureForge, gallery fallback, API account or Codex subprocess is used. The adapter waits for original asynchronous Step 4 work before declaring the overall job complete.

The agent-response boundary intentionally changes who executes inference. Model/profile labels and requested reasoning settings are recorded separately from actual host metadata. The same workflow does not guarantee identical stochastic model output. Pixel-level rendering can depend on the installed browser and system fonts, which are platform dependencies rather than missing source resources.

## Checks

`scripts/test-runtime.mjs` runs real local CLIP retrieval, original prompt construction, SVG generation/repair parsing, native five-format export, revision/review/version activation, PDF extraction, bitmap-to-scene conversion, native Gemini request construction and restart persistence. Its model replies are explicitly synthetic fixtures. It tests executable integration and preservation of workflow behavior; it does not claim to evaluate real model drawing quality.

Original unit tests remain under `assets/figureforge/forge/`. Some historical browser launchers contain the author's absolute Windows paths; those are archived source, not runtime dependencies. Use the portable standalone integration test for this skill. The original lock checker is retained too. Its baseline manifest was already absent in the source working tree; the independent `source-manifest.json` verifies this exact snapshot without modifying the original lock/checker.
