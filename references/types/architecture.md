# Architecture / workflow

Use for a system's components, information/control flow, stages, branches or feedback. A taxonomy expresses membership; an actual run with screenshots belongs to trajectory.

For the paper style requested in this library, read [workflow style grammar](../style/workflow.md) and choose a source-backed visual archetype after semantic routing. The primary references are Task Shield F1/F2 for runtime checking, and TAI3 F3 for staged construction/execution. AgentAuditor F2 illustrates a more complex staged layout that may need manual extension.

## Two reusable templates

- [architecture.json](../../assets/templates/architecture.json): `style.profile: paper_flow`, `data.variant: runtime`. User request → agent; extracted task context → alignment check; permitted action → execution; mismatch → feedback → agent. Heterogeneous objects and a separate external environment replace uniform dashboard cards.
- [architecture_stages.json](../../assets/templates/architecture_stages.json): same profile, `data.variant: staged`. Two shallow-colour phase bands, document/process/memory/model objects, a real three-record constraint table, cross-stage retrieval and a short exterior update edge.

Both contain original illustrative content, `style_reference` source anchors and editable vector glyphs. They demonstrate a paper's visual grammar, not its experimental evidence or exact artwork.

```bash
python scripts/render.py assets/templates/architecture.json --out output/runtime
python scripts/render.py assets/templates/architecture_stages.json --out output/stages
```

## Input

Existing `data.nodes`, `edges` and `groups` remain valid. Every node has a unique string `id`, `label`, optional `detail`, and optional explicit integer `row`/`col`. Supply row and col on every node or omit both everywhere. Automatic columns follow forward edges; mark cyclic edges `kind: feedback`.

Paper-profile additions:

| Object | Fields and meaning |
| --- | --- |
| Node | `kind`: `document`, `memory`, `model`, `process`, `tool`, `environment`, `decision`, `user`, `table`. Default `process`. `group` names a declared group; optional `color` overrides semantic fill. |
| Table node | `kind: table` requires explicit `columns: [string, ...]` and rectangular `rows: [[scalar, ...], ...]`. All cells remain editable SVG text; column widths and row heights fit their actual contents. Tables grow instead of dropping rows. |
| Edge | `from`, `to`, optional short `label`; `kind`: `flow`, `feedback`, `attack`, `mapping`. `semantic`: `flow` (black), `allow` (green), `reject` (red), `retrieve` (blue grey). `attack` defaults to red. |
| Edge ports | Optional paired `from_port` and `to_port`, each `left`, `right`, `top` or `bottom`. Both are required together. The path still avoids node interiors. Use explicit ports when the default loop gives an unclear reading direction. |
| Group | `id`, `label`, optional `color`, `border_color`, `header_color`. Member bounds define the group. Separate groups spatially; overlapping group containers fail explicitly. `runtime` uses restrained boundary outlines; `staged` uses shallow full phase bands. |
| Legend | Optional `data.legend: [{semantic, label}]` explains the line semantics used in this diagram. |
| Title | The normal paper-profile title is SVG metadata, suitable for an external caption. Set `style.show_title: true` to display it inside the figure. |

The legacy profile without `style.profile` remains available for existing specifications. Switching profiles changes visual grammar, not the supplied graph.

## Concrete drawing method

1. Write the message of the figure and the meaning of every edge. Distinguish task context, proposed action, decision, execution and returned evidence. Choose the runtime or staged source archetype from these relations.
2. Assign semantic node objects. Documents and memories should read as artifacts; processes should read as operations. Use labels even where an icon seems obvious.
3. Place the main reading path first, then failures/feedback and shared inputs. Keep related branches close. Stage bands must correspond to real phases, not arbitrary rows.
4. Add short edge labels and optional explicit ports. Red/green belongs to an explained decision meaning. The renderer checks graph IDs, group overlap and object kinds; routes use orthogonal visible corridors.
5. Inspect the resulting SVG/PNG against the selected paper at equal display widths. Check object hierarchy, density, local loops, use of colour and typography. Test at the intended print width; shorten prose or split panels when labels become unreadable.
6. Verify every node and edge, source/target port, header, legend and scientific relation. A route that fits geometrically can still encode the wrong mechanism.

`paper_architecture.py` renders original editable objects. It does not automatically recreate arbitrary irregular source layouts, branded logos, or small embedded data plots; adapt those deliberately from the selected reference and preserve their meaning.
