# Screenshot / execution trajectory

Use when each step must tie observable UI state to an action, timestamp/step ID and result. If the requested figure is a conceptual interaction without actual screenshots, use comparison or architecture; an explicitly labeled schematic trajectory is also supported.

## Input

Start from `assets/templates/trajectory.json`. `data.steps` is a non-empty list of `{id,title,action,observation?,image?,illustration?,callouts?}`. Supply exactly one of `image` or `illustration` for each step. `data.columns` controls the grid (default up to 3). Real image paths resolve relative to the input spec directory (`_base_dir` is injected by the CLI). PNG/JPEG/WebP/SVG are supported and embedded in the output.

`illustration={label,lines}` draws a clearly marked mock interface, suitable only for templates and conceptual examples. The shipped asset is illustrative. Replace it with image for actual execution evidence.

Each callout is `{x,y,width,height,label?}` in normalized image coordinates [0,1]. For a source screenshot of W×H with pixel box (x,y,w,h), use x/W,y/H,w/W,h/H. The renderer scales the original image without cropping, so the normalized box remains attached to the correct feature. All boxes must lie wholly inside the image.

## Drawing method

1. Select meaningful actual steps and retain stable IDs. Pair each screenshot with its recorded action and observation; do not borrow a later screenshot for an earlier action.
2. Choose a fixed number of columns. For a long trace, wrap to a new row instead of squeezing the entire sequence onto a narrow page.
3. Preserve screenshot aspect ratios. Keep raw files unchanged; the SVG annotation layer holds highlights and labels separately.
4. Normalize callouts using the original screenshot dimensions. Explicitly identify the first relevant change instead of highlighting unrelated screen regions.
5. Align title bands, screenshot areas and action text within each row. Real image aspect ratio or long text can increase row height.

## QA

Check every step ID, image source, action and bbox against the original record. Missing files and invalid callouts fail. An illustrative interface never becomes evidence because it resembles the product. If the screenshot is too tall for readable printing, intentionally prepare a recorded crop and remap bbox coordinates before rendering.

Reference patterns: AgentDAM Fig2/4, ShieldAgent Fig7/14, TAI3 Fig12–15, SkillSafetyBench Fig5.
