---
id: data-inter-10
title: Average growth factors with the geometric mean — the arithmetic mean compounds to the wrong total
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 22 min
summary: Growth multiplies, so a series of factors ends at their product, not their sum. The arithmetic mean of factors compounded overshoots — here 1.2 per period predicts 207 over four periods when the truth is 120. The geometric mean, the n-th root of the product, is the constant factor that reproduces the real end value exactly.
eli5: If your money doubles one year and halves the next, you're right back where you started — no gain. But if you "average" doubling and halving you might think you came out ahead. To average things that multiply, you use a different kind of average that gives the honest answer: back to where you started.
---

## Why this module

The phrase "average growth rate" is a trap, because the ordinary average answers a question that compounding never asks.

Growth is multiplicative. A quantity that grows by a factor each period — an investment return, a user-base month over month, a model's loss ratio between training runs, a population — does not accumulate its factors by adding them, it accumulates by multiplying them. After periods of ×2, ×0.5, ×1.5, ×0.8, you are not up by the sum of those; you are at their product. And the product of factors that swing above and below one behaves nothing like their sum. Double then halve and you are exactly where you started — a product of 1.0, a net change of zero — even though the two factors "average," arithmetically, to 1.25.

So when you summarize a series of growth factors with the arithmetic mean and then reason about the total, you overstate it, and the overstatement compounds. The arithmetic mean is the factor with the same *sum* as your data; compounding cares about the *product*. Those are different numbers whenever the factors vary, and the arithmetic one is always the larger — guaranteed, by a theorem, not by luck. Report "average return 25% a year" from an arithmetic mean and you imply a compounded growth the portfolio never achieved.

The correct average for multiplicative data is the geometric mean: the n-th root of the product. It is, by construction, the single constant factor that reproduces the actual end value when applied every period — because it is defined by the product the way the arithmetic mean is defined by the sum. We will grow 100 through factors that land it at 120, then watch the arithmetic mean predict 207 and the geometric mean land exactly on 120.

**Growth accumulates by multiplying, so its honest average is the geometric mean; the arithmetic mean of factors answers a sum question and overstates every compounded total whose factors vary.**

## Concepts

Anchor on what each mean is the answer to. The arithmetic mean of a set is the value that, summed n times, gives the same total sum — it is built from addition. The geometric mean is the value that, multiplied n times, gives the same product — it is built from multiplication. If your quantity accumulates by adding (total revenue across regions, total requests), the arithmetic mean is right. If it accumulates by multiplying (compounded growth, chained ratios), the geometric mean is right. The error is using the addition average on a multiplication process.

Why the arithmetic mean always overstates is the AM-GM inequality: for any set of non-negative numbers, the arithmetic mean is greater than or equal to the geometric mean, with equality only when every number is identical. So the moment your factors vary at all — any real growth series — the arithmetic mean is strictly larger, and compounding that larger factor over the periods magnifies the gap exponentially. The more the factors swing, the wider the spread between the two means and the more the arithmetic one lies.

<svg role="img" aria-label="A number line of the four factors with the arithmetic mean at 1.20 and the geometric mean at 1.05, the arithmetic mean pulled higher by the large factor 2.0" viewBox="0 0 460 140" width="460" height="140">
  <rect x="0" y="0" width="460" height="140" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">the four factors, and the two means of them</text>
  <line x1="40" y1="80" x2="440" y2="80" stroke="var(--line)"/>
  <line x1="40" y1="74" x2="40" y2="86" stroke="var(--grid)"/><text x="34" y="102" font-family="var(--mono)" font-size="9" fill="var(--muted)">0.5</text>
  <line x1="440" y1="74" x2="440" y2="86" stroke="var(--grid)"/><text x="434" y="102" font-family="var(--mono)" font-size="9" fill="var(--muted)">2.0</text>
  <circle cx="40" cy="80" r="4" fill="var(--s1)" stroke="var(--ink)"/><text x="32" y="66" font-family="var(--mono)" font-size="8" fill="var(--muted)">0.5</text>
  <circle cx="176" cy="80" r="4" fill="var(--s1)" stroke="var(--ink)"/><text x="168" y="66" font-family="var(--mono)" font-size="8" fill="var(--muted)">0.8</text>
  <circle cx="312" cy="80" r="4" fill="var(--s1)" stroke="var(--ink)"/><text x="304" y="66" font-family="var(--mono)" font-size="8" fill="var(--muted)">1.5</text>
  <circle cx="440" cy="80" r="4" fill="var(--s1)" stroke="var(--ink)"/><text x="432" y="66" font-family="var(--mono)" font-size="8" fill="var(--muted)">2.0</text>
  <line x1="230" y1="60" x2="230" y2="100" stroke="var(--s2)" stroke-dasharray="3 2"/><text x="204" y="120" font-family="var(--mono)" font-size="9" fill="var(--s2)">AM 1.20</text>
  <line x1="167" y1="60" x2="167" y2="100" stroke="var(--acc-ink)"/><text x="140" y="120" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">GM 1.05</text>
</svg>
^ The geometric mean sits below the arithmetic mean, dragged down toward the small factors; the gap between them is the volatility drag, and it only closes when every factor is equal.

The intuition for the overstatement is that multiplication is unforgiving of volatility in a way addition is not. A ×2 followed by a ×0.5 is a wash — you end where you began — but their arithmetic mean, 1.25, is well above 1.0, because averaging treats the gain and the loss as symmetric when compounding does not. A 50% loss needs a 100% gain to undo it, not another 50%. That asymmetry is exactly what the geometric mean captures and the arithmetic mean ignores. Volatility drags compound growth below the arithmetic average of the returns, and the drag grows with the volatility — the same reason a bumpy road to a destination is longer than a straight one.

This is not academic. It is why fund returns are quoted as compound annual growth rate, which is a geometric mean, and why quoting the arithmetic mean of annual returns is a known way to make a volatile fund look better than it was. It is why "average month-over-month growth" from an arithmetic mean overstates where you actually are. Any time you average ratios or factors and then compound, the arithmetic mean is the wrong tool.

**The arithmetic mean is the sum's average and the geometric mean is the product's average; AM ≥ GM always, so on multiplicative data the arithmetic mean overstates, and the drag is the cost of volatility.**

## Worked example

The fixture is a starting value and the per-period growth factors.

```json filename=modules/ai-for-science-and-data/code/data-inter-10/growth.json:7-13 COMPLETE
  "start": 100.0,
  "factors": [
    2.0,
    0.5,
    1.5,
    0.8
  ]
```

Start at 100. Multiply by 2.0, then 0.5, then 1.5, then 0.8. Watch it compound.

```text filename=modules/ai-for-science-and-data/code/data-inter-10/geometric.py --growth
GROWTH — the value compounding period by period
--------------------------------------------
  start              100.00
  period 1  x2.00    200.00
  period 2  x0.50    100.00
  period 3  x1.50    150.00
  period 4  x0.80    120.00
--------------------------------------------
  end value 120.00 = 100.00 x product([2.0, 0.5, 1.5, 0.8]) = 100.00 x 1.20
```

The true end value is 120 — a 1.2× total over four periods, a modest 20% gain end to end. Notice the product of the factors is 1.2. The geometric mean is the constant factor that reproduces that product.

```python filename=modules/ai-for-science-and-data/code/data-inter-10/geometric.py:52-54 COMPLETE
def geometric_mean(xs):
    """The n-th root of the product -- the constant factor that reproduces the compounded result."""
    return product(xs) ** (1 / len(xs))
```

The true end just applies the real factors in order — the yardstick both means are checked against.

```python filename=modules/ai-for-science-and-data/code/data-inter-10/geometric.py:62-66 COMPLETE
def true_end(start, factors):
    """The actual end value: apply the real factors in sequence."""
    value = start
    for f in factors:
        value *= f
    return value
```

And compounding applies a single constant factor n times — this is what turns a mean into a prediction.

```python filename=modules/ai-for-science-and-data/code/data-inter-10/geometric.py:57-59 COMPLETE
def compound(start, factor, n):
    """Apply a single constant factor n times to a starting value."""
    return start * factor ** n
```

Now the trap. The arithmetic mean of [2.0, 0.5, 1.5, 0.8] is (2.0 + 0.5 + 1.5 + 0.8) / 4 = 1.2 — the same 1.2 as the product, which is the coincidence that makes this fixture so pointed. But 1.2 as an *arithmetic mean* reads as "+20% per period," and compounded four times that is 1.2⁴. Predict it: 1.2⁴ ≈ 2.07, so 207. Now run both means.

```text filename=modules/ai-for-science-and-data/code/data-inter-10/geometric.py --means
MEANS — arithmetic vs geometric factor, and what each predicts over 4 periods
------------------------------------------------------------------
  true end value:                         120.00
  arithmetic mean factor 1.2000 -> predicts   207.36  (off by +87.36)
  geometric  mean factor 1.0466 -> predicts   120.00  (off by +0.00)
------------------------------------------------------------------
  the arithmetic mean compounds to nearly double the truth; the geometric mean lands on it.
```

The arithmetic mean factor 1.2000, compounded four times, predicts 207.36 — off by +87.36, nearly double the real 120. The geometric mean factor 1.0466 (+4.66% per period) compounds to 120.00, off by zero. The two "average factors" are 1.2 versus 1.0466, and the difference between +20% and +4.66% per period, compounded, is the difference between a fantasy 207 and the actual 120. The arithmetic mean did not just round wrong; it answered a different question — the sum's — and the sum has nothing to do with where the value ended up.

<svg role="img" aria-label="The value compounding: 100 to 200 to 100 to 150 to 120 across four periods" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">value by period (start 100, end 120)</text>
  <line x1="50" y1="140" x2="440" y2="140" stroke="var(--line)"/>
  <line x1="50" y1="40" x2="50" y2="140" stroke="var(--line)"/>
  <line x1="50" y1="55" x2="440" y2="55" stroke="var(--grid)" stroke-dasharray="3 3"/><text x="20" y="59" font-family="var(--mono)" font-size="9" fill="var(--muted)">200</text>
  <text x="20" y="99" font-family="var(--mono)" font-size="9" fill="var(--muted)">100</text>
  <polyline points="70,99 160,55 250,99 340,77 420,90" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <circle cx="70" cy="99" r="3" fill="var(--s1)"/><circle cx="160" cy="55" r="3" fill="var(--s1)"/><circle cx="250" cy="99" r="3" fill="var(--s1)"/><circle cx="340" cy="77" r="3" fill="var(--s1)"/><circle cx="420" cy="90" r="3" fill="var(--acc-line)"/>
  <text x="60" y="115" font-family="var(--mono)" font-size="8" fill="var(--muted)">100</text><text x="150" y="49" font-family="var(--mono)" font-size="8" fill="var(--muted)">200</text><text x="240" y="115" font-family="var(--mono)" font-size="8" fill="var(--muted)">100</text><text x="330" y="71" font-family="var(--mono)" font-size="8" fill="var(--muted)">150</text><text x="410" y="106" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">120</text>
</svg>
^ The value swings 100 → 200 → 100 → 150 → 120; the ×2 and ×0.5 nearly cancel, which is exactly the volatility the arithmetic mean ignores.

<svg role="img" aria-label="Three end-value bars: true 120, geometric-mean prediction 120, arithmetic-mean prediction 207" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">predicted end value vs truth</text>
  <line x1="60" y1="140" x2="440" y2="140" stroke="var(--line)"/>
  <line x1="60" y1="83" x2="440" y2="83" stroke="var(--acc-ink)" stroke-dasharray="4 3"/><text x="360" y="79" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">truth 120</text>
  <rect x="90" y="83" width="70" height="57" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="104" y="77" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">120</text><text x="98" y="155" font-family="var(--mono)" font-size="9" fill="var(--muted)">true</text>
  <rect x="200" y="83" width="70" height="57" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="210" y="77" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">120</text><text x="205" y="155" font-family="var(--mono)" font-size="9" fill="var(--muted)">geometric</text>
  <rect x="310" y="41" width="70" height="99" fill="var(--s2)" stroke="var(--line)"/><text x="318" y="35" font-family="var(--mono)" font-size="10" fill="var(--ink)">207</text><text x="315" y="155" font-family="var(--mono)" font-size="9" fill="var(--muted)">arithmetic</text>
</svg>
^ The geometric mean's prediction sits exactly on the truth line; the arithmetic mean's towers 87 above it.

## Build

Reproduce the predictions. Pure standard library, so 120.00, 207.36, and the two mean factors come out exactly.

Run `--growth` for the compounding path, `--means` for the two predictions, `--check` for the gate. The self-test pins the whole claim: the geometric mean reproduces the truth, the arithmetic mean overstates it and fails to reproduce it, and AM ≥ GM.

```python filename=modules/ai-for-science-and-data/code/data-inter-10/geometric.py:110-115 COMPLETE
    geo_reproduces = abs(compound(start, gm, n) - end) < 1e-6
    print("  the geometric mean compounds to the true end value = %s (%.4f vs %.4f)"
          % (geo_reproduces, compound(start, gm, n), end))

    arith_overstates = compound(start, am, n) > end
    print("  the arithmetic mean overstates the compounded result = %s (%.2f vs %.2f)"
          % (arith_overstates, compound(start, am, n), end))
```

The `geo_reproduces` predicate is a near-exact equality — `abs(...) < 1e-6` — not a loose "close." That is the strong form of the claim: the geometric mean does not approximately track the compounded result, it *is* the factor that reproduces it, to floating-point precision, by definition. If that line ever failed, the definition of geometric mean would be wrong, not the fixture. Here is the full gate.

```text filename=modules/ai-for-science-and-data/code/data-inter-10/geometric.py --check
SELF-TEST — only the geometric mean reproduces the true end value; the arithmetic mean overstates it
--------------------------------------------------------------------------------------------
  the geometric mean compounds to the true end value = True (120.0000 vs 120.0000)
  the arithmetic mean overstates the compounded result = True (207.36 vs 120.00)
  the arithmetic mean is >= the geometric mean (AM-GM) = True (1.2000 >= 1.0466)
  the arithmetic mean does NOT reproduce the end value = True (off by 87.36)
--------------------------------------------------------------------------------------------
SELF-TEST PASS  geo_reproduces=True  arith_overstates=True  am_ge_gm=True  arith_not_reproduce=True
```

Four True flags. Geo_reproduces: the geometric mean hits the truth exactly. Arith_overstates: the arithmetic mean predicts more than the truth. Am_ge_gm: the arithmetic mean is the larger of the two, as the theorem guarantees. Arith_not_reproduce: the arithmetic mean is off by 87, not a rounding error but a wrong answer. Together they say the two means are not two estimates of one quantity — one is correct and the other answers a different question.

**The geometric-mean check demands near-exact equality because the claim is definitional, not approximate: the geometric mean is the factor that reproduces the product.**

## Definition of done

You are done when you reproduce 120 and 207 and can say which average answers which question.

Concretely: `--means` shows the arithmetic mean predicting 207.36 and the geometric mean predicting 120.00; `--check` prints PASS with four True flags. You can state what each mean reproduces — the arithmetic mean the sum, the geometric mean the product — and match each to the kind of accumulation it fits. You can state the AM-GM inequality and its equality condition (all values equal), and explain why that makes the arithmetic mean always overstate compound growth on varying factors. And you can explain the volatility drag: why a ×2 then ×0.5 nets zero while their arithmetic mean is positive.

The habit to carry: whenever you are about to average rates, ratios, returns, or growth factors and then compound or chain them, reach for the geometric mean. Treat a "compound growth rate" computed as an arithmetic mean as a red flag, and check whether the number reproduces the actual start-to-end change.

## Boss fight

The instructive failure is a report that makes a losing strategy look like a winner.

A fund returns +80% one year and −40% the next. Someone computes the "average annual return" as (80 − 40) / 2 = +20% and reports the fund grew 20% a year. But 1.80 × 0.60 = 1.08 over two years — a compound annual growth of about 3.9%, not 20%. An investor who put in \$100,000 expecting 20% a year would find \$108,000 after two years, not the \$144,000 the arithmetic average implied. The arithmetic mean of returns is a standard way — sometimes innocent, sometimes not — to make a volatile track record look far better than the money actually did. The geometric mean is the only average that reproduces the ending balance.

Your turn, two moves. First, dial up the volatility and watch the gap widen. Change the factors to [3.0, 0.33, 3.0, 0.33] — big swings that nearly cancel, product ≈ 0.98, so the value barely moves. Predict: the arithmetic mean jumps to about 1.66 and its four-period prediction explodes past 700, while the geometric mean stays near 1.0 and reproduces the near-flat truth. The wilder the swings, the more the arithmetic mean lies. Second, find the equality case. Set every factor to the same value, say [1.1, 1.1, 1.1, 1.1], and predict: the arithmetic and geometric means are now identical, both 1.1, and both reproduce the truth — because AM-GM is an equality exactly when the values are all equal, so with no volatility there is no drag and no overstatement. That boundary is the whole story in miniature: the arithmetic mean is wrong for compounding in proportion to how much the factors vary, and right only when they do not vary at all.

## External resources

Any finance text's treatment of "arithmetic versus geometric returns" makes this concrete; the CFA curriculum and most investment primers state flatly that compound performance must be reported as a geometric mean (the compound annual growth rate).

For the theorem, the AM-GM inequality is standard in any inequalities reference; the two-variable case, √(ab) ≤ (a+b)/2, is a one-line proof from (√a − √b)² ≥ 0 and is enough to see why equality needs a = b.

For the deeper connection — that the geometric mean is the arithmetic mean of the logarithms, exponentiated — see any statistics treatment of log-transformed data; it is why multiplicative processes are analyzed in log space, where multiplying becomes adding and the right average becomes the ordinary one again.
