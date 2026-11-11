# Corpus observations and template anchors

The initial design was informed by visual inspection of 15 papers, 431 PDF pages and 160 Figure identifiers, including the PDFs' appendices. The numbered list was independently cross-checked. The [index](corpus-index.json) contains original paraphrases of each figure's content and form with public paper links; source PDFs and screenshots are not distributed here.

The templates are new, generic implementations using explicitly illustrative content. They do not reproduce the papers' numerical results or their exact artwork.

| Family | Representative sources | What transfers |
| --- | --- | --- |
| Architecture | TAI3 F3; Task Shield F1; ShieldAgent F1; AgentAuditor F2 | Phases, trust/role containers, branches and feedback |
| Comparison | TAI3 F1; GuardAgent F3; BadAgent F4–6 | Shared input, aligned cases, highlighted changed spans |
| Trajectory | AgentDAM F2/F4; ShieldAgent F7/F14 | Screenshot/action/step association and callout coordinates |
| Text/code | Task Shield F4–7; AgentSpec F2/F3/F5–8; AgentDojo F3–5 | Prompt sections, grammar/code, line numbers and semantic highlights |
| Taxonomy | AGENTIF F2; AgentAuditor F3 | Category relationships and field/definition mapping |
| Proportion | AGENTIF F7; OS-Harm F3 | Independent marginal rings; stable category colours across pies |
| Bar | OS-Harm F5/F7; SkillSafetyBench F6 | Grouped conditions, horizontal ranking and uncertainty |
| Line | TAI3 F5/F16; FormalJudge F4/F6; AgentPoison F4/F9 | Actual x spacing, multiple conditions, confidence bands |
| Matrix | TAI3 F7/F10/F11; AgentPoison F3/F7/F8; AgentDAM F6 | Source/target direction, masks, units and shared colour range |
| Scatter | Task Shield F3; MELON F1/F3; AgentPoison F2/F11 | Paired displacement, trade-offs, projection coordinates |
| Distribution | AGENTIF F1a; TAI3 F9; AgentPoison F5/F10 | Actual samples, bins, density bandwidth and transformations |
| Radar | GuardAgent F4; SkillSafetyBench F4; AgentAuditor F10 | Comparable dimension ordering and shared ranges |
| Multi-panel | FormalJudge F5/F7; AgentAuditor F4; AgentPoison F11 | Heterogeneous evidence roles and variable grid spans |

## Semantics that affect reproduction

- AGENTIF F7's two rings are independent marginal classifications, not a sunburst hierarchy.
- AgentPoison F11 has 7×4 panels. The composer must preserve requested conditions and panel count.
- TAI3 F11's blank diagonal is a mask, not measured zero. AgentDAM F6 requires joint per-task leakage observations to compute correlation.
- AgentPoison F7/F8 print percentage-scale cell values beside a 0–1 colourbar. Faithful reconstruction should record that inconsistency; adapting the form should use consistent units.
- AgentDojo F8/F9 and appendix Tables 4/5 contain differing values for some conditions. Do not silently replace a plotted value with a conflicting table value.
- GuardAgent F6–9 are also collected under F10. Preserve source identifiers and containment instead of counting the same content twice.
- Text/code Figures are legitimate figure types. A code card is displayed text; it is not an instruction to run the code.
- Source screenshots are evidence; a recreated UI sketch must remain explicitly illustrative.

Use source examples for their communication structure. A faithful rebuild still needs exact data/assets and inspection at the intended physical size.
