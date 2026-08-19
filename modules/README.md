# Module format

Every learning module is one markdown file at `modules/<topic-id>/<module-id>.md`. Topic ids live in [`topics.json`](topics.json). The site generator (`tools/build_site.py`) renders all modules into the interactive explorer; `--check` fails the build on any format violation.

## Frontmatter (required)

```
---
id: evals-basic-01
title: Your first output-quality eval — a mechanized rubric
topic: evals-and-statistics
level: basic
status: ready
time: 6-8h
summary: One-sentence card text for the explorer.
---
```

- `id` — unique across the hub, `<topic-shortname>-<level>-<nn>`
- `level` — `basic` | `intermediate` | `advanced`
  - **basic**: understand + reproduce a worked example from the labs
  - **intermediate**: build a variation yourself with a measured result
  - **advanced**: original work meeting the "defensible claim with uncertainty" standard
- `status` — `draft` | `ready`
- `time` — honest estimate at 8–12 h/week pace

## Body sections (in this order)

1. `## Why this module` — what gap it closes, with evidence
2. `## Concepts` — the ideas, tersely, with sources
3. `## Worked example` — anchored to a real file from the labs (de-personalized copy or excerpt + source line)
4. `## Build` — what you make; concrete steps
5. `## Definition of done` — checklist written BEFORE starting
6. `## Boss fight` — from-memory recall questions; passing gets a dated entry in [`../ledger/recall-ledger.json`](../ledger/recall-ledger.json)
7. `## External resources` — links + own summaries only, never copies

## Absorption rules (grill Round 2, Q12)

- Own material: de-personalized copies (paths, names, personal content scrubbed), each with a source line (`Source: faisalmahdy/<repo> — <path>`).
- External material: link + own summary/notes only. Never full copies.

## Done means done

A module is complete only when (a) its Definition of done artifact is committed and runnable, and (b) a dated recall pass exists in the ledger. No exceptions — this gate exists because the portfolio scan found the recall machinery built but never run.
