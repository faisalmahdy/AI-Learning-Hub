---
id: evals-inter-02
title: The judge agrees 80% of the time — and that is the problem
topic: evals-and-statistics
level: intermediate
status: ready
time: 8-10h
summary: An LLM judge matches the gold labels on 24 of 30 answers, which sounds like an A — until a rubber-stamp judge scores 63% for free, Cohen's kappa lands at a moderate 0.53 with a CI from 0.19 to 0.83, and the judge turns out to be waving through 5 of the 11 answers that should have failed.
---

## Why this module

evals-basic-01 built a deterministic rubric and evals-inter-01 put an interval on an A/B difference, but both dodged the grader everyone actually reaches for: an LLM judge. The scan found the same judge machinery across the labs, always measured on plumbing and never on output. The author's own reviewer has a documented benchmark — "strong reviewer 71.6->89.7, weak reviewer 91.4->82.8" — which proves the judge *changes* scores, not that it agrees with a human on whether an answer is good. `CURRICULUM.md` names the fix: "Measure your judge against human labels on 30 cases; report bias & agreement", with the definition of done as "Judge agreement number known before the judge is trusted anywhere".

This module measures one judge at `intermediate`. The same 30 cases carry two verdicts now — the gold label and the judge's PASS/FAIL — and you get the one number that says whether the judge has any skill, corrected for the agreement it gets by luck, plus which direction it is biased. What it omits: no judge prompt engineering, no multi-judge panels, no live model calls — the judge column is a fixture so the whole thing runs offline, and calibrating the prompt is a later module. You need evals-inter-01's bootstrap and a Python dict. Stdlib Python 3, offline, $0.00, about two seconds a run, one sitting. The hard part is a single idea: raw agreement is not skill, and the gap between them is a rubber stamp.

By the end, one command calibrates the judge and prints why 80% agreement is not the number you want. Skipping ahead:

```
# modules/evals-and-statistics/code/evals-inter-02/ — COMPLETE, run from that directory
$ python3 judge.py --calibrated

cases=30  file=labels.json  judge column is a fixture (no model call)

CALIBRATION REPORT — judge vs 30 gold labels
------------------------------------------------------------
  raw agreement                 = 0.8000
  Cohen's kappa                 = 0.5337
  kappa 95% CI (bootstrap)      = [0.1892, 0.8305]  seed=0, B=10000
  failure-catch rate            = 6/11 = 0.5455  (gold FAILs the judge caught)
  leniency: judge passes 23, gold passes 19  (+4, the judge is lenient)
------------------------------------------------------------
  VERDICT: kappa 0.53 is moderate, and the judge misses 5 of 11 bad answers.
  Trust it for triage, not for a released number, and never above its CI.
```

run: 2026-08-22 · judge column is a fixture · bootstrap seed=0, B=10000 · n=30 · `python3 judge.py --calibrated`

Four numbers where a lazy harness would print one. The 80% is the number that would go in a slide; every number under it is the reason not to trust the slide. The judge is lenient, it catches barely half the failures, and its real skill — 0.53 — could be anywhere from 0.19 to 0.83 on 30 cases. This module is about earning each of those numbers.

## Concepts

Named here so you can find them again; each is built and, in one case, broken below.

- **Gold label** — the ground-truth verdict per case; here, basic-01's clean/not-clean. What the judge is measured against.
- **Raw agreement** — the fraction of cases where judge and gold match. #1, and the trap.
- **Rubber stamp** — a judge that says PASS to everything; the free-agreement baseline.
- **Chance agreement (p_e)** — the agreement two raters reach by luck, from their actual PASS rates. The number the planted bug gets wrong.
- **Cohen's kappa** — agreement above chance, on a scale where the stamp scores zero. #2.
- **Failure-catch rate** — of the answers gold failed, the fraction the judge also failed. What leniency hides.
- **Leniency** — how many more PASSes the judge hands out than the gold; the direction of its bias.

## Worked example

Source: faisalmahdy/agent — `agent/review.py` (author-blind, critique-only reviewer) and `providers/cli_judge.py` (a CLI judge provider); the LLM-judge implementations this module calibrates. De-personalized, and described only as far as the curriculum states.

Source: faisalmahdy/AI-Learning-Hub — `modules/evals-and-statistics/code/evals-basic-01/` (the 30-case gold verdicts reused as the `human` column) and `code/evals-inter-01/` (the bootstrap reused for kappa's interval).

Script and fixtures: `modules/evals-and-statistics/code/evals-inter-02/` — `judge.py`, 285 lines, `labels.json`, 30 cases with two verdicts each. Every command runs from there.

### Install the frame: the judge is a metal detector

In my opinion, the best way to think of an LLM judge is as the metal detector at an airport, not as a second expert.

The detector beeps or it does not — PASS or FAIL on each bag. You grade the detector by how often it matches the truth about what was in the bag. But here is the catch that runs the whole module: most bags are clean, so a detector that is switched *off* — never beeps, passes everything — still "agrees with the truth" on every clean bag, which is most of them. Its high score is free, and it caught nothing. A real detector has to beat that free score, and the only threats that matter are the ones it lets through.

Three jobs, one line each: raw agreement says "how often does the detector match the truth?", kappa says "how much of that matching is real skill and not the free score?", and the failure-catch rate says "of the bags that were actually dangerous, how many did it stop?"

### Look at the data: thirty answers, screened twice

The 30 cases are evals-basic-01's again. The `human` column is the gold verdict — clean in basic-01 meant PASS, so 19 PASS and 11 FAIL. The `judge` column is one LLM judge's PASS/FAIL on the same answer, stored as a fixture so every run is identical and free. Line them up and there are four kinds of case: both say PASS, both say FAIL, and the two disagreements — the judge fails an answer gold passed (a false alarm) or passes an answer gold failed (a miss).

```
# judge.py:48-62 — COMPLETE (count the four cells of the 2x2)
def confusion(cases):
    """Count the four cells. Returns (both_pass, gold_pass_judge_fail,
    gold_fail_judge_pass, both_fail)."""
    tp = fp = fn = tn = 0   # named from the gold's point of view: 'positive' = PASS
    for c in cases:
        g, j = c["human"], c["judge"]
        if g == "PASS" and j == "PASS":
            tp += 1
        elif g == "PASS" and j == "FAIL":
            fn += 1          # gold passed, judge failed it (a false alarm)
        elif g == "FAIL" and j == "PASS":
            fp += 1          # gold failed, judge passed it (a miss)
        else:
            tn += 1
    return tp, fn, fp, tn

# $ python3 judge.py --confusion
#                 judge PASS   judge FAIL
#   gold PASS         18            1      <- 1 false alarms
#   gold FAIL          5            6      <- 5 misses
#   agree on 24 of 30 cases
```

run: 2026-08-22 · fixture, no model call · n=30 · `python3 judge.py --confusion`

<svg viewBox="0 0 680 250" role="img" aria-label="A two by two confusion table, gold verdict on the rows and judge verdict on the columns: both PASS 18, gold PASS judge FAIL 1, gold FAIL judge PASS 5 highlighted as the dangerous misses, both FAIL 6">
  <g font-family="var(--mono)">
    <text x="300" y="40" font-size="10.5" fill="var(--muted)">judge PASS</text>
    <text x="470" y="40" font-size="10.5" fill="var(--muted)">judge FAIL</text>
    <text x="290" y="105" font-size="10.5" text-anchor="end" fill="var(--muted)">gold PASS</text>
    <text x="290" y="185" font-size="10.5" text-anchor="end" fill="var(--muted)">gold FAIL</text>
    <rect x="300" y="60" width="150" height="70" rx="6" fill="var(--panel)" stroke="var(--grid)"></rect>
    <rect x="460" y="60" width="150" height="70" rx="6" fill="var(--panel)" stroke="var(--grid)"></rect>
    <rect x="300" y="140" width="150" height="70" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <rect x="460" y="140" width="150" height="70" rx="6" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="375" y="102" font-size="22" text-anchor="middle" fill="var(--ink)">18</text>
    <text x="535" y="102" font-size="22" text-anchor="middle" fill="var(--ink)">1</text>
    <text x="375" y="182" font-size="22" text-anchor="middle" fill="var(--acc-ink)">5</text>
    <text x="535" y="182" font-size="22" text-anchor="middle" fill="var(--ink)">6</text>
    <text x="375" y="122" font-size="9" text-anchor="middle" fill="var(--muted)">both PASS</text>
    <text x="535" y="122" font-size="9" text-anchor="middle" fill="var(--muted)">false alarm</text>
    <text x="375" y="202" font-size="9" text-anchor="middle" fill="var(--acc-ink)">MISSES</text>
    <text x="535" y="202" font-size="9" text-anchor="middle" fill="var(--muted)">caught</text>
    <rect x="300" y="224" width="310" height="22" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="455" y="239" font-size="10.5" text-anchor="middle" fill="var(--acc-ink)">the 5 misses are dangerous answers waved through</text>
  </g>
</svg>
^ The judge against the gold, all 30 cases. The two off-diagonal cells are the disagreements; the highlighted one is the judge passing answers that should have failed.

How to read this: agreement lives on the diagonal (18 + 6 = 24), but the number that decides trust is the highlighted cell — 5 dangerous answers the detector waved through. A metric that does not look at that cell is not measuring safety.

### Strategy #1 — raw agreement. Killed by a detector that is switched off.

The obvious grade: what fraction of the 30 did the judge match? Twenty-four of thirty, 0.80.

```
# judge.py:65-68 — COMPLETE (the obvious grade, and the baseline that kills it)
def raw_agreement(cases):
    """Fraction of cases where judge and gold gave the same verdict."""
    same = sum(1 for c in cases if c["human"] == c["judge"])
    return same / len(cases)

# $ python3 judge.py --agreement
#   judge vs gold                 = 0.8000
#   always-PASS stamp vs gold     = 0.6333  (free, for saying nothing)
```

run: 2026-08-22 · fixture, no model call · n=30 · `python3 judge.py --agreement`

This is called **raw agreement**, and it is exactly what a busy harness prints and ships. Now the prediction — commit before the next section. The judge agrees with the gold on 24 of 30, which is 80%. Would you trust it as your grader? Most people say yes; 80% agreement with a human sounds like a solid grader. The answer is at the top of the next section.

The kill is already in the output. A **rubber stamp** — a judge that says PASS to every one of the 30, the detector switched off — agrees with the gold 0.6333 of the time, because 19 of 30 answers really do pass and it gets all 19 for free. So 0.80 is not 0.80 of skill; it is 0.6333 of free agreement plus 0.1667 of whatever the judge actually added, and raw agreement cannot tell you which part is which.

<svg viewBox="0 0 680 150" role="img" aria-label="A horizontal bar from 0 to 1 split into three segments: free agreement up to 0.633 that a rubber stamp gets, real signal from 0.633 to 0.80 that the judge added, and the gap from 0.80 to 1.0 up to perfect agreement">
  <g font-family="var(--mono)">
    <text x="90" y="34" font-size="10.5" fill="var(--muted)">raw agreement 0.80, decomposed</text>
    <rect x="90" y="46" width="335" height="30" rx="3" fill="var(--grid)"></rect>
    <rect x="425" y="46" width="89" height="30" rx="3" fill="var(--s1)"></rect>
    <rect x="514" y="46" width="106" height="30" rx="3" fill="none" stroke="var(--line)" stroke-dasharray="4 3"></rect>
    <line x1="90" y1="82" x2="90" y2="92" stroke="var(--muted)"></line>
    <line x1="425" y1="82" x2="425" y2="92" stroke="var(--acc)"></line>
    <line x1="514" y1="82" x2="514" y2="92" stroke="var(--muted)"></line>
    <line x1="620" y1="82" x2="620" y2="92" stroke="var(--muted)"></line>
    <g font-size="9" fill="var(--muted)"><text x="90" y="104" text-anchor="middle">0.00</text><text x="425" y="104" text-anchor="middle">0.633</text><text x="514" y="104" text-anchor="middle">0.80</text><text x="620" y="104" text-anchor="middle">1.00</text></g>
    <text x="257" y="66" font-size="10" text-anchor="middle" fill="var(--muted)">free (rubber stamp)</text>
    <text x="469" y="66" font-size="9" text-anchor="middle" fill="var(--ink)">signal</text>
    <rect x="360" y="120" width="300" height="22" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="510" y="135" font-size="10.5" text-anchor="middle" fill="var(--acc-ink)">only 0.167 of the 0.80 is the judge's doing</text>
  </g>
</svg>
^ The judge's 0.80 raw agreement, split into the part a switched-off detector gets for nothing and the part the judge actually contributed.

How to read this: the grey block is free — any stamp gets it. The failure signature is a judge whose raw-agreement bar is almost entirely grey, meaning it is riding the base rate, not grading.

### Strategy #2 — kappa, once you answer one question right

The answer to the prediction: no, do not trust it on 80%. The free score is 0.6333, so the judge's real contribution is a sliver, and to measure that sliver we need agreement scored above chance. That means one number — the agreement two raters would reach by luck — and getting it right is the whole game. Here is the function with that line blanked. Fill it in before you read on.

```
# judge.py:73-81 — STUB, the version you write first (committed body below)
def chance_agreement(cases):
    """p_e: the agreement two raters would reach by luck."""
    n = len(cases)
    gold_pass = sum(1 for c in cases if c["human"] == "PASS") / n
    judge_pass = sum(1 for c in cases if c["judge"] == "PASS") / n
    # your turn: is chance agreement 0.5 (a coin flip), or something the
    # actual PASS rates decide?
    ...
```

Stop here. Two verdicts, PASS or FAIL — so chance agreement is 0.5, a coin flip. Right? That is the tempting answer, and it is the bug.

```
# a chance-agreement sketch — COMPLETE, the wrong answer made concrete
p_e = 0.5                                # "two options, so chance is a coin flip"
kappa = (0.80 - p_e) / (1 - p_e)         # = 0.30 / 0.50 = 0.6000
# the judge's kappa is now 0.60 -- 'substantial', a whole band better than it is
```

Watch the arithmetic: with `p_e = 0.5` the judge's kappa comes out 0.6000, a full band higher than the truth. It looks fine, which is why the bug survives. The tell is the rubber stamp — run the balanced-chance formula on the always-PASS judge, which by definition has zero skill:

```
# $ python3 judge.py --check   (the two lines that matter)
#   rubber-stamp kappa, correct   = 0.0000  (must be 0)
#   rubber-stamp kappa, p_e=0.5   = 0.2667  (the bug: not 0 -> inflated)
```

run: 2026-08-22 · fixture, no model call · n=30 · `python3 judge.py --check`

A judge that says PASS to everything has no skill, so its kappa must be 0.0000, and the correct formula gives exactly that. The balanced-chance version gives the stamp 0.2667 — it is crediting a switched-off detector with a quarter of a point of skill it does not have. This is the **balanced-chance bug**: assuming `p_e = 0.5` because there are two labels. It hides on balanced data, where the base rate really is near 0.5 and the shortcut is invisible; here the base rate is 19-to-11, skewed enough that the shortcut inflates every kappa it touches. The one-line assertion that catches it: a rubber-stamp judge must score kappa 0.

The fix is to compute chance agreement from the *actual* rates at which each rater says PASS, not from a coin.

```
# judge.py:73-81 and 84-89 — COMPLETE (chance agreement, and kappa on top of it)
def chance_agreement(cases):
    """p_e: the agreement two raters would reach by luck, from the ACTUAL rate
    at which each says PASS. NOT 0.5 -- that assumes a balanced base rate."""
    n = len(cases)
    gold_pass = sum(1 for c in cases if c["human"] == "PASS") / n
    judge_pass = sum(1 for c in cases if c["judge"] == "PASS") / n
    gold_fail = 1 - gold_pass
    judge_fail = 1 - judge_pass
    return judge_pass * gold_pass + judge_fail * gold_fail

def cohen_kappa(cases):
    p_o = raw_agreement(cases)
    p_e = chance_agreement(cases)
    if p_e >= 1.0:
        return 1.0
    return (p_o - p_e) / (1 - p_e)

# $ python3 judge.py --kappa
#   observed agreement p_o        = 0.8000
#   chance agreement  p_e         = 0.5711  (from the real PASS rates)
#   kappa = (p_o - p_e)/(1 - p_e) = 0.5337
#   same kappa for the stamp      = 0.0000  (no skill -> zero, as it must)
```

run: 2026-08-22 · fixture, no model call · n=30 · `python3 judge.py --kappa`

This is called **Cohen's kappa**. Reading the symbols: `(p_o - p_e)/(1 - p_e)` looks like notation but it is a rescaling — take the agreement you saw, subtract the agreement luck would give, then divide by the room that was left above luck, so that landing exactly at chance scores 0 and landing at perfect scores 1. The chance agreement here is 0.5711, not 0.5, because the judge passes a lot and so does the gold, so two lenient raters collide on PASS more often than a coin would. The judge's kappa is 0.5337.

Bracket for 0.5337: chance level is 0 by construction — a judge no better than luck scores `(p_e - p_e)/(1 - p_e) = 0` — the floor for a useless judge is 0 and the ceiling is 1. Real-world size: 0.53 sits in the "moderate" band of the Landis-Koch scale (0.4-0.6), and published LLM-judge calibrations land anywhere from 0.4 to 0.8 depending on how hard the task is. The stamp at 0 is the baseline; hold it.

**A grader you have not measured against the truth is not a measurement — it is a second opinion with no track record.**

### The interval kappa needs — reuse the bootstrap

A single kappa on 30 cases is one draw. evals-inter-01's bootstrap resamples the cases and recomputes, and it drops straight onto kappa.

```
# judge.py:126-135 — COMPLETE (the inter-01 bootstrap, now recomputing kappa)
def bootstrap_kappa_ci(cases, rng):
    """Resample the 30 cases with replacement, recompute kappa, 10000 times."""
    n = len(cases)
    boots = []
    for _ in range(BOOT):
        resample = [cases[rng.randrange(n)] for _ in range(n)]
        boots.append(cohen_kappa(resample))
    boots.sort()
    return percentile(boots, 2.5), percentile(boots, 97.5)

# kappa 95% CI (bootstrap)      = [0.1892, 0.8305]  seed=0, B=10000
```

run: 2026-08-22 · bootstrap seed=0, B=10000 · n=30 · `python3 judge.py --calibrated`

The interval is `[0.1892, 0.8305]`, and its width is the point. On 30 cases the judge's kappa could be 0.19 — barely better than the stamp — or 0.83 — near-perfect. Three whole Landis-Koch bands. The point estimate 0.53 is real, but anyone who reports it without the interval is claiming a precision 30 cases do not buy.

<svg viewBox="0 0 680 172" role="img" aria-label="A number line from 0 to 1 divided into four kappa bands, poor-to-fair, moderate, substantial and near-perfect, with the point estimate 0.53 marked and a wide confidence whisker running from 0.19 to 0.83 spanning three bands">
  <g font-family="var(--mono)">
    <text x="90" y="30" font-size="10.5" fill="var(--muted)">Cohen's kappa on the Landis-Koch bands</text>
    <rect x="90" y="44" width="212" height="26" fill="var(--grid)" opacity="0.35"></rect>
    <rect x="302" y="44" width="106" height="26" fill="var(--s1)" opacity="0.30"></rect>
    <rect x="408" y="44" width="106" height="26" fill="var(--grid)" opacity="0.35"></rect>
    <rect x="514" y="44" width="106" height="26" fill="var(--grid)" opacity="0.20"></rect>
    <g font-size="8.5" fill="var(--muted)" text-anchor="middle"><text x="196" y="61">poor-fair</text><text x="355" y="61">moderate</text><text x="461" y="61">substantial</text><text x="567" y="61">near-perfect</text></g>
    <g font-size="9" fill="var(--muted)" text-anchor="middle"><text x="90" y="92">0.0</text><text x="302" y="92">0.4</text><text x="408" y="92">0.6</text><text x="514" y="92">0.8</text><text x="620" y="92">1.0</text></g>
    <line x1="190" y1="116" x2="530" y2="116" stroke="var(--ink)" stroke-width="2"></line>
    <line x1="190" y1="108" x2="190" y2="124" stroke="var(--ink)" stroke-width="2"></line>
    <line x1="530" y1="108" x2="530" y2="124" stroke="var(--ink)" stroke-width="2"></line>
    <circle cx="373" cy="116" r="5" fill="var(--acc)"></circle>
    <text x="373" y="140" font-size="10" text-anchor="middle" fill="var(--acc-ink)">0.53</text>
    <text x="190" y="140" font-size="9" text-anchor="middle" fill="var(--muted)">0.19</text>
    <text x="530" y="140" font-size="9" text-anchor="middle" fill="var(--muted)">0.83</text>
    <rect x="410" y="150" width="210" height="20" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="515" y="164" font-size="10" text-anchor="middle" fill="var(--acc-ink)">CI spans 3 bands on n=30</text>
  </g>
</svg>
^ The judge's kappa point estimate and its 95% bootstrap interval, against the standard bands. The whisker crosses from "poor-to-fair" to "near-perfect".

How to read this: the dot is the headline, the whisker is the truth. The diagnostic is whether the whisker stays inside one band; here it crosses three, so "the judge is moderate" is a claim n=30 cannot make.

### What kappa still hides — the direction of the error

Kappa is one number, and it is symmetric: it does not say whether the judge is too harsh or too lenient. The confusion table does, and two more counts read it off.

```
# judge.py:103-116 — COMPLETE (which way the judge is wrong, and what it costs)
def leniency(cases):
    """How many more PASSes the judge hands out than the gold. Positive = the
    judge is lenient (passes answers the gold failed)."""
    judge_pass = sum(1 for c in cases if c["judge"] == "PASS")
    gold_pass = sum(1 for c in cases if c["human"] == "PASS")
    return judge_pass, gold_pass, judge_pass - gold_pass

def failure_catch_rate(cases):
    """Of the answers the gold FAILED, what fraction did the judge also fail?"""
    gold_fail = [c for c in cases if c["human"] == "FAIL"]
    caught = sum(1 for c in gold_fail if c["judge"] == "FAIL")
    return caught, len(gold_fail)

# failure-catch rate            = 6/11 = 0.5455
# leniency: judge passes 23, gold passes 19  (+4, the judge is lenient)
```

run: 2026-08-22 · fixture, no model call · n=30 · `python3 judge.py --calibrated`

The judge passes 23 where the gold passes 19: it is lenient by 4, systematically waving bags through. And of the 11 answers that should have failed, it caught 6 — a **failure-catch rate** of 0.5455, meaning it missed 5. That is the number that should stop you: if you use this judge as a quality gate, nearly half of everything bad sails past, and kappa's single 0.53 never said so out loud.

*"But hold on,"* you say, *"80% agreement is fine for shipping — I'm not chasing the last few percent."* Good question. No: the 0.6333 is free and the 20% it gets wrong is not spread evenly — it is concentrated exactly on the failures, the cases the gate exists to catch. A grader that is right about the easy passes and wrong about the hard fails is worse than useless at a gate, because it looks trustworthy while leaking.

**Kappa is one number, and one number cannot tell you which way a judge is wrong — the confusion table can.**

### Two routes to kappa, and the stamp assertion

A printed number is a claim, so `--check` computes kappa twice — from the `p_o`/`p_e` formula and straight off the confusion counts — and runs the stamp assertion that catches the balanced-chance bug.

```
# $ python3 judge.py --check
#   kappa via formula             = 0.533679
#   kappa via confusion counts    = 0.533679
#   routes agree                  = True
#   rubber-stamp kappa, correct   = 0.0000  (must be 0)
#   rubber-stamp kappa, p_e=0.5   = 0.2667  (the bug: not 0 -> inflated)
#   kappa CI run 1                = [0.1892, 0.8305]
#   kappa CI run 2 (same seed)    = [0.1892, 0.8305]
#   deterministic under seed      = True
# SELF-TEST PASS  routes_agree=True  stamp_zero=True  deterministic=True
```

run: 2026-08-22 · seed=0, B=10000 · n=30 · `python3 judge.py --check`

Both routes print 0.533679, the correct stamp scores 0 and the buggy one scores 0.2667, and the CI is identical across two runs at the same seed. The self-test passes on all three.

### The running tally

| read | what it looks at | verdict | number |
|---|---|---|---|
| #1 raw agreement | matches / total | trust it, 80% | 0.8000 |
| #2 kappa | agreement above chance | moderate skill | 0.5337, stamp at 0 |
| #3 kappa + CI + catch | skill, uncertainty, direction | triage only | 0.5337 [0.19, 0.83], catch 6/11, +4 lenient |

The verdict flips at #1 → #2: raw agreement said "trust it", kappa said "moderate", and the flip cost one idea — subtract the free score a stamp gets. And yet — kappa 0.53 is still a point estimate the CI says we cannot pin, and the catch rate 6/11 has its own interval no one has drawn.

### Bridge to the standard names

Nobody outside this module calls the judge a metal detector. **Cohen's kappa** is exactly that name, `sklearn.metrics.cohen_kappa_score` computes it, and the 0.0/0.2/0.4/0.6/0.8 cut points are the **Landis-Koch** bands. For more than two labels or ordered ones you would reach for **weighted kappa** or **Krippendorff's alpha**; the failure-catch rate is **recall** (or sensitivity) on the FAIL class; leniency is a form of **rater bias**. If you fit the judge against a panel of humans instead of one gold column, the same kappa generalises to **Fleiss' kappa**.

### What we did not settle

Kappa has a known trap of its own, the **kappa paradox**: when the base rate is extreme — 99% of answers pass — even a good judge can score a low kappa because there is almost no room above chance. Our base rate, 19-to-11, is only mildly skewed, so we are clear of it, but on a suite where almost everything passes you must report the base rate beside the kappa or the number misleads the other way.

Three more open ends. The judge column is a fixture, so this measures the calibration *method* honestly and this particular judge only as of these stored calls; a real judge is stochastic and needs several calls per case to get its own temperature spread, which is inter-01's bootstrap pointed at the judge instead of the cases. The catch rate 6/11 is on 11 cases — its interval is enormous and I did not draw it. And a single gold column is one annotator; genuine calibration uses two or three humans and measures their agreement first, because a judge cannot be more reliable than the labels it is scored against. If the kappa-versus-raw-agreement distinction still feels slippery, that is the right reaction — it is the one idea the module turns on, and everything else is counting the four cells.

## Build

The pipeline in one paragraph: take a set of answers with gold labels; run your judge over them for a PASS/FAIL each; count the 2x2 table; report kappa with a bootstrap interval, the failure-catch rate, and the leniency, never the raw agreement alone.

We opened on one command that calibrates the judge and prints why 80% is the wrong number to trust. The payoff block (again):

```
# modules/evals-and-statistics/code/evals-inter-02/ — COMPLETE, run from that directory
$ python3 judge.py --calibrated
...
  raw agreement                 = 0.8000
  Cohen's kappa                 = 0.5337
  kappa 95% CI (bootstrap)      = [0.1892, 0.8305]  seed=0, B=10000
  failure-catch rate            = 6/11 = 0.5455  (gold FAILs the judge caught)
  leniency: judge passes 23, gold passes 19  (+4, the judge is lenient)
  VERDICT: kappa 0.53 is moderate, and the judge misses 5 of 11 bad answers.
```

Now point it at your own judge. The one dial is `labels.json`: label 30 of your own cases by hand (that column is the gold), run your real LLM judge over the same answers, and store its PASS/FAIL as the `judge` column. Everything in `judge.py` derives from that file. This is the one module in the track that costs money to reproduce — a judge call per case — so budget it, and keep the calls committed so the numbers stay checkable.

Your number to beat is not the kappa. It is whether your judge clears its own rubber stamp by a margin the CI can see. Run `--agreement` and read the free score; run `--calibrated` and check the interval. If your kappa CI includes the stamp's 0, you have not shown the judge has any skill yet — you have shown 30 cases cannot tell. Bring back the kappa, its interval, and the failure-catch rate, and never quote the raw agreement without the stamp beside it. Good luck.

### FAQ

**Why not just report agreement — 80% is easy to explain?** Because 63% of it is free, and the easy explanation hides that the judge misses 5 of 11 failures. Explaining a misleading number well is worse than explaining a right one.

**Is an LLM judge grading LLM output not circular?** The judge sees only text and a rubric, not the generator, and here it is scored against a gold column it never saw — that scoring is the whole point. A judge you have calibrated is a tool; a judge you have not is the circularity.

**My kappa CI includes zero — is the judge useless?** Unknown, which is the honest answer: 30 cases could not separate it from the stamp. Label more cases; the CI narrows with n, exactly as inter-01's did.

**Why is mine slow?** This script is not — it is a fixture. Yours will be slow because it calls a model once per case; that cost is real and it is why you commit the calls and re-run the stats offline.

### Errata

Version one, dated 2026-08-22. The judge fixture is built lenient on purpose (misses 5, false-alarms 1) so the leniency and catch-rate numbers have something to show; a judge that were harsh instead would flip the sign of the leniency and the same report would catch it. One soft spot left in: the `confusion` function names its cells `tp/fp/fn/tn` from the gold's point of view with PASS as the positive class, which is a convention worth stating twice because getting it backwards silently swaps "miss" and "false alarm" in every line below.

## Definition of done

- [ ] `labels.json` for your own judge: 30 cases with a hand-made gold column and your judge's real PASS/FAIL, committed before the first statistic
- [ ] The judge's calls are committed so the numbers reproduce offline
- [ ] Cohen's kappa reported with chance agreement computed from the real PASS rates, never assumed 0.5
- [ ] A bootstrap CI on the kappa, and a note on whether it clears the rubber stamp's 0
- [ ] The failure-catch rate and the leniency direction reported beside the kappa
- [ ] `python3 judge.py --check` printing SELF-TEST PASS, so kappa is derived twice and the stamp scores 0
- [ ] A run stamp under every published number: date · seed and B · n · the command
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A judge agrees with the gold on 80% of cases. Say why that is not 80% of skill, and name the baseline that measures the difference.
2. Chance agreement here is 0.5711, not 0.5. Explain where 0.5711 comes from and why assuming 0.5 inflates every kappa on skewed data.
3. Give the one-line assertion that catches the balanced-chance bug, and say what number the buggy version prints for a rubber-stamp judge.
4. Kappa is 0.53 and symmetric. Name the two numbers that tell you the judge is lenient rather than harsh, and which cell of the confusion table each reads.
5. Your own run printed a kappa CI. What was it, did it clear the rubber stamp's zero, and how many Landis-Koch bands did it span?

## External resources

- Jacob Cohen, *A Coefficient of Agreement for Nominal Scales* (1960) — https://doi.org/10.1177/001316446002000104 — my summary: the original kappa paper; the one idea is subtracting chance agreement, and it is worth reading how carefully Cohen defines "chance" from the marginals, which is exactly the line the planted bug gets wrong.
- Landis & Koch, *The Measurement of Observer Agreement for Categorical Data* (1977) — https://doi.org/10.2307/2529310 — my summary: the source of the poor/fair/moderate/substantial/near-perfect bands this module draws; note the authors themselves call the cut points arbitrary, so treat the band names as vocabulary, not law.
- sklearn.metrics.cohen_kappa_score — https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html — my summary: the library version of what judge.py computes by hand, with a `weights` argument for the ordinal case; read against the corpus-bias rule as the mainstream cross-check on the hand implementation.
