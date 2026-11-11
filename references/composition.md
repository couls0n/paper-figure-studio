# Multi-panel composition

A composite is a layout operation over individually routed figures. It is not a thirteenth semantic chart family. Examples: method architecture plus result bars; screenshot trajectory plus a leakage matrix; 7 embedding models × 4 iterations.

## Input and layout

```json
{
  "type": "multipanel",
  "title": "Illustrative mechanism and evidence",
  "width": 1600,
  "height": 1100,
  "data_status": "illustrative",
  "layout": {"rows": 2, "cols": 2, "gap": 24, "margin": 28,
             "column_weights": [2, 1], "row_weights": [1, 1]},
  "panels": [
    {"id": "a", "label": "Mechanism", "row": 0, "col": 0,
     "spec_file": "architecture.json"},
    {"id": "b", "label": "Evidence", "row": 1, "col": 0,
     "spec_file": "bar.json"},
    {"id": "c", "label": "Trade-off", "row": 0, "col": 1,
     "rowspan": 2, "spec_file": "scatter.json"}
  ]
}
```

Each panel contains exactly one `spec_file` or inline `spec`. Child files have their own paths relative to themselves; inline images use the enclosing specification's directory. Inline data status inherits the parent when omitted. IDs are unique. Rows and columns are zero-based, spans default to one. Rows/columns and spans must be integers and remain inside the grid.

`label_height` reserves space for panel letters; `header` reserves space for the figure title. Defaults are 27px and 65px with a title. The content retains aspect ratio inside its slot; it is not stretched. Weights control available grid column/row sizes, excluding gutters. Use a wide span for a long flow, not font shrinking.

## Drawing method

1. Establish each panel's scientific role and route. A matrix can be corroborating evidence, not just another metric.
2. Choose grid rows/columns and spans from the reading sequence. Keep matched comparisons close; align comparable axes.
3. Fill source specifications with their real data. Make category order, palettes, units and scale decisions explicit across comparable panels.
4. Render each panel as editable SVG. Prefix element IDs before embedding so repeated clipping paths and gradients do not collide. Use explicit translation, uniform scale and clipping groups; nested SVG viewport positioning is not consistently honored by PDF exporters.
5. Compose without rasterizing the panels. The compositor rejects overlapping occupied cells, duplicate panel IDs and out-of-grid spans.
6. Inspect `*.render.json`: it records panel slots and scale factors. Slot checks are **not** a claim that matplotlib plot-area edges align; verify those visually or with a plot geometry tool when comparable panels need exact alignment.
7. Inspect final physical size. If source labels become too small, enlarge canvas, reduce redundant text, adjust spans or split pages. A 28-panel plot needs short repeated labels and shared encodings.

## Concrete checks

- All intended panels appear once, with correct conditions and labels.
- Repeated axes have intended limits; independent axes are visibly labelled.
- Shared legend entries correspond to all panels, not just one selected panel.
- Overlays, clipping and SVG element IDs remain valid after composition.
- Screenshot pixels are not redrawn as a claimed real interface result.

Use [multipanel.json](../assets/templates/multipanel.json) for a mixed layout and [multipanel_28.json](../assets/templates/multipanel_28.json) to exercise a 7×4 matrix. Both are illustrative test material.
