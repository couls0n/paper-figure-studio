# Classification / hierarchy / field mapping

Use for “belongs to”, subtypes, parent/child grouping or field definitions. The edge means membership or correspondence, not execution. Category frequencies belong to proportion or bar; independent category systems must not be invented into a parent/child tree.

## Tree input

`assets/templates/taxonomy.json` has `data.variant="tree"`, `nodes` and `edges`. Nodes use `{id,label,detail?,row?,col?}`; edges use `{from,to}`. The renderer layers the tree left to right, or respects explicit row/col on all nodes. Each node has at most one parent. Cycles and feedback fail. Multiple roots are permitted for an explicitly stated forest.

For a large or asymmetrical tree, use explicit positions or split into panels. No node size or edge width implies frequency. If frequencies are required, provide actual counts to a quantitative template instead.

## Field mapping input

Use `data.variant="mapping"` with `mappings=[{field,description}]`. Optional `left_title`, `right_title` and `left_fraction` (.18–.6, default .3) control headings and widths. The renderer aligns two cards per row, joins the matching fields with arrows and grows the row for longer definitions. This is suitable for structured record fields and their explanations.

## Drawing method

1. Decide whether relations are hierarchical, independent marginal categories, or field-to-definition mappings.
2. Write explicit IDs and relations; check no category was omitted or duplicated under an unjustified parent.
3. For tree, allocate one layer per level and place siblings in consistent order. For mapping, preserve field order and align the corresponding explanation.
4. Use color to encode families only when the grouping is meaningful. The structure must remain understandable from labels and links.
5. Check node coverage and label readability at final figure size.

Reference patterns: AGENTIF Fig2/3; AgentAuditor Fig3 and OS-Harm category examples. AGENTIF Fig7's concentric rings are independent marginal distributions and should route to proportion with independent rings, not tree taxonomy.
