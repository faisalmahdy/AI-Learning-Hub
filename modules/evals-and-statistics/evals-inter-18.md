---
id: evals-inter-18
title: Put a Wilson interval on a pass rate — the normal approximation claims certainty from ten trials
topic: evals-and-statistics
level: intermediate
status: ready
time: 19 min
summary: You run an eval, a model passes 10 of 10, and you want a confidence interval on its true pass rate. The textbook normal (Wald) interval is p ± z√(p(1−p)/n). Plug in p = 1.0 and it returns [1.0, 1.0] — zero width, claiming certainty that the true rate is exactly 100% from ten trials. The collapse is structural: the width is driven by p(1−p), which is zero at the extremes, so the formula reports no uncertainty exactly when the sample is least informative — and for the same reason it runs outside [0, 1] at small n, giving a probability interval that includes negative probabilities. The Wilson score interval fixes both, staying inside [0, 1] with honest width even at a perfect score. On this fixture 10/10 gives Wald [1.00, 1.00] but Wilson [0.72, 1.00], and 1/3 gives Wald [−0.20, 0.87] but Wilson [0.06, 0.79].
eli5: If you flip a coin ten times and it lands heads all ten, it would be silly to announce "this coin is exactly 100% heads, no doubt." Ten flips just can't prove that. One common formula does exactly that silly thing at the extremes — it reports zero doubt. A better formula keeps some honest doubt, saying "probably high, maybe around 72% to 100%," which is what ten flips actually tell you.
---

## Why this module

The default confidence interval taught for a proportion fails hardest exactly where model evals operate — small samples and pass rates near 0 or 100%.

You have k passes out of n trials and want an interval for the true pass rate. The formula in every intro course is the normal approximation: take the observed rate p, go z standard errors each way, where the standard error is √(p(1−p)/n). It is fine for a coin near 50% flipped thousands of times. Feed it an eval — ten trials, a perfect score — and it breaks. At p = 1.0 the standard error is √0 = 0, so the interval is [1.0, 1.0]: it claims you are certain the true rate is exactly 100%, from ten trials. Ten passes is perfectly consistent with a true rate of 85%; the interval that says otherwise is not conservative, it is wrong.

**The Wald interval's width is proportional to p(1−p), so it reports zero uncertainty at a perfect or zero score — the least informative case, dressed as the most certain.**

The Wilson score interval is the fix. It stays strictly inside [0, 1] and keeps a sensible non-zero width at the extremes, because it inverts the test around the hypothesized rate rather than the observed one. This module computes both on three eval-shaped cases and shows Wald collapse and escape [0, 1] while Wilson stays honest.

## Concepts

The **point estimate** is the observed rate p = k/n. A **confidence interval** is a range that should cover the true rate at the stated confidence (here 95%, z = 1.96).

The **Wald interval** is p ± z√(p(1−p)/n). Its two failures both come from the p(1−p) factor. At p = 0 or p = 1 that factor is zero, so the interval has zero width — false certainty. And because the interval is symmetric around p with no floor or ceiling, at small n it extends past 0 or 1 — a "probability" interval that includes impossible values.

The **Wilson interval** re-centers. Instead of asking "which rates are within z standard errors of the observed p," it asks "which hypothesized rates make the observed p within z standard errors of themselves," and solves for them. Algebraically that pulls the center toward 0.5 by an amount that shrinks as n grows, and the result is always inside [0, 1] with non-zero width even at a perfect score.

The two agree when n is large and p is mid-range — the regime the Wald formula was derived for. They diverge at small n and extreme p, which is precisely the regime of a model eval: dozens of trials, not thousands, and rates that are often near ceiling.

**Wilson answers "what true rates are consistent with this result," which is the question a confidence interval is supposed to answer; Wald approximates it in a way that degrades exactly where evals live.**

The two intervals part ways as the sample shrinks and the rate nears the edge — mid-range and large-n they nearly coincide, at the corners they disagree completely.

<svg role="img" aria-label="A grid of sample size versus pass rate: Wald and Wilson agree in the large-n mid-rate region and diverge at small-n extreme-rate corners" viewBox="0 0 300 120" width="300" height="120">
  <line x1="40" y1="15" x2="40" y2="100" stroke="var(--grid)" stroke-width="1"/>
  <line x1="40" y1="100" x2="280" y2="100" stroke="var(--grid)" stroke-width="1"/>
  <text x="5" y="22" fill="var(--muted)" font-size="7">large n</text>
  <text x="5" y="98" fill="var(--muted)" font-size="7">small n</text>
  <text x="150" y="115" fill="var(--muted)" font-size="7">pass rate → 0 or 1</text>
  <rect x="40" y="15" width="90" height="45" fill="var(--s2)" opacity="0.5"/>
  <text x="52" y="40" fill="var(--ink)" font-size="7">agree</text>
  <rect x="190" y="60" width="90" height="40" fill="var(--s1)" opacity="0.6"/>
  <text x="200" y="84" fill="var(--panel)" font-size="7">diverge (evals)</text>
</svg>
^ Wald was derived for the upper-left region — many trials, mid-range rate — and is fine there; evals sit in the lower-right corner, small n and extreme rates, where Wald and Wilson disagree.

The trap is that the Wald interval is the one everyone learned, so a 10/10 reported as "100%, interval [100%, 100%]" looks authoritative when it is meaningless.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/evals-inter-18/wilson.py

The fixture is three cases chosen to stress the formulas: a perfect score, a tiny sample, and a middling one.

```json filename=modules/evals-and-statistics/code/evals-inter-18/trials.json:1-11 COMPLETE
{
  "_meta": "Pass counts from an eval: each case is n trials with k passes, so the observed pass rate is k/n. z is the normal quantile for the confidence level (1.96 for 95%). We compare two ways to put a confidence interval on the true pass rate: the Wald (normal-approximation) interval p +/- z*sqrt(p(1-p)/n), and the Wilson score interval. The cases are chosen to stress both: a perfect score, a tiny sample, and a middling one.",
  "z": 1.96,
  "cases": [
    {"n": 10, "k": 10},
    {"n": 3,  "k": 1},
    {"n": 10, "k": 7}
  ]
}
```

The two intervals are two formulas. Wald is symmetric around p; Wilson divides through by a factor that keeps it bounded.

```python filename=modules/evals-and-statistics/code/evals-inter-18/wilson.py:41-54 COMPLETE
def wald(k, n, z):
    """Normal-approximation interval: p +/- z*sqrt(p(1-p)/n). Can hit zero width or leave [0,1]."""
    p = k / n
    half = z * math.sqrt(p * (1 - p) / n)
    return (p - half, p + half)


def wilson(k, n, z):
    """Wilson score interval: inverts the test around the hypothesized rate; stays inside [0,1]."""
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (center - half, center + half)
```

Run `--intervals`.

```text filename=--intervals
INTERVALS — Wald vs Wilson 95% intervals (z=1.96)
------------------------------------------------------------------
  k/n       point    Wald                 Wilson
  10/10     1.00    [+1.00, +1.00]     [0.72, 1.00]
   1/3      0.33    [-0.20, +0.87]     [0.06, 0.79]
   7/10     0.70    [+0.42, +0.98]     [0.40, 0.89]
------------------------------------------------------------------
  Wald collapses at 10/10 and goes negative at 1/3; Wilson stays in [0,1].
```

At 10/10 Wald reports [1.00, 1.00] — a point, not an interval — while Wilson reports [0.72, 1.00], honest uncertainty. At 1/3 Wald reaches −0.20, a negative probability, while Wilson stays at [0.06, 0.79]. Only at the middling 7/10 do the two roughly agree, and even there Wald's upper bound (0.98) crowds the ceiling more than Wilson's (0.89).

<svg role="img" aria-label="Interval comparison: at 10/10 Wald is a point at 1.0 while Wilson spans 0.72 to 1.0; at 1/3 Wald crosses below zero while Wilson stays positive" viewBox="0 0 300 140" width="300" height="140">
  <line x1="90" y1="15" x2="90" y2="120" stroke="var(--grid)" stroke-width="1"/>
  <text x="80" y="132" fill="var(--muted)" font-size="8">0</text>
  <line x1="270" y1="15" x2="270" y2="120" stroke="var(--grid)" stroke-width="1"/>
  <text x="262" y="132" fill="var(--muted)" font-size="8">1</text>
  <line x1="72" y1="15" x2="72" y2="120" stroke="var(--s1)" stroke-width="1" stroke-dasharray="2 2"/>
  <text x="55" y="132" fill="var(--s1)" font-size="8">-0.2</text>
  <text x="10" y="34" fill="var(--muted)" font-size="8">10/10</text>
  <circle cx="270" cy="30" r="4" fill="var(--s1)"/>
  <text x="200" y="26" fill="var(--s1)" font-size="7">Wald: a point</text>
  <line x1="220" y1="44" x2="270" y2="44" stroke="var(--s2)" stroke-width="3"/>
  <text x="150" y="42" fill="var(--s2)" font-size="7">Wilson 0.72-1.0</text>
  <text x="10" y="80" fill="var(--muted)" font-size="8">1/3</text>
  <line x1="72" y1="78" x2="246" y2="78" stroke="var(--s1)" stroke-width="3"/>
  <text x="120" y="74" fill="var(--s1)" font-size="7">Wald dips below 0</text>
  <line x1="101" y1="92" x2="232" y2="92" stroke="var(--s2)" stroke-width="3"/>
  <text x="120" y="104" fill="var(--s2)" font-size="7">Wilson 0.06-0.79</text>
</svg>
^ At 10/10 the Wald interval is a single point at 1.0 while Wilson spans a real range; at 1/3 the Wald bar crosses left of zero into negative probability while Wilson stays inside the axis.

## Build

The flaws view flags each Wald interval that collapsed to zero width or ran outside [0, 1].

```python filename=modules/evals-and-statistics/code/evals-inter-18/wilson.py:84-89 COMPLETE
        notes = []
        if width((wl, wu)) < 1e-9:
            notes.append("ZERO WIDTH (false certainty)")
        if wl < 0 or wu > 1:
            notes.append("OUTSIDE [0,1]")
        print("  %2d/%-2d  Wald [%+.2f, %+.2f]  width %.2f  %s" % (k, n, wl, wu, width((wl, wu)), "  ".join(notes) if notes else "ok"))
```

The `--flaws` view names exactly what went wrong in each Wald interval.

```text filename=--flaws
FLAWS — where the Wald interval breaks
------------------------------------------------------------------
  10/10  Wald [+1.00, +1.00]  width 0.00  ZERO WIDTH (false certainty)
   1/3   Wald [-0.20, +0.87]  width 1.07  OUTSIDE [0,1]
   7/10  Wald [+0.42, +0.98]  width 0.57  ok
------------------------------------------------------------------
  the breaks happen at the extremes and small n -- exactly where evals sit.
```

Two of the three Wald intervals are broken, and they are broken in the two ways the p(1−p) term predicts: zero width at the perfect score, and a span reaching below zero at the tiny sample. Only the mid-range case survives. An eval suite is full of ceiling scores and small samples, so "usually fine" is not the operating regime — the broken cases are the common ones.

<svg role="img" aria-label="Wald interval width versus point estimate: width collapses to zero at p=0 and p=1, peaks at p=0.5" viewBox="0 0 300 120" width="300" height="120">
  <line x1="30" y1="15" x2="30" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <text x="20" y="108" fill="var(--muted)" font-size="8">p=0</text>
  <text x="150" y="108" fill="var(--muted)" font-size="8">0.5</text>
  <text x="270" y="108" fill="var(--muted)" font-size="8">p=1</text>
  <path d="M30,95 Q157,20 285,95" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <circle cx="30" cy="95" r="3" fill="var(--s1)"/>
  <circle cx="285" cy="95" r="3" fill="var(--s1)"/>
  <text x="35" y="90" fill="var(--s1)" font-size="7">width 0</text>
  <text x="235" y="90" fill="var(--s1)" font-size="7">width 0</text>
  <text x="120" y="30" fill="var(--muted)" font-size="8">Wald width ∝ √(p(1-p))</text>
</svg>
^ The Wald interval's width is a dome that collapses to zero at both ends — so a pass rate at the ceiling, the most common eval result, is exactly where it reports no uncertainty.

## Definition of done

The self-test pins both Wald failures and Wilson's soundness: Wald has zero width at 10/10, escapes [0,1] at 1/3, while Wilson keeps real width at 10/10, stays in [0,1] everywhere, and always contains its point estimate.

```python filename=modules/evals-and-statistics/code/evals-inter-18/wilson.py:101-115 COMPLETE
    wald_zero_width_at_perfect = width(wl_perfect) < 1e-9
    print("  Wald has zero width at 10/10 = %s ([%.2f, %.2f])" % (wald_zero_width_at_perfect, wl_perfect[0], wl_perfect[1]))

    wl_small = wald(1, 3, z)
    wald_escapes_unit = wl_small[0] < 0 or wl_small[1] > 1
    print("  Wald leaves [0,1] at 1/3 = %s (lower %.2f)" % (wald_escapes_unit, wl_small[0]))

    sl_perfect = wilson(10, 10, z)
    wilson_nonzero_at_perfect = width(sl_perfect) > 0.05
    print("  Wilson keeps real width at 10/10 = %s ([%.2f, %.2f])" % (wilson_nonzero_at_perfect, sl_perfect[0], sl_perfect[1]))

    wilson_within_unit = all(0 <= wilson(c["k"], c["n"], z)[0] and wilson(c["k"], c["n"], z)[1] <= 1 for c in data["cases"])
    print("  every Wilson interval stays in [0,1] = %s" % wilson_within_unit)

    wilson_contains_point = all(wilson(c["k"], c["n"], z)[0] <= c["k"] / c["n"] <= wilson(c["k"], c["n"], z)[1] for c in data["cases"])
    print("  every Wilson interval contains its point estimate = %s" % wilson_contains_point)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — Wald gives zero width at 10/10 and escapes [0,1] at 1/3; Wilson stays honest on both
--------------------------------------------------------------------------------------------------------
  Wald has zero width at 10/10 = True ([1.00, 1.00])
  Wald leaves [0,1] at 1/3 = True (lower -0.20)
  Wilson keeps real width at 10/10 = True ([0.72, 1.00])
  every Wilson interval stays in [0,1] = True
  every Wilson interval contains its point estimate = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  wald_zero_width_at_perfect=True  wald_escapes_unit=True  wilson_nonzero_at_perfect=True  wilson_within_unit=True  wilson_contains_point=True
```

**Done means the failure is exhibited, not asserted: Wald returns the point [1.00, 1.00] at 10/10 and dips to −0.20 at 1/3, while Wilson returns [0.72, 1.00] and [0.06, 0.79] — bounded and non-degenerate on both.**

## Boss fight

Wilson's upper bound at 10/10 is 1.00. Predict whether that means Wilson also claims certainty at the top. It is tempting to see the 1.00 and think Wilson has the same problem.

It does not, and the asymmetry is the point. Wilson's interval at 10/10 is [0.72, 1.00]: the upper bound is 1.0 because a true rate of 100% genuinely is consistent with observing 10/10, but the lower bound is 0.72, so the interval has real width and admits that the true rate could be well below perfect. Wald's [1.00, 1.00] excludes 0.72 entirely — it says a true rate of 90% is impossible given 10/10, which is false. The right reading of a perfect score is "the true rate could be anywhere from about 0.72 up to 1.0," and only Wilson says that.

The mirror-image mistake is switching to Wilson and then still reporting only the point estimate. A 10/10 is not "100%"; it is "100% observed, 95% interval [0.72, 1.00]." Report the interval, not the point — especially at the ceiling, where the point is most misleading and where a small eval most often lands. For very small n, an exact (Clopper–Pearson) interval is more conservative still, but Wilson is the sensible default over Wald in every case here.

```python filename=modules/evals-and-statistics/code/evals-inter-18/wilson.py:48-54 COMPLETE
def wilson(k, n, z):
    """Wilson score interval: inverts the test around the hypothesized rate; stays inside [0,1]."""
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (center - half, center + half)
```

**Report a pass rate as a Wilson interval, not a point or a Wald interval: at the small samples and ceiling scores evals live at, Wald claims a certainty it has not earned and Wilson tells you how much you actually know.**

## External resources

Wilson, "Probable Inference, the Law of Succession, and Statistical Inference" (1927) — the original score interval, and the modern comparison in Brown, Cai, and DasGupta, "Interval Estimation for a Binomial Proportion" (2001), which recommends Wilson over Wald.

The Clopper–Pearson exact interval — the conservative alternative mentioned in the boss fight for very small n, and why it trades width for guaranteed coverage.

Any discussion of pass@k confidence intervals in LLM eval reports — the applied setting where n is small and rates hit the ceiling, exactly where the Wald/Wilson gap bites.
