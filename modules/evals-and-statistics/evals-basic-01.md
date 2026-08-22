---
id: evals-basic-01
title: Three graders, thirty answers — your first mechanized rubric
topic: evals-and-statistics
level: basic
status: ready
time: 6-8h
summary: Grade 30 held-out answers three ways — string match, token overlap, six named boolean checks — and watch the word counter hand 0.96 to an answer that is flatly wrong while it fails a correct one.
---

## Why this module

The 16-repo scan reached one verdict above all others: **everything in the portfolio measures plumbing, never product.** Hash chains are verified, retrieval ranks are benchmarked over 150 adversarial cases, side effects are graded — but no script answers "was the *output* any good?" The one real attempt, a 10-persona blind rubric scoring the second-brain 6.28/10, is markdown, not runnable code.

This module closes the gap at `basic`. Three graders read the same 30 stored answers — exact match, token-overlap F1, six named boolean checks — and the first two fail in ways you can name and count. No judge and no statistics beyond counting: a judge needs a key and a budget and gets its own module, variance needs resampling and is `evals-inter-01`. The bar is a Python function and a regular expression. Stdlib Python 3, offline, $0.00, under a tenth of a second a run, one sitting to read; the hard part is writing your own expectations, in the last section.

By the end, one command grades 30 of your answers and prints every case where two graders disagree. Skipping ahead:

```
# modules/evals-and-statistics/code/evals-basic-01/ — COMPLETE, run from that directory
$ python3 eval.py --strategy all

cases=30  file=cases.json  graders are deterministic (no model call)

ALL THREE — one row per case
------------------------------------------------------------------------------
case  kind          exact   overlap        rubric
F01   factual       FAIL    PASS f1=0.80   [......] 6/6 PASS
...
F04   factual       FAIL    FAIL f1=0.43   [......] 6/6 PASS
...
F07   factual       FAIL    PASS f1=0.80   [xx....] 4/6 FAIL
...
F09   factual       FAIL    PASS f1=0.96   [..xx..] 4/6 FAIL
...
------------------------------------------------------------------------------
disagreements between overlap and rubric: 9
  F04: rubric 6/6 but overlap FAIL (f1=0.43)
  F07: overlap PASS (f1=0.80) but rubric 4/6
  F09: overlap PASS (f1=0.96) but rubric 4/6
  S02: overlap PASS (f1=0.71) but rubric 5/6
  S03: overlap PASS (f1=0.57) but rubric 5/6
  S04: overlap PASS (f1=0.77) but rubric 5/6
  S06: overlap PASS (f1=0.74) but rubric 4/6
  S07: overlap PASS (f1=0.82) but rubric 4/6
  S10: overlap PASS (f1=0.74) but rubric 5/6
```

run: 2026-08-20 · deterministic, no model call · n=30 · `python3 eval.py --strategy all`

Nine times in thirty, one answer gets opposite verdicts. F09 says 137B active parameters where its page says 37B; overlap gave it 0.96. F01 and F07 both score 0.80, one clean and one citing no page. F04 is the mirror — overlap failed a correct answer.

## Concepts

Named here so you can find them again; each is built and killed below.

- **Golden set** — dated inputs, expectations written before grading.
- **Exact match** — is the answer the reference string? #1.
- **Token F1** — what share of words do answer and reference share? #2.
- **Rubric** — six named yes/no questions about the answer itself. #3.
- **Grader disagreement** — one answer, two graders, two verdicts; the only signal here that a grader is broken.
- **Fixture** — a stored answer standing in for a live model call.

## Worked example

Source: faisalmahdy/ai-engineer-learning — `CLAUDE.md` (section 4, the Ingest / Query / Lint contract), `schema/relation-types.md`, `wiki/tiers.md`, `wiki/index.json`, `wiki/graph.json`, `llms.txt`, and 26 pages under `wiki/concepts/`.

Source: faisalmahdy/second-brain-through-agents — `raw/topics/agent-systems/second-brain-evaluation/2026-07-04-10-persona-usage-harness-verdicts.md`, the hand-run rubric this script mechanizes.

Script and fixtures: `modules/evals-and-statistics/code/evals-basic-01/` — `eval.py`, 424 lines, `cases.json`, 548 lines. Every command runs from there.

### The 30 cases, and the one answer we keep

Target: the Query workflow of the AI Engineering LLM Wiki, 209 concept pages over 8 domains, never evaluated. Thirty questions, ten each — `factual`, `synthesis`, `unanswerable`, where a refusal is the right answer. Fixed, dated, committed before grading: this is called a **golden set**, and there is nothing more to it. Expectations went in by hand first — 46 required citations + 64 required facts + 32 forbidden ones = 142 over 30 cases, plus 209 slugs and 9 refusal markers.

A fence at the moment it matters, not a disclaimer up top: the answers are stored, not generated. `cases.json` — "The `answer` field is a stored fixture, not a live model call ... the graders only ever read `answer`."

F09 is the case to hold on to. Its reference opens "DeepSeek-V3 is 671B total parameters with 37B active per token, about 5.5% active"; its answer opens "...with 137B active per token, about 20% active". Two numbers moved, everything else copied. `_meta.planted_cases`: "F09 — the fixture copies the reference and changes two numbers (37B -> 137B, 5.5% -> 20%)."

### Grading ten of them by hand

| case | what the answer does | my verdict |
|---|---|---|
| F01 | names Ingest, Query and Lint and what each one does | pass |
| F02 | repeats the six edge types word for word | pass |
| F03 | defines tier T0, counts 16 of the 209 pages in it | pass |
| F04 | says the same thing about prompt caching in different words | pass |
| F05 | what the KV cache holds, and why it pins memory at long context | pass |
| F06 | the 60-68% judge-expert agreement floor, all three named biases | pass |
| F07 | right on both numbers, cites no page at all | fail — ungrounded |
| F08 | dates MCP to November 2024, names host / client / server | pass |
| F09 | copies the reference, 37B becomes 137B | fail — wrong number |
| F10 | 209 pages, 8 domains, 1162 edges | pass |

U08, further down, answers an unanswerable question and asserts SOC 2 Type II — fail, it should have refused. The judgments are easy; the arithmetic is not. Every row is six questions at once — page cited, right page, facts present, nothing false, refusal where required, well formed — so ten answers cost 60 judgments and thirty cost 180 a run, again every time the system changes.

### Strategy #1 — exact match, one comparison per case

Before any grader existed, `cases.json` wrote the right verdict for six cases into `_meta.planted_cases`: F04, F09, S07, S10, U02, U08. Call them the **planted set** — F04 correct, the other five broken.

Strategy #1 is the dumbest grader in the file: is the answer character-for-character the reference? On those six, how many verdicts does it get right? Write your number down. Most people say one or two — a string comparison against paragraphs should get almost nothing right. I wrote one.

<svg viewBox="0 0 680 296" role="img" aria-label="Three panels showing what each grader reads from the same answer: exact match does one string comparison, token overlap sees a bag of 65 unordered tokens, and the rubric runs six named probes labelled C1 to C6">
  <g font-family="var(--mono)">
    <rect x="0" y="0" width="680" height="88" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="16" y="26" font-size="11" font-weight="600" fill="var(--ink)">STRATEGY 1 — EXACT</text>
    <rect x="176" y="16" width="230" height="18" rx="3" fill="var(--grid)"></rect>
    <rect x="176" y="48" width="230" height="18" rx="3" fill="var(--grid)"></rect>
    <text x="168" y="30" font-size="9.5" text-anchor="end" fill="var(--muted)">answer</text>
    <text x="168" y="62" font-size="9.5" text-anchor="end" fill="var(--muted)">reference</text>
    <text x="422" y="50" font-size="15" fill="var(--ink)">=?</text>
    <rect x="470" y="30" width="190" height="26" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="565" y="47" font-size="10.5" text-anchor="middle" fill="var(--acc-ink)">1 comparison per case</text>
    <rect x="0" y="100" width="680" height="88" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="16" y="126" font-size="11" font-weight="600" fill="var(--ink)">STRATEGY 2 — OVERLAP</text>
    <path d="M176 114 h230 v50 a10 10 0 0 1 -10 10 h-210 a10 10 0 0 1 -10 -10 Z" fill="none" stroke="var(--line)"></path>
    <g fill="var(--grid)">
      <rect x="188" y="124" width="16" height="9" rx="2"></rect><rect x="212" y="140" width="20" height="9" rx="2"></rect><rect x="242" y="126" width="14" height="9" rx="2"></rect>
      <rect x="266" y="150" width="18" height="9" rx="2"></rect><rect x="294" y="130" width="22" height="9" rx="2"></rect><rect x="326" y="146" width="14" height="9" rx="2"></rect>
      <rect x="350" y="124" width="18" height="9" rx="2"></rect><rect x="376" y="142" width="20" height="9" rx="2"></rect><rect x="204" y="158" width="16" height="9" rx="2"></rect>
      <rect x="234" y="160" width="20" height="9" rx="2"></rect><rect x="300" y="158" width="16" height="9" rx="2"></rect><rect x="346" y="160" width="22" height="9" rx="2"></rect>
    </g>
    <rect x="470" y="130" width="190" height="26" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="565" y="147" font-size="10.5" text-anchor="middle" fill="var(--acc-ink)">65 tokens, order discarded</text>
    <rect x="0" y="200" width="680" height="96" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="16" y="226" font-size="11" font-weight="600" fill="var(--ink)">STRATEGY 3 — RUBRIC</text>
    <rect x="176" y="216" width="230" height="18" rx="3" fill="var(--grid)"></rect>
    <g stroke="var(--line)" fill="none"><path d="M186 244 v14"></path><path d="M222 244 v14"></path><path d="M258 244 v14"></path><path d="M294 244 v14"></path><path d="M330 244 v14"></path><path d="M366 244 v14"></path></g>
    <g font-size="9.5" fill="var(--muted)" text-anchor="middle">
      <text x="186" y="272">C1</text><text x="222" y="272">C2</text><text x="258" y="272">C3</text>
      <text x="294" y="272">C4</text><text x="330" y="272">C5</text><text x="366" y="272">C6</text>
    </g>
    <rect x="470" y="236" width="190" height="26" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="565" y="253" font-size="10.5" text-anchor="middle" fill="var(--acc-ink)">6 named probes</text>
  </g>
</svg>
^ What each grader reads from the same answer (F09, 65 tokens). The bag is schematic — twelve chips drawn, sixty-five in the real one.

How to read this: only the badges matter; what sits outside one is what that grader cannot fail you for. Exact never says *what* was wrong; overlap cannot know one of those words is a number.

```
# eval.py:36-42 — COMPLETE (runs exactly as shown)
def grade_exact(case):
    """Did the system emit the reference answer, character for character?"""
    got = case["answer"].strip()
    want = case["reference"].strip()
    if got == want:
        return True, "identical to reference"
    return False, "differs from reference"

# $ python3 eval.py --strategy exact
# F02  factual       PASS  identical to reference
# ...
# F09  factual       FAIL  differs from reference
# ...
# SUMMARY exact    n=30  matched=3  score=0.100
```

run: 2026-08-20 · deterministic, no model call · n=30 · `python3 eval.py --strategy exact`

This is called **exact match**: `==` on two stripped strings, seven lines, nothing to tune. It survives in real harnesses because on short-form answers — a date, a slug, a yes/no — it is the right grader. Here the answers are paragraphs.

Bracket for 0.100: floor 0.000, ceiling 1.000 if every answer were a verbatim copy, chance 0.000 because two separately written paragraphs never match byte for byte. Three fixtures are copies, so 3/30 is all it can reach here.

Five of six. I wrote one. The truth flatters a grader doing nothing: exact said FAIL on 27 of the 30, and five of the planted six are supposed to fail — a stopped clock getting the time. The sixth is the cost: F04 is correct in other words and exact failed it, which the planted set names **the paraphrase**.

Concede: seven lines, and F02, F06 and F10 came back identical. The death: 19 answers pass every rubric check below and this grader passed 3, so 19 − 3 = **16 answers clear all six checks and exact match calls FAIL.**

### Strategy #2 — token overlap, one case at a time

Stop asking whether the strings are identical; count the words they share. F09 alone — one case, one loop over single tokens, nothing batched.

```
# eval.py:16, 29-31, 47-70 — COMPLETE (spliced from three ranges; trailing comments added here)
import re

def words(text):
    """Lowercase alphanumeric tokens. Every strategy uses this one tokenizer."""
    return re.findall(r"[a-z0-9]+", text.lower())

def token_f1(answer, reference):
    got = words(answer)                                   # F09 answer:    65 tokens
    want = words(reference)                               # F09 reference: 66 tokens
    if not got or not want:
        return 0.0
    pool = list(want)
    hits = 0
    for token in got:                                     # one token at a time
        if token in pool:
            pool.remove(token)                            # each reference word matched once
            hits = hits + 1
    if hits == 0:
        return 0.0
    precision = hits / len(got)                           # 63/65 = 0.969231
    recall = hits / len(want)                             # 63/66 = 0.954545
    return 2 * precision * recall / (precision + recall)  # 0.961832

def grade_overlap(case, threshold):
    score = token_f1(case["answer"], case["reference"])
    return score >= threshold, score

# $ python3 eval.py --strategy overlap
# F04  factual       FAIL  f1=0.429
# ...
# F09  factual       PASS  f1=0.962
# ...
# S07  synthesis     PASS  f1=0.820
# ...
# SUMMARY overlap  n=30  passed=26  score=0.867  mean_f1=0.714
```

run: 2026-08-20 · deterministic, no model call · n=30 · `python3 eval.py --strategy overlap`

The loop ends on F09 with `hits` at 63. The reference words never matched are `37b`, `5`, `5`; the answer words that matched nothing are `137b` and `20`.

This is called **token F1**.

F1 is not a statistical object. It is 63/65 and 63/66, combined so the smaller wins. Reading the symbols: `2PR/(P+R)` looks like notation only because precision and recall got shortened to capitals — average the two fractions, punish the lower one. The misparse is reading F1 as a probability the answer is correct. It knows the meaning of no word it counts.

Bracket for 0.867: floor 0.000 for an answer sharing no word with its reference, ceiling 1.000 for a copy, no chance level because nothing here is random. Drop the pass line to 0.00 and it scores 1.000 on anything.

<svg viewBox="0 0 680 208" role="img" aria-label="Two token strips at identical coordinates: the F09 reference has 66 tokens with three highlighted, the F09 answer has 65 tokens with two highlighted, and they diverge at the eighth token">
  <g font-family="var(--mono)">
    <text x="44" y="42" font-size="10.5" fill="var(--muted)">reference — 66 tokens</text>
    <line x1="44" y1="67" x2="638" y2="67" stroke="var(--grid)" stroke-width="22" stroke-dasharray="6.6 2.4"></line>
    <rect x="107" y="56" width="6.6" height="22" fill="var(--s1)"></rect>
    <rect x="152" y="56" width="6.6" height="22" fill="var(--s1)"></rect>
    <rect x="161" y="56" width="6.6" height="22" fill="var(--s1)"></rect>
    <text x="44" y="110" font-size="10.5" fill="var(--muted)">answer — 65 tokens</text>
    <line x1="44" y1="135" x2="629" y2="135" stroke="var(--grid)" stroke-width="22" stroke-dasharray="6.6 2.4"></line>
    <rect x="107" y="124" width="6.6" height="22" fill="var(--s1)"></rect>
    <rect x="152" y="124" width="6.6" height="22" fill="var(--s1)"></rect>
    <line x1="110" y1="50" x2="110" y2="152" stroke="var(--acc)" stroke-width="1.2" stroke-dasharray="3 3"></line>
    <text x="118" y="172" font-size="10" fill="var(--acc-ink)">token 8 (index 7) — 37b becomes 137b</text>
    <text x="44" y="196" font-size="10.5" fill="var(--muted)">63 of 65 answer tokens matched</text>
    <rect x="470" y="176" width="190" height="26" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="565" y="193" font-size="10.5" text-anchor="middle" fill="var(--acc-ink)">f1 = 0.962 · pass line 0.50</text>
  </g>
</svg>
^ F09's reference and its stored answer, same token pitch, same origin. Three marked cells above, two below; every other cell is shared.

How to read this: the failure signature is a strip almost entirely unmarked. Two marked cells in sixty-five is what a wrong answer looks like to a word counter, 0.462 above the pass line.

Concede: overlap rescues 23 of the 27 exact rejected. The kills are the planted set's next two — **the number swap**, F09's 0.962 beating 26 of the other 29, and **the polarity flip** (S07), one No turned Yes and still 0.820 PASS. F04 is still failed at 0.429. Magic number, confessed: the 0.50 pass line is `_config.overlap_threshold`, picked by eye.

### Strategy #3 — six named probes, still one case at a time

Stop comparing to a reference at all. Ask six questions about the answer itself and write down, per case and in advance, what each answer should be: a real page cited, the right page cited, the facts present, a refusal when the wiki cannot answer, the length band, a `Sources:` line. C1 is the only check here that can see an invented citation, which is how S10 and U02 die. The sixth you write.

```
# eval.py:109 — STUB, the version you write first (the committed body is below)
def check_no_known_error(case, config):
    """C4 correctness: the specific wrong claims this question attracts."""
    patterns = case["expect"]["must_not_match"]
    if not patterns:
        return True, "no error pattern for this case"
    # your turn: what goes here?
```

Why it is not obvious: C3 already requires the facts, and F09 is missing `37B`, so C3 fires. But an answer that keeps `37B` and adds "which is 137B on the Pro variant" satisfies C3 and is still wrong. A check for what must be present cannot see what must be absent; C4 is its mirror, 32 forbidden patterns across the suite.

```
# eval.py:109-118 and 153-160 — COMPLETE (uses `re` from the block above)
def check_no_known_error(case, config):
    """C4 correctness: the specific wrong claims this question attracts."""
    patterns = case["expect"]["must_not_match"]
    if not patterns:
        return True, "no error pattern for this case"
    for pattern in patterns:
        found = re.search(pattern, case["answer"])
        if found:
            return False, "asserts known error: " + repr(found.group(0))
    return True, "clear of " + str(len(patterns)) + " error pattern(s)"

CHECKS = [
    ("C1", "cites-valid-slug", check_cites_valid_slug),        # grounding
    ("C2", "cites-required-page", check_cites_required),       # grounding
    ("C3", "key-facts-present", check_key_facts),              # correctness
    ("C4", "no-known-error", check_no_known_error),            # correctness
    ("C5", "refusal-honesty", check_refusal_honesty),          # honest-refusal
    ("C6", "well-formed", check_well_formed),                  # completeness
]

# $ python3 eval.py --strategy rubric
# F09  factual       [..xx..]  4/6  FAIL
#        C3 key-facts-present: missing required fact /\b37B\b/
#        C4 no-known-error: asserts known error: '137B'
# ...
# U08  unanswerable  [...xx.]  4/6  FAIL
#        C4 no-known-error: asserts known error: 'SOC 2 Type II'
#        C5 refusal-honesty: should have refused, answered instead
# ...
# failures by check:
#   C1 cites-valid-slug      3 of 30 cases
#   C2 cites-required-page   2 of 30 cases
#   C3 key-facts-present     4 of 30 cases
#   C4 no-known-error        6 of 30 cases
#   C5 refusal-honesty       2 of 30 cases
#   C6 well-formed           1 of 30 cases
# SUMMARY rubric   n=30  checks_passed=162/180  score=0.900  clean_cases=19/30  clean_rate=0.633
```

run: 2026-08-20 · deterministic, no model call · n=30 · `python3 eval.py --strategy rubric`

This is called a **rubric**. Not a scoring model, nothing statistical in it: six `if` statements with names, plus 142 expectations you typed by hand.

Nothing in the six checks changed between one case and thirty — the only new code is the loop in `run_rubric`. `[..xx..]` is one character per check in `CHECKS` order, dot for pass, `x` for fail: F09 is grounded fine, both correctness checks blown. It printed `'137B'`, the thing you go and fix.

### What the two numbers are worth

Thirty cases at six checks is 180 checks. The **rubber stamp** — True unconditionally — scores 180/180 = 1.000 and `clean_rate` 30/30 = 1.000 while catching 0 of the 11 answers this rubric flags; all-False scores 0.000 and condemns the 19 it calls clean along with them; a coin flip lands near 0.500. The two numbers we report, 0.900 and 0.633, both top out at 1.000 on the rubber stamp, so neither ceiling separates a real grader from a fake one. Sensitivity does: one failed check out of six costs a case its entire `clean_rate` contribution, 1/30 = 0.033, but moves the check score by 1/180 = 0.006. That is why `clean_rate` is what I report, against the labs' hand-run 6.28/10 on this wiki.

| rung | code | written per case | score, n=30 | planted verdicts right |
|---|---|---|---|---|
| #1 exact | 7 lines (eval.py:36-42) | one reference answer | 0.100 — 3 of 30 matched | 5 of 6 |
| #2 overlap | 24 lines (eval.py:16, 29-31, 47-70) | same reference, one threshold | 0.867 — 26 of 30, mean_f1 0.714 | 2 of 6 |
| #3 rubric | 89 lines (eval.py:75-180) | 142 expectations over 30 cases | 0.900 checks, 0.633 clean | 6 of 6 |

Last column counted by hand off the `--strategy all` block. The code is not what got expensive.

A printed number is a claim, so the script derives 0.900 twice: per case then summed, and again by flattening all 180 booleans into one list counted in a plain loop.

```
# $ python3 eval.py --check
# route A (per case, summed)   checks_passed=162/180  score=0.900000  clean=19
# route B (flat dumb loop)     checks_passed=162/180  score=0.900000  clean=19
# flat list length=180  expected=180
# determinism: two independent passes produce identical per-case marks
# SELF-TEST PASS  routes agree=True  deterministic=True
#
# $ python3 eval.py --strategy rubric | md5sum     (three times)
# d7a8c9deb26c4b6309c02941af8d2253  -
# d7a8c9deb26c4b6309c02941af8d2253  -
# d7a8c9deb26c4b6309c02941af8d2253  -
```

run: 2026-08-20 · deterministic, no model call · n=30 · `python3 eval.py --check`

Third route, by hand: 162/180 = 0.9 exactly, and 19/30 = 0.6333…, which rounds to the printed 0.633.

Now the uncertainty. n=30, and the spread across reruns is 0.000 — not because these graders are steady but because nothing in them can be unstable: no model call, no sampling, no clock. A spread of zero by construction is not a small spread; it is a spread nobody measured. What varies is what this module holds fixed: which 30 questions got drawn. Draw a different 30 and 0.633 moves, by an amount nothing here can say — `evals-inter-01`.

<svg viewBox="0 0 680 190" role="img" aria-label="Two rows of thirty squares: the top row is the token-overlap verdict per case, the bottom row is the rubric verdict, with nine vertical connectors marking the cases where the two graders disagree">
  <g font-family="var(--mono)">
    <text x="44" y="26" font-size="10.5" fill="var(--muted)">top row: overlap verdict · bottom row: rubric verdict · filled square = FAIL</text>
    <text x="40" y="73" font-size="9.5" text-anchor="end" fill="var(--muted)">ovl</text>
    <text x="40" y="129" font-size="9.5" text-anchor="end" fill="var(--muted)">rub</text>
    <g><rect x="44" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="64" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="84" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="104" y="62" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="124" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="144" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="164" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="184" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="204" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="224" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="260" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="280" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="300" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="320" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="340" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="360" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="380" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="400" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="420" y="62" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="440" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="476" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="496" y="62" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="516" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="536" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="556" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="576" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="596" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="616" y="62" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="636" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="656" y="62" width="14" height="14" rx="3" fill="var(--grid)"></rect></g>
    <g><rect x="44" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="64" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="84" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="104" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="124" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="144" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="164" y="118" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="184" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="204" y="118" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="224" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="260" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="280" y="118" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="300" y="118" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="320" y="118" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="340" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="360" y="118" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="380" y="118" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="400" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="420" y="118" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="440" y="118" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="476" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="496" y="118" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="516" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="536" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="556" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="576" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="596" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="616" y="118" width="14" height="14" rx="3" fill="var(--s1)"></rect><rect x="636" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect><rect x="656" y="118" width="14" height="14" rx="3" fill="var(--grid)"></rect></g>
    <g stroke="var(--acc)" stroke-width="1.6"><line x1="111" y1="76" x2="111" y2="118"></line><line x1="171" y1="76" x2="171" y2="118"></line><line x1="211" y1="76" x2="211" y2="118"></line><line x1="287" y1="76" x2="287" y2="118"></line><line x1="307" y1="76" x2="307" y2="118"></line><line x1="327" y1="76" x2="327" y2="118"></line><line x1="367" y1="76" x2="367" y2="118"></line><line x1="387" y1="76" x2="387" y2="118"></line><line x1="447" y1="76" x2="447" y2="118"></line></g>
    <g font-size="10" fill="var(--muted)" text-anchor="middle"><text x="141" y="152">F01-F10 factual</text><text x="357" y="152">S01-S10 synthesis</text><text x="573" y="152">U01-U10 unanswerable</text></g>
    <rect x="470" y="164" width="190" height="24" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="565" y="180" font-size="10.5" text-anchor="middle" fill="var(--acc-ink)">9 of 30 disagree</text>
  </g>
</svg>
^ The same 30 answers, graded twice. Nine connectors, one per case where the two graders returned opposite verdicts.

How to read this: hunt for connectors, not filled squares. Bottom filled and top clear is overlap waving through an answer with a hole in it — eight of the nine, six in synthesis. The ninth is F04, far left, the other way.

### The whole file

Diff your copy against this.

```
# eval.py — COMPLETE, the whole file, 424 lines
#!/usr/bin/env python3
"""Three graders for the same 30 answers, from worst to least-bad.

  --strategy exact    string identity against a reference answer
  --strategy overlap  token-overlap F1 against the same reference
  --strategy rubric   six per-case boolean checks (the mechanized rubric)
  --strategy all      run all three and print where they disagree
  --check             re-derive the rubric score by a second, dumb route

Stdlib only. No network, no API keys, no model calls. The answers being
graded are fixtures stored in cases.json, so every run prints the same
numbers; see _meta.how_answers_were_produced in that file.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES_FILE = HERE / "cases.json"


def load_cases():
    data = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    return data["_config"], data["cases"]


def words(text):
    """Lowercase alphanumeric tokens. Every strategy uses this one tokenizer."""
    return re.findall(r"[a-z0-9]+", text.lower())


# ----------------------------------------------------------------- strategy 1

def grade_exact(case):
    """Did the system emit the reference answer, character for character?"""
    got = case["answer"].strip()
    want = case["reference"].strip()
    if got == want:
        return True, "identical to reference"
    return False, "differs from reference"


# ----------------------------------------------------------------- strategy 2

def token_f1(answer, reference):
    """Harmonic mean of token precision and recall, each token counted once."""
    got = words(answer)
    want = words(reference)
    if not got or not want:
        return 0.0

    pool = list(want)
    hits = 0
    for token in got:
        if token in pool:
            pool.remove(token)
            hits = hits + 1

    if hits == 0:
        return 0.0
    precision = hits / len(got)
    recall = hits / len(want)
    return 2 * precision * recall / (precision + recall)


def grade_overlap(case, threshold):
    score = token_f1(case["answer"], case["reference"])
    return score >= threshold, score


# ----------------------------------------------------------------- strategy 3

def check_cites_valid_slug(case, config):
    """C1 grounding: at least one [[slug]], and no invented ones."""
    cited = re.findall(config["citation_pattern"], case["answer"])
    if not cited:
        return False, "no [[slug]] citation at all"
    known = set(config["known_slugs"])
    for slug in cited:
        if slug not in known:
            return False, "cites [[" + slug + "]], which is not a wiki page"
    return True, str(len(cited)) + " citation(s), all real"


def check_cites_required(case, config):
    """C2 grounding: did it route to the page this question belongs to?"""
    required = case["expect"]["must_cite"]
    if not required:
        return True, "no page required"
    for slug in required:
        if "[[" + slug + "]]" not in case["answer"]:
            return False, "missing required citation [[" + slug + "]]"
    return True, "cites all " + str(len(required)) + " required page(s)"


def check_key_facts(case, config):
    """C3 correctness: every fact this question must contain."""
    patterns = case["expect"]["must_match"]
    if not patterns:
        return True, "no required facts"
    for pattern in patterns:
        if not re.search(pattern, case["answer"]):
            return False, "missing required fact /" + pattern + "/"
    return True, "all " + str(len(patterns)) + " fact patterns present"


def check_no_known_error(case, config):
    """C4 correctness: the specific wrong claims this question attracts."""
    patterns = case["expect"]["must_not_match"]
    if not patterns:
        return True, "no error pattern for this case"
    for pattern in patterns:
        found = re.search(pattern, case["answer"])
        if found:
            return False, "asserts known error: " + repr(found.group(0))
    return True, "clear of " + str(len(patterns)) + " error pattern(s)"


def check_refusal_honesty(case, config):
    """C5 honest-refusal: refuse when the wiki cannot answer, and only then."""
    refused = False
    for marker in config["refusal_markers"]:
        if re.search(marker, case["answer"]):
            refused = True

    expected = case["expect"]["refusal_expected"]
    if expected and not refused:
        return False, "should have refused, answered instead"
    if refused and not expected:
        return False, "refused a question the wiki can answer"
    if expected:
        return True, "refused, correctly"
    return True, "answered, correctly"


def check_well_formed(case, config):
    """C6 completeness: inside the length band and carrying a Sources: line."""
    answer = case["answer"]
    count = len(answer.split())
    low = case["expect"].get("min_words", config["default_min_words"])
    high = case["expect"].get("max_words", config["default_max_words"])
    if count < low:
        return False, str(count) + " words, under the " + str(low) + "-word floor"
    if count > high:
        return False, str(count) + " words, over the " + str(high) + "-word cap"
    if not re.search(config["sources_line_pattern"], answer):
        return False, "no Sources: line"
    return True, str(count) + " words, has Sources:"


CHECKS = [
    ("C1", "cites-valid-slug", check_cites_valid_slug),
    ("C2", "cites-required-page", check_cites_required),
    ("C3", "key-facts-present", check_key_facts),
    ("C4", "no-known-error", check_no_known_error),
    ("C5", "refusal-honesty", check_refusal_honesty),
    ("C6", "well-formed", check_well_formed),
]


def grade_rubric(case, config):
    """Run all six checks over one case. Returns a list of (id, name, ok, why)."""
    results = []
    for check_id, name, function in CHECKS:
        ok, why = function(case, config)
        results.append((check_id, name, ok, why))
    return results


def rubric_marks(results):
    """'..x..x' — a dot per passing check, an x per failing one."""
    marks = ""
    for _, _, ok, _ in results:
        if ok:
            marks = marks + "."
        else:
            marks = marks + "x"
    return marks


# ---------------------------------------------------------------- run + print

def line(case_id, kind, rest):
    return case_id.ljust(5) + kind.ljust(14) + rest


def run_exact(config, cases):
    print("STRATEGY 1 — exact: answer.strip() == reference.strip()")
    print("-" * 78)
    matched = 0
    for case in cases:
        ok, why = grade_exact(case)
        if ok:
            matched = matched + 1
        verdict = "PASS" if ok else "FAIL"
        print(line(case["id"], case["kind"], verdict + "  " + why))
    score = matched / len(cases)
    print("-" * 78)
    print("SUMMARY exact    n=%d  matched=%d  score=%.3f" % (len(cases), matched, score))
    return score


def run_overlap(config, cases):
    threshold = config["overlap_threshold"]
    print("STRATEGY 2 — overlap: token F1 vs reference, pass at F1 >= %.2f" % threshold)
    print("-" * 78)
    passed = 0
    total_f1 = 0.0
    for case in cases:
        ok, score = grade_overlap(case, threshold)
        total_f1 = total_f1 + score
        if ok:
            passed = passed + 1
        verdict = "PASS" if ok else "FAIL"
        print(line(case["id"], case["kind"], verdict + "  f1=%.3f" % score))
    score = passed / len(cases)
    mean_f1 = total_f1 / len(cases)
    print("-" * 78)
    print("SUMMARY overlap  n=%d  passed=%d  score=%.3f  mean_f1=%.3f"
          % (len(cases), passed, score, mean_f1))
    return score


def run_rubric(config, cases):
    print("STRATEGY 3 — rubric: six boolean checks per case")
    for check_id, name, _ in CHECKS:
        print("  " + check_id + " " + name)
    print("-" * 78)

    checks_passed = 0
    clean_cases = 0
    failures_by_check = {}
    for check_id, _, _ in CHECKS:
        failures_by_check[check_id] = 0

    for case in cases:
        results = grade_rubric(case, config)
        hits = 0
        for _, _, ok, _ in results:
            if ok:
                hits = hits + 1
        checks_passed = checks_passed + hits
        if hits == len(CHECKS):
            clean_cases = clean_cases + 1
        marks = rubric_marks(results)
        verdict = "PASS" if hits == len(CHECKS) else "FAIL"
        print(line(case["id"], case["kind"],
                   "[" + marks + "]  " + str(hits) + "/6  " + verdict))
        for check_id, name, ok, why in results:
            if not ok:
                failures_by_check[check_id] = failures_by_check[check_id] + 1
                print("       " + check_id + " " + name + ": " + why)

    total_checks = len(cases) * len(CHECKS)
    score = checks_passed / total_checks
    clean_rate = clean_cases / len(cases)

    print("-" * 78)
    print("failures by check:")
    for check_id, name, _ in CHECKS:
        print("  " + check_id + " " + name.ljust(22)
              + str(failures_by_check[check_id]) + " of " + str(len(cases)) + " cases")
    print("failures by kind:")
    for kind in ("factual", "synthesis", "unanswerable"):
        kind_cases = 0
        kind_failed = 0
        for case in cases:
            if case["kind"] != kind:
                continue
            kind_cases = kind_cases + 1
            results = grade_rubric(case, config)
            for _, _, ok, _ in results:
                if not ok:
                    kind_failed = kind_failed + 1
        print("  " + kind.ljust(14) + str(kind_failed) + " failed checks over "
              + str(kind_cases * len(CHECKS)))
    print("-" * 78)
    print("SUMMARY rubric   n=%d  checks_passed=%d/%d  score=%.3f  clean_cases=%d/%d  clean_rate=%.3f"
          % (len(cases), checks_passed, total_checks, score,
             clean_cases, len(cases), clean_rate))
    return score


def run_all(config, cases):
    """One row per case, three verdicts, so disagreements are visible."""
    print("ALL THREE — one row per case")
    print("-" * 78)
    print("case  kind          exact   overlap        rubric")
    disagreements = []
    for case in cases:
        exact_ok, _ = grade_exact(case)
        overlap_ok, f1 = grade_overlap(case, config["overlap_threshold"])
        results = grade_rubric(case, config)
        hits = 0
        for _, _, ok, _ in results:
            if ok:
                hits = hits + 1
        rubric_ok = hits == len(CHECKS)

        print(case["id"].ljust(6) + case["kind"].ljust(14)
              + ("PASS" if exact_ok else "FAIL").ljust(8)
              + ("PASS" if overlap_ok else "FAIL") + " f1=%.2f" % f1 + "   "
              + "[" + rubric_marks(results) + "] " + str(hits) + "/6 "
              + ("PASS" if rubric_ok else "FAIL"))

        if overlap_ok and not rubric_ok:
            disagreements.append(
                case["id"] + ": overlap PASS (f1=%.2f) but rubric %d/6" % (f1, hits))
        if rubric_ok and not overlap_ok:
            disagreements.append(
                case["id"] + ": rubric 6/6 but overlap FAIL (f1=%.2f)" % f1)

    print("-" * 78)
    print("disagreements between overlap and rubric: " + str(len(disagreements)))
    for item in disagreements:
        print("  " + item)


def self_check(config, cases):
    """Compute the rubric score twice by different routes and compare."""
    print("SELF-TEST — re-derive the rubric score by a second, dumb route")
    print("-" * 78)

    # Route A: the route the report uses. Per case, count hits, sum them.
    route_a_hits = 0
    route_a_clean = 0
    for case in cases:
        results = grade_rubric(case, config)
        hits = 0
        for _, _, ok, _ in results:
            if ok:
                hits = hits + 1
        route_a_hits = route_a_hits + hits
        if hits == len(CHECKS):
            route_a_clean = route_a_clean + 1

    # Route B: forget cases exist. Flatten every check into one list of
    # booleans, then count the list with a plain loop.
    flat = []
    for case in cases:
        for check_id, name, function in CHECKS:
            ok, why = function(case, config)
            flat.append(ok)

    route_b_hits = 0
    for ok in flat:
        if ok:
            route_b_hits = route_b_hits + 1

    # Route B's clean-case count, also the dumb way: walk the flat list in
    # groups of six and require all six.
    route_b_clean = 0
    position = 0
    while position < len(flat):
        group = flat[position:position + len(CHECKS)]
        all_ok = True
        for ok in group:
            if not ok:
                all_ok = False
        if all_ok:
            route_b_clean = route_b_clean + 1
        position = position + len(CHECKS)

    total = len(cases) * len(CHECKS)
    print("route A (per case, summed)   checks_passed=%d/%d  score=%.6f  clean=%d"
          % (route_a_hits, total, route_a_hits / total, route_a_clean))
    print("route B (flat dumb loop)     checks_passed=%d/%d  score=%.6f  clean=%d"
          % (route_b_hits, len(flat), route_b_hits / len(flat), route_b_clean))
    print("flat list length=%d  expected=%d" % (len(flat), total))

    ok = (route_a_hits == route_b_hits and route_a_clean == route_b_clean
          and len(flat) == total)

    # And once more, to show the grader is deterministic across runs.
    again = []
    for case in cases:
        again.append(rubric_marks(grade_rubric(case, config)))
    once = []
    for case in cases:
        once.append(rubric_marks(grade_rubric(case, config)))
    deterministic = again == once
    print("determinism: two independent passes produce "
          + ("identical" if deterministic else "DIFFERENT") + " per-case marks")

    print("-" * 78)
    print("SELF-TEST " + ("PASS" if ok and deterministic else "FAIL")
          + "  routes agree=%s  deterministic=%s" % (ok, deterministic))
    return ok and deterministic


def main():
    parser = argparse.ArgumentParser(description="Grade 30 stored Query-workflow answers.")
    parser.add_argument("--strategy", choices=["exact", "overlap", "rubric", "all"])
    parser.add_argument("--check", action="store_true",
                        help="cross-verify the rubric score by a second route")
    args = parser.parse_args()

    config, cases = load_cases()
    print("cases=%d  file=%s  graders are deterministic (no model call)"
          % (len(cases), CASES_FILE.name))
    print("")

    if args.check:
        ok = self_check(config, cases)
        return 0 if ok else 1

    if args.strategy == "exact":
        run_exact(config, cases)
    elif args.strategy == "overlap":
        run_overlap(config, cases)
    elif args.strategy == "rubric":
        run_rubric(config, cases)
    elif args.strategy == "all":
        run_all(config, cases)
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### What we did not settle

The fixture fence is the big one: the 30 answers are stored strings. That bought a grader that runs offline with no key, and it means this measures the graders honestly and the system only as of the day they were written.

No judge, no resampling spread, no inter-rater agreement — ten hand-graded cases cannot produce one. Two more magic numbers beside the 0.50: `default_min_words: 20`, `default_max_words: 180`. C6 fired once (S03, 204 words), so nothing shows the band is right, only that it is enforceable.

And the planted set is mine: all six failures are ones I wrote into the fixtures, so this tests the graders, not the wiki. A failure mode I never thought of has no pattern in `must_not_match` and gets a clean `[......]`. That partly undercuts the exercise, which is why the disagreement count is what I would show first.

## Build

The pipeline in one paragraph: write 30 held-out questions, including ones the system should refuse; run them and store the raw answers; write the expectations per case before you see a score; grade with two graders; print where they disagree.

We opened on one command that prints where two graders disagree. The payoff block (again):

```
# modules/evals-and-statistics/code/evals-basic-01/ — COMPLETE, run from that directory
$ python3 eval.py --strategy all

cases=30  file=cases.json  graders are deterministic (no model call)

ALL THREE — one row per case
------------------------------------------------------------------------------
case  kind          exact   overlap        rubric
F01   factual       FAIL    PASS f1=0.80   [......] 6/6 PASS
...
F04   factual       FAIL    FAIL f1=0.43   [......] 6/6 PASS
...
F07   factual       FAIL    PASS f1=0.80   [xx....] 4/6 FAIL
...
F09   factual       FAIL    PASS f1=0.96   [..xx..] 4/6 FAIL
...
------------------------------------------------------------------------------
disagreements between overlap and rubric: 9
  F04: rubric 6/6 but overlap FAIL (f1=0.43)
  F07: overlap PASS (f1=0.80) but rubric 4/6
  F09: overlap PASS (f1=0.96) but rubric 4/6
  S02: overlap PASS (f1=0.71) but rubric 5/6
  S03: overlap PASS (f1=0.57) but rubric 5/6
  S04: overlap PASS (f1=0.77) but rubric 5/6
  S06: overlap PASS (f1=0.74) but rubric 4/6
  S07: overlap PASS (f1=0.82) but rubric 4/6
  S10: overlap PASS (f1=0.74) but rubric 5/6
```

F09 is the DeepSeek parameter count, and we now know which grader was right and why: `C4 no-known-error: asserts known error: '137B'`.

Now point it at your own system. The one dial is `cases.json`; everything in `eval.py` derives from it, because the graders only ever read `answer`. Commit 30 dated questions in the same three-way split, paste your raw answers in untidied, fill `must_cite`, `must_match` and `must_not_match` from wrong answers you have actually seen, swap `known_slugs`, `refusal_markers` and the word band in `_config` for yours, then run `python3 eval.py --strategy all`.

Your number to beat is not 0.633. It is **9**, the disagreements 30 cases produced here. Zero means one grader is doing no work; twenty-five means your references and your rubric grade different systems. Bring back the list. Good luck.

### FAQ

**Why not just eyeball the outputs?** You did, ten cases above — 60 judgments — and you cannot repeat that after every system change.

**Why 30 cases and not 300?** Thirty is what one sitting of hand-written expectations costs: 142 of them. What 300 buys is how far 0.633 moves on a different draw, which needs resampling — `evals-inter-01`.

**Can I raise the 0.50 threshold until overlap stops passing F09?** No. F09's 0.962 beats 26 of the other 29 answers, so any line that fails F09 fails almost the whole suite. It is a dial on strictness, not correctness.

**Is a rubric of regular expressions an eval, or am I testing my own patterns?** Mechanically the second, which is how eval suites rot. It becomes an eval because the patterns came from the source pages before any grader ran, and because a grader on another principle disagrees 9 times in 30.

**Why is mine slow?** This one is not: under a tenth of a second, one JSON read, no network, no model call. If yours is slow the cost is generating the answers, once per system change.

### Errata

Version one, dated 2026-08-20. Corrected before publication and re-pasted from a fresh run: both payoff blocks were missing the `F07` row under a header that says nine, and the scoreboard credited the rubric with 95 lines where `eval.py:75-180` is 89. I never timed the hand-grading pass, so its cost is counted in judgments, not minutes. One soft spot left in: `check_refusal_honesty` reads "did it refuse" off 9 regular-expression markers, so a system that refuses in other wording scores as having answered. It will bite on yours.

## Definition of done

- [ ] `cases.json` for your own system: 30 cases, dated, split 10 / 10 / 10, committed before the first run
- [ ] Expectations written per case before you have seen any score
- [ ] `eval.py` committed and running against your file with no API key and no network
- [ ] One command in the README that reproduces every number you report
- [ ] `python3 eval.py --check` printing SELF-TEST PASS, so the headline number is derived twice
- [ ] A run stamp under every published number: date · deterministic or model+seed · n · the command
- [ ] Five sentences on what the disagreement list says and what these numbers cannot say yet
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Name what each grader can see, and the one thing exact match can never tell you even when right.
2. An answer copies its reference and changes one number; token F1 gives it 0.962. Explain from what F1 counts why, and name the check that catches it.
3. Give an answer that passes C3 and fails C4, and say why one check cannot do both jobs.
4. A rubber stamp scores 1.000 on both of this rubric's numbers. Say why `clean_rate` is reported anyway, in terms of what one failed check does to each.
5. Your own run printed a disagreement count. What was it, which case surprised you, and what would you have concluded if it had come back 0?

## External resources

- Hamel Husain, *Your AI Product Needs Evals* — https://hamel.dev/blog/posts/evals/ — my summary: eval infrastructure, not prompts or models, is where AI products win; it walks the ladder this module builds by hand.
- Eugene Yan, *Patterns for Building LLM-based Systems* — https://eugeneyan.com/writing/llm-patterns/ — my summary: evals first among seven patterns, plus the judge-bias literature that makes the judge its own module.
- Anthropic docs, evaluation guides — https://docs.claude.com — my summary: vendor guidance on empirical evals and rubrics, read per the hub's corpus-bias rule.
