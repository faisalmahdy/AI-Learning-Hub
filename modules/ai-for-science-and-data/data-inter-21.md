---
id: data-inter-21
title: Don't plug the average into a curved model — the average of the outputs is not the output of the average
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 18 min
summary: Summarizing inputs by their average and running that one number through a model is exact only when the model is a straight line. The moment it curves — and most real models do — the average of the outputs differs from the output of the average, and the gap is a one-directional bias, not noise. This is Jensen's inequality, the flaw of averages. For a convex function (curving up, like squaring or a queue's delay) the true average output is larger than the output of the average input, so plugging in the mean underestimates; for a concave function (square root, log, a saturating yield) the mean overestimates; only linear is exact. On two datasets that share a mean of 5, squaring the spread set [1,5,9] gives a true average of 35.67 versus the shortcut's 25.00 — a gap of 10.67, exactly the variance — while the tight set [4,5,6] has a gap of only 0.67. The bias grows with the spread of the input.
eli5: A person who can't swim hears a river is on average three feet deep and wades in — then drowns in the eight-foot middle, because "on average safe" is not "safe everywhere." Feeding one average number into a curved calculation makes the same mistake: the curve turns the ups and downs into a lopsided answer, so the average of the real results is not what you get by working from the average alone.
---

## Why this module

Replacing a spread of inputs with their average and pushing that single number through the model feels like a harmless simplification, but any curve in the model turns it into a systematic error that points one way and never averages out.

A model fed the average input returns the output *of the average*. What you almost always want is the *average of the outputs* — the mean result across the real, varying inputs. These are equal only when the model is a straight line. As soon as it bends, the two diverge, because a curve weights the highs and lows unequally: on a convex curve the high inputs are pushed up more than the lows are pushed down, so the true average output ends up above the shortcut, and on a concave curve the reverse. This is Jensen's inequality, and its field name is the flaw of averages — the statistician who drowned crossing a river three feet deep on average. The error is not random noise you can shrug off; it is a bias with a fixed direction set by the curvature.

**For any curved model the average of the outputs is not the output of the average, and the difference is a one-directional bias — convex curves make the shortcut underestimate, concave curves make it overestimate.**

The size of the bias is set by how spread out the inputs are: the wider they vary, the more the curve's unequal weighting bites. For squaring, the gap between the average of the squares and the square of the average is *exactly the variance* — a clean, computable amount. This module runs a convex, a concave, and a linear function over two datasets that share a mean but not a spread, and shows the shortcut's error appear, flip sign with the curvature, and grow with the variance.

## Concepts

The **output of the average** is the shortcut: collapse the inputs to their mean, then apply the model once. Cheap, and exact only for a linear model.

The **average of the outputs** is the honest quantity: apply the model to every input, then average the results. This is what "the expected result" means when inputs vary.

A **convex** function curves upward (squaring, exponentials, a queue's delay as utilization rises). Jensen's inequality says its average output is greater than or equal to its output of the average, so the shortcut **underestimates**.

A **concave** function curves downward (square root, logarithm, a saturating yield or dose response). The inequality flips: the shortcut **overestimates**.

**The bias grows with the input's spread.** Same mean but wider inputs means a bigger gap; for squaring the gap is precisely the variance, so zero spread gives zero error and the error climbs from there.

```python filename=modules/ai-for-science-and-data/code/data-inter-21/flawofaverages.py:48-50 COMPLETE
def variance(xs):
    m = mean(xs)
    return sum((v - m) ** 2 for v in xs) / len(xs)
```

**Whether the shortcut is safe depends entirely on the model's curvature and the input's spread: a straight model or a single value is exact, but a curved model over varying inputs is biased in the direction the curve bends.**

<svg role="img" aria-label="On a convex curve, the average of two output points sits above the curve at the average input; on a concave curve it sits below" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="12" fill="var(--muted)" font-size="8">convex: chord above curve (underestimate)</text>
  <path d="M30 95 Q70 20 110 30" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <line x1="30" y1="95" x2="110" y2="30" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3 2"/>
  <circle cx="70" cy="62" r="2.5" fill="var(--ink)"/><text x="74" y="60" fill="var(--muted)" font-size="7">avg output</text>
  <circle cx="70" cy="47" r="2.5" fill="var(--s1)"/><text x="34" y="44" fill="var(--s1)" font-size="7">f(avg)</text>
  <text x="160" y="12" fill="var(--muted)" font-size="8">concave: chord below (overestimate)</text>
  <path d="M180 95 Q220 25 285 95" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <line x1="180" y1="95" x2="285" y2="95" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3 2"/>
  <circle cx="232" cy="95" r="2.5" fill="var(--ink)"/><text x="200" y="108" fill="var(--muted)" font-size="7">avg output</text>
  <circle cx="232" cy="55" r="2.5" fill="var(--s2)"/><text x="236" y="53" fill="var(--s2)" font-size="7">f(avg)</text>
  <text x="20" y="124" fill="var(--muted)" font-size="8">the chord (true average) and the curve (shortcut) split apart wherever the model bends</text>
</svg>
^ The dashed chord is the average of the outputs and the point on the curve is the output of the average; they coincide only on a straight line, and split above or below as the curve bends up or down.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/data-inter-21/flawofaverages.py

The fixture is two datasets that share a mean of 5 but differ in spread.

```json filename=modules/ai-for-science-and-data/code/data-inter-21/flawofaverages.json:1-5 COMPLETE
{
  "_meta": "Two datasets with the SAME mean (5) but different spread, to show the flaw of averages (Jensen's inequality). When a quantity is a curved function f of an input x, the average of f(x) over the data is NOT f of the average x. For a convex f (curving up, like squaring) the true average f(x) is LARGER than f(mean x), so plugging in the mean underestimates. For a concave f (curving down, like square root) it is smaller, so the mean overestimates. Only a linear f is exact. The size of the error grows with the spread of x: for f(x)=x^2 the gap mean(x^2) - (mean x)^2 is exactly the variance. spread and tight share a mean but not a variance, so they share f(mean x) but not the true average.",
  "spread": [1, 5, 9],
  "tight": [4, 5, 6]
}
```

The two quantities are one function call apart: average then apply, or apply then average.

```python filename=modules/ai-for-science-and-data/code/data-inter-21/flawofaverages.py:53-60 COMPLETE
def mean_of_f(xs, f):
    """The true average output: average f over the data."""
    return mean([f(v) for v in xs])


def f_of_mean(xs, f):
    """The shortcut: apply f to the average input."""
    return f(mean(xs))
```

Run `--gap` to see both, for a convex, concave, and linear function.

```text filename=--gap
GAP — true average output mean(f(x)) vs the shortcut f(mean(x))
--------------------------------------------------------------------
  dataset   function   mean(f(x))   f(mean(x))   gap        direction
  spread    square      35.6667      25.0000     +10.6667   underestimate
  spread    sqrt         2.0787       2.2361      -0.1574   overestimate
  spread    identity     5.0000       5.0000      +0.0000   exact
  tight     square      25.6667      25.0000      +0.6667   underestimate
  tight     sqrt         2.2285       2.2361      -0.0075   overestimate
  tight     identity     5.0000       5.0000      +0.0000   exact
```

Squaring the spread set, the true average of the squares is 35.67 but the square of the average is only 25.00 — the shortcut underestimates by 10.67. The square root reverses the sign: the true average is 2.08 while the root of the average is 2.24, an overestimate. The identity function, being linear, is exact both times. The direction is read straight off the curvature, and it does not depend on the data — only its sign does.

<svg role="img" aria-label="For squaring the true average 35.67 towers over the shortcut 25.00; for sqrt the true average 2.08 is below the shortcut 2.24; identity is equal" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">spread set: mean(f(x)) (dark) vs f(mean(x)) (light)</text>
  <line x1="30" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <text x="55" y="108" fill="var(--muted)" font-size="8">square</text>
  <rect x="45" y="18" width="22" height="77" fill="var(--s1)"/><text x="42" y="15" fill="var(--s1)" font-size="7">35.67</text>
  <rect x="70" y="41" width="22" height="54" fill="var(--muted)"/><text x="70" y="38" fill="var(--muted)" font-size="7">25.0</text>
  <text x="150" y="108" fill="var(--muted)" font-size="8">sqrt (×20)</text>
  <rect x="150" y="53" width="22" height="42" fill="var(--s2)"/><text x="146" y="50" fill="var(--s2)" font-size="7">2.08</text>
  <rect x="175" y="50" width="22" height="45" fill="var(--muted)"/><text x="175" y="47" fill="var(--muted)" font-size="7">2.24</text>
  <text x="245" y="108" fill="var(--muted)" font-size="8">identity</text>
  <rect x="245" y="45" width="22" height="50" fill="var(--s1)"/><rect x="255" y="45" width="12" height="50" fill="var(--muted)"/><text x="248" y="42" fill="var(--muted)" font-size="7">equal</text>
  <text x="30" y="118" fill="var(--muted)" font-size="8">convex bar taller, concave bar shorter, linear bars equal</text>
</svg>
^ For the convex square the true-average bar towers over the shortcut; for the concave root it falls just short; for the linear identity the two are equal — the sign of the gap is the sign of the curvature.

## Build

Why does the same function give a 10.67 gap on one set and 0.67 on another? Run `--spread`.

```text filename=--spread
SPREAD — the convex gap is the variance and grows with spread (both means = 5)
--------------------------------------------------------------------
  spread    values [1, 5, 9]  mean 5  f(mean)=25.00  gap 10.6667  variance 10.6667
  tight     values [4, 5, 6]  mean 5  f(mean)=25.00  gap 0.6667  variance 0.6667
--------------------------------------------------------------------
  same mean -> same f(mean); the wider set's larger variance is exactly its larger bias.
```

Both sets have mean 5, so both give the same shortcut, `f(mean) = 25`. But the true average of the squares differs, and the difference is exactly each set's variance: 10.67 for the wide spread, 0.67 for the tight one. This is the identity `mean(x²) − (mean x)² = variance`, and it makes the abstract warning quantitative — the bias from using the average is not vague, it is the variance of what you averaged over. Feed a model a mean and you have silently discarded exactly the quantity that measures your error.

<svg role="img" aria-label="Both datasets share the shortcut value 25 but the spread set's true average is 35.67 and the tight set's is 25.67, gaps equal to their variances 10.67 and 0.67" viewBox="0 0 300 115" width="300" height="115">
  <text x="10" y="12" fill="var(--muted)" font-size="8">same f(mean)=25; the gap up to the true average = variance</text>
  <line x1="30" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="50" x2="285" y2="50" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 3"/><text x="230" y="48" fill="var(--muted)" font-size="7">f(mean)=25</text>
  <text x="70" y="108" fill="var(--muted)" font-size="8">spread</text>
  <rect x="60" y="18" width="30" height="77" fill="var(--s1)"/><text x="58" y="15" fill="var(--s1)" font-size="7">35.67</text><text x="92" y="34" fill="var(--muted)" font-size="7">gap 10.67</text>
  <text x="205" y="108" fill="var(--muted)" font-size="8">tight</text>
  <rect x="195" y="45" width="30" height="50" fill="var(--s2)"/><text x="193" y="42" fill="var(--s2)" font-size="7">25.67</text><text x="227" y="48" fill="var(--muted)" font-size="7">gap 0.67</text>
  <text x="30" y="113" fill="var(--muted)" font-size="8">the dashed line is the shared shortcut; the bar height above it is the variance</text>
</svg>
^ Both bars would stop at the dashed shortcut of 25 if the model were linear; the height they rise above it is exactly the variance, large for the spread set and small for the tight one.

## Definition of done

The self-test pins all four facts: convex underestimates, concave overestimates, linear is exact, the squaring gap equals the variance, and it grows with spread at equal mean.

```python filename=modules/ai-for-science-and-data/code/data-inter-21/flawofaverages.py:99-113 COMPLETE
    convex_underestimates = f_of_mean(xs, sq) < mean_of_f(xs, sq)
    print("  convex: f(mean) underestimates the true average = %s (%.2f < %.2f)" % (convex_underestimates, f_of_mean(xs, sq), mean_of_f(xs, sq)))

    concave_overestimates = f_of_mean(xs, sr) > mean_of_f(xs, sr)
    print("  concave: f(mean) overestimates the true average = %s (%.4f > %.4f)" % (concave_overestimates, f_of_mean(xs, sr), mean_of_f(xs, sr)))

    linear_exact = abs(f_of_mean(xs, idn) - mean_of_f(xs, idn)) < 1e-9
    print("  linear: the shortcut is exact = %s (%.2f = %.2f)" % (linear_exact, f_of_mean(xs, idn), mean_of_f(xs, idn)))

    square_gap_is_variance = abs((mean_of_f(xs, sq) - f_of_mean(xs, sq)) - variance(xs)) < 1e-9
    print("  the squaring gap equals the variance = %s (%.4f = %.4f)" % (square_gap_is_variance, mean_of_f(xs, sq) - f_of_mean(xs, sq), variance(xs)))

    tight = data["tight"]
    gap_grows_with_spread = (mean_of_f(xs, sq) - f_of_mean(xs, sq)) > (mean_of_f(tight, sq) - f_of_mean(tight, sq)) and mean(xs) == mean(tight)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — convex underestimates, concave overestimates, linear is exact, the square gap is the variance
------------------------------------------------------------------------------------------------------------
  convex: f(mean) underestimates the true average = True (25.00 < 35.67)
  concave: f(mean) overestimates the true average = True (2.2361 > 2.0787)
  linear: the shortcut is exact = True (5.00 = 5.00)
  the squaring gap equals the variance = True (10.6667 = 10.6667)
  wider spread, same mean, bigger gap = True (10.6667 > 0.6667)
------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  convex_underestimates=True  concave_overestimates=True  linear_exact=True  square_gap_is_variance=True  gap_grows_with_spread=True
```

**Done means the bias is proven directional and sized: squaring underestimates by 10.67 (exactly the variance), the square root overestimates, the identity is exact, and the same function's gap shrinks to 0.67 on the tighter set — so the shortcut's error is the variance of what you averaged over.**

## Boss fight

The variance identity was for squaring. Predict how to estimate the bias for a general curved model, and whether the fix is ever just "use the average anyway." It is tempting to hope most models are close enough to linear that the shortcut is fine.

For a general smooth function the bias is approximately half the second derivative times the variance — the curvature times the spread, which is the same story squaring told exactly. That gives you both the size and a rule for when the shortcut is safe: it is fine when the model is nearly straight over the range your inputs actually cover, or when that range is narrow (small variance). It is dangerous when the model bends sharply where your data lives — near a saturation point, an exponential's knee, a queue approaching full — or when inputs are widely spread. The honest fix is to run the model over the distribution of inputs and average the outputs (a Monte Carlo or a full enumeration like this fixture), not to average first; you only collapse to the mean after checking the curvature is negligible over your range.

The subtler trap is that the flaw hides inside quantities you did not think of as models. An average of rates, an average of ratios, a growth rate compounded from average returns, a cost computed from average demand — each is a nonlinear function of its inputs, so each carries this bias. "Average utilization is 80%, so average wait is W(80%)" understates the wait, because waiting time is violently convex near full load; "average monthly return is 1%" does not compound to the average final balance, because compounding is convex. Whenever a summary statistic goes *into* a calculation rather than *out* of one, ask whether the calculation is curved — and if it is, the average is the wrong number to feed it.

```python filename=modules/ai-for-science-and-data/code/data-inter-21/flawofaverages.py:108-109 COMPLETE
    square_gap_is_variance = abs((mean_of_f(xs, sq) - f_of_mean(xs, sq)) - variance(xs)) < 1e-9
    print("  the squaring gap equals the variance = %s (%.4f = %.4f)" % (square_gap_is_variance, mean_of_f(xs, sq) - f_of_mean(xs, sq), variance(xs)))
```

**A curved model turns the average of its inputs into a biased output — convex underestimates, concave overestimates, by roughly half the curvature times the variance — so average the outputs over the real spread of inputs, and only collapse to the mean once you have checked the model is near-straight over the range your data covers.**

## External resources

Sam Savage's *The Flaw of Averages* — the book-length treatment of exactly this error, with the drowning-statistician parable and a catalogue of business and engineering cases where plugging in the average went wrong.

Any probability text's statement of Jensen's inequality — the formal `E[f(X)] ≥ f(E[X])` for convex f, and the second-order (delta-method) approximation of the gap as ½·f″·Var(X).

The companion "average growth factors with the geometric mean" and "the mean describes no typical request" modules — both are the flaw of averages in a specific disguise: compounding is convex, and a heavy-tailed workload makes the mean an input no single request resembles.
