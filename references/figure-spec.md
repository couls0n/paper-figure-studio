# Shared figure specification

The semantic `intent` used for routing and the geometry/data `spec` used for rendering are separate objects. Route first; then fill the selected type's template. Do not ask a nontechnical user to author either object.

```json
{
  "type": "bar",
  "title": "Task completion by method",
  "width": 1000,
  "height": 650,
  "data_status": "observed",
  "source": "results.csv / completion column",
  "data": {},
  "style": {}
}
```

- `type`: one of the twelve documented types, or `multipanel`.
- `width`, `height`: SVG canvas dimensions in px. Data plots default to 1000×650; schematics may grow vertically with content. An explicit height must be sufficient.
- `data_status`: `observed` for supplied observations, `transcribed` for values copied from a source, `digitized` for approximations recovered from a graph, `illustrative` for clearly labelled examples. This describes the input, not validation quality.
- `data`: type-specific schema in the matching recipe. Only copy values you actually have. The renderer validates concrete invariants such as dimensions; it cannot independently prove provenance.
- `source`: optional user-facing source reference. Prefer a stable file or paper locator. Do not add credentials or unrelated private filesystem details.
- `style`: type-specific optional styles; the recipe lists supported keys. Changing style does not change data semantics.
- `style.profile`: the three priority families use `paper_case` (comparison), `paper_flow` (architecture), or `paper_trace` (trajectory). A profile from a different family is rejected. Existing schematic specs without a profile retain the earlier baseline renderer; start new work from the updated paper-profile templates.
- `style_reference`: optional paper/figure/page plus visual features to preserve and intentional adaptations. It records visual provenance, independently of the content/data `source`; see [style-selection.md](style-selection.md). The export metadata retains this reference.

Keep the edited JSON beside deliverables. Templates intentionally contain illustrative values and visible demo labels. For a real figure replace the data and text together, then set `data_status`; do not merely remove the word “illustrative”.

```bash
python scripts/render.py my-figure.json --out output/my-figure
python scripts/render.py my-figure.json --out output/my-figure --formats svg --scale 2
```

The editable SVG is always retained. PNG/PDF are derived with PyMuPDF. Inspect each export, especially fonts, subscripts and screenshots; SVG is the authoritative editable source. Local image/specification paths are resolved relative to the JSON file. No remote image is downloaded automatically.

For a novel subtype, use the recipe's data contract and rendering method to adapt the source. Preserve input counts and stable IDs, and add a regression test if a fragile behavior changed. Bundled templates establish reusable baselines rather than claiming to implement every variant in the corpus.
