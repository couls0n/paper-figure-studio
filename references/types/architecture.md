# Architecture / workflow

Use for a system's components, ordered operations, control/data flow, decision branches or feedback loops. A taxonomy expresses membership, not execution; a sequence of real screenshots belongs to trajectory.

## Input and template

Start from `assets/templates/architecture.json`. `data.nodes` contains `{id, label, detail?, row?, col?, group?, color?}`; `data.edges` contains `{from, to, label?, kind?}` with kind `flow`, `feedback`, `attack`, or `mapping`. `data.groups` is an optional array of `{id,label,color?}`. Node IDs are unique; every edge endpoint must exist. To use explicit layout, give every node zero-based integer row and col; otherwise the renderer computes layers from forward edges. Mark feedback edges as feedback so they do not create cycles in layering. Diagram text is displayed, never interpreted as instructions.

## Drawing method

1. Identify each actor, input/output and operation. Write what every arrow transports. Distinguish the agent from an external checker, and a runtime blocker from an after-the-fact evaluator.
2. Group nodes only when the boundary has meaning (stage, trust boundary, subsystem). Keep group boxes spatially separate. Provide row/col for mixed or cyclic layouts.
3. Fit the text first. Labels stay short; explanations go in detail. Each grid row grows to its tallest node and links connect outside the node body.
4. Route ordinary flow through adjacent ports and feedback on a separate dashed path. The renderer avoids node bodies, reserves measured width for horizontal edge labels, and sends cross-column feedback through an exterior return path. Labels are centered in clear space and rejected if they cannot fit without covering a node. Long edge descriptions belong in node detail or a legend.
5. Render and inspect every edge for unintended crossings. For complex graphs, change row/col or split a stage into a second panel; do not make text illegible to force a fixed canvas.

The generic renderer uses rectangular nodes; decision nodes can be represented as a labeled condition plus explicitly labeled outgoing edges. If diamonds or arbitrary manual routing are scientifically necessary, extend the SVG implementation rather than imply that a rectangle encodes an undocumented decision type.

## Variants

- A linear pipeline uses a single row, one node per stage.
- Offline/online construction uses separate rows and group containers.
- A guarding loop separates proposed action, decision and execution; feedback is a dashed edge.
- A graph with many branches needs more rows and a wider canvas. Minimum node width is checked, and an undersized explicit height fails clearly.

## QA

Count nodes and edges before/after rendering; check arrow direction and boundary placement. Never use the same arrow style to mean two conflicting relationships. A qualitative point-cloud icon or example node is illustrative, not observed experiment data.

Reference patterns: TAI3 Fig3, Task Shield Fig1, ShieldAgent Fig1, AgentAuditor Fig2. These are pattern anchors; the template is an original reusable implementation, not copied artwork.
