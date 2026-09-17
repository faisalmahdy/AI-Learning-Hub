---
id: evals-inter-08
title: A leaked test item inflates the score — and on a head-to-head it can crown a false winner
topic: evals-and-statistics
level: intermediate
status: ready
time: 5-8h
summary: An eval is only honest if the system has not seen the answers, because when test items leak into a system's training data, its context, or its memory, it does not solve them, it recalls them, and it scores near-perfect on exactly those items — inflating the aggregate. The danger is sharpest in a comparison: if one system was contaminated and its baseline was not, the contaminated system wins the eval on memorized items alone while the clean items, where real ability shows, are tied. Here system A has seen 4 of 10 test items and B has not; on the 6 clean items the two are dead even at 0.60, but A scores a perfect 1.0 on its 4 contaminated items, so the naive aggregate over all 10 gives A 0.76 to B's 0.60 and declares A the clear winner — yet scoring only the clean items undoes it, 0.60 to 0.60, a tie. Contamination did not just inflate a number, it manufactured a ranking that reverses on honest data, so an eval must exclude (or detect) the items a system has already seen, and a suspiciously perfect score on a subset is itself the fingerprint of a leak.
eli5: Imagine two students taking the same test, and one of them somehow got the answer key for four of the ten questions. On those four they score perfectly — not because they're smarter, but because they memorized the answers. On the other six they do exactly as well as the other student. If you grade all ten questions, the one with the answer key "wins." If you grade only the six fair questions, it's a tie. The four leaked questions didn't measure anything except who cheated, and counting them invents a winner who isn't really better.
---

## Why this module

An eval measures ability by posing problems the system has not seen and checking the answers. That "has not seen" is load-bearing, and it is the part that quietly fails. Test items leak — into pretraining data scraped from the web, into a few-shot prompt, into a retrieval store, into an agent's memory of a previous run — and once an item has leaked, the system's response to it is no longer a measurement of ability. It is recall. The system reproduces the memorized answer and scores near-perfect, and that perfect score enters the aggregate looking exactly like competence.

On a single system this inflates the headline number, which is bad enough. But evals are mostly used to compare — is the new model better than the old, does this change help — and that is where contamination does its real damage. Suppose you are comparing a new system against a baseline, and the new system's training data happened to include some of your test set while the baseline's did not. On the contaminated items the new system scores perfectly by recall; on the clean items the two systems show their true, possibly equal, ability. Average over everything and the new system wins — not because it is better, but because it memorized part of the test. You ship it believing in an improvement that does not exist.

This module makes the false winner concrete. Two systems, A and B, have identical true ability — on clean items they both average 0.60. But A has seen 4 of the 10 test items and scores 1.0 on them by recall. The naive aggregate crowns A at 0.76 against B's 0.60; the clean-only aggregate, over just the items neither system memorized, reports the truth: 0.60 to 0.60, a tie. Everything runs offline against an eval fixture, stdlib Python 3, `$0.00`, with every aggregate computed. The instinct to unlearn is that a higher eval score means a better system. A higher score can mean a more contaminated test set, and the only defense is to know which items the system has seen and score on the ones it has not.

## Concepts

Named here so you can find them again; each is built below.

- **Contamination** — a test item the system has already seen (in training, context, or memory).
- **Recall vs ability** — a memorized answer scores perfectly but measures nothing about skill.
- **Naive aggregate** — the score over all items, including contaminated ones; inflated.
- **Clean-only aggregate** — the score over items the system has not seen; the honest estimate.
- **False winner** — a head-to-head ranking that contamination produces and clean data reverses.
- **Contamination fingerprint** — a suspiciously perfect score on a subset of items.

## Worked example

Source: a head-to-head model comparison — the eval that decides whether a new system beats a baseline. The two systems and the per-item scores stand in for a real A/B where one model's training set overlapped the test set; the clean/contaminated split is the knowledge of which items leaked.

Script and fixture: `modules/evals-and-statistics/code/evals-inter-08/` — `contamination.py`, and `eval.json`, ten items scored for two systems. Every command runs from there.

### The two aggregates

The naive score averages every item; the clean score averages only the items that did not leak.

```
# contamination.py:44-53 — COMPLETE (average over all items vs over only the clean ones)
def naive_score(items, system):
    """Average over ALL items -- including the ones the system has already seen."""
    return mean([it[system] for it in items])


def clean_score(items, system):
    """Average over only the items that did NOT leak to the system."""
    clean = [it for it in items if not it["contaminated"]]
    return mean([it[system] for it in clean])
```

The only difference is the `if not it["contaminated"]` filter — the clean score drops the items the system has seen. That one filter is the entire fix, and its absence is the entire bug. Look at the items:

```
# $ python3 contamination.py --items   (abbreviated)
#   id    A score  B score  contaminated (for A)
#   q1    0.50     0.60     False
#   q6    0.70     0.50     False
#   q7    1.00     0.60     True
#   q10   1.00     0.70     True
```

run: 2026-08-27 · deterministic; per-item scores and flags are a fixture · 10 items · `python3 contamination.py --items`

On the clean items (q1–q6) A and B trade the lead item by item and come out even — neither is systematically better. On the contaminated items (q7–q10) A scores a flat 1.0 every time while B scores its usual ~0.6, because A has seen those four and B has not. A's perfect run on exactly the leaked items is the fingerprint: real ability is noisy and item-dependent, but recall is perfect and uniform, so a subset where one system suddenly scores 1.0 across the board is the shape contamination makes.

<svg viewBox="0 0 700 200" role="img" aria-label="Per-item scores for A and B. On clean items q1 to q6, A and B bars are similar heights around 0.5 to 0.7, trading the lead. On contaminated items q7 to q10, A's bars are all at the maximum 1.0 while B's stay around 0.6. A's flat perfect run on the contaminated items stands out.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">per-item A (filled) vs B (outline): A is perfect only on the leaked items</text>
    <line x1="50" y1="150" x2="660" y2="150" stroke="var(--line)"></line>
    <line x1="360" y1="40" x2="360" y2="160" stroke="var(--s2)" stroke-dasharray="4 3"></line><text x="360" y="34" text-anchor="middle" fill="var(--s2)" font-size="7">contaminated →</text>
    <g>
      <rect x="60" y="100" width="14" height="50" fill="var(--s1)"></rect><rect x="76" y="90" width="14" height="60" fill="none" stroke="var(--muted)"></rect>
      <rect x="110" y="80" width="14" height="70" fill="var(--s1)"></rect><rect x="126" y="90" width="14" height="60" fill="none" stroke="var(--muted)"></rect>
      <rect x="160" y="90" width="14" height="60" fill="var(--s1)"></rect><rect x="176" y="100" width="14" height="50" fill="none" stroke="var(--muted)"></rect>
      <rect x="210" y="90" width="14" height="60" fill="var(--s1)"></rect><rect x="226" y="80" width="14" height="70" fill="none" stroke="var(--muted)"></rect>
      <rect x="260" y="100" width="14" height="50" fill="var(--s1)"></rect><rect x="276" y="80" width="14" height="70" fill="none" stroke="var(--muted)"></rect>
      <rect x="310" y="80" width="14" height="70" fill="var(--s1)"></rect><rect x="326" y="100" width="14" height="50" fill="none" stroke="var(--muted)"></rect>
      <rect x="390" y="50" width="14" height="100" fill="var(--s2)"></rect><rect x="406" y="90" width="14" height="60" fill="none" stroke="var(--muted)"></rect>
      <rect x="440" y="50" width="14" height="100" fill="var(--s2)"></rect><rect x="456" y="100" width="14" height="50" fill="none" stroke="var(--muted)"></rect>
      <rect x="490" y="50" width="14" height="100" fill="var(--s2)"></rect><rect x="506" y="90" width="14" height="60" fill="none" stroke="var(--muted)"></rect>
      <rect x="540" y="50" width="14" height="100" fill="var(--s2)"></rect><rect x="556" y="80" width="14" height="70" fill="none" stroke="var(--muted)"></rect>
    </g>
    <text x="200" y="176" text-anchor="middle" fill="var(--muted)" font-size="7">clean items (A ≈ B)</text>
    <text x="470" y="176" text-anchor="middle" fill="var(--s2)" font-size="7">contaminated (A = 1.0, recall)</text>
  </g>
</svg>
^ On the clean items A and B are interchangeable; on the contaminated items A's bars all hit the ceiling while B's stay normal. That flat, perfect block on the leaked items is recall, not skill, and it is the visual signature of contamination.

### The false winner

Aggregate both ways and the verdict flips.

```
# contamination.py:60-63 — COMPLETE (who wins, with a tie band)
def winner(a, b, eps=1e-9):
    if abs(a - b) < eps:
        return "tie"
    return "A" if a > b else "B"
```

```
# $ python3 contamination.py --scores
#   naive:      A 0.7600   B 0.6000   -> winner A
#   clean-only: A 0.6000   B 0.6000   -> winner tie
```

run: 2026-08-27 · deterministic · `python3 contamination.py --scores`

<svg viewBox="0 0 700 190" role="img" aria-label="Two aggregates side by side. Naive: A at 0.76 clearly above B at 0.60, A wins. Clean-only: A at 0.60 equal to B at 0.60, a tie. The verdict flips between the two.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the verdict flips: naive crowns A, clean-only is a tie</text>
    <line x1="60" y1="160" x2="660" y2="160" stroke="var(--line)"></line>
    <text x="200" y="178" text-anchor="middle" fill="var(--muted)" font-size="8">NAIVE (all items)</text>
    <rect x="110" y="46" width="60" height="114" fill="var(--s2)"></rect><text x="140" y="40" text-anchor="middle" fill="var(--s2)" font-size="8">A .76</text>
    <rect x="230" y="70" width="60" height="90" fill="var(--muted)"></rect><text x="260" y="64" text-anchor="middle" fill="var(--muted)" font-size="8">B .60</text>
    <text x="200" y="192" text-anchor="middle" fill="var(--s2)" font-size="7">A wins ✗</text>
    <text x="500" y="178" text-anchor="middle" fill="var(--muted)" font-size="8">CLEAN-ONLY</text>
    <rect x="420" y="70" width="60" height="90" fill="var(--s1)"></rect><text x="450" y="64" text-anchor="middle" fill="var(--s1)" font-size="8">A .60</text>
    <rect x="540" y="70" width="60" height="90" fill="var(--s1)"></rect><text x="570" y="64" text-anchor="middle" fill="var(--s1)" font-size="8">B .60</text>
    <text x="500" y="192" text-anchor="middle" fill="var(--s1)" font-size="7">tie ✓</text>
  </g>
</svg>
^ The naive aggregate shows A towering over B and ends the debate; the clean-only aggregate shows them level. The entire margin was the four memorized items.

The naive aggregate gives A 0.76 to B's 0.60 and declares A the winner by a wide, confident margin — the kind of margin that ends a debate and ships a model. The clean-only aggregate, computed over just the six items neither system had seen, gives 0.60 to 0.60: a tie. The 0.16-point "win" was entirely the four memorized items, worth nothing about ability. An eval that reported the naive number would have crowned a system that is not actually better, and no amount of statistical care on the naive number — confidence intervals, more items, significance tests — would have caught it, because the contamination biases the estimate itself, not its variance.

**A leaked test item is scored by recall, not ability, so it inflates the aggregate — and in a head-to-head where one system is contaminated and its baseline is not, it manufactures a false winner: A beats B 0.76 to 0.60 on all items but ties 0.60 to 0.60 on the clean ones, so an eval must score only items the system has not seen, and a perfect score on a subset is the fingerprint of a leak, not a triumph.**

### The self-test

The `--check` mode plants the bug — scoring contaminated items — and proves it: A scores higher on seen items than clean ones (recall), the naive eval crowns A, the clean eval says tie, so the naive winner is false.

```
# $ python3 contamination.py --check
#   A scores higher on seen items than on clean ones (recall) = True (1.00 vs 0.60)
#   the naive eval (all items) declares A the winner = True (0.7600 vs 0.6000)
#   the clean-only eval declares a tie = True (0.6000 vs 0.6000)
#   so the naive winner is FALSE -- it reverses on clean data = True
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 contamination.py --check`

The inflation is measured directly as A's mean on the items it has seen versus the items it has not:

```
# contamination.py:55-58 — COMPLETE (A's mean on the contaminated items -- pure recall)
def contaminated_mean(items, system):
    con = [it for it in items if it["contaminated"]]
    return mean([it[system] for it in con]) if con else 0.0
```

<svg viewBox="0 0 700 150" role="img" aria-label="The naive score for A shown as a blend. Six clean items contribute a true tie at 0.60; four contaminated items contribute a fake win at 1.0. Blended 6-to-4, the naive score is 0.76, pulled up from the true 0.60 by the memorized items.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">A's naive 0.76 is a blend of a true tie and a fake win</text>
    <rect x="60" y="50" width="300" height="30" fill="var(--s1)"></rect><text x="210" y="69" text-anchor="middle" fill="var(--panel)" font-size="8">6 clean items · true 0.60 (tie)</text>
    <rect x="360" y="50" width="200" height="30" fill="var(--s2)"></rect><text x="460" y="69" text-anchor="middle" fill="var(--panel)" font-size="8">4 leaked · 1.0 (recall)</text>
    <line x1="60" y1="95" x2="560" y2="95" stroke="var(--line)"></line>
    <line x1="456" y1="95" x2="456" y2="110" stroke="var(--acc-line)"></line><text x="456" y="124" text-anchor="middle" fill="var(--acc-ink)" font-size="8">blend = 0.76</text>
    <text x="60" y="140" fill="var(--muted)" font-size="8">the leaked items drag the average up from the honest 0.60 — the fake win leaks through</text>
  </g>
</svg>
^ The naive average mixes six honest items (true 0.60) with four memorized ones (1.0), landing at 0.76. The contamination does not average out; it pulls the score up, and the pull is the false margin.

The `inflates` line is the detector and the `false_winner` line is the stakes. That A scores 1.0 on seen items and 0.60 on clean ones is both the mechanism of the inflation and, in practice, the signal you would use to suspect contamination in the first place — a system that is far better on a specific subset than on the rest has probably seen that subset. And `false_winner` is why this matters more than a wrong absolute score: it corrupts the decision the eval exists to make.

```
# contamination.py:103-108 — COMPLETE (naive crowns A; clean says tie -> the winner is false)
    naive_says_a = winner(na, nb) == "A"
    print("  the naive eval (all items) declares A the winner = %s (%.4f vs %.4f)" % (naive_says_a, na, nb))

    ca, cb = clean_score(items, "A"), clean_score(items, "B")
    clean_says_tie = winner(ca, cb) == "tie"
    print("  the clean-only eval declares a tie = %s (%.4f vs %.4f)" % (clean_says_tie, ca, cb))
```

### The running tally

| item set | A score | B score | verdict |
|---|---|---|---|
| clean (q1–q6) | 0.60 | 0.60 | tie (true ability) |
| contaminated (q7–q10) | 1.00 | 0.60 | A (by recall) |
| all items (naive) | 0.76 | 0.60 | A (false winner) |

Read down the verdict column: the true relationship is the tie on clean items, the contaminated items alone say "A" purely through recall, and the naive aggregate inherits that false "A" by mixing the two. The naive result is a weighted blend of a real tie and a fake win, and the fake win leaks through. The fix is to compute the eval only on the clean row — but that requires knowing which items are contaminated, which is the hard part in practice and the reason contamination is so corrosive: by default you cannot see it in the aggregate, only in the per-item pattern that the clean/contaminated split makes visible.

### What we did not settle

This is the mechanism; defending against it is an active discipline. Detecting contamination is the real work — you rarely get a clean `contaminated` flag — so practitioners look for the fingerprint (a subset scored far above the rest), test on data created after the model's training cutoff, use canary strings and held-out private sets, and probe whether a model can complete a test item verbatim. Contamination is a spectrum: verbatim memorization is the extreme, but near-duplicates and having seen the answer explained also leak signal. A private, rotating eval set is the strongest structural defense, since a set that never leaves your hands cannot be trained on. And contamination interacts with the Goodhart problem (`evals-inter-06`): once a benchmark is public and optimized against, some leakage is nearly inevitable, which is why a single public benchmark score is weak evidence. The invariant: score only what the system has not seen, and treat a suspiciously perfect subset as a leak until proven otherwise.

## Build

The build in one paragraph: before trusting an eval, establish which items the system may have already seen — from its training data, its context, its memory — and compute the score on only the clean items, because a leaked item is answered by recall and measures nothing; in a head-to-head, contamination of one side manufactures a winner that vanishes on clean data. Detect leakage by its fingerprint (a subset scored far above the rest), prefer data created after the training cutoff, keep a private rotating held-out set, and treat any single public-benchmark number as weak evidence.

We opened on the items. The number that proves the danger is the verdict flipping between the two aggregates:

```
# modules/evals-and-statistics/code/evals-inter-08/ — COMPLETE, run from that directory
$ python3 contamination.py --scores
  naive:      A 0.7600   B 0.6000   -> winner A
  clean-only: A 0.6000   B 0.6000   -> winner tie
```

Now build your own. Take a real head-to-head where you can mark which items one system may have seen (or synthesize a contaminated subset), and compute both the naive and clean-only aggregates. Your number to beat is not the headline score; it is **the winner under each aggregate** — the naive eval should crown the contaminated system while the clean eval undoes it. Confirm the contaminated system scores far higher on seen items than clean ones. Bring back both verdicts. Good luck.

## Definition of done

- [ ] Per-item scores for two systems and a contamination flag per item
- [ ] A naive aggregate over all items and a clean-only aggregate
- [ ] A winner function with a tie band
- [ ] Confirmation the contaminated system scores higher on seen items than clean ones
- [ ] Confirmation the naive eval crowns the contaminated system
- [ ] Confirmation the clean-only eval reverses the verdict (a tie)
- [ ] `python3 contamination.py --check` printing SELF-TEST PASS: inflates, naive_says_a, clean_says_tie, false_winner
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does a leaked test item measure recall rather than ability?
2. Why is contamination more dangerous in a head-to-head than for a single system's absolute score?
3. On the fixture, what did the naive eval decide and what did the clean-only eval decide? Why do they differ?
4. What is the "fingerprint" of contamination in the per-item scores, and why does it look that way?
5. Your own head-to-head had a contaminated subset. What winner did each aggregate report, and did the clean one reverse it?

## External resources

- Work on data contamination in LLM benchmarks (e.g. the GSM8k / benchmark-leakage analyses, and Oren et al. on provable test-set contamination) — my summary: how leakage inflates public benchmark scores and how to detect it; read it for the detection methods this module only names.
- Guidance on held-out and post-cutoff evaluation sets — my summary: why a private, rotating, or post-training-cutoff test set is the structural defense against contamination; read it for how to build an eval that cannot be trained on.
- This hub, *evals-inter-06* (Goodhart) and *evals-inter-01* (the interval that decides) — read them for why an optimized public benchmark leaks by nature, and why no confidence interval on a contaminated score can rescue it.
