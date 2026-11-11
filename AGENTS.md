# Working in this repository

This repository is a discoverable Codex skill plus its runnable figure templates. Keep the twelve type IDs stable; multipanel is a composition operation.

- Intent interpretation belongs in the skill guidance; `route.py` maps structured semantic evidence. Do not replace it with a word-count classifier.
- Prioritize paper-like case studies, workflows and execution traces. Keep type routing separate from visual-archetype selection, record the source figure in `style_reference`, and compare source/result images before claiming a style match.
- Add or change a type's renderer, JSON template, drawing recipe and meaningful behavior tests together.
- Never relabel bundled illustrative values as measured research results.
- Preserve editable SVG text and object structure; verify rendered PNG/PDF, not only XML validity.
- Keep image paths relative to the spec and do not include local research PDFs, private screenshots, credentials or environment files in commits.
- Keep the skill self-contained. Do not hard-code a developer's local skill/runtime paths.
- Run `python -m unittest discover -s tests` and render affected templates before committing. Changes to routing need ambiguous/negative and multi-panel cases.
