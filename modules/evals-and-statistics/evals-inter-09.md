---
id: evals-inter-09
title: Pair the comparison on the same cases — an unpaired test drowns a real win in case difficulty
topic: evals-and-statistics
level: intermediate
status: ready
time: 24 min
summary: When two systems run on the same eval cases, comparing them as two separate piles lets case-to-case difficulty swamp the signal. Pairing on the case cancels that variance. On identical data the unpaired 95% interval is (−12, 18) and calls it a wash; the paired interval is (2.4, 3.4) and B wins.
eli5: To see if your new shoes make you jump higher, you don't compare a pile of jumps in old shoes to a pile in new shoes — people's jumping ability differs so much it hides the shoes. You have each person jump in both and look at how much higher they got. The differences are small and steady, and the answer jumps right out.
---

## Why this module

Almost every eval you run compares two systems on the same set of cases — and if you analyze it as though they were two unrelated groups, you throw away most of your power to detect a difference.

Here is the shape of the problem. You have twelve test cases. Some are easy, some are hard, and that difficulty varies enormously — one case scores in the nineties for everyone, another in the forties. You run system A and system B across all twelve. On every case B edges out A by a couple of points. The question is whether that edge is real or noise, and the honest-looking move is to compute A's average, compute B's average, and put a confidence interval on the gap. That is the unpaired, two-sample comparison, and on data like this it will tell you there is no significant difference — because each system's scores are spread across sixty points of case difficulty, and a two-point gap is invisible against sixty points of spread.

But you did not run A and B on different cases. You ran them on the same cases, and that is a gift you just threw away. Case c04 is hard for A and hard for B; subtract one score from the other and the hardness cancels, leaving only the thing you care about — how much better B is on that case. Pairing on the case removes the case-to-case variance from the comparison entirely, and what is left is a small, steady signal you can measure precisely.

We will run both analyses on one fixture and watch them disagree completely. Same twelve pairs of numbers, same point estimate of the gap, and yet the unpaired interval spans from −12 to +18 while the paired interval sits at (2.4, 3.4). One says "who knows," the other says "B wins, and by about three points."

**When both systems saw the same cases, the case is a variable you can subtract out — analyze the per-case differences, not two piles of scores, or you pay for variance that has nothing to do with which system is better.**

## Concepts

The unpaired two-sample test asks: are these two piles of numbers drawn from distributions with different means? Its uncertainty about the answer grows with how spread out each pile is, because a wide pile could have any mean. When the spread comes from case difficulty — an intrinsic property of the test set, identical for both systems — that spread inflates the uncertainty of the unpaired test even though it tells you nothing about A versus B.

The paired test asks a different question: are the per-case differences centered away from zero? It forms one number per case, B minus A, and tests whether those differences have a nonzero mean. The move is subtraction, and subtraction is where the magic lives. Whatever made case c04 score high — its difficulty, its topic, its length — affects A's score and B's score together, so it appears in both terms of `B - A` and cancels. The difference retains only the part that differs between the systems.

Variance is the currency here. The standard error of the unpaired difference is built from the variance of A's scores plus the variance of B's scores — both large, because both mix easy and hard cases. The standard error of the paired difference is built from the variance of the differences alone — small, because the differences are all in a tight band. Same data, but the paired standard error is a fraction of the unpaired one, and the standard error is what sets the width of your interval and the threshold for significance.

<svg role="img" aria-label="One case decomposed: A's and B's score each equal case difficulty plus a system term; subtracting cancels the shared difficulty and leaves only the system gap" viewBox="0 0 460 160" width="460" height="160">
  <rect x="0" y="0" width="460" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="26" font-family="var(--mono)" font-size="11" fill="var(--muted)">case c04 (a hard case)</text>
  <rect x="40" y="36" width="200" height="26" fill="var(--s2)" stroke="var(--line)"/>
  <text x="48" y="54" font-family="var(--mono)" font-size="11" fill="var(--ink)">A = difficulty 90</text>
  <rect x="240" y="36" width="40" height="26" fill="var(--acc-line)" stroke="var(--acc-ink)"/>
  <text x="285" y="54" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">= 90</text>
  <rect x="40" y="70" width="200" height="26" fill="var(--s2)" stroke="var(--line)"/>
  <text x="48" y="88" font-family="var(--mono)" font-size="11" fill="var(--ink)">B = difficulty 90</text>
  <rect x="240" y="70" width="53" height="26" fill="var(--acc-line)" stroke="var(--acc-ink)"/>
  <text x="298" y="88" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">= 93</text>
  <line x1="40" y1="112" x2="300" y2="112" stroke="var(--line)"/>
  <text x="48" y="132" font-family="var(--mono)" font-size="11" fill="var(--ink)">B − A: the 90s cancel →</text>
  <rect x="240" y="118" width="18" height="20" fill="var(--acc-ink)"/>
  <text x="264" y="134" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">+3</text>
</svg>
^ Each score is case difficulty plus a small system term; the difficulty is identical for A and B, so subtracting on the case erases it and leaves only the +3 you care about.

This is not a trick to manufacture significance; it is using information you already have. The pairing is real — A and B genuinely faced the same case — so subtracting on the case is a valid, more powerful analysis, not a cheat. The cheat would be the reverse: running A and B on different cases and then pretending they were paired. When the design pairs, the analysis must pair, or you are answering a harder question than the one you set up.

**The unpaired test spends its precision estimating case difficulty you do not care about; the paired test spends all of it on the system gap you do.**

## Worked example

The fixture is twelve cases, each with A's score, B's score, and — because the design is paired — the two critical t-values noted alongside.

```json filename=modules/evals-and-statistics/code/evals-inter-09/scores.json:7-16 COMPLETE
  "t_crit_95": {
    "df11_paired": 2.201,
    "df22_unpaired": 2.074
  },
  "cases": [
    {
      "case": "c01",
      "A": 55,
      "B": 58
    },
```

The two critical values are the only fixed statistical inputs — the 95% two-sided t-multipliers for the paired test's 11 degrees of freedom and the unpaired test's 22. Everything else is computed from the scores. Print the scores with their per-case differences.

```text filename=modules/evals-and-statistics/code/evals-inter-09/paired.py --scores
  case    A     B    B-A
  c01   55    58   +3
  c02   82    84   +2
  c03   61    65   +4
  c04   90    93   +3
  c05   48    50   +2
  c06   73    76   +3
  c07   88    92   +4
  c08   52    54   +2
  c09   67    70   +3
  c10   79    82   +3
  c11   43    47   +4
  c12   95    97   +2
  mean A = 69.42   mean B = 72.33   mean diff = +2.92
  B beats A on 12 of 12 cases; the gap is small but never reverses.
```

Read the two columns of scores and then read the `B-A` column. The scores swing from 43 to 97 — a sixty-point range of case difficulty. The differences swing from +2 to +4 — a two-point band, and never once negative. That contrast is the whole module in one table: huge variance in the levels, tiny variance in the differences. B beats A on all twelve cases, which no unpaired test will ever be able to see, because it never looks at a case.

<svg role="img" aria-label="Two views of the same scores: A and B levels scattered across a wide range, and the per-case B-minus-A differences clustered tightly above zero" viewBox="0 0 460 210" width="460" height="210">
  <rect x="0" y="0" width="460" height="210" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">levels (A ○, B ●): spread over 60 points</text>
  <line x1="30" y1="70" x2="440" y2="70" stroke="var(--grid)"/>
  <circle cx="70" cy="62" r="4" fill="var(--panel)" stroke="var(--ink)"/><circle cx="76" cy="62" r="4" fill="var(--s1)" stroke="var(--ink)"/>
  <circle cx="250" cy="42" r="4" fill="var(--panel)" stroke="var(--ink)"/><circle cx="256" cy="42" r="4" fill="var(--s1)" stroke="var(--ink)"/>
  <circle cx="120" cy="58" r="4" fill="var(--panel)" stroke="var(--ink)"/><circle cx="126" cy="58" r="4" fill="var(--s1)" stroke="var(--ink)"/>
  <circle cx="400" cy="38" r="4" fill="var(--panel)" stroke="var(--ink)"/><circle cx="406" cy="38" r="4" fill="var(--s1)" stroke="var(--ink)"/>
  <circle cx="180" cy="66" r="4" fill="var(--panel)" stroke="var(--ink)"/><circle cx="186" cy="66" r="4" fill="var(--s1)" stroke="var(--ink)"/>
  <text x="16" y="120" font-family="var(--mono)" font-size="11" fill="var(--muted)">differences (B−A): clustered at +3</text>
  <line x1="30" y1="175" x2="440" y2="175" stroke="var(--grid)"/>
  <text x="24" y="192" font-family="var(--mono)" font-size="10" fill="var(--muted)">0</text>
  <line x1="30" y1="140" x2="440" y2="140" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="360" y="136" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">+3</text>
  <circle cx="70" cy="140" r="4" fill="var(--acc-line)" stroke="var(--acc-ink)"/><circle cx="120" cy="148" r="4" fill="var(--acc-line)" stroke="var(--acc-ink)"/><circle cx="170" cy="132" r="4" fill="var(--acc-line)" stroke="var(--acc-ink)"/><circle cx="220" cy="140" r="4" fill="var(--acc-line)" stroke="var(--acc-ink)"/><circle cx="270" cy="148" r="4" fill="var(--acc-line)" stroke="var(--acc-ink)"/><circle cx="320" cy="140" r="4" fill="var(--acc-line)" stroke="var(--acc-ink)"/><circle cx="370" cy="132" r="4" fill="var(--acc-line)" stroke="var(--acc-ink)"/><circle cx="410" cy="148" r="4" fill="var(--acc-line)" stroke="var(--acc-ink)"/>
</svg>
^ The levels scatter across the whole range because cases differ in difficulty; the differences collapse into a tight band above zero because that difficulty cancels case by case.

Here is the unpaired test. It builds its standard error from both piles' variances.

```python filename=modules/evals-and-statistics/code/evals-inter-09/paired.py:52-57 COMPLETE
def unpaired_interval(a, b, t_crit):
    """Two-sample 95% interval for mean(B) - mean(A): treats A and B as independent piles."""
    diff = mean(b) - mean(a)
    se = (variance(a) / len(a) + variance(b) / len(b)) ** 0.5
    half = t_crit * se
    return diff, se, (round(diff - half, 3), round(diff + half, 3))
```

And the paired test. It forms the differences first, then builds its standard error from that one tight pile.

```python filename=modules/evals-and-statistics/code/evals-inter-09/paired.py:60-65 COMPLETE
def paired_interval(a, b, t_crit):
    """Paired 95% interval for the mean of the per-case differences B - A: case difficulty cancels."""
    diffs = [bi - ai for ai, bi in zip(a, b)]
    d = mean(diffs)
    se = (variance(diffs) / len(diffs)) ** 0.5
    half = t_crit * se
    return d, se, (round(d - half, 3), round(d + half, 3))
```

Both variances come from the same helper — sample variance with the n−1 denominator — so the only difference between the two functions is what they take the variance of: the raw scores, or the differences.

```python filename=modules/evals-and-statistics/code/evals-inter-09/paired.py:44-47 COMPLETE
def variance(xs):
    """Sample variance (n-1 denominator)."""
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
```

Run both and read the intervals.

```text filename=modules/evals-and-statistics/code/evals-inter-09/paired.py --tests
TESTS — 95% interval for the mean B-A difference, two ways
--------------------------------------------------------------
  unpaired (two-sample): diff +2.92  SE 7.20  95% CI (-12.01, 17.844)
  paired   (per case):   diff +2.92  SE 0.23  95% CI (2.413, 3.42)
--------------------------------------------------------------
  the unpaired interval straddles 0; the paired one sits entirely above it.
```

Both estimate the same gap: +2.92. That is the point to hold onto — pairing did not change the answer, it changed the precision. The unpaired standard error is 7.20 and its interval runs from −12 to +18, a span so wide it includes zero, twice the true effect below zero, and six times the true effect above it. The paired standard error is 0.23 — over thirty times smaller — and its interval is (2.4, 3.4), which excludes zero and pins the gap to within a point. The unpaired test would have you ship nothing; the paired test tells you B is reliably about three points better.

<svg role="img" aria-label="The two 95% intervals on a common axis: the unpaired interval wide and crossing zero, the paired interval narrow and entirely above zero" viewBox="0 0 460 160" width="460" height="160">
  <rect x="0" y="0" width="460" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <line x1="40" y1="110" x2="440" y2="110" stroke="var(--line)"/>
  <line x1="160" y1="30" x2="160" y2="120" stroke="var(--ink)"/>
  <text x="152" y="138" font-family="var(--mono)" font-size="11" fill="var(--muted)">0</text>
  <text x="40" y="30" font-family="var(--mono)" font-size="11" fill="var(--muted)">unpaired: (−12, 18)</text>
  <line x1="60" y1="55" x2="420" y2="55" stroke="var(--s2)" stroke-width="3"/>
  <line x1="60" y1="48" x2="60" y2="62" stroke="var(--s2)"/><line x1="420" y1="48" x2="420" y2="62" stroke="var(--s2)"/>
  <circle cx="230" cy="55" r="4" fill="var(--s2)"/>
  <text x="250" y="88" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">paired: (2.4, 3.4)</text>
  <line x1="223" y1="90" x2="243" y2="90" stroke="var(--acc-ink)" stroke-width="3"/>
  <line x1="223" y1="84" x2="223" y2="96" stroke="var(--acc-ink)"/><line x1="243" y1="84" x2="243" y2="96" stroke="var(--acc-ink)"/>
  <circle cx="230" cy="90" r="4" fill="var(--acc-ink)"/>
</svg>
^ Same center, wildly different width: the unpaired bar straddles zero and decides nothing, while the paired bar clears zero and settles the question.

## Build

Reproduce both intervals. Pure standard library — the t-criticals are constants in the fixture, so your numbers must match exactly.

Run `--scores` for the table, `--tests` for the two intervals, `--check` for the gate. The self-test checks the pairing did its job without changing the estimate, and it checks the two failure-relevant facts: that the unpaired interval is inconclusive and the paired one is decisive.

```python filename=modules/evals-and-statistics/code/evals-inter-09/paired.py:115-122 COMPLETE
    same_point_estimate = abs(du - dp) < 1e-9
    print("  both tests estimate the same mean difference = %s (%.3f)" % (same_point_estimate, du))

    unpaired_inconclusive = includes_zero(iu)
    print("  the unpaired interval includes 0 (calls it a wash) = %s (%s)" % (unpaired_inconclusive, iu))

    paired_significant = not includes_zero(ip) and ip[0] > 0
    print("  the paired interval excludes 0 above (B wins) = %s (%s)" % (paired_significant, ip))
```

The first flag is the honesty check on the whole story: `abs(du - dp) < 1e-9` demands the two tests agree on the point estimate to nine decimals. That is what lets us say pairing changed only the precision. If pairing shifted the estimate, something other than variance reduction would be going on, and the clean "same answer, sharper" narrative would be a lie. Here is the full gate.

```text filename=modules/evals-and-statistics/code/evals-inter-09/paired.py --check
SELF-TEST — the unpaired interval includes 0 (inconclusive); the paired one excludes it (B wins)
------------------------------------------------------------------------------
  both tests estimate the same mean difference = True (2.917)
  the unpaired interval includes 0 (calls it a wash) = True ((-12.01, 17.844))
  the paired interval excludes 0 above (B wins) = True ((2.413, 3.42))
  pairing shrinks the standard error = True (paired SE 0.23 vs unpaired 7.20)
------------------------------------------------------------------------------
SELF-TEST PASS  same_point_estimate=True  unpaired_inconclusive=True  paired_significant=True  variance_cancels=True
```

Four True flags. Same_point_estimate says the gap is +2.917 either way. Unpaired_inconclusive says the two-sample interval calls it a wash. Paired_significant says the paired interval clears zero on the positive side. Variance_cancels says the paired standard error is under a fifth of the unpaired one — the mechanism, stated as a measured fact, not a hope.

**The self-test insists the two tests share a point estimate; that is what proves the paired interval earned its narrowness by canceling variance, not by moving the answer.**

## Definition of done

You are done when you reproduce both intervals and can explain why they differ without reciting a formula.

Concretely: `--tests` prints +2.92 for both tests with standard errors 7.20 and 0.23; `--check` prints PASS with four True flags. You can say what the paired test subtracts out — case difficulty, the between-case variance that is identical for both systems — and why that subtraction is legitimate rather than a p-hacking trick: the systems really did face the same cases, so the pairing is in the design, not invented in the analysis. You can state the inverse rule: if A and B were run on different cases, you may not pair, and pretending to would be the actual cheat.

The habit to carry out: whenever your eval runs both systems on a shared set — which is almost always — analyze the per-case differences. The mechanical tell that you are leaving power on the table is a two-sample or unpaired test on a design where every case was seen by both systems.

## Boss fight

The costly version of this mistake is not a wrong answer — it is a shipped decision to do nothing.

A team A/B-tests a new model against the incumbent on a shared eval suite. They compute two averages, run an unpaired t-test, get p = 0.4, and conclude "no significant improvement — not worth the migration." They shelve a model that beats the incumbent on every single case, because their analysis mixed sixty points of case difficulty into the uncertainty of a three-point gap. The improvement was real, reproducible, and unanimous, and the statistics said "wash" — not because the model was weak, but because the test asked the wrong question of the right data. This is a false negative that looks exactly like due diligence.

Your turn, two moves. First, make the win harder to see and watch pairing hold up. Add noise to the differences: change the B scores so the per-case gap varies more — say +1 on some cases and +6 on others, keeping the mean near +3. Predict before running: the paired standard error will grow, the paired interval will widen, and at some point it will touch zero. Find roughly how much difference-variance it takes to make even the paired test inconclusive — that is the honest limit of your twelve cases. Second, break the pairing legitimately: imagine A and B were run on different case sets with the same difficulty spread. Now you cannot subtract, the unpaired test is the only valid one, and its verdict — "wash" — is correct, because you genuinely have less information. Sit with that: the paired test is not a stronger test you can always reach for, it is the reward for a paired design.

## External resources

Any introductory statistics text covers the paired vs two-sample t-test, but the framing that matters for evals is "blocking": the case is a block, and blocking on it removes nuisance variance. The Wikipedia article "Paired difference test" states exactly when pairing is valid and why it reduces variance.

For the eval-specific version — comparing language models on a shared benchmark — see the literature on "variance reduction in LLM evaluation," where paired bootstrapping and common test items are the standard tools for tightening the interval without running more cases.

Gelman and Hill's "Data Analysis Using Regression and Multilevel Models" frames the same idea as a within-subject design and shows how the paired comparison is a special case of adding a per-case fixed effect — the bridge from this toy to real experimental analysis.
