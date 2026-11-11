# Execution-trace taste: evidence first

Use this page after the semantic route has selected `trajectory`. Choose the visual archetype from the supplied evidence, not from the word “timeline”. The default is `style.profile: paper_trace`; the reference anchor remains in `style_reference` so the choice can be reviewed.

## Directly inspected anchors

| Anchor | Observed visual grammar | Reusable decision |
| --- | --- | --- |
| AgentDAM, Figure 2, PDF p. 5 | One light-gray enclosure; a narrow task area and wider user-data area; thin horizontal/vertical rules; time columns; compact monospaced trace over screenshots; short notes below; red unrelated data and green relevant data | `evidence_columns`: align a few decisive states so their textual decisions, screen evidence and outcomes can be compared vertically |
| ShieldAgent, Figure 7, PDF p. 17 | Left wide, vertically continuing environment/agent run; small role icons; screenshots paired with green thought/action strips; right narrow blue task configuration and pale-purple JSON annotations | `annotated_run`: keep the interaction sequence continuous and place machine-readable judgments beside it |
| ShieldAgent, Figure 14, PDF p. 23 | History screenshots form one compact strip; the proposed dangerous action has local red emphasis; the guard procedure has a separate dashed enclosure with numbered steps | When guard reasoning is also needed, compose a trajectory with a workflow/text panel. Do not stretch every guard operation into another screenshot step |
| OS-Harm, Figure 4, PDF p. 6 | Branching task construction ends in example desktop screenshots; branch edges encode alternatives, not chronological observations | This source is a routing boundary: use architecture for task generation, not a falsely chronological trajectory |

These are visual observations from the supplied paper pages, not a claim that all four papers share a single style. The bundled layouts adapt the first two anchors. Original paper screenshots and text are not redistributed with the skill.

## Taste parameters

- Background: shared `#F3F3F2` enclosure, not a separate elevated card around every step. No shadow or gradient.
- Rules: near-black 0.8–1.8 px at a 1200 px baseline, small corner radius only on the shared enclosure.
- Typography: serif explanation at 13–14 px; monospaced trace at about 11–12 px; screenshot interface stays independent. In a paper, the figure caption supplies the main title; the default omits a large visible banner while preserving SVG `<title>` metadata. `style.show_title: true` adds a restrained 18 px title.
- Color: red identifies the exact violating span or screen region, green identifies task-relevant content or the agent turn. Light blue/purple identify task configuration versus annotation. Color must carry the same meaning across steps.
- Density: a small context block precedes a few informative steps. A screenshot is a major evidence area, not a tiny decorative thumbnail. Remove redundant prose before shrinking all text.
- Callouts: thin red rectangles with short IDs; their explanation lives in the note or adjacent annotation. Preserve screenshot aspect ratio, never stretch pixels to fit another step.
- In an annotated run, align a verdict to the start of its own step and let long verdicts increase the shared step height. Explicit IDs complement spatial alignment rather than replace it.
- Continuous runs and selected snapshots are different forms. A tall annotated run can occupy an appendix page; a narrow main-text figure should select decisive states or use multiple panels.

## Reference-aware review

Put the selected source figure and generated figure beside each other locally. Compare the reading path, the ratio of evidence to explanation, grouping, type hierarchy, text density, and the role of color. Check whether a reader can connect each recorded action to its own screenshot and outcome. Do not award a numerical similarity score based on shared colors or rectangular cards.

The default mock interfaces are explicitly marked **ILLUSTRATIVE UI**. For a real execution use the recorded images. A visually plausible drawing never supplies missing execution evidence.
