---
id: ceiling-inter-01
title: Retire a benchmark once models saturate it — at the ceiling two different models both score 100% and look equal
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: A benchmark is a measuring instrument, and like any instrument it has a range. For a capability benchmark, the range is item difficulty: a benchmark can only tell two models apart on the items where one succeeds and the other fails. If every item is easy enough that both models pass, every item is uninformative, and the benchmark reports the same score — 100% — for both, no matter how large the real gap in their ability. This is saturation (a ceiling effect): the benchmark has hit its ceiling, and a score at the ceiling carries no information about how much further a model could have gone. The trap is that a saturated benchmark still produces numbers that look like a result — two models tied at 99–100% read as "equivalent" when the benchmark has simply run out of items hard enough to separate them. Worse, near the ceiling the tiny remaining differences are dominated by the handful of hardest, noisiest items, so the ranking among top models becomes driven by measurement noise rather than capability. The fix is to match the instrument to what you are measuring: a benchmark whose items straddle the models' current ability discriminates, so a real gap shows up as a real score difference, and as models improve you must retire the saturated benchmark for a harder one. On a fixture where model A (ability 8) is genuinely stronger than model B (ability 6), the easy benchmark ties them at 100%/100% (measured gap 0), while the discriminating benchmark whose items straddle the two abilities shows A at 75% and B at 25% (a 50-point gap).
eli5: Imagine testing two kids' math with a quiz that only asks "what's 2+2?" and "what's 3+1?" — both kids get everything right and score 100%, so the quiz says they're exactly equal. But one kid can do algebra and the other can't; the quiz just never asked anything hard enough to tell them apart. A perfect score doesn't mean a kid is perfect at math — it means the quiz was too easy to measure them. To see who's really better, you need harder questions that one can answer and the other can't. When both kids ace the test, it's time for a harder test, not a conclusion that they're the same.
---

## Why this module

A leaderboard where the top models cluster at 99 and 100 looks like a photo finish, and it is usually a broken stopwatch. A benchmark measures a difference in capability only through items that expose that difference — problems one model gets right and another gets wrong. Once both models clear every item, there is no exposed difference left to measure, and the identical scores they receive say nothing about whether they are actually equal; they say the test ran out of room. The failure is quiet because the benchmark still returns crisp numbers, and a tie in crisp numbers is easy to mistake for a measured equivalence rather than a measurement that hit its ceiling.

A benchmark can only tell two models apart on the items where one succeeds and the other fails. If every item is easy enough that both pass, every item is uninformative, and the benchmark reports the same score — 100% — for both, no matter how large the real gap. This is saturation, and a score at the ceiling carries no information about how much further a model could have gone, because there was nothing left to test.

Worse, near the ceiling the tiny remaining differences are dominated by the handful of hardest, noisiest, most flawed items, so the ranking among top models becomes driven by measurement noise rather than real capability. The fix is to match the instrument to what you measure: a benchmark whose items straddle the models' current ability discriminates, and as models improve you must retire the saturated one for a harder one. This module scores two models on an easy benchmark and a discriminating one.

**A benchmark can only distinguish models on items where they differ, so once models saturate it (both near the maximum score) it has hit its ceiling and can no longer rank them — their tie is an artifact of the test's range, not their equality — and you must move to a harder, discriminating benchmark to keep measuring the real gap.**

## Concepts

**A model passes an item when its ability clears the item's difficulty, and its score is the fraction it passes** — with the gap being the score difference between the two models.

```python filename=modules/evals-and-statistics/code/ceiling-inter-01/ceiling.py:52-64 COMPLETE
def passes(ability, difficulty):
    """A model passes an item when its ability is at least the item's difficulty."""
    return ability >= difficulty


def score(ability, items):
    """Fraction of items the model passes (0..1)."""
    return sum(1 for d in items if passes(ability, d)) / len(items)


def gap(abilities, items):
    """The score difference between model A and model B on a benchmark (percentage points)."""
    return (score(abilities["A"], items) - score(abilities["B"], items)) * 100
```

**Only the items the two models disagree on carry ranking signal** — a benchmark with none of them is saturated.

```python filename=modules/evals-and-statistics/code/ceiling-inter-01/ceiling.py:67-69 COMPLETE
def discriminating_items(abilities, items):
    """Items that one model passes and the other fails -- the only items that carry ranking signal."""
    return [d for d in items if passes(abilities["A"], d) != passes(abilities["B"], d)]
```

<svg role="img" aria-label="A difficulty scale from 1 to 10 with model B's ability at 6 and A's at 8 marked; the easy items 1-4 sit below both, the hard items 6-9 straddle the two abilities" viewBox="0 0 300 112" width="300" height="112">
  <text x="6" y="12" fill="var(--muted)" font-size="8">difficulty scale: easy items below both; hard items straddle</text>
  <line x1="20" y1="60" x2="285" y2="60" stroke="var(--grid)"/>
  <text x="16" y="74" fill="var(--muted)" font-size="6">1</text><text x="270" y="74" fill="var(--muted)" font-size="6">10</text>
  <line x1="170" y1="50" x2="170" y2="70" stroke="var(--s1)"/><text x="158" y="46" fill="var(--s1)" font-size="6">B=6</text>
  <line x1="222" y1="50" x2="222" y2="70" stroke="var(--s2)"/><text x="212" y="46" fill="var(--s2)" font-size="6">A=8</text>
  <g fill="var(--muted)"><circle cx="46" cy="60" r="3"/><circle cx="72" cy="60" r="3"/><circle cx="98" cy="60" r="3"/><circle cx="124" cy="60" r="3"/></g>
  <text x="46" y="90" fill="var(--muted)" font-size="6">easy 1-4: both pass (no signal)</text>
  <g><circle cx="170" cy="60" r="3" fill="var(--ink)"/><circle cx="196" cy="60" r="3" fill="var(--ink)"/><circle cx="222" cy="60" r="3" fill="var(--ink)"/><circle cx="248" cy="60" r="3" fill="var(--ink)"/></g>
  <text x="150" y="104" fill="var(--muted)" font-size="6">hard 6-9: 7 &amp; 8 fall between B and A → discriminate</text>
</svg>
^ On the difficulty scale, the easy items (1–4) sit below both models' ability so both pass them and they carry no signal, while the hard items (6–9) straddle the two abilities — items 7 and 8 fall between B's 6 and A's 8, so A passes and B fails, exposing the gap.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/ceiling-inter-01/ceiling.py

The fixture is the two models' abilities and two benchmarks — an easy one and a discriminating one.

```json filename=modules/evals-and-statistics/code/ceiling-inter-01/ceiling.json:3-7 COMPLETE
  "model_ability": {"A": 8, "B": 6},
  "benchmarks": {
    "easy_saturated": [1, 2, 3, 4],
    "hard_discriminating": [6, 7, 8, 9]
  }
```

Run `--score`.

```text filename=--score
SCORE — model A (ability 8) vs B (ability 6) on each benchmark
--------------------------------------------------------------
  benchmark              A score   B score   measured gap
  easy_saturated        100%      100%      +0 pts
  hard_discriminating   75%       25%       +50 pts
```

Read the two rows against the fact that A (ability 8) is genuinely stronger than B (ability 6). On the easy benchmark, both models score 100% and the measured gap is 0 — the benchmark declares them equal. They are not equal; every item was easy enough (difficulty 1–4) that even the weaker model cleared it, so the benchmark had nothing that could distinguish them and returned a tie. On the discriminating benchmark, whose items (6–9) straddle the two abilities, A scores 75% and B scores 25%, a 50-point gap that reflects the real difference. Same two models, same true skill gap; the only thing that changed is whether the benchmark's items were hard enough to expose it. The easy benchmark's 100/100 is not a measurement of equality — it is the absence of a measurement, dressed up as one.

## Build

The per-item view shows exactly where the signal is and where it is missing.

```text filename=--items
ITEMS — per-item pass/fail; an item separates models only if they disagree on it
------------------------------------------------------------------
  easy_saturated:
    difficulty:   1   2   3   4
    A passes:     y   y   y   y
    B passes:     y   y   y   y
    discriminating items (A!=B): none -- benchmark is saturated
  hard_discriminating:
    difficulty:   6   7   8   9
    A passes:     y   y   y   n
    B passes:     y   n   n   n
    discriminating items (A!=B): [7, 8]
```

<svg role="img" aria-label="A grid of pass/fail for the hard benchmark: item 6 both pass, items 7 and 8 A passes but B fails (discriminating), item 9 both fail; only 7 and 8 carry signal" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">hard benchmark: only items 7 &amp; 8 separate A from B</text>
  <text x="30" y="30" fill="var(--muted)" font-size="7">item</text><text x="90" y="30" fill="var(--muted)" font-size="7">6</text><text x="140" y="30" fill="var(--muted)" font-size="7">7</text><text x="190" y="30" fill="var(--muted)" font-size="7">8</text><text x="240" y="30" fill="var(--muted)" font-size="7">9</text>
  <text x="30" y="48" fill="var(--s2)" font-size="7">A</text><text x="88" y="48" fill="var(--s1)" font-size="7">✓</text><text x="138" y="48" fill="var(--s1)" font-size="7">✓</text><text x="188" y="48" fill="var(--s1)" font-size="7">✓</text><text x="238" y="48" fill="var(--s2)" font-size="7">✗</text>
  <text x="30" y="66" fill="var(--s1)" font-size="7">B</text><text x="88" y="66" fill="var(--s1)" font-size="7">✓</text><text x="138" y="66" fill="var(--s2)" font-size="7">✗</text><text x="188" y="66" fill="var(--s2)" font-size="7">✗</text><text x="238" y="66" fill="var(--s2)" font-size="7">✗</text>
  <rect x="128" y="34" width="84" height="40" fill="none" stroke="var(--ink)"/><text x="128" y="88" fill="var(--ink)" font-size="6">discriminating (A≠B): items 7, 8</text>
  <text x="30" y="88" fill="var(--muted)" font-size="6">6: both ✓ (floor)</text><text x="216" y="88" fill="var(--muted)" font-size="6">9: both ✗ (ceiling)</text>
</svg>
^ On the hard benchmark only items 7 and 8 discriminate — A passes and B fails them; item 6 is at this benchmark's floor for these models (both pass) and item 9 at its ceiling (both fail), so those two contribute nothing to the ranking, and the whole 50-point gap comes from the two boxed items.

Look at where A and B disagree. On the easy benchmark, the "A passes" and "B passes" rows are identical — all y — so there is not a single item on which the two models differ, and the count of discriminating items is zero. Every item is redundant with respect to ranking: it tells you both models can do easy things, which you already knew, and nothing about which is better. On the discriminating benchmark, items 7 and 8 are the ones that matter: they are harder than B's ability (6) but within A's (8), so A passes and B fails, and those two items are the entire source of the 50-point gap. Item 6 (both pass) and item 9 (both fail) contribute nothing to the ranking — they are at the floor and ceiling of *this* benchmark for these models. The general principle is that a benchmark's discriminating power for a given pair of models lives entirely in the items whose difficulty falls *between* their abilities; a benchmark with none such is saturated for that pair, and adding more easy items never helps — you need items in the gap.

```python filename=modules/evals-and-statistics/code/ceiling-inter-01/ceiling.py:107-115 COMPLETE
    saturated_both_max = score(ab["A"], easy) == 1.0 and score(ab["B"], easy) == 1.0
    print("  on the easy benchmark both models score 100%% = %s (A %.0f%%, B %.0f%%)"
          % (saturated_both_max, score(ab["A"], easy) * 100, score(ab["B"], easy) * 100))

    saturated_gap_zero = gap(ab, easy) == 0
    print("  the saturated benchmark measures a zero gap = %s (%.0f pts)" % (saturated_gap_zero, gap(ab, easy)))

    true_gap_exists = ab["A"] > ab["B"]
    print("  but the models are genuinely unequal = %s (ability %d vs %d)" % (true_gap_exists, ab["A"], ab["B"]))
```

## Definition of done

The self-test pins the ceiling tie, the true inequality it hides, the discriminating benchmark's revealed gap, and the absence of signal in the saturated one.

```python filename=modules/evals-and-statistics/code/ceiling-inter-01/ceiling.py:117-122 COMPLETE
    discriminating_shows_gap = gap(ab, hard) > 0
    print("  the discriminating benchmark reveals the gap = %s (%.0f pts)" % (discriminating_shows_gap, gap(ab, hard)))

    saturated_has_no_signal = len(discriminating_items(ab, easy)) == 0 and len(discriminating_items(ab, hard)) > 0
    print("  the saturated benchmark has no discriminating items, the hard one does = %s (%d vs %d)"
          % (saturated_has_no_signal, len(discriminating_items(ab, easy)), len(discriminating_items(ab, hard))))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the saturated benchmark ties two unequal models at the ceiling; the discriminating one reveals the true gap
------------------------------------------------------------------------------------------------------------------------
  on the easy benchmark both models score 100% = True (A 100%, B 100%)
  the saturated benchmark measures a zero gap = True (0 pts)
  but the models are genuinely unequal = True (ability 8 vs 6)
  the discriminating benchmark reveals the gap = True (50 pts)
  the saturated benchmark has no discriminating items, the hard one does = True (0 vs 2)
```

<svg role="img" aria-label="Measured gap on two benchmarks for the same two models: 0 points on the saturated benchmark, 50 points on the discriminating one" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same two models, same true gap — different benchmark, different verdict</text>
  <text x="10" y="38" fill="var(--muted)" font-size="7">saturated</text>
  <rect x="90" y="28" width="3" height="14" fill="var(--s2)"/><text x="98" y="39" fill="var(--muted)" font-size="7">gap 0 — "they're equal" (wrong)</text>
  <text x="10" y="66" fill="var(--muted)" font-size="7">discriminating</text>
  <rect x="90" y="56" width="150" height="14" fill="var(--s1)"/><text x="244" y="66" fill="var(--muted)" font-size="7">gap 50</text>
  <text x="10" y="86" fill="var(--muted)" font-size="6">a 0-point gap at the ceiling is the absence of a measurement, not equality</text>
</svg>
^ The identical models yield a 0-point gap on the saturated benchmark (read as "equal") and a 50-point gap on the discriminating one — the flat saturated bar is not a measurement of equality but the absence of a measurement, which only a harder benchmark supplies.

**Done means the ceiling effect is proven on real scores: two genuinely unequal models (ability 8 vs 6) both score 100% on the easy benchmark for a measured gap of 0, while the discriminating benchmark whose items straddle their abilities shows 75% vs 25% for a 50-point gap — the saturated benchmark has zero discriminating items and its tie is an artifact of its range, so a saturated benchmark must be retired for a harder one.**

## Boss fight

Predict two ways benchmark saturation is subtler than "retire it at 100%," because the ceiling bites before the score reads 100 and pushing past it has its own hazards.

The first trap is that saturation degrades a benchmark long before any model literally maxes it out — the ceiling effect is gradual, and the top of the range goes bad first. As models approach the ceiling, the pool of discriminating items shrinks (there are fewer problems that separate the leaders), so the effective sample size for ranking the top models collapses even while the headline score is only, say, 92%. At that point the ranking among the frontier models rests on a handful of the hardest items, which are disproportionately the benchmark's noisiest and most flawed — mislabeled answers, ambiguous questions, items sensitive to prompt formatting — so the top of the leaderboard becomes a measurement of who best fits the benchmark's quirks and errors, not who is most capable. This is why a benchmark can be simultaneously "not yet saturated" by its average score and useless for its most important job (ranking the best models): the discriminating power at the top is exhausted well before the mean is. The practical signals are a compressed spread among top models, results that flip with trivial reformatting, and gains that come from the known-bad items — all of which say "retire or refresh this benchmark for the frontier" long before it reads 100%.

The second trap is that the fix — harder items, or a new benchmark — reintroduces every measurement problem a mature benchmark had solved, so "just make it harder" is not free. A new, harder benchmark is unvalidated: its items may be hard for the wrong reasons (ambiguous, mis-keyed, or requiring knowledge the task did not intend), its difficulty may not be calibrated to the models, and it has no track record, so early scores on it are noisy and easy to over-read. Harder benchmarks are also more expensive to build and label correctly (expert annotation, careful adjudication), and they are prime targets for contamination — a much-discussed hard benchmark leaks into training data and re-saturates, this time falsely. And there is a measurement-theory point: raising difficulty helps only if the new items are hard along the dimension you care about; adding items that are hard because they are tricky or adversarial in an irrelevant way measures robustness-to-quirks, not capability. So keeping a benchmark useful is an ongoing instrument-design problem — calibrate item difficulty to the current frontier, validate and clean the hard items especially, guard against contamination, and be clear about which capability the difficulty is testing — not a one-time swap. The ceiling is a moving target, and the discipline is continuous recalibration of the instrument to the thing being measured.

**Saturation bites at the top of the range first: the discriminating pool for the frontier models shrinks long before the mean score hits 100%, so a compressed top-of-leaderboard, format-sensitive flips, and gains coming from the benchmark's flawed hardest items all mean it should be retired or refreshed for ranking leaders even at, say, 92%. And "make it harder" is not free — a new benchmark is unvalidated, costly to label, prone to contamination that re-saturates it, and only useful if its added difficulty is along the capability dimension you care about — so keeping an eval informative is continuous instrument recalibration, not a one-time swap.**

## External resources

Writing on benchmark saturation and the shift to harder evaluations (the retirement of GLUE for SuperGLUE, and the motivation behind frontier benchmarks like GPQA, ARC-AGI, and Humanity's Last Exam) — why benchmarks are retired as models saturate them and how difficulty is targeted to the frontier.

Item response theory and psychometrics references — how item difficulty and discrimination determine an instrument's measuring range, why a test discriminates only near the tested abilities, and how ceiling and floor effects arise.

The companion item-discrimination, run-to-run-variance, and winner's-curse modules in this topic — saturation is the aggregate consequence of a benchmark running out of discriminating items, near-ceiling ranking is dominated by the seed and item noise those modules quantify, and picking the "best" model on the noisy top items is the winner's curse in another form.
