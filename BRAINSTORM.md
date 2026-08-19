# Brainstorm & Open Decisions

> Working document. The **Open decisions** section is the design tree for the grill-me session;
> each round of answers reshapes it. Decided items move to **Settled**.

## The vision (as currently understood — to be stress-tested)

Maximize the potential of AI for **general purpose, science & development, coding, and beyond** — first for Faisal, then for others. The Hub is the place where that development becomes visible, measurable, and teachable.

## What the Hub is (decided in Round 1)

**A monorepo of learning modules, readable as an interactive, visualized website.** The Hub absorbs the teaching-worthy material from the labs (anatomy episodes, contracts, worked examples — de-personalized), curates reliable external resources per topic, and organizes everything as **modules per topic, each leveled basic → intermediate → advanced**, with a recall ledger gating "done." Public, English-first, Indonesian later.

Rejected alternatives (for the record): ledger+links-only hub (kept content in the labs but failed the "one interactive place to read" requirement); published-course-first (contradicts the evidence that nothing has been validated on a second learner yet).

Drift risk accepted knowingly: absorbing content means lab copies and hub copies can diverge — mitigated by the "docs generated from data" doctrine and by making the hub copy canonical for *teaching* content once absorbed.

## Ideas parked for later rounds

- **A public "learning in the open" cadence**: weekly artifact + a short write-up, in the spirit of your deep-dive studies but smaller.
- **Indonesian-language track**: tolongin-ai and Predator Takjil show your applied work is locally grounded; an Indonesian AI-engineering track would have little competition. (Dicoding already validates demand for Indonesian ML education.)
- **The Hub as an agent-operated repo**: agents maintain the ledger/matrix via PR-gated writes — dogfooding Track 4 governance.
- **Convergence encyclopedia**: your ×7/×6 primitives list (hooks, sandboxing, MCP, plan mode, checkpoints, progressive disclosure…) as a maintained public reference — nobody else has this dataset.
- **"Finish-it Fridays"**: a standing slot dedicated purely to last-mile closure of one 80%-built thing, since that's the diagnosed failure mode.
- **Cross-vendor councils as bias control** (from fm-llm-wikipedia): make Claude+Gemini+Codex agreement a standard verification step for Hub claims, countering the measured Anthropic-corpus bias.
- **Source-credibility grading** as a first-class Hub skill: you already implemented it 3 times (S/A/B/C tiers, [n/N] triangulation, source_tier+confidence) — name it, teach it.
- **operator-knowledge**: currently an empty stub occupying a repo slot — either fill it from operator's six missing binding documents or archive it.

## Risks the scan surfaced (design around these)

- **Last-mile abandonment** — every phase must end with something *run*, not something *written*.
- **Anthropic/agent-centric corpus bias** — deliberately schedule non-Anthropic stacks, non-agent AI (classical ML, science tooling).
- **Doc/code drift** — generate every count/claim in Hub docs from data.
- **Building pedagogy instead of doing exercises** — the compulsive-curriculum reflex is real (4 repos contain syllabi); the Hub must cap "syllabus work" and force "module work."

---

## Open decisions (grill-me design tree)

### Frontier: EMPTY as of Round 2 (2026-08-19)

Shared understanding reached; building started per the Q13 directive. Remaining deferred-by-choice items (not blockers): choice of external scientific domain (Track 6.7), Indonesian-track timing, module-by-module cuts for Phases 2–4.

### Settled (Round 2 — 2026-08-19)

- **Q9 Web surface**: GitHub Pages + a generated, self-contained HTML explorer. Markdown is the source of truth; views are generated (stdlib-only `tools/build_site.py`).
- **Q10 Taxonomy**: the 8 tracks + **generative-media** as a 9th topic folder (seeded from ai-studio pipeline/provenance + arena-ai verification work).
- **Q11 Levels**: **basic** = understand + reproduce a worked example from the labs; **intermediate** = build a variation with a measured result; **advanced** = original work meeting the "defensible claim with uncertainty" standard. Boss-fight recall required at every level.
- **Q12 Absorption policy**: own material absorbed as de-personalized copies (paths/names/personal content scrubbed); external resources as **link + own summary only**, never full copies; every absorbed page carries a source line.
- **Q13 First module**: *Evals & Statistics — basic*, built together with the explorer skeleton.

### Settled (Round 1 — 2026-08-19)

- **Q1 Audience**: Self-first. The Hub must be readable **via web, interactive and visualized**, progressing basic → intermediate → advanced.
- **Q2 Time budget**: 8–12 h/week.
- **Q3 First track**: (clarification requested — re-asked as Round 2 Q11 after explaining the track structure.)
- **Q4 Hub shape**: **Monorepo absorb** — the Hub absorbs the teaching material from the labs AND curates reliable, structured outside resources; content organized as modules per topic.
- **Q5 Visibility & language**: Public, English by default; Indonesian is the next development.
- **Q6 Dicoding**: Submissions NOT folded in as tracked milestones — but their *tasks* are mined as raw material for learning modules.
- **Q7 Definition of done**: Dated recall pass in the ledger adopted hub-wide.
- **Q8 Science scope**: Start with data science on own systems, AND develop an external scientific domain in parallel (not a deferred elective).
