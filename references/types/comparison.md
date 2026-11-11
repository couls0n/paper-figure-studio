# Dialogue / case comparison

Use when the claim depends on a contrast: baseline versus proposed method, before versus after, normal versus altered behavior. Keep common inputs and aligned events so readers can see what changed. It is not a numerical bar chart merely because the request says “compare”.

## Input

`assets/templates/comparison.json` contains `data.shared_input` and `data.columns`. Every column has `{id,title,status?,events}`. Every event has `{role,text,highlights?}`; highlights are `{text,color?}` matches inside visible lines. Status may be normal/safe/success, unsafe/attack/blocked, or neutral. Status is a visual label supplied by evidence; the renderer does not infer safety from wording.

## Drawing method

1. Put the shared instruction/context once across the top.
2. Use identical event order in each condition. A missing event should be explicitly labeled absent rather than silently shifting later rows.
3. Keep role labels as headers and explanatory content as readable paragraphs. Emphasize only the changed or decisive phrase.
4. Fit all columns to the same event-row heights. The renderer wraps text and increases height from the longest counterpart.
5. Use the same column identity, role labels and state colors across related figures.

Two or more columns are supported. Canvas width must allow at least 220 px per column. Large comparisons should become several panels; width or role count changes must not cause text to disappear.

## QA and limitations

Compare the original and shown text, action order and conclusion. `highlights` matches substrings of rendered lines; if a highlighted phrase crosses a line break, shorten it to the key phrase or use multiple highlight fragments. Color alone should not carry the conclusion: retain an Outcome event. A dialogue illustration is not a transcript unless its source is supplied.

Reference patterns: TAI3 Fig1, GuardAgent Fig3/23, BadAgent Fig1/4–6 and MELON Fig2.
