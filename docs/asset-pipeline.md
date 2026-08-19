# Asset pipeline — generated images & video

How AI-generated media (Higgsfield or any other generator) enters the hub. The design borrows the manifest-first provenance pattern from `ai-studio-genblaze-hackathon` (`worker/genblaze_pipeline.py`).

## Where assets live

```
modules/<topic-id>/assets/   ← source of truth, committed
site/assets/<topic-id>/      ← copied by tools/build_site.py at build time (never edit)
data/assets-manifest.json    ← provenance ledger, one entry per generated asset
```

## How a module uses an asset

```markdown
![alt text](eval-pipeline-hero.png "optional caption")
![explainer loop](pipeline-loop.mp4 "6s loop — the eval pipeline in motion")
```

- A bare filename resolves to that module's topic assets folder.
- `.mp4`/`.webm` render as muted, looping, controllable `<video>`.
- Frontmatter `hero: <filename>` puts a thumbnail on the module's card.
- Inline `<svg>` blocks pass through as theme-aware figures (they may use the site's CSS variables); a `^ caption` line after any figure becomes its caption.

## Provenance rule (non-negotiable)

Every generated asset gets a manifest entry **in the same commit**:

```json
{
  "file": "modules/evals-and-statistics/assets/eval-pipeline-hero.png",
  "kind": "image",
  "role": "module-hero",
  "prompt": "…the exact prompt used…",
  "model": "higgsfield/<model-id>",
  "date": "YYYY-MM-DD",
  "sha256": "…",
  "approved": true
}
```

`tools/build_site.py --check` fails on a manifest entry whose file is missing or whose required fields (file, kind, prompt, model, date) are empty.

## Honesty rules for generated media

1. Assets **illustrate**; they never carry data. Numbers, charts, and progress live in code-drawn SVG bound to real repo data — a generated image must never contain a statistic.
2. No text baked into generated images (it drifts from the truth and can't be themed); typography belongs to the page.
3. One visual language: the briefs in [asset-briefs.md](asset-briefs.md) carry the shared style block so all assets look like one system (Mission Control: dark slate, signal orange, technical-blueprint mood).
4. Videos: short loops (≤10s), muted by default, always with a text alternative in the module body.

## Size discipline

GitHub Pages serves the repo directly: keep images ≤300KB (1600px max edge, prefer WebP/optimized PNG) and loops ≤3MB (720p, H.264). Downsample before committing.

## Connecting Higgsfield (decided 2026-08-19)

Three lanes exist; the first is the chosen one:

1. **Hosted MCP (chosen for interactive generation).** Official server at `https://mcp.higgsfield.ai` (30+ models, images to 4K, video to 15s, OAuth — no API key). One-time setup, done by the owner in a browser: claude.ai → Settings → Connectors → Add custom connector → `https://mcp.higgsfield.ai` → sign in → enable for Claude Code sessions. Agent sessions then call the `mcp__higgsfield__*` tools directly.
2. **Direct API (reserved for CI).** Bearer token from docs.higgsfield.ai stored as the `HIGGSFIELD_API_KEY` environment secret — never committed. Submit-then-poll, same pattern as `muapi.js` in the open-generative-ai fork. `tools/generate_assets.py` gets written only after observing one real request/response (never a guessed schema).
3. **CLI (laptop only).** `npm i -g @higgsfield/cli` + `higgsfield auth login` — browser login, so it does not work inside headless cloud containers.

First batch to generate once connected: see [asset-briefs.md](asset-briefs.md).
