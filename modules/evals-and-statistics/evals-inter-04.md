---
id: evals-inter-04
title: The rubric tied them — until you weigh which checks they failed
topic: evals-and-statistics
level: intermediate
status: ready
eli5: Two students with the same GPA — but one failed the required course. The average hid it; graduation requirements didn't.
time: 8-10h
summary: Two systems score an identical 0.9333 on the same six-check rubric, a dead tie — until you notice A's misses are all on critical checks and B's on cosmetic ones, so a critical gate splits them 0.60 to 1.00 at p=0.0002, because the equal-weight mean was silently calling a wrong answer and a formatting nitpick the same 1/6.
---

## Why this module

evals-basic-01 built a six-check rubric and scored each case as the fraction of checks it passed — every check worth exactly 1/6. That was the right start and the wrong finish: it treats a grounding failure (the answer cites nothing real) exactly like a length-band miss (the answer runs four words long). `CURRICULUM.md`'s Track 1.1 is "rubric evals for output quality", and the quality of a rubric is mostly in the part basic-01 skipped — how the per-criterion results get combined into one number. The scan found the same reflex in the labs' own rubric verdicts: many criteria, averaged flat.

This module fixes the aggregation at `intermediate`. Two systems are graded by basic-01's six checks on the same 30 cases, and you score them three ways — an equal-weight mean, a weighted mean, and a critical gate — and watch the winner change. What it omits: no new checks, no partial credit within a check (each is still pass/fail), and no live model calls — the results are a fixture. You need basic-01's rubric and inter-01's paired bootstrap. Stdlib Python 3, offline, $0.00, about two seconds a run, one sitting. The hard part is one uncomfortable idea: the mean you have been reporting is itself a strong claim about your criteria, and it is usually false.

By the end, one command scores the two systems three ways and shows the tie become a rout. Skipping ahead:

```
# modules/evals-and-statistics/code/evals-inter-04/ — COMPLETE, run from that directory
$ python3 rubric.py --all

cases=30  checks=6  systems=A,B  file=graded.json  (results are a fixture)

THREE AGGREGATIONS OF THE SAME SIX CHECKS
------------------------------------------------------------
  aggregation        A        B        winner
  equal-weight mean  0.9333   0.9333   TIE
  weighted mean      0.9143   0.9714   B
  critical gate      0.6000   1.0000   B
------------------------------------------------------------
  same 360 check results, three totals: from a dead TIE to a rout.
  the aggregation is not a display choice -- it is the rubric.
```

run: 2026-08-22 · results are a fixture · scorer is deterministic · n=30 cases x 6 checks x 2 systems · `python3 rubric.py --all`

Three rows, one set of check results. The equal-weight mean calls it a perfect tie. The critical gate calls it 0.60 against 1.00. Nothing about the two systems changed between those rows — only the function that added up their checks. This module is about why that function is the most consequential line in your eval, and how to pick it on purpose.

## Concepts

Named here so you can find them again; each is built, and one is broken, below.

- **Aggregation** — the function that turns per-criterion results into one score. The rubric's real content.
- **Equal-weight mean** — every check worth 1/N; basic-01's rule, and the trap.
- **Weighted mean** — critical checks worth more than cosmetic ones.
- **Critical gate** — a case passes only if every must-pass check passes, whatever the rest do.
- **Compensatory vs non-compensatory** — whether a good score can offset a bad one (the mean) or not (the gate).
- **Any/all gate inversion** — writing the gate to fail only when *all* critical checks fail. The planted bug.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — `modules/evals-and-statistics/code/evals-basic-01/` (the six-check rubric whose per-check results this module aggregates) and `code/evals-inter-01/` (the paired bootstrap reused for the gate's interval).

Source: faisalmahdy/second-brain-through-agents — the 10-persona rubric harness whose verdicts average many criteria; and faisalmahdy/agent — `docs/EVAL.md`, the rubric-judge specs. De-personalized, described only as far as the curriculum states.

Script and fixtures: `modules/evals-and-statistics/code/evals-inter-04/` — `rubric.py`, 273 lines, `graded.json`, 30 cases with a six-check result string per system. Every command runs from there.

### Install the frame: a report card, not a single grade

In my opinion, the best way to think of a multi-criterion rubric score is as a school transcript, not a single grade.

A flat GPA averages every course: an A in gym can offset an F in the core subject, and two students with wildly different transcripts land on the same number. A weighted GPA lets honors courses count for more. And graduation requirements ignore the average entirely — fail the one required course and you do not graduate, no matter how high your GPA. Those are three different questions you can ask of the same report card, and they can name three different "best students". A rubric is a report card, and picking the mean is picking the flat GPA — the rule that lets gym offset the failed core class.

Three jobs, one line each: the mean says "how many checks passed, on average?", the weight says "how much does each check actually matter?", and the gate says "did the answer clear the checks it is not allowed to fail?"

### Look at the data: two systems, the same six checks

The six checks are basic-01's: C1 cites a real page, C2 cites the specific required page, C3 has the key facts, C4 makes no known error, C5 refuses honestly when it must, C6 is well-formed. Four of them are **critical** — C1, C3, C4, C5, the ones where a failure means the answer is ungrounded, wrong, or dishonest. Two are **cosmetic** — C2 and C6, nice to have. Each system's result on a case is a six-character string, `1` pass and `0` fail, in C1..C6 order.

```
# rubric.py:47-53 — COMPLETE (which checks a system passed on one case)
def passed(case, system, config):
    """The set of check ids this system passed on this case."""
    order = config["order"]
    marks = case[system]
    return {order[i] for i, ch in enumerate(marks) if ch == "1"}
```

Hold one case for the whole module: F09, the DeepSeek parameter-count question from basic-01, where the wrong answer says 137B active parameters and the truth is 37B. System A's result is `111011` — it passes everything except C4, the no-known-error check, because it asserts the 137B error. System B's is `111110` — it passes everything except C6, well-formed. Both failed exactly one check. Count the passes and they are identical: five of six.

<svg viewBox="0 0 680 236" role="img" aria-label="Two rows, system A and system B, of the six rubric checks grouped into four critical checks and two cosmetic checks. A fails one critical check C4; B fails one cosmetic check C6. Both fail exactly one check.">
  <g font-family="var(--mono)">
    <rect x="96" y="34" width="340" height="182" rx="8" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <rect x="452" y="34" width="176" height="182" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="266" y="26" font-size="10.5" text-anchor="middle" fill="var(--acc-ink)">CRITICAL — must pass</text>
    <text x="540" y="26" font-size="10.5" text-anchor="middle" fill="var(--muted)">COSMETIC</text>
    <g font-size="10.5" fill="var(--muted)" text-anchor="middle">
      <text x="136" y="54">C1</text><text x="211" y="54">C3</text><text x="286" y="54">C4</text><text x="361" y="54">C5</text><text x="492" y="54">C2</text><text x="588" y="54">C6</text>
    </g>
    <g font-size="8.5" fill="var(--faint, var(--muted))" text-anchor="middle">
      <text x="136" y="66">w3</text><text x="211" y="66">w3</text><text x="286" y="66">w3</text><text x="361" y="66">w3</text><text x="492" y="66">w1</text><text x="588" y="66">w1</text>
    </g>
    <text x="60" y="112" font-size="11" text-anchor="end" fill="var(--ink)">A</text>
    <text x="60" y="180" font-size="11" text-anchor="end" fill="var(--ink)">B</text>
    <g font-size="15" text-anchor="middle">
      <text x="136" y="117" fill="var(--muted)">✓</text><text x="211" y="117" fill="var(--muted)">✓</text><text x="286" y="117" fill="var(--acc)" font-size="18">✗</text><text x="361" y="117" fill="var(--muted)">✓</text><text x="492" y="117" fill="var(--muted)">✓</text><text x="588" y="117" fill="var(--muted)">✓</text>
      <text x="136" y="185" fill="var(--muted)">✓</text><text x="211" y="185" fill="var(--muted)">✓</text><text x="286" y="185" fill="var(--muted)">✓</text><text x="361" y="185" fill="var(--muted)">✓</text><text x="492" y="185" fill="var(--muted)">✓</text><text x="588" y="185" fill="var(--acc)" font-size="18">✗</text>
    </g>
    <rect x="96" y="200" width="532" height="0" fill="none"></rect>
    <text x="266" y="216" font-size="9.5" text-anchor="middle" fill="var(--acc-ink)">A's one miss lands here</text>
    <text x="540" y="216" font-size="9.5" text-anchor="middle" fill="var(--muted)">B's one miss lands here</text>
  </g>
</svg>
^ Case F09, both systems. Each fails exactly one of six checks — but A's miss is a critical check (the answer is factually wrong) and B's is cosmetic (formatting).

How to read this: the two rows have the same number of ✗ marks, which is all the equal-weight mean can see. The whole module is in *which column* the ✗ sits: A's is in the tinted critical band, B's is not.

### Strategy #1 — the equal-weight mean. A perfect tie.

Score each case as the fraction of six checks it passed, then average over the 30. This is exactly basic-01's number.

```
# rubric.py:56-58 — COMPLETE (every check worth 1/6)
def mean_score(case, system, config):
    """Fraction of the six checks passed. Every check weighted the same."""
    return len(passed(case, system, config)) / len(config["order"])

# $ python3 rubric.py --mean
#   system A  = 0.9333
#   system B  = 0.9333
#   winner    = TIE
```

run: 2026-08-22 · fixture, deterministic · n=30 · `python3 rubric.py --mean`

This is the **equal-weight mean**, and on F09 both systems score 5/6 = 0.833; across all 30 they land on an identical 0.9333. Now the prediction — commit before the next section. The two systems tie to four decimals on the rubric everyone would report. Are they equally good? Most people say yes; a tie is a tie. The answer is at the top of the next section, and it is not a tie.

Bracket for 0.9333: chance level is not defined here (no random baseline), the floor is 0.0 and the ceiling 1.0 for a system that passes every check on every case. Real-world size: 0.9333 is the number that goes on the slide, and it is the same number for a system that ships wrong answers and one that ships ugly-but-correct ones. Hold it — it is the number the next two aggregations have to overturn.

**A mean treats every criterion as equally important, and no rubric's criteria ever are.**

### Strategy #2 — weight what matters. B pulls ahead.

The equal-weight mean made a choice — every check counts 1/6 — and it made it silently. Make a different choice out loud: a critical check is worth 3, a cosmetic one worth 1.

```
# rubric.py:61-66 — COMPLETE (sum the weights of the passed checks)
def weighted_score(case, system, config):
    """Sum of the weights of the passed checks, over the total weight."""
    w = config["weights"]
    got = sum(w[c] for c in passed(case, system, config))
    total = sum(w.values())
    return got / total

# $ python3 rubric.py --weighted
#   system A  = 0.9143
#   system B  = 0.9714
#   winner    = B
```

run: 2026-08-22 · fixture, deterministic · n=30 · `python3 rubric.py --weighted`

This is a **weighted mean**. Reading the symbols: `sum(weights of passed) / sum(all weights)` is "of the 14 total weight on a case, how much did the passed checks carry?" — the four criticals are worth 3 each and the two cosmetics 1 each, so the denominator is 4·3 + 2·1 = 14. On F09, A missed C4 (weight 3) and scores 11/14 = 0.786; B missed C6 (weight 1) and scores 13/14 = 0.929. Same one miss each, very different price. Across the 30, B leads 0.971 to 0.914 — the tie is already broken, and only the weights changed.

*"But hold on,"* you say, *"the weights are made up — who says grounding is worth exactly three formatting checks?"* Good question. Yes, the 3-and-1 are a judgment, and a different shop would pick different numbers. No, that does not make the equal-weight mean the neutral default: the mean is also a weighting — the one that asserts every check is *exactly* equal, which is a strong claim and, for these six, plainly false. There is no unweighted score. There is only a weighting you chose and one you inherited.

### Strategy #3 — the gate. Write down what may not fail.

Weights still let a good score offset a bad one — enough cosmetic passes can paper over a critical miss. Some failures should not be offsettable at all. A **critical gate** says a case passes only if every critical check passes, whatever the cosmetics do. Here is the gate with its rule blanked — fill it in before reading on.

```
# rubric.py:69-73 — STUB, the line you write first (committed body below)
def gate_pass(case, system, config):
    p = passed(case, system, config)
    # your turn: the case passes only if WHICH critical checks passed?
    ...
```

You require *all* of them. The gate passes a case only when every critical check is in the passed set; one missing critical fails it, no matter how many cosmetics passed.

```
# rubric.py:69-73 — COMPLETE (every critical check must pass)
def gate_pass(case, system, config):
    """A case passes iff EVERY critical check passed. A cosmetic miss is fine;
    a critical miss fails the whole case."""
    p = passed(case, system, config)
    return all(c in p for c in config["critical"])

# $ python3 rubric.py --gate
#   system A gate-pass rate = 0.6000
#   system B gate-pass rate = 1.0000
#   paired difference B - A = +0.4000
#   95% CI (bootstrap)      = [+0.2333, +0.5667]  seed=0, B=10000
#   sign test: B passes 12 cases A failed, A passes 0 B failed, ties 18
#   sign-test p (exact)     = 0.000244
```

run: 2026-08-22 · fixture; bootstrap seed=0, B=10000 · n=30 · `python3 rubric.py --gate`

On F09, A fails the gate (its C4 miss is critical) and B passes it (its C6 miss is cosmetic). Across the 30, A clears the gate on 0.60 of cases and B on 1.00 — the same systems the mean tied, now 40 points apart. This is the answer to the prediction, and the size of the surprise is the point: the mean said a dead tie to four decimals; the gate says B by 0.40, on 12 discordant cases all in B's favour, at p=0.0002. Not a close call the mean rounded off — a rout the mean was structurally blind to, because averaging let A's cosmetic passes buy back its critical failures.

This is called a **non-compensatory** rule: a good score cannot compensate for a critical miss. The mean and the weighted mean are **compensatory** — enough small passes offset a big fail. The gate is the graduation requirement; the mean is the GPA.

<svg viewBox="0 0 680 150" role="img" aria-label="A number line for the paired gate difference from -0.1 to +0.7 with zero marked; the B-minus-A interval runs from +0.233 to +0.567 with the point estimate at +0.40, entirely right of zero.">
  <g font-family="var(--mono)">
    <text x="90" y="30" font-size="10.5" fill="var(--muted)">gate-pass difference B - A (paired over the 30 cases)</text>
    <line x1="90" y1="86" x2="620" y2="86" stroke="var(--grid)" stroke-width="1.5"></line>
    <g font-size="9" fill="var(--muted)" text-anchor="middle"><text x="156" y="104">0.0</text><text x="287" y="104">+0.2</text><text x="419" y="104">+0.4</text><text x="550" y="104">+0.6</text></g>
    <line x1="156" y1="70" x2="156" y2="102" stroke="var(--acc)" stroke-width="1.4" stroke-dasharray="3 3"></line>
    <text x="156" y="66" font-size="9.5" text-anchor="middle" fill="var(--acc-ink)">zero</text>
    <line x1="309" y1="86" x2="529" y2="86" stroke="var(--ink)" stroke-width="2.5"></line>
    <line x1="309" y1="78" x2="309" y2="94" stroke="var(--ink)" stroke-width="2.5"></line>
    <line x1="529" y1="78" x2="529" y2="94" stroke="var(--ink)" stroke-width="2.5"></line>
    <circle cx="419" cy="86" r="4.5" fill="var(--ink)"></circle>
    <text x="419" y="128" font-size="10" text-anchor="middle" fill="var(--ink)">+0.40  [+0.233, +0.567]</text>
    <rect x="430" y="112" width="190" height="20" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="525" y="126" font-size="9.5" text-anchor="middle" fill="var(--acc-ink)">clears zero · sign p=0.0002</text>
  </g>
</svg>
^ The gate gap the mean hid, with its paired 95% interval — the same inter-01 machinery, pointed at the gate outcome per case.

How to read this: the diagnostic is the left end against zero. It clears by 0.233, and the interval is entirely positive, so B's edge under the gate is real, not the luck of which 30 cases. The mean's tie has no interval that could ever have shown this — it was measuring the wrong thing.

### The planted bug: a gate that lets the wrong answers through

The gate is one line, so it is one line to get backwards. Write it as "the case fails only if *all* the critical checks fail" and watch what happens.

```
# rubric.py:76-81 — COMPLETE (the bug: any/all inverted)
def gate_pass_buggy(case, system, config):
    """THE BUG: 'fails only if ALL critical checks fail' — an any/all swap.
    A case that fails a single critical check still passes, so ungrounded and
    wrong answers sail through."""
    p = passed(case, system, config)
    return not all(c not in p for c in config["critical"])

# $ python3 rubric.py --bug
#   system A gate-pass, correct (any critical miss fails) = 0.6000
#   system A gate-pass, buggy  (only all-critical-miss fails) = 1.0000
```

run: 2026-08-22 · fixture, deterministic · n=30 · `python3 rubric.py --bug`

Stop here. The buggy gate gives system A a perfect 1.0000 — every case passes. Why is that wrong, and not just lenient? Because `not all(c not in p ...)` reads as "not (every critical check is missing)", which is true the moment *any* critical check passed — so a case that failed C4 but passed the other three criticals sails through. The gate you wanted requires all criticals to pass; the gate you wrote only requires one to. On F09, A fails just C4 and keeps C1, C3, C5, so the buggy gate waves it through — the factually wrong answer passes the quality gate. The minimal reproducer:

```
# a gate sketch — COMPLETE, watch the any/all swap
critical = {"C1", "C3", "C4", "C5"}
passed_set = {"C1", "C3", "C5", "C2", "C6"}          # failed C4 only
correct = all(c in passed_set for c in critical)     # False — good, it failed
buggy   = not all(c not in passed_set for c in critical)  # True — waved through
```

It hides because most cases pass everything (both gates agree), and a case that fails *every* critical does fail both — so the bug only bites the cases with a single critical miss, which are exactly the ones the gate exists to catch. Named: the **any/all gate inversion**. The one-line assertion: any case with a missing critical check must fail the gate. `--check` runs it over all 60 system-cases:

```
# $ python3 rubric.py --check
#   A mean via per-case    = 0.933333
#   A mean via flat pool   = 0.933333
#   routes agree           = True
#   correct gate: critical-miss cases that still passed = 0   (must be 0)
#   buggy gate:   critical-miss cases that still passed = 12  (the bug)
#   gate CI run 1          = [+0.2333, +0.5667]
#   gate CI run 2          = [+0.2333, +0.5667]
#   deterministic          = True
# SELF-TEST PASS  routes_agree=True  gate_sound=True  deterministic=True
```

run: 2026-08-22 · seed=0, B=10000 · n=30 · `python3 rubric.py --check`

The mean agrees to six places by two routes, the correct gate lets zero critical-miss cases pass while the buggy one lets 12 through, and the interval is identical across two seeded runs.

### The running tally

| aggregation | A | B | winner |
|---|---|---|---|
| equal-weight mean | 0.9333 | 0.9333 | TIE |
| weighted mean | 0.9143 | 0.9714 | B |
| critical gate | 0.6000 | 1.0000 | B (+0.40, p=0.0002) |

<svg viewBox="0 0 680 200" role="img" aria-label="Three rows — equal-weight mean, weighted mean, and critical gate — each plotting system A and system B on a 0 to 1 scale. On the mean the two coincide as a tie near 0.93; on the weighted mean they separate slightly; on the gate they split from 0.60 to 1.00.">
  <g font-family="var(--mono)">
    <text x="140" y="24" font-size="10.5" fill="var(--muted)">A and B under each aggregation (score, 0 to 1)</text>
    <line x1="140" y1="172" x2="620" y2="172" stroke="var(--grid)"></line>
    <g font-size="9" fill="var(--muted)" text-anchor="middle"><text x="140" y="188">0.0</text><text x="380" y="188">0.5</text><text x="620" y="188">1.0</text></g>
    <text x="128" y="66" font-size="10" text-anchor="end" fill="var(--ink)">mean</text>
    <line x1="140" y1="62" x2="620" y2="62" stroke="var(--grid)" stroke-dasharray="2 4"></line>
    <circle cx="588" cy="62" r="5" fill="var(--muted)"></circle>
    <text x="588" y="50" font-size="9" text-anchor="middle" fill="var(--muted)">A = B  0.93  (tie)</text>
    <text x="128" y="112" font-size="10" text-anchor="end" fill="var(--ink)">weighted</text>
    <line x1="140" y1="108" x2="620" y2="108" stroke="var(--grid)" stroke-dasharray="2 4"></line>
    <line x1="579" y1="108" x2="606" y2="108" stroke="var(--line)" stroke-width="1.5"></line>
    <circle cx="579" cy="108" r="4.5" fill="var(--s1)"></circle>
    <circle cx="606" cy="108" r="4.5" fill="var(--s2)"></circle>
    <text x="128" y="158" font-size="10" text-anchor="end" fill="var(--ink)">gate</text>
    <line x1="140" y1="154" x2="620" y2="154" stroke="var(--grid)" stroke-dasharray="2 4"></line>
    <line x1="428" y1="154" x2="620" y2="154" stroke="var(--acc-line)" stroke-width="1.6"></line>
    <circle cx="428" cy="154" r="4.5" fill="var(--s1)"></circle>
    <circle cx="620" cy="154" r="4.5" fill="var(--s2)"></circle>
    <text x="428" y="144" font-size="9" text-anchor="middle" fill="var(--s1)">A 0.60</text>
    <text x="614" y="144" font-size="9" text-anchor="end" fill="var(--s2)">B 1.00</text>
  </g>
</svg>
^ The same two systems under three aggregations — coincident on the mean, edging apart when weighted, split wide at the gate.

How to read this: the left dot in each row is A (var s1), the right is B (var s2); the mean's single grey dot is the two landing on the same score. The failure signature is a row where the two dots sit on top of each other — a tie that a stricter rule would tear open.

Nothing in the check results moved between rows — only the aggregation. The tie was never a fact about the systems; it was a fact about the mean. And yet — the weights and the critical set are choices I made, and a different set would move these numbers.

**The aggregation function is not how you display the score — it is the rubric. Choose it before you grade, not after you see who won.**

### Bridge to the standard names

Nobody outside this module calls it a report card. The equal-weight and weighted means are **compensatory** scoring rules — the decision literature's term for "a strength can offset a weakness"; the gate is **non-compensatory**, or a **conjunctive** rule (all must-pass conditions ANDed together). Practitioners call the critical checks **hard constraints** or **must-pass criteria**, and a gated eval a **guardrail** or **blocking** check, as opposed to the **scored** ones. `sklearn` and eval frameworks will happily average your criteria for you; none of them will tell you the average was the wrong rule.

### What we did not settle

The weights are hand-set, and picking them honestly is the real work a rubric owner does — ideally from what each failure actually costs downstream, not from a round number. Two more axes we left closed: partial credit within a check (each is still binary pass/fail here, where a graded 0/1/2 would carry more) and a tiered gate (must-pass, should-pass, nice-to-have) instead of the two tiers used here. And the mean is not useless — when criteria genuinely are exchangeable, it is the right rule; the error is reaching for it by default when they are not. If the compensatory-versus-gate distinction still feels abstract, that is the correct reaction: it is the one idea the module turns on, and everything else is counting checks three ways.

## Build

The pipeline in one paragraph: grade each system's outputs with your per-criterion checks; mark which criteria are critical; score the cases by an equal-weight mean, a weighted mean, and a critical gate; report all three, put a paired interval on the gate gap, and choose the aggregation before you look at who won.

We opened on one command that scores the two systems three ways. The payoff block (again):

```
# modules/evals-and-statistics/code/evals-inter-04/ — COMPLETE, run from that directory
$ python3 rubric.py --all
...
  aggregation        A        B        winner
  equal-weight mean  0.9333   0.9333   TIE
  weighted mean      0.9143   0.9714   B
  critical gate      0.6000   1.0000   B
```

Now point it at your own rubric. The one dial is `graded.json`: run your per-criterion checks over two of your own systems, store each system's pass/fail string per case, and mark your critical checks in `_config`. Everything in `rubric.py` derives from that file. Keep the cosmetic checks in — they are what makes the tie possible and the lesson visible.

Your number to beat is not a score — it is the **gap between your aggregations**. Run `--mean` and `--gate`: if the mean ranks your systems one way and the gate another, the mean was hiding which system ships broken answers, and the gate is the one to trust for a quality bar. If they agree, your systems fail on the same kinds of checks and the aggregation did not matter this time — but you now know that, instead of assuming it. Bring back all three numbers and which critical checks moved the gate. Good luck.

### FAQ

**The two systems tie at 0.9333 — isn't that a fair summary?** It is an accurate average and a misleading summary: it counts a wrong, ungrounded answer and a formatting slip as the same 1/6, so it ties a system you can ship with one you can't.

**Isn't weighting just moving the goalposts until my favorite wins?** It can be, which is why you set the weights and the critical set *before* you see the scores — the same discipline as pre-registering a hypothesis. The dishonest move is re-weighting after the ranking disappoints you.

**Why a hard gate instead of just big weights?** Because weights are compensatory: make the critical weight large enough and a pile of cosmetic passes can still buy back a critical failure. A gate says some failures are not for sale at any number of cosmetic passes.

**Why is mine slow?** This one isn't — it's a fixture and pure counting. Yours is slow only where the underlying checks are (an LLM-judged criterion costs a call); the aggregation itself is free, so compute all three.

### Errata

Version one, dated 2026-08-22. The fixture is built so the equal-weight mean ties *exactly* — A and B fail the same number of checks by construction — which is cleaner than real data, where the mean usually merely blurs a gap rather than hiding it perfectly; the point survives either way. One soft spot left in: the critical set (C1, C3, C4, C5) and the 3/1 weights are asserted, not derived, so the module shows what aggregation does, not how to price your own criteria — that pricing is the reader's job in Build.

## Definition of done

- [ ] `graded.json` for your own two systems: per-criterion pass/fail per case, and the critical set marked, committed before you look at the scores
- [ ] The critical checks and weights chosen before scoring, not after seeing the ranking
- [ ] All three aggregations reported — equal-weight mean, weighted mean, critical gate — never the mean alone
- [ ] A paired bootstrap CI on the gate gap, and whether it clears zero
- [ ] `python3 rubric.py --check` printing SELF-TEST PASS, so the mean is derived twice and the gate lets no critical-miss case pass
- [ ] A run stamp under every published number: date · seed and B (for the gate CI) · n · the command
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Two systems score an identical mean on the same rubric. Say what that number cannot tell you, and the one property of their failures that decides whether they are actually equal.
2. Explain why the equal-weight mean is itself a weighting, and what claim it makes about the criteria.
3. Define compensatory and non-compensatory aggregation, and say which of the mean, the weighted mean, and the gate are which.
4. The buggy gate gives a system a perfect gate-pass rate. State the any/all mistake in one sentence, and the assertion that catches it.
5. Your own run printed a gate gap and its interval. What was it, did it clear zero, and did it agree or disagree with your mean's ranking?

## External resources

- Hamel Husain, *Creating a LLM-as-a-Judge That Drives Business Results* — https://hamel.dev/blog/posts/llm-judge/ — my summary: argues for binary pass/fail criteria and a small set of critical ones over sprawling 1–5 scales; the practical case for gating over averaging.
- Eugene Yan, *Task-Specific LLM Evals* — https://eugeneyan.com/writing/evals/ — my summary: catalogs criterion types and how to combine them, including where a hard constraint beats a weighted score.
- Wikipedia, *Multiple-criteria decision analysis* (compensatory vs non-compensatory) — https://en.wikipedia.org/wiki/Multiple-criteria_decision_analysis — my summary: the decision-theory backbone for why a conjunctive rule and a weighted sum answer different questions; read for the vocabulary this module borrows.
