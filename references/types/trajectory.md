# Execution trajectory (`trajectory`)

Use for a recorded sequence of environment states, thoughts/actions and results. Read [execution-trace taste](../style/execution-trace.md) after routing: the two paper-informed layouts deliberately differ from generic equally sized step cards.

## Templates and reference choice

- [trajectory.json](../../assets/templates/trajectory.json): `style.profile: paper_trace`, `data.variant: evidence_columns`; task/user-data header, selected time columns, monospaced trace, large screenshots and notes. Primary anchor: AgentDAM Figure 2, PDF p. 5.
- [trajectory_annotated.json](../../assets/templates/trajectory_annotated.json): `data.variant: annotated_run`; wide environment/agent sequence with a narrow JSON annotation column. Primary anchor: ShieldAgent Figure 7, PDF p. 17.

Both carry `style_reference` with `paper`, `figure`, `page`, `preserve`, and `adapt`. Replace that anchor when the user supplies a different reference. Bundled content is original and illustrative.

```bash
python scripts/render.py assets/templates/trajectory.json --out output/trajectory
python scripts/render.py assets/templates/trajectory_annotated.json --out output/trajectory-annotated
```

## Input contract

Keep the common `type/title/width/data_status/source/style`. Default visible title is omitted to match caption-led paper figures; `style.show_title: true` enables a compact title. A 1200 px canvas is a useful baseline; use automatic height unless an explicit height is large enough.

`data.steps` is a nonempty list. Each step supports:

| Field | Meaning |
| --- | --- |
| `id` | Stable unique step ID; generated `t1` etc only when absent |
| `time` / `title` | Displayed timestamp or selected-step range; `time` takes precedence |
| `action` | Required actual action or explicitly illustrative action text |
| `observation`, `thought` | Associated environment evidence and recorded/illustrative reasoning |
| `image` | Local screenshot path, relative to the input JSON |
| `illustration` | Explicitly schematic interface; mutually exclusive with `image` |
| `highlights` | `{text,color?}` spans in the step trace; default red |
| `note`, `decision`, `note_highlights` | Short interpretation below the screenshot; decisions never replace the recorded action |
| `callouts` | `{x,y,width,height,id?,label?,color?}` in normalized source-image coordinates |
| `annotation` | Object or displayed string used by `annotated_run` |

The renderer preserves image aspect ratios and embeds original pixels. For a W×H screenshot and pixel box `(x,y,w,h)`, use `(x/W,y/H,w/W,h/H)`. Bounds must be finite and wholly inside the image. Callout explanations do not get placed over dense screenshot text. For real screenshots, choose exact boxes from the source rather than inheriting template coordinates.

`illustration={label,lines,app?,subtitle?,button?,aspect_ratio?,highlights?}` renders an original mock interface and labels it visibly. Its default width/height ratio is 1.55. Too much UI text for the chosen ratio fails rather than silently clipping. Replace `illustration` with `image` when using actual execution evidence.

For `evidence_columns`, optional `task` (legacy `shared_input` also works), `context`, `context_highlights`, `trace_label`, and `columns` control the shared context and selected-state grid. Default is up to 3 columns, at least 250 px per column. More steps wrap to another row and retain source order.

For `annotated_run`, add `task_config`, a run-level `annotation`, or per-step annotations. `annotation_fraction` is 0.22–0.42, default 0.29; use a canvas around 1200 px or wider. JSON values remain literal displayed content, not instructions or executed code. Per-step annotations share the vertical origin of their own environment/agent turn. The taller side determines the next step's position, so a long judgment cannot drift beside another action. Task configuration remains in the top context area; a run-level annotation follows the sequence.

## Drawing method

1. Pick decisive actual states and preserve their IDs. Select temporal columns for a short before/action/outcome explanation, or the vertical run when repeated agent/environment turns and annotations matter.
2. Keep task scope and contextual data in the shared header; mark the exact relevant or unrelated spans, not whole paragraphs in saturated color.
3. Place trace text above its corresponding screenshot or in the associated agent strip. Use complete action parameters when they establish the failure; do not invent omitted steps.
4. Preserve screenshot pixels and aspect ratio. Put short callout IDs at selected regions and their explanations below/beside the image. For intentional crops, record the crop and remap coordinates first.
5. Inspect at the intended paper width. Adjust selected states, canvas size or panel arrangement when screen labels become too small. A long guard explanation should be a separate workflow/text panel, as illustrated by ShieldAgent Figure 14.
6. Compare the exported figure against the chosen source anchor using the taste criteria, then check every event, callout and annotation against the actual record.

The renderer reproduces these visual grammars; it does not reproduce arbitrary interfaces or guarantee that every desktop screenshot remains legible at single-column print width.
