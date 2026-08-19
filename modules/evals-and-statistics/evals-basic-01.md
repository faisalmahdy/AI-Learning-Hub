---
id: evals-basic-01
title: Your first output-quality eval — a mechanized rubric
topic: evals-and-statistics
level: basic
status: ready
time: 6-8h
summary: Build a 30-case, rubric-graded eval of an AI system's actual output quality — mechanized, re-runnable, and honest about judge reliability.
---

## Why this module

The 16-repo scan reached one verdict above all others: **everything in the portfolio measures plumbing, never product.** Hash chains are verified, retrieval ranks are benchmarked (150 adversarial cases!), side effects are graded — but nowhere is there a running script that answers "was the *output* any good?" The one real attempt (a 10-persona blind rubric harness that scored the second-brain at 6.28/10, with genuine contamination controls) lives as dated markdown, not as code anyone can re-run.

This module closes that gap at `basic` level: you reproduce the rubric-eval pattern you already invented, as a mechanized, committed script.

## Concepts

- **Golden set** — a fixed collection of inputs with known-good expectations, held out from anything that tuned the system. Your own `goldenCases.test.js` in tolongin-ai is already this pattern for extraction; here we apply it to open-ended output.

<svg viewBox="0 0 680 130" role="img" aria-label="The four properties of a golden set: held out, dated, never tuned on, refusals included">
  <g font-family="var(--mono)">
    <g>
      <rect x="0" y="0" width="160" height="130" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
      <g fill="none" stroke="var(--s1)" stroke-width="1.8"><rect x="62" y="30" width="36" height="26" rx="4"></rect><path d="M70 30 V24 a10 10 0 0 1 20 0 V30"></path><circle cx="80" cy="42" r="3" fill="var(--s1)" stroke="none"></circle></g>
      <text x="80" y="86" text-anchor="middle" font-size="12" font-weight="600" fill="var(--ink)">HELD OUT</text>
      <text x="80" y="104" text-anchor="middle" font-size="9.5" fill="var(--muted)">the system never</text>
      <text x="80" y="116" text-anchor="middle" font-size="9.5" fill="var(--muted)">saw these cases</text>
    </g>
    <g>
      <rect x="173" y="0" width="160" height="130" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
      <g fill="none" stroke="var(--s1)" stroke-width="1.8"><rect x="233" y="24" width="40" height="34" rx="4"></rect><path d="M233 34 H273 M243 20 V28 M263 20 V28"></path><path d="M241 46 L249 52 L265 40" stroke-width="2"></path></g>
      <text x="253" y="86" text-anchor="middle" font-size="12" font-weight="600" fill="var(--ink)">DATED</text>
      <text x="253" y="104" text-anchor="middle" font-size="9.5" fill="var(--muted)">committed before</text>
      <text x="253" y="116" text-anchor="middle" font-size="9.5" fill="var(--muted)">the first run</text>
    </g>
    <g>
      <rect x="346" y="0" width="160" height="130" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
      <g fill="none" stroke="var(--s1)" stroke-width="1.8"><path d="M406 26 V40 M406 48 V56 M418 26 V32 M418 40 V56 M430 26 V48 M430 56 V56" transform="translate(-8 0)"></path><circle cx="398" cy="44" r="3.5"></circle><circle cx="410" cy="36" r="3.5"></circle><circle cx="422" cy="52" r="3.5"></circle><line x1="384" y1="62" x2="436" y2="20" stroke-width="2.2"></line></g>
      <text x="426" y="86" text-anchor="middle" font-size="12" font-weight="600" fill="var(--ink)">NEVER TUNED ON</text>
      <text x="426" y="104" text-anchor="middle" font-size="9.5" fill="var(--muted)">tuning on it makes</text>
      <text x="426" y="116" text-anchor="middle" font-size="9.5" fill="var(--muted)">every score fiction</text>
    </g>
    <g>
      <rect x="519" y="0" width="160" height="130" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
      <g fill="none" stroke="var(--s1)" stroke-width="1.8"><path d="M599 22 L619 30 V44 C619 54 610 60 599 64 C588 60 579 54 579 44 V30 Z"></path><path d="M591 42 H607" stroke-width="2.2"></path></g>
      <text x="599" y="86" text-anchor="middle" font-size="12" font-weight="600" fill="var(--ink)">REFUSALS INCLUDED</text>
      <text x="599" y="104" text-anchor="middle" font-size="9.5" fill="var(--muted)">unanswerable cases</text>
      <text x="599" y="116" text-anchor="middle" font-size="9.5" fill="var(--muted)">test honesty, not recall</text>
    </g>
  </g>
</svg>
^ The four properties of a golden set. Your 10-persona harness enforced the one most setups skip: held-out (personas were forbidden from reading the benchmark YAMLs).
- **Rubric** — 3–5 named dimensions, each with a 1–5 scale and *written anchors* for what a 1, 3, and 5 look like. Unanchored scales drift; anchored scales transfer between raters.
- **Blind grading** — the grader must not see which system/version produced the output, and must not see other graders' scores. Your 10-persona harness already enforced this (personas were forbidden from reading benchmark YAMLs and prior verdicts).
- **LLM-as-judge, with suspicion** — a judge model can scale grading, but it has measurable biases. Your own reviewer benchmark documented this: a strong reviewer lifted results 71.6→89.7 while a weak reviewer *dropped* them 91.4→82.8. Rule: never trust a judge whose agreement with human labels you haven't measured.

<svg viewBox="0 0 680 268" role="img" aria-label="Slope chart: a strong reviewer raises scores from 71.6 to 89.7 while a weak reviewer lowers them from 91.4 to 82.8">
  <g font-family="var(--mono)">
    <g font-size="10.5">
      <rect x="170" y="6" width="10" height="10" rx="2" fill="var(--s1)"></rect>
      <text x="186" y="15" fill="var(--mid)">strong reviewer</text>
      <rect x="330" y="6" width="10" height="10" rx="2" fill="var(--s2)"></rect>
      <text x="346" y="15" fill="var(--mid)">weak reviewer</text>
    </g>
    <g stroke="var(--grid)"><line x1="150" y1="77.5" x2="530" y2="77.5"></line><line x1="150" y1="125" x2="530" y2="125"></line><line x1="150" y1="172.5" x2="530" y2="172.5"></line></g>
    <line x1="170" y1="164.9" x2="510" y2="78.9" stroke="var(--s1)" stroke-width="2.5"></line>
    <line x1="170" y1="70.9" x2="510" y2="111.7" stroke="var(--s2)" stroke-width="2.5"></line>
    <g stroke="var(--sunk)" stroke-width="2">
      <circle cx="170" cy="164.9" r="5" fill="var(--s1)"></circle>
      <circle cx="510" cy="78.9" r="5" fill="var(--s1)"></circle>
      <circle cx="170" cy="70.9" r="5" fill="var(--s2)"></circle>
      <circle cx="510" cy="111.7" r="5" fill="var(--s2)"></circle>
    </g>
    <g font-size="11" fill="var(--ink)">
      <text x="156" y="169" text-anchor="end">71.6</text>
      <text x="156" y="75" text-anchor="end">91.4</text>
      <text x="524" y="83" font-weight="600">89.7</text>
      <text x="524" y="116" font-weight="600">82.8</text>
    </g>
    <g font-size="11" fill="var(--mid)" text-anchor="middle">
      <text x="170" y="252">solo pass</text>
      <text x="510" y="252">after one reviewer pass</text>
    </g>
  </g>
</svg>
^ Benchmark score before and after a reviewer pass (agent/agent/review.py). The lesson: a reviewer is only worth its measured strength — a weak judge actively destroys good work.
- **Contamination** — if the eval questions (or answers) leaked into the system's build process, scores are fiction. Hold the set out; date it; never tune on it.

## Worked example

Source: faisalmahdy/second-brain-through-agents — `raw/topics/agent-systems/second-brain-evaluation/2026-07-04-10-persona-usage-harness-verdicts.md`

The existing harness ran 10 parallel persona subagents over a 5-dimension rubric (`retrieval_quality`, `packet_sufficiency`, `provenance_trust`, `governance_safety`, `handoff_ergonomics`), forbade them from reading the benchmark YAMLs, hint tables, and each other's verdicts, and produced a composite 6.28/10. A follow-up note reasoned about why three rounds scored 5.7 / ~7.3 / 6.3–6.5 — instrument changes, not system changes, explained the divergence. That is genuine measurement metacognition.

What it lacks (and what you add here): it is not re-runnable by a script, and it reports composites with no variance.

## Build

Target system: the **Query workflow of ai-engineer-learning** (209-concept wiki) — chosen because it has *never* been evaluated despite the repo naming eval-driven development as its own #1 pattern.

<svg viewBox="0 0 680 172" role="img" aria-label="The eval pipeline: 30 questions flow into the system, outputs are graded by a blind LLM judge and by hand on 10 cases, producing scores plus a judge-agreement number">
  <g font-family="var(--mono)" font-size="10.5" text-anchor="middle">
    <rect x="4" y="57" width="108" height="52" rx="6" fill="var(--panel)" stroke="var(--line)" stroke-width="1.3"></rect>
    <text x="58" y="79" fill="var(--ink)" font-weight="600">30 QUESTIONS</text>
    <text x="58" y="95" fill="var(--muted)" font-size="9">held-out · dated</text>
    <rect x="152" y="57" width="108" height="52" rx="6" fill="var(--panel)" stroke="var(--line)" stroke-width="1.3"></rect>
    <text x="206" y="79" fill="var(--ink)" font-weight="600">SYSTEM</text>
    <text x="206" y="95" fill="var(--muted)" font-size="9">wiki Query flow</text>
    <rect x="300" y="57" width="108" height="52" rx="6" fill="var(--panel)" stroke="var(--line)" stroke-width="1.3"></rect>
    <text x="354" y="79" fill="var(--ink)" font-weight="600">OUTPUTS</text>
    <text x="354" y="95" fill="var(--muted)" font-size="9">stored raw</text>
    <rect x="448" y="8" width="108" height="52" rx="6" fill="var(--acc-soft)" stroke="var(--acc)" stroke-width="1.5"></rect>
    <text x="502" y="30" fill="var(--acc-ink)" font-weight="600">LLM JUDGE</text>
    <text x="502" y="46" fill="var(--acc-ink)" font-size="9">blind · rubric</text>
    <rect x="448" y="106" width="108" height="52" rx="6" fill="var(--panel)" stroke="var(--line)" stroke-width="1.3"></rect>
    <text x="502" y="128" fill="var(--ink)" font-weight="600">HUMAN ×10</text>
    <text x="502" y="144" fill="var(--muted)" font-size="9">hand-graded</text>
    <rect x="596" y="57" width="80" height="52" rx="6" fill="var(--rail)"></rect>
    <text x="636" y="79" fill="var(--acc-hi)" font-weight="600">SCORES</text>
    <text x="636" y="95" fill="var(--faint)" font-size="9">+ agreement</text>
  </g>
  <g stroke="var(--faint)" stroke-width="1.5" fill="none">
    <path d="M112 83 H147"></path><path d="M260 83 H295"></path>
    <path d="M408 83 C428 83, 428 34, 443 34"></path>
    <path d="M408 83 C428 83, 428 132, 443 132"></path>
    <path d="M556 34 C576 34, 576 72, 591 76"></path>
    <path d="M556 132 C576 132, 576 94, 591 90"></path>
  </g>
  <g fill="var(--faint)"><path d="M147 83 l-6 -4 v8 Z"></path><path d="M295 83 l-6 -4 v8 Z"></path><path d="M443 34 l-6 -4 v8 Z"></path><path d="M443 132 l-6 -4 v8 Z"></path><path d="M591 76 l-7 -1 l3 7 Z"></path><path d="M591 90 l-7 1 l3 -7 Z"></path></g>
</svg>
^ The pipeline you build. The judge's scores mean nothing until the HUMAN ×10 leg reports agreement — that comparison is the module's whole point.

1. **Write 30 held-out questions** the wiki should answer (spread: 10 factual, 10 synthesis-across-pages, 10 "not answerable from the wiki" — the refusal cases). Write expected-answer notes for each. Date the file; commit it before running anything.
2. **Define the rubric** (suggest 4 dimensions: correctness, grounding/citation, completeness, honest-refusal) with written 1/3/5 anchors per dimension.
3. **Mechanize**: a script runs each question through the Query workflow, stores raw outputs, then grades each output against the rubric with an LLM judge (blind: judge sees output + rubric, not the system's identity or other scores).
4. **Calibrate the judge**: hand-grade 10 of the 30 yourself before looking at judge scores; report human–judge agreement per dimension.
5. **Report**: per-dimension mean across the 30 cases, plus the agreement number, in a dated results file.

Keep it stdlib-plus-one-SDK; no framework. The point is the discipline, not the tooling.

## Definition of done

- [ ] `questions.json` (30 cases, dated) committed before first run
- [ ] Rubric with written anchors committed
- [ ] One command re-runs the whole eval and regenerates the results file
- [ ] Human-vs-judge agreement reported on ≥10 hand-graded cases
- [ ] A 5-sentence written finding: what the numbers say, what they cannot say yet (variance comes in `evals-basic-02`)
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, no notes:

1. Name the four properties a golden set must have, and which one your 10-persona harness enforced that most eval setups skip.
2. Why must rubric scales have written anchors? What failure mode do unanchored scales produce?
3. Your own reviewer benchmark showed 71.6→89.7 and 91.4→82.8. What do those two numbers together prove about LLM-as-judge?
4. What is contamination, and what is the cheapest procedural defense against it?
5. Your eval reports correctness 4.1/5. Name three things this number cannot tell you (hint: they are the subject of the next module).

## External resources

- Hamel Husain, *Your AI Product Needs Evals* — https://hamel.dev/blog/posts/evals/ — my summary: the strongest practitioner argument that eval infrastructure, not prompts or models, is where AI products win; walks the unit-test → LLM-judge → human-review ladder this module climbs.
- Eugene Yan, *Patterns for Building LLM-based Systems* — https://eugeneyan.com/writing/llm-patterns/ — my summary: places evals first among seven patterns and catalogs the judge-bias literature (position bias, verbosity bias) that motivates step 4's calibration.
- Anthropic docs, evaluation guides — https://docs.claude.com — my summary: vendor guidance on building empirical evals and grading rubrics; useful for the judge-prompt shape, read critically per the hub's corpus-bias rule.
