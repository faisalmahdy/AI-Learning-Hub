# Asset briefs — batch 1 (ready for Higgsfield)

Run these the moment the Higgsfield MCP/CLI is connected. Every output gets a
manifest entry per [asset-pipeline.md](asset-pipeline.md) and is downsampled to the
size caps before committing.

## Shared style block (append to every image prompt)

> technical blueprint illustration, mission-control aesthetic, dark slate background
> (#10151c), a single signal-orange accent (#f97316), thin precise linework, subtle
> grid, isometric or orthographic viewpoint, high contrast, clean negative space,
> no text, no letters, no numbers, no watermarks, no people's faces

Negative prompt: `text, typography, numbers, watermark, logo, photorealistic faces, clutter, gradients of many colors`

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

## C. Hub hero loop — one video, 6–8s, 720p, ≤3MB

Filename `modules/evals-and-statistics/assets/hub-hero-loop.mp4` (mounts on the dashboard later), role `hub-hero`.

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
