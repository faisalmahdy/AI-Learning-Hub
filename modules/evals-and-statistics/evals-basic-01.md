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
- **Rubric** — 3–5 named dimensions, each with a 1–5 scale and *written anchors* for what a 1, 3, and 5 look like. Unanchored scales drift; anchored scales transfer between raters.
- **Blind grading** — the grader must not see which system/version produced the output, and must not see other graders' scores. Your 10-persona harness already enforced this (personas were forbidden from reading benchmark YAMLs and prior verdicts).
- **LLM-as-judge, with suspicion** — a judge model can scale grading, but it has measurable biases. Your own reviewer benchmark documented this: a strong reviewer lifted results 71.6→89.7 while a weak reviewer *dropped* them 91.4→82.8. Rule: never trust a judge whose agreement with human labels you haven't measured.
- **Contamination** — if the eval questions (or answers) leaked into the system's build process, scores are fiction. Hold the set out; date it; never tune on it.

## Worked example

Source: faisalmahdy/second-brain-through-agents — `raw/topics/agent-systems/second-brain-evaluation/2026-07-04-10-persona-usage-harness-verdicts.md`

The existing harness ran 10 parallel persona subagents over a 5-dimension rubric (`retrieval_quality`, `packet_sufficiency`, `provenance_trust`, `governance_safety`, `handoff_ergonomics`), forbade them from reading the benchmark YAMLs, hint tables, and each other's verdicts, and produced a composite 6.28/10. A follow-up note reasoned about why three rounds scored 5.7 / ~7.3 / 6.3–6.5 — instrument changes, not system changes, explained the divergence. That is genuine measurement metacognition.

What it lacks (and what you add here): it is not re-runnable by a script, and it reports composites with no variance.

## Build

Target system: the **Query workflow of ai-engineer-learning** (209-concept wiki) — chosen because it has *never* been evaluated despite the repo naming eval-driven development as its own #1 pattern.

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
