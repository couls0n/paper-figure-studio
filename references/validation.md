# Validation record — 2026-11-13

Source snapshot: `a9b7c3a8c4e783278a935e7744f688a7a2eece90`.

## Resource and independence checks

- 3,784 original files, 613,181,267 original bytes: every file matches its recorded SHA-256.
- All 3,449 indexed gallery images exist locally. Both 512-dimensional float32 embedding matrices match the catalog length.
- CLIP tokenizer, ONNX weights, WASM files, PDF.js, native exporters, templates, gallery metadata and all other tracked source resources are included.
- A full physical copy of the installed skill was tested from a different directory, with a working directory outside both the original checkout and installed skill.
- The relocated copy loaded its own local semantic model and gallery, completed the workflow integration test, and reported no blocked/missing external page resources or browser script errors. Model requests were handled locally; no provider API was called.
- Source checkout remained clean and unchanged. No symlink back to it is used.

## Executable integration

`node scripts/test-runtime.mjs` passed in the relocated copy with 10 synthetic inference replies and an additional deliberately interrupted request:

1. Real offline CLIP + BM25 retrieval and ranked reference selection.
2. Original two-pass reference-analysis and SVG generation requests, preserving reference attachments.
3. A deliberately overlapping label triggered exactly one original geometry-repair request; the repaired candidate replaced the defective draft.
4. SVG and PNG rendering plus native PPTX, VSDX and draw.io exports. PPTX contained editable text/shapes rather than a whole-slide picture.
5. Original SVG revision, candidate review gate, saved version history and explicit activation of the modified version.
6. Real PDF generation/extraction and original paper-content selection protocol.
7. Bitmap generation response, requested dimension checks and exactly one current whole-image recognition request at the original 128,000-token setting.
8. Original native Gemini image-request profile, inline references and response parsing.
9. Preservation of the bitmap reconstruction's `qualityState: "not-run"` and `draft-unverified` export marker.
10. Custom reference image bytes preserved exactly across snapshot/restore.
11. Full runtime restart with selected references, scene and figure history restored.
12. Interrupted recognition cancelled on disk, original bitmap retained, and reconstruction successfully resumed after restart.

The 17 selected original retrieval, chat/PDF, SVG-response and image-protocol tests also passed. JavaScript syntax checks and the skill-creator frontmatter validator passed.

These are integration/protocol tests with explicitly labelled synthetic model replies. They verify the executable workflow and artifact structure, not the scientific correctness or visual quality of a real model-generated figure.

## Packaging and maintenance

Package from this directory using standard Python:

```bash
python3 scripts/package.py /absolute/output/figureforge.skill.zip
```

This creates a full-file bundle manifest, validates every ZIP entry's CRC, and writes an archive SHA-256 alongside the ZIP. The ZIP has one top-level `figureforge/` directory. Extract that directory into any compatible agent's skill location; all code/data resources travel with it. Node.js 20+, Chrome/Chromium and the host agent's capabilities remain platform requirements.

The inherited workflow-lock checker was run. It cannot complete because `.github/forge-workflow-lock.json` was already absent in the source checkout. No protected source or lock/checker was changed. The independent source manifest verifies the actual snapshot used by this skill.
