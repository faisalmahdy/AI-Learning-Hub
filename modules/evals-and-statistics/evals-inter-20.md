---
id: evals-inter-20
title: Compare two models on the same items by their disagreements — the items they agree on carry no signal
topic: evals-and-statistics
level: intermediate
status: ready
time: 19 min
summary: When two models are evaluated on the same items, the results are paired: each item sorts into both-right, A-only-right, B-only-right, or both-wrong. The instinct is to compare the two accuracies, but their difference is acc(A) − acc(B) = (A-only − B-only)/n — the both-right and both-wrong items appear in both accuracies and cancel completely. They say nothing about which model is better, because both models handled them identically. Only the discordant items — where the models disagree — carry information. McNemar's test uses exactly those: its statistic is (A-only − B-only)² / (A-only + B-only), built from the two disagreement counts alone. On two scenarios with the same discordant counts (3 vs 1) but wildly different agreement (96 items one way, 96 the other), the accuracy difference (0.02) and the McNemar statistic (1.0) are identical, because both depend only on the 3 and the 1.
eli5: If you and a friend both ace the same easy questions and both flub the same impossible ones, those questions can't tell who is smarter — you did identically on them. What separates you is only the questions where one got it and the other missed. So to compare two test-takers who took the exact same test, look just at the questions they disagreed on and ignore all the ones they answered the same way.
---

## Why this module

Comparing two models by their headline accuracies wastes the most valuable thing a shared test set gives you: the pairing that lets every item's difficulty cancel.

Run two models on the same items and you know, per item, whether each one succeeded — so the items fall into a 2×2 table: both right, A-only right, B-only right, both wrong. The natural comparison is A's accuracy against B's. But write out the difference and something drops away: acc(A) − acc(B) = (A-only − B-only) / n. The both-right count is in both accuracies; so is the both-wrong count; they cancel exactly. An item both models got right, or both got wrong, contributes nothing to which is better — the two models performed identically on it. All of the comparative signal lives in the discordant items, the ones where the models disagree, and comparing raw accuracies as if the two sets of results were independent samples ignores that the same items produced both.

**On a shared test set the concordant items cancel out of the model comparison, so only the disagreements carry information about which model is better.**

McNemar's test is built precisely on that fact: its statistic uses only the two discordant counts and ignores the agreements entirely. This module tallies two paired-eval scenarios and shows that the comparison is set by the disagreements alone, no matter how the agreements are distributed.

## Concepts

The **2×2 paired table** sorts the shared items into four cells: **both_correct**, **A-only** (A right, B wrong), **B-only** (A wrong, B right), and **both_wrong**.

The **marginal accuracies** are acc(A) = (both_correct + A-only)/n and acc(B) = (both_correct + B-only)/n. Their **difference** is (A-only − B-only)/n — the both_correct term cancels, and both_wrong never appeared. So the accuracy gap between the two models is determined entirely by the two discordant cells.

The **concordant** cells (both_correct, both_wrong) are the items the models handled the same way. They inflate or deflate both accuracies equally, so they wash out of any comparison. They tell you how hard the test was, not which model won.

**McNemar's statistic** is (A-only − B-only)² / (A-only + B-only) — a function of the discordant counts only. The larger and more lopsided the disagreement, the more evidence one model beats the other; the agreements do not enter.

The trap is thinking that agreeing on many items makes a comparison more trustworthy, or that a high shared accuracy strengthens a small gap. It does neither. The evidence for "A beats B" is entirely in the handful of items where they diverge, so the effective sample size for the comparison is the discordant count, not n.

**The comparison's evidence is the discordant count, not the test size — 100 items where 96 agree is a comparison resting on 4.**

The 2×2 table splits into a diagonal the models share and an off-diagonal where they split, and only the off-diagonal decides the winner.

<svg role="img" aria-label="A 2x2 grid: the diagonal cells (both right, both wrong) are shared and cancel; the off-diagonal cells (A-only, B-only) decide the comparison" viewBox="0 0 300 120" width="300" height="120">
  <text x="70" y="16" fill="var(--muted)" font-size="7">B right</text>
  <text x="140" y="16" fill="var(--muted)" font-size="7">B wrong</text>
  <text x="6" y="42" fill="var(--muted)" font-size="7">A right</text>
  <text x="6" y="82" fill="var(--muted)" font-size="7">A wrong</text>
  <rect x="60" y="22" width="60" height="34" fill="var(--s2)" opacity="0.4"/><text x="72" y="43" fill="var(--muted)" font-size="7">both right</text>
  <rect x="122" y="22" width="60" height="34" fill="var(--s1)"/><text x="130" y="43" fill="var(--panel)" font-size="7">A-only</text>
  <rect x="60" y="58" width="60" height="34" fill="var(--s1)"/><text x="72" y="79" fill="var(--panel)" font-size="7">B-only</text>
  <rect x="122" y="58" width="60" height="34" fill="var(--s2)" opacity="0.4"/><text x="130" y="79" fill="var(--muted)" font-size="7">both wrong</text>
  <text x="200" y="45" fill="var(--s2)" font-size="7">diagonal: cancels</text>
  <text x="200" y="72" fill="var(--s1)" font-size="7">off-diagonal: decides</text>
</svg>
^ The shaded diagonal (both agree) washes out of the comparison; the solid off-diagonal (they disagree) is the only part McNemar reads.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/evals-inter-20/mcnemar.py

The fixture is two scenarios with identical discordant counts but opposite agreement.

```json filename=modules/evals-and-statistics/code/evals-inter-20/paired.json:1-9 COMPLETE
{
  "_meta": "Two models (A and B) run on the SAME eval items, tallied into a 2x2 table: both_correct, a_only (A right, B wrong), b_only (A wrong, B right), both_wrong. The two scenarios have the same discordant counts (a_only, b_only) but very different concordant counts (both_correct, both_wrong). The question: does the comparison between A and B depend on the items they agree on, or only on the ones they disagree on?",
  "n": 100,
  "scenarios": {
    "high_agreement": {"both_correct": 90, "a_only": 3, "b_only": 1, "both_wrong": 6},
    "low_agreement":  {"both_correct": 40, "a_only": 3, "b_only": 1, "both_wrong": 56}
  }
}
```

The accuracies add the concordant both-right cell to each model's own discordant cell; the McNemar statistic uses only the two discordant cells.

```python filename=modules/evals-and-statistics/code/evals-inter-20/mcnemar.py:41-53 COMPLETE
def acc_a(c, n):
    """A's accuracy: items A got right = both_correct + a_only."""
    return (c["both_correct"] + c["a_only"]) / n


def acc_b(c, n):
    return (c["both_correct"] + c["b_only"]) / n


def mcnemar(c):
    """McNemar statistic from the discordant cells only: (a_only - b_only)^2 / (a_only + b_only)."""
    b, cc = c["a_only"], c["b_only"]
    return (b - cc) ** 2 / (b + cc) if (b + cc) else 0.0
```

The table view prints each scenario's 2×2 tally with both models' accuracies and their difference.

```python filename=modules/evals-and-statistics/code/evals-inter-20/mcnemar.py:59-66 COMPLETE
    n = data["n"]
    print("TABLE — 2x2 paired results, marginal accuracies, and the difference (n=%d)" % n)
    print("-" * 68)
    for name, c in data["scenarios"].items():
        print("  %-14s both=%d  A-only=%d  B-only=%d  both_wrong=%d" % (name, c["both_correct"], c["a_only"], c["b_only"], c["both_wrong"]))
        print("                 acc(A)=%.2f  acc(B)=%.2f  diff=%+.2f" % (acc_a(c, n), acc_b(c, n), acc_a(c, n) - acc_b(c, n)))
    print("-" * 68)
    print("  the two scenarios agree on very different numbers of items, yet the diff is the same.")
```

Run `--table` for the marginals.

```text filename=--table
TABLE — 2x2 paired results, marginal accuracies, and the difference (n=100)
--------------------------------------------------------------------
  high_agreement both=90  A-only=3  B-only=1  both_wrong=6
                 acc(A)=0.93  acc(B)=0.91  diff=+0.02
  low_agreement  both=40  A-only=3  B-only=1  both_wrong=56
                 acc(A)=0.43  acc(B)=0.41  diff=+0.02
```

The two scenarios could not look more different by accuracy — 93%/91% versus 43%/41%. One is an easy test both models mostly pass, the other a hard test both mostly fail. Yet the difference between A and B is +0.02 in both, because in both the discordant cells are 3 and 1, and (3 − 1)/100 = 0.02. The 90-vs-40 gulf in both_correct changed both accuracies together and cancelled out of the comparison.

<svg role="img" aria-label="Two 2x2 tables: high-agreement has both=90, low-agreement both=40, but both have A-only=3 B-only=1 and the same diff 0.02" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="14" fill="var(--muted)" font-size="8">high agreement</text>
  <rect x="20" y="20" width="30" height="24" fill="var(--s2)"/><text x="26" y="35" fill="var(--panel)" font-size="8">90</text>
  <rect x="52" y="20" width="30" height="24" fill="var(--s1)"/><text x="60" y="35" fill="var(--panel)" font-size="8">3</text>
  <rect x="20" y="46" width="30" height="24" fill="var(--s1)"/><text x="62" y="61" fill="var(--panel)" font-size="8"></text><text x="30" y="61" fill="var(--panel)" font-size="8">1</text>
  <rect x="52" y="46" width="30" height="24" fill="var(--s2)"/><text x="60" y="61" fill="var(--panel)" font-size="8">6</text>
  <text x="10" y="90" fill="var(--muted)" font-size="8">low agreement</text>
  <rect x="20" y="94" width="30" height="20" fill="var(--s2)"/><text x="26" y="108" fill="var(--panel)" font-size="8">40</text>
  <rect x="52" y="94" width="30" height="20" fill="var(--s1)"/><text x="60" y="108" fill="var(--panel)" font-size="8">3</text>
  <text x="95" y="55" fill="var(--s1)" font-size="8">discordant 3 vs 1</text>
  <text x="95" y="70" fill="var(--muted)" font-size="8">→ diff +0.02 in BOTH</text>
  <text x="95" y="105" fill="var(--muted)" font-size="7">both_correct 90 vs 40 cancels out</text>
</svg>
^ The bright discordant cells (3 and 1) are identical across the two tables; only the shaded concordant cells differ, and those cancel — so the comparison is the same in both.

## Build

Confirm it with the actual test statistic, `--mcnemar`.

```text filename=--mcnemar
MCNEMAR — the statistic uses only the discordant cells
--------------------------------------------------------------------
  high_agreement discordant 3 vs 1  ->  statistic (3-1)^2/(3+1) = 1.00
  low_agreement  discordant 3 vs 1  ->  statistic (3-1)^2/(3+1) = 1.00
```

Both scenarios give a McNemar statistic of 1.00, computed from (3 − 1)² / (3 + 1). The both_correct and both_wrong counts — 90 and 6, or 40 and 56 — never appear in the formula, so they cannot change the result. The significance of "A beats B" is set by the four discordant items alone. A statistic of 1.0 is small; it is not significant (well under the ~3.84 chi-square threshold), which is the honest reading: 3 versus 1 disagreements is barely any evidence, on either test, however impressive 93% looks.

<svg role="img" aria-label="McNemar statistic 1.0 for both scenarios, driven only by the 3-versus-1 discordant split" viewBox="0 0 300 100" width="300" height="100">
  <line x1="70" y1="12" x2="70" y2="65" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="65" x2="285" y2="65" stroke="var(--grid)" stroke-width="1"/>
  <line x1="230" y1="12" x2="230" y2="65" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 2"/>
  <text x="205" y="22" fill="var(--ink)" font-size="7">sig ~3.84</text>
  <rect x="70" y="45" width="42" height="14" fill="var(--s1)"/><text x="116" y="56" fill="var(--muted)" font-size="8">high-agree 1.0</text>
  <rect x="70" y="24" width="42" height="14" fill="var(--s1)"/><text x="116" y="35" fill="var(--muted)" font-size="8">low-agree 1.0</text>
  <text x="70" y="88" fill="var(--muted)" font-size="8">identical, and both far short of significance — 4 disagreements is thin evidence</text>
</svg>
^ Both statistics land at 1.0, well short of the significance threshold — the comparison is thin because it rests on four discordant items, regardless of the 90%+ that agreed.

## Definition of done

The self-test pins the identity: the accuracy difference equals the discordant split over n, the two scenarios differ greatly in agreement, yet the difference and the McNemar statistic are identical, and the comparison rests on the discordant items.

```python filename=modules/evals-and-statistics/code/evals-inter-20/mcnemar.py:86-98 COMPLETE
    diff_is_discordant = abs((acc_a(hi, n) - acc_b(hi, n)) - (hi["a_only"] - hi["b_only"]) / n) < 1e-9
    print("  acc(A)-acc(B) equals (A-only - B-only)/n = %s (%.2f)" % (diff_is_discordant, acc_a(hi, n) - acc_b(hi, n)))

    concordant_differs = hi["both_correct"] != lo["both_correct"]
    print("  the two scenarios have very different agreement = %s (both_correct %d vs %d)" % (concordant_differs, hi["both_correct"], lo["both_correct"]))

    same_diff = abs((acc_a(hi, n) - acc_b(hi, n)) - (acc_a(lo, n) - acc_b(lo, n))) < 1e-9
    print("  yet the accuracy difference is identical = %s (%+.2f both)" % (same_diff, acc_a(hi, n) - acc_b(hi, n)))

    same_statistic = abs(mcnemar(hi) - mcnemar(lo)) < 1e-9
    print("  and the McNemar statistic is identical = %s (%.2f both)" % (same_statistic, mcnemar(hi)))

    evidence_is_discordant = (hi["a_only"] + hi["b_only"]) < n
    print("  the comparison rests on the %d discordant items, not all %d = %s" % (hi["a_only"] + hi["b_only"], n, evidence_is_discordant))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the difference and the statistic depend only on the discordant cells, not the agreements
--------------------------------------------------------------------------------------------------------
  acc(A)-acc(B) equals (A-only - B-only)/n = True (0.02)
  the two scenarios have very different agreement = True (both_correct 90 vs 40)
  yet the accuracy difference is identical = True (+0.02 both)
  and the McNemar statistic is identical = True (1.00 both)
  the comparison rests on the 4 discordant items, not all 100 = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  diff_is_discordant=True  concordant_differs=True  same_diff=True  same_statistic=True  evidence_is_discordant=True
```

**Done means the cancellation is exact, not approximate: two scenarios with 90 vs 40 agreements give the identical +0.02 difference and 1.00 statistic, because both are functions of the discordant 3 and 1 alone.**

## Boss fight

The statistic ignored the concordant items. Predict whether that means the number of concordant items is irrelevant to the eval entirely. It is tempting to conclude the agreements do not matter at all.

They do not matter for *comparing the two models*, but they matter for everything else. The concordant items tell you the shared difficulty — 90% both-right versus 40% both-right is the difference between an easy benchmark and a hard one — and that shapes whether the eval discriminates at all. An eval where both models get everything right (all concordant, zero discordant) gives a McNemar statistic of 0/0: it cannot compare them, because they never diverged. So you want *enough* discordant items to have power, which means the eval must contain items that separate the models. The agreements are irrelevant to the verdict but diagnostic of whether the eval can render one.

The mirror-image mistake is comparing two models on *different* test sets and reaching for McNemar. The whole method depends on the pairing — the same items, so each item's difficulty is shared and cancels. On different item sets there are no concordant cells to cancel, the results are unpaired, and you need an unpaired test (a two-proportion test) with its larger variance. Pairing is what makes the comparison powerful; McNemar is how you cash that in, and only when the pairing is real.

```python filename=modules/evals-and-statistics/code/evals-inter-20/mcnemar.py:50-53 COMPLETE
def mcnemar(c):
    """McNemar statistic from the discordant cells only: (a_only - b_only)^2 / (a_only + b_only)."""
    b, cc = c["a_only"], c["b_only"]
    return (b - cc) ** 2 / (b + cc) if (b + cc) else 0.0
```

**Compare two models on a shared test set by their discordant items with McNemar's test — the agreements cancel from the verdict, so the evidence is the disagreement count, and the whole method requires the pairing to be real.**

## External resources

McNemar (1947) and any biostatistics text's paired-proportions chapter — the derivation that only the discordant pairs enter, and the chi-square (or exact binomial) reference distribution for the statistic.

The scikit-learn / statsmodels `mcnemar` utilities — production implementations, including the exact binomial version used when the discordant counts are small (as here).

The companion "pair the comparison on the same cases" and "per-item regression diff" modules — pairing is why you use the same cases, the regression-diff module's off-diagonal counts are exactly these discordant cells, and McNemar is the test that turns them into a verdict.
