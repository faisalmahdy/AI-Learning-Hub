# Asset briefs — batch 1 (ready for Higgsfield)

**Direction: simple and bright** (decided 2026-08-19) — matching the site's default light theme, not the dark nav rail.

**Generate over MCP with `recraft_v4_1` in a vector mode.** Recraft is chosen over the free-lane models for two concrete reasons: it takes an explicit `colors` + `background_color` palette, so the site tokens are pinned rather than described; and `model_type: "vector"` / `"utility_vector"` return **real `.svg` files** (verified), which are kilobytes instead of hundreds of KB, stay crisp at any size, and — because an SVG is text — can be recolored to `var(--acc)` / `var(--ink)` so one asset serves light *and* dark mode. `"utility_vector"` with `background_color: null` also yields no background, so artwork sits on the card colour.

Cost is 1.25 credits per image; the whole set is well under 20 credits.

Every output gets a manifest entry per [asset-pipeline.md](asset-pipeline.md). Retrieval into the repo is still the manual/allowlist step described there — MCP generates, a browser (or an allowlisted CDN host) delivers.

Free-lane alternatives, if credits ever need conserving: Seedream 4.5 (4K), Flux.2 Pro (1K), Nano Banana, Kling O1 Image, GPT Image — all 365-day unlimited **on web only**, and none of them take a palette parameter, so the hex values must go in the prompt text and be checked.

## Shared style block (append to every image prompt)

> minimal flat vector illustration, bright and airy, generous white space,
> editorial minimalism, simple geometric shapes with thin clean outlines,
> one single orange accent (hex #f97316) with charcoal (hex #1a2028) linework,
> flat with no heavy shading, calm and uncluttered,
> no text, no letters, no numbers, no watermarks, no people's faces

Negative prompt: `text, typography, numbers, watermark, logo, photorealistic faces, clutter, dark background, rainbow colors, multiple accent colors, heavy gradients`

Recraft params for every image: `model_type: "vector"` (white ground) or `"utility_vector"` (transparent), `colors: ["#f97316", "#1a2028", "#9aa8b8"]`, `background_color: "#ffffff"` or `null`, `aspect_ratio: "16:9"`, `resolution: "1k"`.

## A. Topic hero images — 9 images, 16:9, 1600×900

One per topic folder, filename `hero.png`, manifest role `topic-hero`. Subject line per topic (each + shared style block):

| Topic | Subject |
|---|---|
| evals-and-statistics | a precision balance scale weighing glowing data shards, calipers and measurement marks around it |
| agent-harness | an exploded-view mechanical assembly of a loop engine: rotor, valves, and one orange drive belt forming a cycle |
| context-and-retrieval | a vast card-index archive with one drawer open, light beams pulling three cards toward a lens |
| orchestration-and-governance | a conductor's podium over a grid of small identical machines, one raised approval gate in orange |
| below-the-prompt | a cutaway of a layered engine block descending underground: surface console above, glowing token gears below |
| ai-for-science-and-data | a laboratory bench with beakers feeding a scatter of points into an ascending curve of light |
| teaching-and-portability | a relay handoff: one robotic hand passing a glowing blueprint cube to an open human hand |
| generative-media | a film clapperboard dissolving into a spray of pixels and frames on a light table |
| ship-and-operate | a container ship made of server racks leaving a dry dock, one orange running light |

## B. Module hero — evals-basic-01, 16:9, 1600×900

Filename `modules/evals-and-statistics/assets/evals-basic-01-hero.png`, role `module-hero`, then add `hero: evals-basic-01-hero.png` to the module frontmatter.

> Subject: a magnifying loupe held over a strip of thirty film frames, one frame
> lifted and glowing under the lens, a rubber stamp waiting beside it
> (+ shared style block)

## C. Hub hero loop — one video, 5–8s, 720p, ≤3MB

Filename `modules/evals-and-statistics/assets/hub-hero-loop.mp4` (mounts on the dashboard later), role `hub-hero`. Generate with **sound off** — the site plays it muted. Free on the web app via Kling 3.0 (720p/5s) or Seedance 2.0; over MCP this single clip would cost 39 credits.

> Subject: slow camera drift across a dark mission-control wall of thin orange
> telemetry lines that pulse once per second; a single radar sweep completes one
> rotation; seamless loop; no text, no numbers
> (+ shared style block, motion: subtle, loopable)

## D. Boss-fight stamp — 1:1, 800×800, transparent background

Filename `modules/evals-and-statistics/assets/boss-stamp.png`, role `ui-accent` — the celebratory image shown when a recall pass is logged.

> Subject: an engraved medal/stamp of a five-pointed star inside a gear ring,
> single orange ink on transparency, woodcut linework
> (+ shared style block)

## Acceptance checklist (every asset)

- [ ] No text/numbers baked in
- [ ] Reads correctly at card size (240px wide) — check before committing
- [ ] Under the size cap (images ≤300KB, video ≤3MB)
- [ ] Manifest entry with exact prompt, model id, date, sha256
- [ ] Looks like the same system as the site (slate + orange, thin linework)
