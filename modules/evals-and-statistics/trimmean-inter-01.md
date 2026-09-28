---
id: trimmean-inter-01
title: Rank systems by a robust aggregate, not the mean — one outlier item can flip the leaderboard
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: An eval that scores each item on a continuous scale — an LLM-judge quality score, a graded rubric total, a latency — has to collapse the per-item scores into one number per system to rank them, and the reflex is the mean. The mean is a fine descriptive summary and a terrible comparison aggregate, because it has a breakdown point of zero: a single item, pushed far enough, moves the mean as far as you like, and in an eval that single item can be a judge glitch, a mis-scaled grade, or one freak easy case that should not decide the leaderboard. On the fixture system B scores a little above system A on nine of ten items, but on the tenth A has an outlier score of 200; that one item drags A's mean to 75.20 above B's 70.80, so a leaderboard ranked by mean crowns A — the system that lost nine of ten items. Every robust summary disagrees: B wins on the median (70.50 vs 61.50), B wins on a 10% trimmed mean (70.88 vs 61.75), and B wins the paired per-item head-to-head 9 to 1. Drop the single outlier item and even the mean flips back to B (71.33 vs 61.33), which is the tell that one point was driving the whole verdict. The fix is to aggregate a comparison with a statistic a lone item cannot capture — the median, a trimmed mean, or the paired win rate. This is not the descriptive point that a mean can be unrepresentative of a skewed distribution; it is that a non-robust aggregate lets one item flip a decision between two systems, which a comparison metric must never do.
eli5: Imagine two students graded on ten problems. Student B does a bit better than student A on nine of them, and on the tenth a grading mistake gives A a wildly huge score. If you rank them by their average, that one giant number lifts A above B, so the average says A is better — even though B actually beat A on nine problems out of ten. The average is easy to hijack: one crazy number drags it wherever it wants. If instead you rank by the middle score, or throw out the highest and lowest before averaging, or just count who won more problems, B wins every time, the way they should. The lesson is that when you are deciding which of two is better, you should use a score that a single weird result can't take over.
---

## Why this module

Leaderboards run on one number per system, and that number is almost always a mean — mean accuracy, mean judge score, mean reward. For a pass/fail eval the mean is just a rate and is fine. For an eval that scores each item on a continuous scale, the mean quietly acquires a dangerous property: any single item can move it without limit.

That matters because eval scores are not clean. A judge occasionally returns a wild number, a rubric occasionally sums wrong, one item is accidentally on a different scale. With a mean, one such item does not just add noise — it can outvote every other item combined and flip which system you ship.

**A comparison metric must not let one item decide the outcome, and the mean of continuous scores does exactly that.**

## Concepts

The breakdown point of an aggregate is the fraction of the data you must corrupt to move the aggregate arbitrarily far. The mean's breakdown point is zero: corrupt one value out of any number and, by making it large enough, you move the mean anywhere. The median's breakdown point is one half — you must corrupt half the data to move it arbitrarily. A trimmed mean sits in between, set by how much you trim.

For describing a single distribution, the mean's sensitivity is a known caveat. For comparing two systems, it is a correctness bug, because the decision "A or B" can be flipped by a single item that has nothing to do with which system is actually better. The other nine items can unanimously favor B and lose to one anomalous point favoring A.

Three aggregates resist this. The median takes the middle score, so an extreme value changes which value is in the middle by at most one position, not the value itself. A trimmed mean drops the top and bottom fraction before averaging, discarding the extremes outright. The paired per-item win rate ignores magnitudes entirely and counts how many items each system won — the most robust of all, because it is blind to how large any single score is.

The clean diagnostic is drop-one. If removing a single item flips the verdict, the verdict was that item's, not the eval's — and a robust aggregate would not have let it.

**Swap the mean for the median, a trimmed mean, or the paired win rate, and no single item can outvote the rest.**

<svg role="img" aria-label="A robustness scale from 0 to one half. The mean sits at breakdown point 0, the 10 percent trimmed mean at 0.1, and the median at one half. The further right, the more of the data must be corrupted to move the aggregate." viewBox="0 0 460 130">
<rect x="0" y="0" width="460" height="130" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">breakdown point: fraction you must corrupt to move it</text>
<line x1="60" y1="80" x2="420" y2="80" stroke="var(--line)"></line>
<text x="52" y="100" fill="var(--muted)" font-size="9">0</text>
<text x="404" y="100" fill="var(--muted)" font-size="9">0.5</text>
<circle cx="60" cy="80" r="5" fill="var(--s1)"></circle>
<text x="46" y="66" fill="var(--s1)" font-size="10">mean (0)</text>
<circle cx="132" cy="80" r="5" fill="var(--s2)"></circle>
<text x="104" y="66" fill="var(--s2)" font-size="10">trim 10% (0.1)</text>
<circle cx="420" cy="80" r="5" fill="var(--s2)"></circle>
<text x="386" y="66" fill="var(--s2)" font-size="10">median (0.5)</text>
</svg>
^ The mean breaks at a single corrupted item (breakdown 0); the trimmed mean tolerates the trimmed fraction; the median tolerates almost half the data before it can be moved arbitrarily.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/evals-and-statistics/code/trimmean-inter-01/trimmean.py

The fixture scores two systems on the same ten items; B leads on nine, A has one outlier.

```json filename=modules/evals-and-statistics/code/trimmean-inter-01/trimmean.json:3-14 COMPLETE
  "trim_frac": 0.1,
  "items": [
    {"id": "q1",  "A": 60,  "B": 70},
    {"id": "q2",  "A": 62,  "B": 72},
    {"id": "q3",  "A": 58,  "B": 68},
    {"id": "q4",  "A": 65,  "B": 75},
    {"id": "q5",  "A": 61,  "B": 71},
    {"id": "q6",  "A": 59,  "B": 69},
    {"id": "q7",  "A": 63,  "B": 73},
    {"id": "q8",  "A": 64,  "B": 74},
    {"id": "q9",  "A": 60,  "B": 70},
    {"id": "q10", "A": 200, "B": 66}
  ]
```

The three aggregates are the mean, the median, and a trimmed mean.

```python filename=modules/evals-and-statistics/code/trimmean-inter-01/trimmean.py:28-30 COMPLETE
def mean(xs):
    """The arithmetic mean -- breakdown point zero, so one item has unbounded leverage."""
    return sum(xs) / len(xs)
```

```python filename=modules/evals-and-statistics/code/trimmean-inter-01/trimmean.py:33-38 COMPLETE
def median(xs):
    """The middle value (or mean of the two middle) -- unmoved by how extreme the tails are."""
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2
```

```python filename=modules/evals-and-statistics/code/trimmean-inter-01/trimmean.py:41-46 COMPLETE
def trimmed_mean(xs, trim_frac):
    """The mean after dropping the top and bottom trim_frac of the values -- discards the extremes."""
    s = sorted(xs)
    k = int(len(s) * trim_frac)
    kept = s[k:len(s) - k]
    return sum(kept) / len(kept)
```

Run all three and only the mean disagrees with the rest.

```text filename=trimmean.py --aggregate
AGGREGATE — each system's score under three aggregates
----------------------------------------------------------------
  mean:         A =  75.20   B =  70.80   -> picks A
  median:       A =  61.50   B =  70.50   -> picks B
  trimmed 10%:  A =  61.75   B =  70.88   -> picks B
----------------------------------------------------------------
  the mean alone crowns A; every robust aggregate crowns B
```

The mean puts A at 75.20 over B at 70.80 — A wins. But A's median is 61.50 and B's is 70.50, and A's trimmed mean is 61.75 to B's 70.88, so both robust aggregates put B comfortably ahead. The mean is the outlier among the aggregates, and it is the only one that crowns A.

<svg role="img" aria-label="System A's ten scores: nine clustered near 60, and one far to the right at 200. The mean is pulled to 75, to the right of all nine clustered points, while the median sits at 61.5 inside the cluster." viewBox="0 0 480 140">
<rect x="0" y="0" width="480" height="140" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">system A's scores: nine near 60, one at 200</text>
<line x1="40" y1="95" x2="460" y2="95" stroke="var(--line)"></line>
<circle cx="70" cy="95" r="4" fill="var(--ink)"></circle>
<circle cx="80" cy="95" r="4" fill="var(--ink)"></circle>
<circle cx="88" cy="95" r="4" fill="var(--ink)"></circle>
<circle cx="96" cy="95" r="4" fill="var(--ink)"></circle>
<circle cx="104" cy="95" r="4" fill="var(--ink)"></circle>
<circle cx="112" cy="95" r="4" fill="var(--ink)"></circle>
<circle cx="120" cy="95" r="4" fill="var(--ink)"></circle>
<circle cx="128" cy="95" r="4" fill="var(--ink)"></circle>
<circle cx="136" cy="95" r="4" fill="var(--ink)"></circle>
<circle cx="440" cy="95" r="4" fill="var(--s1)"></circle>
<text x="420" y="88" fill="var(--s1)" font-size="9">200</text>
<line x1="102" y1="60" x2="102" y2="105" stroke="var(--s2)"></line>
<text x="86" y="54" fill="var(--s2)" font-size="9">median 61.5</text>
<line x1="168" y1="60" x2="168" y2="105" stroke="var(--s1)"></line>
<text x="150" y="122" fill="var(--s1)" font-size="9">mean 75.2</text>
</svg>
^ The single point at 200 drags the mean out past all nine clustered scores, while the median stays inside the cluster where the bulk of the data actually is.

## Build

The per-item view shows the verdict the mean overturned, and the drop-one diagnostic.

```text filename=trimmean.py --items
ITEMS — per-item head-to-head (B better on almost every item)
----------------------------------------------------------------
  q1   A= 60  B= 70  -> B
  q2   A= 62  B= 72  -> B
  q3   A= 58  B= 68  -> B
  q4   A= 65  B= 75  -> B
  q5   A= 61  B= 71  -> B
  q6   A= 59  B= 69  -> B
  q7   A= 63  B= 73  -> B
  q8   A= 64  B= 74  -> B
  q9   A= 60  B= 70  -> B
  q10  A=200  B= 66  -> A   <- A's outlier
----------------------------------------------------------------
  item wins: A 1, B 9
  mean with all items:        A = 75.20  B = 70.80  -> A
  mean dropping q10 (A's outlier): A = 61.33  B = 71.33  -> B
```

B wins nine of the ten items head-to-head; A wins only q10, its outlier. And the drop-one test is decisive: remove q10 and the mean flips from A (75.20 vs 70.80) to B (61.33 vs 71.33). One item out of ten was carrying the entire mean-based verdict.

<svg role="img" aria-label="Two rows of bars for the ten items. On nine items B's bar is taller than A's; on the tenth item A's bar towers over B's. B wins nine, A wins one." viewBox="0 0 480 140">
<rect x="0" y="0" width="480" height="140" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">per-item winner (taller bar wins)</text>
<line x1="30" y1="110" x2="470" y2="110" stroke="var(--line)"></line>
<rect x="40" y="80" width="10" height="30" fill="var(--muted)"></rect>
<rect x="52" y="72" width="10" height="38" fill="var(--s2)"></rect>
<rect x="80" y="80" width="10" height="30" fill="var(--muted)"></rect>
<rect x="92" y="72" width="10" height="38" fill="var(--s2)"></rect>
<rect x="120" y="80" width="10" height="30" fill="var(--muted)"></rect>
<rect x="132" y="72" width="10" height="38" fill="var(--s2)"></rect>
<rect x="160" y="80" width="10" height="30" fill="var(--muted)"></rect>
<rect x="172" y="72" width="10" height="38" fill="var(--s2)"></rect>
<rect x="200" y="80" width="10" height="30" fill="var(--muted)"></rect>
<rect x="212" y="72" width="10" height="38" fill="var(--s2)"></rect>
<rect x="240" y="80" width="10" height="30" fill="var(--muted)"></rect>
<rect x="252" y="72" width="10" height="38" fill="var(--s2)"></rect>
<rect x="280" y="80" width="10" height="30" fill="var(--muted)"></rect>
<rect x="292" y="72" width="10" height="38" fill="var(--s2)"></rect>
<rect x="320" y="80" width="10" height="30" fill="var(--muted)"></rect>
<rect x="332" y="72" width="10" height="38" fill="var(--s2)"></rect>
<rect x="360" y="80" width="10" height="30" fill="var(--muted)"></rect>
<rect x="372" y="72" width="10" height="38" fill="var(--s2)"></rect>
<rect x="400" y="24" width="10" height="86" fill="var(--s1)"></rect>
<rect x="412" y="82" width="10" height="28" fill="var(--muted)"></rect>
<text x="392" y="20" fill="var(--s1)" font-size="9">q10: A</text>
<text x="40" y="128" fill="var(--s2)" font-size="9">q1-q9: B wins each</text>
</svg>
^ B (the lighter bar) is taller on nine items; only on q10 does A's bar tower — that lone spike is what the mean rewards and every robust aggregate ignores.

The self-test states the whole disagreement: the mean picks A, the median and trimmed mean and item majority all pick B, and dropping the one outlier flips the mean back.

```python filename=modules/evals-and-statistics/code/trimmean-inter-01/trimmean.py:104-111 COMPLETE
    mean_picks_a = winner(mean(A), mean(B)) == "A"
    print("  the mean picks A = %s (%.2f vs %.2f)" % (mean_picks_a, mean(A), mean(B)))

    median_picks_b = winner(median(A), median(B)) == "B"
    print("  the median picks B = %s (%.2f vs %.2f)" % (median_picks_b, median(A), median(B)))

    trimmed_picks_b = winner(trimmed_mean(A, tf), trimmed_mean(B, tf)) == "B"
    print("  the trimmed mean picks B = %s (%.2f vs %.2f)" % (trimmed_picks_b, trimmed_mean(A, tf), trimmed_mean(B, tf)))
```

```text filename=trimmean.py --check
SELF-TEST — the mean picks A while the median, the trimmed mean, and the item majority all pick B, and removing the one outlier item flips the mean back to B
----------------------------------------------------------------------------------------------------------------
  the mean picks A = True (75.20 vs 70.80)
  the median picks B = True (61.50 vs 70.50)
  the trimmed mean picks B = True (61.75 vs 70.88)
  the item-by-item majority favors B = True (B 9, A 1)
  removing the single outlier item flips the mean to B = True (61.33 vs 71.33)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  mean_picks_a=True  median_picks_b=True  trimmed_picks_b=True  item_majority_b=True  drop_flips_mean=True
```

**drop_flips_mean is the diagnostic to keep: if removing one item flips your leaderboard, the leaderboard was that item's, and a robust aggregate would not have let it.**

## Definition of done

You can state why the mean is a correctness bug for a comparison, not just a descriptive caveat: its breakdown point is zero, so one item can flip the decision between two systems.

You can name three robust alternatives and their relative robustness: the paired win rate (blind to magnitude), the median (breakdown point one half), and the trimmed mean (set by the trim fraction).

You can run the drop-one diagnostic — remove the single most extreme item and re-rank — and interpret a flip as evidence the verdict rested on that item.

You can say what you would investigate before trusting any of the aggregates: whether the outlier is a real score or a pipeline error, because a robust aggregate hides the bad item rather than fixing it.

## Boss fight

Your eval ranks models by mean judge score on 500 prompts, and a new model jumps to the top of the leaderboard overnight. The per-prompt scores are 0–10, but a handful of prompts show scores like 40 and 95 for the new model — the judge occasionally emits an out-of-range number.

First: explain why the mean is exquisitely sensitive to those few out-of-range scores even though they are a tiny fraction of 500, and estimate how few such prompts it would take to lift a mean-based rank, given the scores are supposed to be capped at 10.

Then: you have three fixes available — clamp every score to [0, 10] before aggregating, switch the aggregate to the median, or report the paired win rate against the incumbent. Each fixes the symptom differently. Say what each one does to the out-of-range scores, and which one still lets a legitimately excellent answer count for more than a merely good one.

Finally: the robust aggregate makes the leaderboard stable, but it also hid a real problem — the judge is emitting invalid scores. State why "robust aggregate" is a reason to keep investigating, not to stop, and what you would add to the eval so that bad scores are caught rather than silently down-weighted.

## External resources

Any robust-statistics reference (for example the entry on the breakdown point, or Huber's work on robust estimation) formalizes why the median and trimmed mean survive contamination that destroys the mean — the "breakdown point zero" claim here is that literature's headline.

Benchmark leaderboards increasingly report win rates or Elo from pairwise comparisons rather than mean scores (for example Chatbot Arena) precisely because a rank built on paired outcomes is robust to a single item's magnitude in a way a mean is not.
