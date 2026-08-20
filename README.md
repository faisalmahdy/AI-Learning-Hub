<img src="brand/logo.svg" width="72" alt="AI-Learning-Hub mark — a precise square outline struck by a tilted orange square whose corner breaks the frame">

# AI-Learning-Hub

**A personal (soon shareable) curriculum for maximizing the potential of AI — for general purpose use, science & development, coding, and beyond — grounded in evidence from 16 of my own repositories.**

> Status: **DRAFT v0.2** — Round 1 of the grill-me session settled the shape: a **public, English-first monorepo of leveled learning modules (basic → intermediate → advanced), readable as an interactive website**, absorbing teaching material from my labs plus curated external resources, gated by a dated-recall ledger. Round 2 decisions are pending in [BRAINSTORM.md](BRAINSTORM.md).

## Contents

| File | What it is |
|------|-----------|
| [CURRICULUM.md](CURRICULUM.md) | The curriculum: 7 tracks + 1 cross-cutting ops track, every module anchored to a file I already wrote, each with a definition of done |
| [BRAINSTORM.md](BRAINSTORM.md) | Vision, candidate shapes for the Hub, parked ideas, risks, and the open-decision tree |
| [docs/skills-matrix.md](docs/skills-matrix.md) | 35 skills assessed solid/developing/touched/missing, with file-level evidence |
| [docs/repo-map.md](docs/repo-map.md) | Per-repo profiles of the 16 source repositories (the evidence base) |

## How this was built

- **2026-08-19**: 16 AI-related repos scanned by an 18-agent workflow (one profiler per repo — Opus for the deep repos, Sonnet for the rest — then a cross-repo synthesis and an adversarial completeness critic that corrected four headline claims). Prior research artifacts (the 9 agent-harness deep-dive studies, the Santara evaluations, the Coding Language Anatomy curriculum, the Dicoding plan) were read alongside.
- Orchestration doctrine: a planner/evaluator model plans, monitors, and verifies; task-optimized worker models execute in parallel.

## The doctrine

1. Assets are not learning — **dated recall** is.
2. Read → Build → Test → **Artifact**, every week.
3. **Measure or it didn't happen** — every claim gets a number, every number gets an uncertainty.
4. Learn against **your own artifacts**, not toy exercises.
5. **Preserve process provenance** — real PRs, no squashed history.
6. Definition of done is written **before** starting.
