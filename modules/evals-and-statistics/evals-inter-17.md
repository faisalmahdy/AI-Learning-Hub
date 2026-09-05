---
id: evals-inter-17
title: Diff the eval item by item — a higher aggregate score hides the cases the new model broke
topic: evals-and-statistics
level: intermediate
status: ready
time: 19 min
summary: You ship a new model version, run the eval, and the score went up — 7 of 10 versus 5. Green light. But that single number is a sum, and a sum tells you that the score changed, not how. The new model could have fixed three cases and broken one, and both the win and the breakage net into the same aggregate. A broken case is a regression — something that used to work now fails — and if it is a case that matters, a net-positive release can still be one you must not ship. The fix is to diff the eval at the item level: line up each case's old and new result and count fixed, regressed, still-pass, still-fail. On a ten-case fixture the aggregate improves by +2, but the item diff reveals three fixes and one regression — the new model broke safety_refusal, which the old model passed.
eli5: If your report card average goes up, it looks like you improved everywhere — but you might have aced two new subjects and quietly failed one you used to pass. The average blends the win and the loss into one cheerful number. To catch the subject you dropped, you have to compare each grade to last term's, not just the averages. Model evals are the same: the total can rise while something important breaks underneath it.
---

## Why this module

An aggregate eval score answers "is the new model better on average" — but shipping decisions turn on "did the new model break anything," and the average cannot see that.

Run the eval on the old model and the new one, compare the totals, and the number went up. It is the most natural release signal there is, and it is dangerously incomplete. A total is a sum over cases, and summation is lossy: it records that more cases pass now, not which cases changed direction. The new model may have fixed several cases and broken others; as long as the fixes outnumber the breaks, the aggregate rises and every regression is averaged away with the wins. If one of those broken cases is a safety refusal, a billing calculation, or any behavior you are contractually on the hook for, a net-positive release is still a release you cannot make.

**A rising aggregate proves net improvement; it does not prove the absence of regressions, and those are different questions.**

The fix is to stop comparing totals and start diffing cases. Line up each item's old and new result and count the four cells — still-pass, still-fail, fixed, regressed. This module builds both the aggregate and the item diff on one result set and shows the regression the total conceals.

## Concepts

The **aggregate score** is the pass count: how many of the N cases the model passed. Comparing two models' aggregates gives the **net change** — a single signed number.

The **item diff** compares the two models case by case and sorts every case into a 2×2 confusion: **still-pass** (both pass), **still-fail** (both fail), **fixed** (old fails, new passes), and **regressed** (old passes, new fails). The regressed cell is the one the aggregate cannot show.

The relationship is exact: the net change equals fixes minus regressions. That is precisely why the aggregate is insufficient — it is those two numbers collapsed into their difference, and a difference cannot be un-subtracted back into its parts. A net of +2 could be 2 fixes and 0 regressions, or 5 fixes and 3 regressions; the aggregate cannot tell them apart, and the second one broke three things.

The trap is treating "score went up" as "safe to ship." Improvement and regression are not opposites; a release can be both at once. The item diff lets you gate on what actually matters — for instance, "zero regressions on critical cases" — a rule the aggregate literally cannot express because it has thrown the per-case identity away.

**Net change is fixes minus regressions, so a single aggregate can never tell you whether the release broke a case you care about — only the diff can.**

The collapse is one-directional: many diffs map to the same net, and once you hold only the net you cannot recover which one you had.

<svg role="img" aria-label="Three different fix/regression splits all collapse to the same net of plus 2" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="20" fill="var(--muted)" font-size="8">2 fixed, 0 regressed</text>
  <text x="10" y="45" fill="var(--muted)" font-size="8">3 fixed, 1 regressed</text>
  <text x="10" y="70" fill="var(--muted)" font-size="8">5 fixed, 3 regressed</text>
  <line x1="150" y1="15" x2="215" y2="55" stroke="var(--s1)" stroke-width="1"/>
  <line x1="150" y1="40" x2="215" y2="58" stroke="var(--s1)" stroke-width="1"/>
  <line x1="150" y1="65" x2="215" y2="61" stroke="var(--s1)" stroke-width="1"/>
  <rect x="215" y="48" width="55" height="22" fill="var(--s2)"/>
  <text x="228" y="63" fill="var(--panel)" font-size="9">net +2</text>
  <text x="30" y="100" fill="var(--muted)" font-size="8">the aggregate keeps the arrow's tip and forgets the tail</text>
</svg>
^ Every split with two more fixes than regressions produces net +2; the aggregate stores only that tip, so a clean release and a churn-heavy one are indistinguishable in the total.

This is why eval harnesses store per-item results, not just scores, and why regression tests in software track which tests flipped, not just the pass rate.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/evals-inter-17/regressions.py

The fixture is ten cases with each model's per-item pass (1) or fail (0).

```json filename=modules/evals-and-statistics/code/evals-inter-17/results.json:1-15 COMPLETE
{
  "_meta": "Per-item eval results for two model versions on the same test cases. a is whether the OLD model passed the case (1/0); b is whether the NEW model passed it. The aggregate score is the pass count. The question the aggregate cannot answer: which specific cases did the new model BREAK that the old one passed?",
  "items": [
    {"name": "format_json",   "a": 1, "b": 1},
    {"name": "cite_source",   "a": 1, "b": 1},
    {"name": "math_add",      "a": 1, "b": 1},
    {"name": "safety_refusal","a": 1, "b": 0},
    {"name": "summarize",     "a": 1, "b": 1},
    {"name": "code_fix",      "a": 0, "b": 1},
    {"name": "translate",     "a": 0, "b": 1},
    {"name": "classify",      "a": 0, "b": 1},
    {"name": "long_context",  "a": 0, "b": 0},
    {"name": "multi_hop",     "a": 0, "b": 0}
  ]
}
```

The aggregate is a sum; the diff is two list comprehensions over the same cases. Fixed is fail-to-pass; regressed is pass-to-fail — the asymmetry is the whole point.

```python filename=modules/evals-and-statistics/code/evals-inter-17/regressions.py:39-50 COMPLETE
def score(items, key):
    return sum(it[key] for it in items)


def fixed(items):
    """Cases the old model failed and the new model passed."""
    return [it["name"] for it in items if it["a"] == 0 and it["b"] == 1]


def regressed(items):
    """Cases the old model passed and the new model failed -- the ones the aggregate hides."""
    return [it["name"] for it in items if it["a"] == 1 and it["b"] == 0]
```

Run `--scores` — the release signal most teams stop at.

```text filename=--scores
SCORES — aggregate pass counts (10 cases)
----------------------------------------------------------
  old model: 5 / 10
  new model: 7 / 10
  net change: +2
----------------------------------------------------------
  the total went up; the total cannot say what moved.
```

Five to seven, a clean +2. On this signal alone you ship. Nothing here even hints that a case regressed — the number is monotone and cheerful.

<svg role="img" aria-label="Two aggregate bars: old model 5 of 10, new model 7 of 10, showing only a plus 2 gain" viewBox="0 0 300 100" width="300" height="100">
  <line x1="70" y1="15" x2="70" y2="80" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="80" x2="285" y2="80" stroke="var(--grid)" stroke-width="1"/>
  <rect x="80" y="35" width="100" height="16" fill="var(--s2)"/>
  <text x="10" y="47" fill="var(--muted)" font-size="9">old</text>
  <text x="185" y="47" fill="var(--muted)" font-size="9">5 / 10</text>
  <rect x="80" y="58" width="140" height="16" fill="var(--s1)"/>
  <text x="10" y="70" fill="var(--muted)" font-size="9">new</text>
  <text x="225" y="70" fill="var(--muted)" font-size="9">7 / 10  (+2)</text>
  <text x="80" y="24" fill="var(--muted)" font-size="8">the only signal the aggregate gives you</text>
</svg>
^ The aggregate view: two bars, a +2 gain, and no way to see that a case flipped from pass to fail.

## Build

The diff view sorts every case into the four cells of the confusion and reports each by name.

```python filename=modules/evals-and-statistics/code/evals-inter-17/regressions.py:69-80 COMPLETE
    items = data["items"]
    f, r = fixed(items), regressed(items)
    still_pass = [it["name"] for it in items if it["a"] == 1 and it["b"] == 1]
    still_fail = [it["name"] for it in items if it["a"] == 0 and it["b"] == 0]
    print("DIFF — item-level confusion between old and new")
    print("-" * 58)
    print("  fixed     (fail->pass): %d  %s" % (len(f), f))
    print("  REGRESSED (pass->fail): %d  %s" % (len(r), r))
    print("  still pass:             %d" % len(still_pass))
    print("  still fail:             %d" % len(still_fail))
    print("-" * 58)
    print("  net %+d = %d fixed - %d regressed" % (len(f) - len(r), len(f), len(r)))
```

Now run `--diff` on the identical results.

```text filename=--diff
DIFF — item-level confusion between old and new
----------------------------------------------------------
  fixed     (fail->pass): 3  ['code_fix', 'translate', 'classify']
  REGRESSED (pass->fail): 1  ['safety_refusal']
  still pass:             4
  still fail:             2
-----------------------------------------------------------
  net +2 = 3 fixed - 1 regressed
```

The +2 was never "two improvements." It was three fixes minus one regression, and the regression is `safety_refusal` — a case the old model passed and the new one broke. The aggregate reported the release as pure progress; the diff shows it fixed three things and broke a safety behavior. Whether to ship is now a real decision, not a rubber stamp.

<svg role="img" aria-label="Item diff 2 by 2: 4 still pass, 2 still fail, 3 fixed fail-to-pass, 1 regressed pass-to-fail" viewBox="0 0 300 140" width="300" height="140">
  <text x="95" y="18" fill="var(--muted)" font-size="8">new pass</text>
  <text x="175" y="18" fill="var(--muted)" font-size="8">new fail</text>
  <text x="10" y="45" fill="var(--muted)" font-size="8">old pass</text>
  <text x="10" y="95" fill="var(--muted)" font-size="8">old fail</text>
  <rect x="80" y="25" width="80" height="40" fill="var(--s2)"/>
  <text x="95" y="48" fill="var(--panel)" font-size="9">4 still pass</text>
  <rect x="165" y="25" width="80" height="40" fill="var(--s1)"/>
  <text x="178" y="43" fill="var(--panel)" font-size="9">1 REGRESSED</text>
  <text x="178" y="55" fill="var(--panel)" font-size="7">safety_refusal</text>
  <rect x="80" y="70" width="80" height="40" fill="var(--acc-soft)"/>
  <text x="98" y="93" fill="var(--acc-ink)" font-size="9">3 fixed</text>
  <rect x="165" y="70" width="80" height="40" fill="none" stroke="var(--line)" stroke-width="1"/>
  <text x="185" y="93" fill="var(--muted)" font-size="9">2 still fail</text>
  <text x="80" y="130" fill="var(--muted)" font-size="8">the regressed cell is exactly what the aggregate erases</text>
</svg>
^ The 2×2 the aggregate collapses: the top-right cell — one pass-to-fail regression on a safety case — is invisible in a total that only rose.

## Definition of done

The self-test pins the concealment: the aggregate improved, a regression exists, so the aggregate hid it; the net equals fixes minus regressions; and the net understates the fixes because a regression cancelled one.

```python filename=modules/evals-and-statistics/code/evals-inter-17/regressions.py:90-103 COMPLETE
    aggregate_improved = b > a
    print("  the aggregate score improved = %s (%d -> %d, %+d)" % (aggregate_improved, a, b, b - a))

    regressions_exist = len(r) > 0
    print("  at least one case regressed = %s (%s)" % (regressions_exist, r))

    aggregate_hides_regressions = aggregate_improved and regressions_exist
    print("  a positive aggregate hides a regression = %s" % aggregate_hides_regressions)

    net_equals_fixes_minus_regressions = (b - a) == (len(f) - len(r))
    print("  net change = fixes - regressions = %s (%+d = %d - %d)" % (net_equals_fixes_minus_regressions, b - a, len(f), len(r)))

    regression_invisible_in_total = (b - a) > 0 and len(r) > 0 and (b - a) < len(f)
    print("  the total understates the fixes because a regression cancels one = %s (net %+d < %d fixed)"
          % (regression_invisible_in_total, b - a, len(f)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the aggregate improves while a real regression hides inside it
------------------------------------------------------------------------------------------------
  the aggregate score improved = True (5 -> 7, +2)
  at least one case regressed = True (['safety_refusal'])
  a positive aggregate hides a regression = True
  net change = fixes - regressions = True (+2 = 3 - 1)
  the total understates the fixes because a regression cancels one = True (net +2 < 3 fixed)
------------------------------------------------------------------------------------------------
SELF-TEST PASS  aggregate_improved=True  regressions_exist=True  aggregate_hides_regressions=True  net_equals_fixes_minus_regressions=True  regression_invisible_in_total=True
```

**Done means the hidden regression is surfaced by construction: the net +2 equals 3 fixed minus 1 regressed, so the aggregate provably discarded the pass-to-fail case rather than being unable to have one.**

## Boss fight

The net here is +2 with one regression. Predict the most dangerous version of this bug — the aggregate that most confidently hides the most damage. It is tempting to think a bigger positive net is safer.

The opposite is true, and it is the release trap worth internalizing. A net of zero — same aggregate, "no change, skip the review" — can hide five fixes and five regressions: half your critical behaviors silently swapped for other passes. The larger the eval and the closer the net to zero, the more churn a flat aggregate can conceal, because fixes and regressions cancel one-for-one. "The score didn't move" is not "nothing moved"; it is the strongest possible camouflage for regressions. Always diff, even — especially — when the total is unchanged.

The mirror-image mistake is over-reacting to any regression and blocking every release. Regressions are expected; the discipline is to classify them. A regression on `long_context` may be an acceptable trade for three fixes; a regression on `safety_refusal` is not. That triage is only possible with the named, per-item diff — which is why the fix is not "never regress" but "never regress silently."

```python filename=modules/evals-and-statistics/code/evals-inter-17/regressions.py:48-50 COMPLETE
def regressed(items):
    """Cases the old model passed and the new model failed -- the ones the aggregate hides."""
    return [it["name"] for it in items if it["a"] == 1 and it["b"] == 0]
```

**Gate a release on the item diff, not the aggregate: a total that rose, fell, or held flat can each hide a regression, and only the pass-to-fail list tells you what you are about to break.**

## External resources

The software-testing literature on regression testing — the whole discipline exists because "the suite still mostly passes" is not "nothing broke"; you track which tests flipped, the exact analogue here.

Anthropic's and OpenAI's evals guidance on storing per-example results — harnesses persist item-level outcomes precisely so you can diff versions, not just compare headline scores.

McNemar's test — the statistical companion to this diff: when comparing two models on the same cases, the fixed and regressed counts (the off-diagonal of the 2×2) are exactly what the test uses to decide whether the change is real.
