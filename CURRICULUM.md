# AI-Learning-Hub — The Curriculum

> **Status: DRAFT v0.2** — built from a deep scan of all 16 AI-related repos + prior research artifacts.
> Round 1 decisions settled (see [BRAINSTORM.md](BRAINSTORM.md)): self-first · 8–12 h/week · public monorepo of topic modules · interactive web surface · recall-ledger gate.
> Evidence: [docs/repo-map.md](docs/repo-map.md) · [docs/skills-matrix.md](docs/skills-matrix.md)

## How this curriculum becomes the Hub

- A **track** below = a **topic folder** in the monorepo (e.g. `modules/evals-and-statistics/`). There are 7 tracks + 1 cross-cutting ops track.
- Each track's modules get a **level tag** — `basic` / `intermediate` / `advanced` — so the web surface can be browsed either by topic or by level.
- The Hub **absorbs** teaching material from the labs (de-personalized) and curates reliable **external resources** per topic (links + own summaries).
- Everything is rendered as an **interactive, visualized website** (tech decision pending in Round 2); markdown stays the source of truth, views are generated.

## Who this is for

Written for Faisal first, structured so it can later be taught to others. This is **not a generic AI syllabus**: every module anchors to a file you already wrote. The scan's verdict, in one line:

> *"What accelerates him is not new content but new constraint: point the existing eval machinery at output quality, attach numbers with uncertainty to every claim, finish the last mile of things already 80% built, and add the quantitative and post-training layers below prompting."*

Your portfolio already demonstrates **solid** skill in 20 of 35 assessed areas (agent harness engineering, memory architecture, MCP, orchestration with governance, security engineering, knowledge graphs, provenance discipline, instructional design…). The genuinely missing foundations are exactly four:

1. **Statistical rigor in evaluation** (variance, confidence intervals, pass^k, N>1)
2. **Output-quality evals as running code** (everything today grades plumbing, not product)
3. **Post-training practice** (SFT/DPO/GRPO exist only as wiki pages)
4. **Scientific computing** (zero notebooks/numpy/pandas across 16 repos, while rich in-house datasets sit unanalyzed)

Plus two meta-skills the scan surfaced as the real bottleneck:

- **Last-mile closure** — the 800-transcript ingest never ran, the recall gate has zero dated passes, SAKSI is absent, fleet metrics ship UNCOMPUTABLE, the SWE-bench harness sits unrun. The skill to learn is *finishing and verifying*, not starting.
- **Teaching transfer** — nothing you built has been run or rebuilt by a second person yet.

## The doctrine (imported from your own repos)

These rules come from `second-brain-through-agents` and are adopted hub-wide:

1. **Assets are not learning — dated recall is.** Every module ends with a from-memory boss fight, logged with a date in the recall ledger. (Your `recall_gate.py` machinery exists; this curriculum finally runs it.)
2. **Read → Build → Test → Artifact**, every week. No module is "done" without a committed, verifiable artifact.
3. **Measure or it didn't happen.** Every claim about an AI system gets a number, and every number gets an uncertainty. "It seems better" is banned vocabulary.
4. **Learn against your own artifacts, not toy exercises.** The best worked examples for your purposes are files you wrote.
5. **Preserve process provenance.** No more squashed single commits — the iteration path is the most instructive material an agent-built repo produces. Real PRs, real history (you already proved you can: second-brain has 330+ merged PRs).
6. **Definition of done is written before starting.** Your own kill-meter/pre-registered-bars pattern (operator, agent-command-center), applied to learning itself.

---

## Track 1 — Measure or it didn't happen: output evals + statistics

*The unblocking track. Placed first because without it, no other track can claim improvement.*

**Where you stand.** You own ~80% of the machinery: second-brain's 150-case adversarial retrieval benchmark (blind grading, no-oracle/no-hints gates), operator's clean-room 12-class tamper matrix, agent's side-effect graders and judge-bias-aware reviewer (documented: strong reviewer 71.6→89.7, weak reviewer 91.4→82.8), and a 10-persona blind rubric harness that scored second-brain at 6.28/10 with contamination controls. What's missing: it's never pointed at *generated work quality*, it lives as dated markdown instead of CI, and it reports point scores with no variance.

**Modules**

| # | Module | Anchor (yours) | Build | Definition of done |
|---|--------|----------------|-------|-------------------|
| 1.1 | Rubric evals for output quality | second-brain 10-persona harness verdicts; agent/docs/EVAL.md | 30 held-out questions against ai-engineer-learning's Query workflow, graded by a mechanized rubric | Score reproducible by re-running one script; committed to CI |
| 1.2 | Statistics for eval readers | oh-my-claudecode `benchmark/compare_results.py` (has *no* significance function — you add it) | Bootstrap confidence intervals + a paired significance test on any A/B eval | One conclusion that survives/doesn't survive the interval, stated in writing |
| 1.3 | Repeated trials & pass^k | ai-engineer-learning wiki (pass^k exists as prose only) | Re-run the canaan 6-model bake-off at N≥5 per model with 2 raters + agreement stats | The old N=1 verdict confirmed or overturned, with numbers |
| 1.4 | LLM-as-judge, calibrated | agent/agent/review.py; providers/cli_judge.py | Measure your judge against human labels on 30 cases; report bias & agreement | Judge agreement number known before the judge is trusted anywhere |
| 1.5 | **Capstone: run the unrun benchmark** | oh-my-claudecode `benchmark/` (complete SWE-bench A/B harness, predictions/ empty) | Actually run OMC vs vanilla on a SWE-bench slice, with intervals | `results/` non-empty; a defensible claim about whether OMC helps |

## Track 2 — The harness and its seams: agent engineering from first principles

*Your strongest territory, converted from private knowledge into teachable modules.*

**Where you stand.** Santara-Agent is already a textbook: a 384-LOC hand-written loop whose docstring enumerates its reliability guarantees, four ABCs (provider/tool/sandbox/engine), a 4.4K-LOC kernel with one import rule enforced by a failing test, a dependency-free MCP client with a fake server, ~3,200 tests that run offline via a deterministic Echo provider. Plus 9 completed harness deep-dives (Hermes, OpenClaw, NanoClaw, Claude Code, Codex, OpenCode, Cursor, T3 Code + comparison) with 60+ ranked lessons.

**Modules**

| # | Module | Anchor | Build | Definition of done |
|---|--------|--------|-------|-------------------|
| 2.1 | Build the loop yourself | agent/agent/core/loop.py | Add a fifth provider behind the ABC, suite stays green | CI green; provider passes the same contract tests |
| 2.2 | The seams: provider/tool/sandbox/engine ABCs | agent/agent/providers/base.py etc. | Break the kernel import rule on purpose; watch the test fail; write up why the rule exists | A short explainer another person can follow |
| 2.3 | MCP client & governed servers | agent/agent/mcp/*; second-brain nusa-memory-mcp | Write one governed MCP server (no raw write; proposal/review surface) | Server + fake-transport tests |
| 2.4 | Skills & self-improvement loops | agent/agent/skills/{reflect,ratchet}.py | Measure whether a learned skill improves task outcomes (currently unmeasured) | One before/after eval with Track-1 statistics |
| 2.5 | Live evals on a schedule | agent docs/LIVE_VALIDATION.md (manual runbook today) | Turn the runbook into a scheduled real-model eval that trends over time | A dashboard/ledger with ≥3 dated runs |
| 2.6 | Lessons-from-the-field seminar | Your 9 deep-dive studies | Distill the ×7/×6 convergence list into hub modules (hooks, sandboxing, plan mode, checkpoints, progressive disclosure) | One hub page per convergent primitive, each with a Santara implementation status |

## Track 3 — Context & retrieval, done properly and measured

**Where you stand.** Two hand-built retrieval systems (nusa-memory-mcp's 2,227-line tiered ranker with a 150-case benchmark; agent's relevance+recency+centrality blend), a strong opinion that compiled wikis beat RAG — and, per the critic, **dense retrieval already practiced** in fm-llm-wikipedia/omega (sentence-transformers → sqlite-vec, hybrid FTS5+vector in one SQL query, cross-encoder reranker with ablation flags). What's genuinely missing: **chunking** (whole pages embedded today) and **retrieval measurement** — the wiki-vs-RAG opinion is currently unearned because it was never tested.

**Modules**

| # | Module | Anchor | Build | Definition of done |
|---|--------|--------|-------|-------------------|
| 3.1 | Chunking strategies | fm-llm-wikipedia/omega (embeds whole pages) | Add section/semantic chunking; ablate chunk sizes | Retrieval quality per chunk size, measured |
| 3.2 | The head-to-head your opinion needs | ai-engineer-learning wiki + omega + nusa-memory-mcp | Compiled-wiki vs dense-RAG vs hybrid on one shared eval set, with cost and latency recorded | The wiki-vs-RAG claim becomes *earned* (or revised) with numbers |
| 3.3 | Finish the deferred legs | nusa-memory-mcp K1 (default-off) & K2.1 demotion | Wire them; extend the 150-case benchmark to cover them | Benchmark green including staleness slices |
| 3.4 | Context budgeting | anatomy episode 007 ("retrieved ≠ injected"); agent's compaction | Instrument dropped-context reasons + cache-hit telemetry across one week of real use | A written finding about what your context budget actually does |

## Track 4 — Orchestration with governance and instrumentation

**Where you stand.** Genuine executed practice: 8+8+8 subagent fan-outs with partitioned ownership and worker contracts (ai-engineer-learning), typed HandoffResult with MAST-informed restraint (agent), PR-gated agent output (agents-workspace-files), keyless proposer agents with hash-chained receipts (operator), a fleet wire protocol with read-time status derivation (agent-command-center). The conspicuous unfinished business: fleet metrics ship UNCOMPUTABLE, "earned autonomy" outcome linkage is designed-not-built, 5 of 8 agent folders are empty, and the council method is used but never validated against outcomes.

**Modules**

| # | Module | Anchor | Build | Definition of done |
|---|--------|--------|-------|-------------------|
| 4.1 | Make the kill-meter computable | agent-command-center eval/metrics.json (UNCOMPUTABLE) | Extend fleet-protocol-v1 so task_completion/steering_rate compute | Dashboard shows real numbers; kill-meter decides |
| 4.2 | Earned autonomy, data-driven | personal-command-center accuracy spine | Implement outcome linkage; gate one autonomy tier on measured accuracy | An autonomy promotion/demotion that actually fired from data |
| 4.3 | Agent PRs for real | agents-workspace-files GOVERNANCE.md | One agent produces real PRs through the pipeline for a week | ≥5 merged agent PRs with provenance blocks |
| 4.4 | Councils: do they help? | operator 25-pole council; fm-llm-wikipedia council/ (cross-vendor, 4 rounds) | A/B one real decision: council vs single strong pass, scored blind | First evidence (either way) on the council method |
| 4.5 | Staged autonomy patterns | fm-llm-wikipedia CLAUDE.md tiers; operator owner gate; PCC earned autonomy | Compare your three independent takes; unify into one hub pattern doc | A single staged-autonomy pattern page with tradeoffs |

## Track 5 — Below the prompt: internals, local serving, post-training

*The widest true capability gap — removes prompting as your only lever.*

**Where you stand.** Concept coverage is broad (anatomy episodes on attention/RoPE/tokenizers; wiki pages on KV cache, quantization, SFT/DPO/GRPO) but zero implementation: no tiny-rebuilds executed, no local serving config anywhere, no training script in 16 repos. Your own workloads are textbook fine-tuning candidates already sitting in-repo.

**Modules**

| # | Module | Anchor | Build | Definition of done |
|---|--------|--------|-------|-------------------|
| 5.1 | Tiny rebuilds, finally executed | anatomy episodes 001/002/011-013 (instructions already written) | Tokenizer, attention, RoPE, KV-cache rebuilds | Boss fights cleared with **dated recall passes** in the ledger |
| 5.2 | Local serving & quantization | (nothing exists — greenfield) | Serve a small model locally (llama.cpp/vLLM/Ollama-server); measure tokens/s & quality vs API | A latency/cost/quality table you measured yourself |
| 5.3 | First SFT | Your own corpora: 624 scored sources, tier assignments, FACT/PLAYBOOK/WISDOM registers, tolongin field extraction | Fine-tune a small model on one of these classification tasks | Beats (or measurably loses to) the prompted baseline on a Track-1 harness |
| 5.4 | Preference tuning | 5.3's task + preference pairs from your review data | DPO/GRPO pass; same eval | A written verdict: when is post-training worth it for you |

## Track 6 — AI for science & data: the quantitative spine

**Where you stand.** Absent — and blocking the "science" half of your goal. But you don't need toy datasets: you generated real ones. (The critic found one exception proving the point: the SWE-bench harness in your OMC fork pins pandas/numpy/matplotlib/seaborn — and was never run.)

**Modules**

| # | Module | Anchor dataset (yours) | Build | Definition of done |
|---|--------|------------------------|-------|-------------------|
| 6.1 | Notebooks + pandas fundamentals | 624 scored sources (ai-engineer-learning) | Quantify the corpus's vendor bias; visualize | A committed, reproducible notebook |
| 6.2 | Graph analysis | 1,522-edge concept graph | Analyze tier drift (110 T2 vs 6 T3); propose re-tiering from centrality | A data-backed re-tiering PR to ai-engineer-learning |
| 6.3 | Experiment design & uncertainty | 150-case retrieval benchmark results | Variance across runs; which differences are real? | Intervals on your own benchmark |
| 6.4 | Personal data science | Garmin series (personal-command-center) | Validate the future-self projection against actuals | Projection error quantified |
| 6.5 | **Capstone** | any of the above | One defensible empirical claim about your own systems, stated with uncertainty, reproducible from a committed notebook | The format a scientific collaborator would accept |
| 6.6 | Dicoding-derived modules | Dicoding priority plan (Tier S → C) | The 8 submission *tasks* (deep learning, MLOps, GenAI fine-tuning + RAG, Flutter ML, cloud deploy) are mined as raw material for hub modules — the submissions themselves are not tracked here | Each mined task becomes a leveled module with its own recall gate |
| 6.7 | External scientific domain (parallel) | greenfield — chosen domain TBD in grill session | Alongside own-systems work, develop one external scientific domain (e.g. bio/health data via Garmin experience, or physics/simulation) | One external-domain analysis meeting the 6.5 standard |

## Track 7 — Teaching, portability, and the compounding loop

**Where you stand.** You've already built the pedagogy (12-week curriculum shape, T0-T3 tiers, anatomy templates, NotebookLM packs) — but everything is single-author, path-hardcoded (`/Users/mac/wiki/...`), partly undocumented, with doc/code drift (README says 127 concepts; graph says 209). Matt Pocock's skills repo (grill-me/grilling, teach, handoff, writing-for-agents) is direct prior art for the missing assessment/teaching lane.

**Modules**

| # | Module | Anchor | Build | Definition of done |
|---|--------|--------|-------|-------------------|
| 7.1 | Extract the reusable modules | CLAUDE.md contracts, orchestration.md, concept-writer-contract.md, T0-T3 framework | De-personalize paths & content; publish as hub modules | A stranger could run them |
| 7.2 | Docs generated from code | ai-engineer-learning README drift (127 vs 209) | Generate counts/claims from graph.json in CI | Drift becomes impossible |
| 7.3 | Provenance-preserving agent workflow | second-brain's 330-PR history (the good example) | Adopt commit/PR conventions hub-wide; stop squashing | Next 3 projects have real history |
| 7.4 | Assessment lane | mattpocock/skills teach.md + grilling.md; your recall_gate.py | Wire grill-style assessment into hub modules | Every module has a boss fight |
| 7.5 | **Capstone: teach one human** | One extracted module | One other person completes it; measure whether they can rebuild | The Hub's first external learner artifact |

## Cross-cutting track — Ship it and keep it running (deployment & ops)

*Elevated by the critic: only `agent/` has a deploy story (systemd units, Docker) and only tolongin-ai has an edge config; no inference serving exists anywhere. Nothing gets you from "run these in two terminals" to something that runs while you sleep.*

- Containerize + supervise one fleet member end-to-end (anchor: agent/deploy/*.service).
- Stand up one inference server (ties into 5.2) with health checks and a rollback story.
- Secrets hygiene pass: rotate the committed operator token; make key_audit catch it; timing-safe compares. (Verified real: `OPERATOR_GATEWAY_TOKEN` committed at integrations/hermes/README.md:19.)
- CI everywhere: 12 of 18 workspace dirs have zero workflows; ai-engineer-learning ships a `--check` gate nothing runs — wire it.

---

## Sequencing (8–12 h/week, settled in Round 1; ordering still open in Round 2)

**Phase 1 (weeks 1–4): Measurement + closure + hub skeleton.** Track 1 modules 1.1–1.2 at `basic` level, quick last-mile wins (wire the `--check` gate, fix README drift, rotate the committed token), start the recall ledger with dated passes, and stand up the interactive web surface with the first topic rendered.
**Phase 2 (weeks 5–8): Retrieval head-to-head + orchestration instrumentation.** Track 3.1–3.2, Track 4.1–4.2, continue Track 1 at `intermediate`.
**Phase 3 (weeks 9–12): Below the prompt + quantitative spine.** Track 5.1–5.3, Track 6.1–6.3 (own-systems data science), SWE-bench capstone.
**Phase 4 (weeks 13+): Science capstones + teaching.** Track 6.5 + 6.7 (external scientific domain), Track 7, first external learner.

Model-usage doctrine for the Hub itself (your stated preference, now written down): **Fable 5 plans, evaluates, and monitors; task-optimized workers (Opus/Sonnet/Haiku, or Codex/Gemini via councils) execute.** Every phase runs as: plan (Fable) → fan-out build (workers) → adversarial verify (mixed) → dated artifact.
