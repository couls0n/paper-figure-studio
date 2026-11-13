# Working in this repository

The owner replaced the former twelve-template skill with the complete standalone FigureForge skill. The skill name is `figureforge`; this repository is `couls0n/paper-figure-studio`.

- Keep the skill self-contained. Runtime paths must resolve from the installed skill directory. Do not depend on the original FigureForge checkout, remote gallery assets, a developer's local runtime, or an existing Codex login.
- The frozen original implementation/resources are under `assets/figureforge/`. Preserve their bytes and workflow behavior unless the user explicitly requests an engine update. `references/source-manifest.json` records that snapshot; do not rewrite it merely to hide unexpected differences.
- Independent orchestration and host-agent transport live under `scripts/`. Preserve original prompts, ordered reference images, request parameters, reconstruction behavior, native object exports and candidate review gates.
- Never label synthetic fixtures as real model evaluation or illustrative values as measured research results. Keep actual host model metadata separate from transport/profile labels.
- Keep the full gallery, indexes, model weights, tokenizer, WASM runtime, PDF resources, templates and licenses. Do not silently trim resources to make the repository smaller.
- Keep generated projects and credentials outside the skill checkout. Do not add local research PDFs, private screenshots, API keys or environment files.
- Before committing, run `node scripts/verify.mjs` and `node scripts/test-runtime.mjs`; verify changed runtime modules with `node --check`. The former Python renderer/routing tests belonged to the replaced skill and no longer define this repository's workflow.
- When changing packaged skill files, regenerate `references/bundle-manifest.json` with `python3 scripts/package.py /path/outside/checkout/figureforge.skill.zip`, then run `node scripts/verify.mjs` again. Preserve original attribution and distinguish the frozen source manifest from the current skill bundle manifest.
