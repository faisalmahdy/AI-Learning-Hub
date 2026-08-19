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

### Round 2 — asked 2026-08-19 (answers pending)

- **Q9 Web surface tech** — how the interactive hub is served (static site generated from the monorepo vs app framework)?
- **Q10 Module taxonomy** — the top-level topic list for the monorepo modules?
- **Q11 Topics × levels** — confirm: modules organized by topic, each tagged basic/intermediate/advanced, web UI navigable both ways?
- **Q12 Absorption policy** — what may be absorbed into a public monorepo (own private-repo material? external resources: links+summaries vs copies)?
- **Q13 First module** — which module gets built first as the template for all others?

### Settled (Round 1 — 2026-08-19)

- **Q1 Audience**: Self-first. The Hub must be readable **via web, interactive and visualized**, progressing basic → intermediate → advanced.
- **Q2 Time budget**: 8–12 h/week.
- **Q3 First track**: (clarification requested — re-asked as Round 2 Q11 after explaining the track structure.)
- **Q4 Hub shape**: **Monorepo absorb** — the Hub absorbs the teaching material from the labs AND curates reliable, structured outside resources; content organized as modules per topic.
- **Q5 Visibility & language**: Public, English by default; Indonesian is the next development.
- **Q6 Dicoding**: Submissions NOT folded in as tracked milestones — but their *tasks* are mined as raw material for learning modules.
- **Q7 Definition of done**: Dated recall pass in the ledger adopted hub-wide.
- **Q8 Science scope**: Start with data science on own systems, AND develop an external scientific domain in parallel (not a deferred elective).
