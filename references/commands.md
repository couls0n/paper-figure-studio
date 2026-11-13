# Standalone command and agent-response protocol

Use an absolute path to `scripts/figureforge.mjs`. In the examples, `SKILL` denotes this installed skill directory and `PROJECT` denotes a user-chosen output directory; substitute their actual paths. No command depends on the original repository or a globally installed Node package. No API credentials are needed.

## Job lifecycle

`start PROJECT` launches the self-contained runtime; running it again attaches to that project's existing runtime. `run PROJECT ACTION --input OPTIONS.json` returns a job ID immediately. `status PROJECT` reports its state and the path to its full job JSON. `requests PROJECT` lists pending inference tasks. Read the completed job file for results; results are not always printed in the compact status output.

```bash
node "$SKILL/scripts/figureforge.mjs" start "$PROJECT"
node "$SKILL/scripts/figureforge.mjs" run "$PROJECT" configure --input /absolute/path/config.json
node "$SKILL/scripts/figureforge.mjs" status "$PROJECT"
```

Only one workflow job runs in a project at a time. An active job may await an agent reply or revision review; don't launch a second generation over it. Poll while doing useful work and wait briefly between unchanged statuses. Never abandon a running generation just because one tool call yielded.

## Operations

| Action | JSON options | Result |
|---|---|---|
| `configure` | `paper`, `target`, `targetDescription`, `mode`, `pass`, `ratio`, `resolution`, `language`, `font`, `contentMode`, `contentQuery` | Current configuration/state |
| `search` | `query`, optional `pattern`, `venue`, `year`, `tier`, `limit` | Ranked original catalog records, scores and absolute `imagePath` |
| `select` | `ids: [catalog or uploaded reference IDs]` | Selected references; max 10 |
| `upload-references` | `files: [absolute image paths]` | Validated uploads added to selection |
| `parse-pdf` | `file: absolute PDF path`, optional `contentMode: "intent"`, `contentQuery` | Original PDF parsing route and drawing brief |
| `analyze` | `{}` | Original reference analysis; useful for inspecting the analysis alone |
| `generate` | `{}` | Complete configured generation, including its own analysis in two-pass mode and automatic Step 4 for bitmaps |
| `import-svg` | `file: absolute SVG path` | Original SVG version validation and editable scene parsing |
| `import-bitmap` | `file: absolute bitmap path` | Original bitmap-upload path; follow with `reconstruct` when needed |
| `reconstruct` | `{}` | Original single whole-image recognition and scene conversion |
| `audit` | `{}` | Original geometry/reconstruction reports |
| `revise` | `prompt`, optional `versionId`, `attachments: [paths]`, `revisionMode: "auto" / "local" / "reflow"` | Original revision flow, including its review gate |
| `activate-version` | optional `versionId` (default newest) | Select requested version for export; bitmap rebuild follows original behavior if needed |
| `export` | `formats: ["svg","png","pptx","drawio","vsdx"]`, optional PNG `scale` (default 2) | Output paths and native scene JSON |

Supported `target`: `overview`, `architecture`, `pipeline`, `results`, `custom`. Supported `mode`: `svg`, `image`; `pass`: `two`, `direct`; ratios: `16:9`, `3:2`, `4:3`, `1:1`; resolutions: `1K`, `2K`, `4K`. Original provider-specific dimensional restrictions still apply. A `search` query updates the paper field, as in the original UI; set the final complete paper/brief with `configure` after reference selection.

Example configuration:

```json
{
  "paper": "The user's concrete drawing brief, with factual entities and relationships.",
  "target": "pipeline",
  "mode": "svg",
  "pass": "two",
  "ratio": "16:9",
  "language": "zh"
}
```

Calling `analyze` and then `generate` in two-pass mode performs analysis twice, matching the original generation button. Normally call `generate` directly and answer its first analysis request. Do not silently switch to direct mode to save that call: direct mode has different prompt construction.

## Answer an inference request

```bash
node "$SKILL/scripts/figureforge.mjs" requests "$PROJECT"
```

Each entry provides a request ID, its kind (`text` or `image`), `prompt.md`, ordered attachments, original requested model/effort, and a directory containing:

- `request.json`: original endpoint, content type, and full logical payload.
- `wire-body.bin`: exact HTTP body, including original multipart data when used.
- `readable-request.json`: same text/structure with base64 replaced by numbered local-file references.
- `attachments.json`: ordered files, MIME types, sizes, and SHA-256 hashes.
- `status.json`: pending/answered/failed/cancelled status.
- After response: `response.txt` (text), `response.json` and actual execution metadata when provided.

Read the full prompt and all images; do not answer from only filenames or thumbnails. Create the requested JSON/SVG/text as a project file, then:

```bash
node "$SKILL/scripts/figureforge.mjs" respond "$PROJECT" REQUEST_ID --file /absolute/path/response.txt
node "$SKILL/scripts/figureforge.mjs" respond "$PROJECT" REQUEST_ID --file /absolute/path/generated.png --image
```

Optional `--actual-model NAME` and `--actual-effort LEVEL` record verified host execution metadata. Omit them when unknown. They do not change the enclosing agent's model or reasoning setting. For an actual failure:

```bash
node "$SKILL/scripts/figureforge.mjs" fail "$PROJECT" REQUEST_ID --message 'Concrete failure reason'
```

The runtime wraps replies in the response protocol expected by the unchanged workflow. It supports OpenAI-compatible text/image/multipart profiles, Anthropic text responses, and native Gemini text/image profiles. It preserves request parameters and image bytes. Provider names and model IDs identify a request-building profile; the active host agent/tool supplies the response, and the network request is never sent to that provider.

Default SVG profile: original local Codex branch, transport label `agent-vision`, requested `max`. Default bitmap profile: original OpenAI-compatible `gpt-image-2` request construction. To select another existing profile, `configure` also accepts `provider`, `visionModel`, and `imageModel`, e.g. `provider: "infistar", imageModel: "gemini-3.1-flash-image-preview"`. These select original request/prompt/revision behavior; they are not claims that the host tool is that model. Choose a profile consistent with the available tool's capabilities and report the actual model separately. Model traffic is intercepted into the local queue; other external networking is blocked.

## Review, export, and shutdown

```bash
node "$SKILL/scripts/figureforge.mjs" review "$PROJECT"
node "$SKILL/scripts/figureforge.mjs" accept-review "$PROJECT"
# Or, when the user rejects the result:
node "$SKILL/scripts/figureforge.mjs" reject-review "$PROJECT"
node "$SKILL/scripts/figureforge.mjs" run "$PROJECT" activate-version
node "$SKILL/scripts/figureforge.mjs" export "$PROJECT" --formats svg,png,pptx,drawio,vsdx
node "$SKILL/scripts/figureforge.mjs" stop "$PROJECT"
```

`review` writes the original/candidate/reference files and returns their paths. Preserve the user confirmation step; do not auto-accept every candidate. Accepted revisions are new versions. Activate the version to be exported explicitly, because accepting a candidate does not replace the currently active original in FigureForge.

The original export filename marks unverified bitmap reconstruction as `draft-unverified`; retain this status when delivering. Every export has a job-specific filename, so previous outputs remain available. `stop --force` cancels active work; use it only for a requested stop or failed runtime/test cleanup. Restart restores completed snapshots, not live HTTP requests.

## Project layout

`inputs/` holds copied source files. `requests/` archives exact model calls and responses. `jobs/` holds operation results. `outputs/` holds previews, native files, review candidates, and scene JSON. `.figureforge/state.json` holds the restorable project, including reference uploads and original version records. `.figureforge/connection.json` is temporary local runtime metadata. The package remains unchanged during drawing.
