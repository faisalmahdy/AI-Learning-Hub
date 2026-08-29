---
id: data-inter-07
title: A fit is only valid inside its data's range — extrapolate and a great model predicts nonsense
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 5-8h
summary: A line fit to data can be excellent — small residuals, high R-squared — and still be worthless for a prediction outside the range of points it was fit on, because the fit only ever saw a window of the input and what the relationship does beyond that window is an assumption, not a measurement. On a saturating curve sampled over x in [10, 50] the least-squares line y = 0.825x + 10.68 fits beautifully — worst in-range residual 2.26, in-range prediction errors 2.02 and 1.62 — yet asked to predict at x = 200, far past the last data point, it marches on to 175.7 while the true value has flattened to 80.0, an error of 95.7 that is 47 times the worst in-range error. The fix is not a better line; it is knowing the fit's support (the min and max of the training x) and refusing to extrapolate past it, or at least flagging that a prediction out there is unvouched-for. The naive predictor answers any query with the same false confidence; a support-aware one flags x = 200 as extrapolation, because the straight line is a claim about the window, not about forever.
eli5: If you measure how fast a plant grows over its first month and draw a straight line, the line fits that month great — but use it to predict the plant's height in ten years and it says the plant is taller than a house. The line only knew about the first month; it has no idea the plant stops growing. Predicting way outside the range you actually watched isn't measuring, it's guessing that the line goes on forever, and it usually doesn't.
---

## Why this module

Fitting a model to data feels like it captures a relationship, and within the data it does. But a fit is a summary of the points it saw, and it makes no promise whatsoever about inputs it never saw. This is the difference between interpolation — predicting inside the range of your data, between points you measured — and extrapolation — predicting outside that range, past the last point. Interpolation is supported by the data; extrapolation is supported only by an assumption you slipped in without noticing: that whatever shape the model has continues, unchanged, forever in both directions.

<svg viewBox="0 0 700 130" role="img" aria-label="A number line for x. A shaded band from 10 to 50 marks the training support. Queries at 25 and 35 sit inside it, labeled interpolation. Queries at 100 and 200 sit far to the right outside it, labeled extrapolation, with 200 furthest out.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">inside the support is interpolation; past the last point is extrapolation</text>
    <line x1="50" y1="70" x2="670" y2="70" stroke="var(--line)"></line>
    <rect x="80" y="56" width="80" height="28" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="120" y="48" text-anchor="middle" fill="var(--acc-ink)" font-size="8">support [10,50]</text>
    <circle cx="100" cy="70" r="4" fill="var(--s1)"></circle><text x="100" y="100" text-anchor="middle" fill="var(--s1)" font-size="7">25 ✓</text>
    <circle cx="140" cy="70" r="4" fill="var(--s1)"></circle><text x="140" y="100" text-anchor="middle" fill="var(--s1)" font-size="7">35 ✓</text>
    <circle cx="370" cy="70" r="4" fill="var(--s2)"></circle><text x="370" y="100" text-anchor="middle" fill="var(--s2)" font-size="7">100 ✗</text>
    <circle cx="630" cy="70" r="4" fill="var(--s2)"></circle><text x="630" y="100" text-anchor="middle" fill="var(--s2)" font-size="7">200 ✗</text>
    <text x="500" y="52" fill="var(--s2)" font-size="7">extrapolation — no data out here</text>
    <text x="50" y="118" fill="var(--muted)" font-size="8">the data ended at 50; everything past it is the line's assumption, not a measurement</text>
  </g>
</svg>
^ The training data covers x in [10, 50]; queries at 25 and 35 are interpolation (inside), while 100 and 200 are extrapolation (outside), with 200 the furthest into territory the fit never saw.

For a straight line, that assumption is that the relationship is linear everywhere — not just linear across your window, but linear out to infinity. Almost nothing in the real world obeys that. Growth saturates, returns diminish, resources deplete, physics imposes ceilings. So a relationship that is beautifully straight across the range you measured can be bending hard just past your last data point, and your line, which has no way to know, keeps going straight. The model that scored a near-perfect fit in-range produces a confidently wrong number out-of-range, and nothing in the fit statistics warns you, because those statistics are computed on the in-range data where the model is genuinely good.

This module makes the trap concrete. The data is a saturating curve, sampled over a window where it bends only gently, so a line fits it well — the worst residual on the training points is about 2. Ask that line to predict inside the window and it is within a couple of units of the truth. Ask it to predict at x = 200, four times past the last data point, and it is off by nearly 100 — the curve has flattened toward its ceiling while the line has climbed away. The fix is not a fancier model; it is discipline about support: know the range your fit actually saw, and treat any prediction outside it as an extrapolation to be flagged or refused. Everything runs offline against a curve fixture, stdlib Python 3, `$0.00`, with the least-squares fit computed. The instinct to unlearn is that a good fit licenses prediction. A good fit licenses prediction inside its support; outside, the fit is silent and the straight line is just an assumption wearing the fit's authority.

## Concepts

Named here so you can find them again; each is built below.

- **Least-squares fit** — the line minimizing squared error to the training points.
- **Support** — the range [min, max] of the training inputs; where the fit is grounded.
- **Interpolation** — predicting inside the support, between measured points; data-backed.
- **Extrapolation** — predicting outside the support, past the last point; assumption-backed.
- **In-range residual** — the fit's honest error bar, measured on its own training window.
- **Support-aware prediction** — flagging or refusing a query outside the support.

## Worked example

Source: a regression prediction — the everyday act of fitting a trend and reading a value off it. The saturating curve stands in for any real relationship that is locally straight and globally bent (growth, dose-response, load-latency), chosen so the fit is honestly good in-range and honestly disastrous out.

Script and fixture: `modules/ai-for-science-and-data/code/data-inter-07/` — `extrapolate.py`, and `curve.json`, five training points and four queries. Every command runs from there.

### The fit and its support

The fit is an ordinary least-squares line; the support is just the range of x it saw.

```
# extrapolate.py:42-62 — COMPLETE (least-squares line, prediction, and the training support)
def fit_line(points):
    """Ordinary least-squares slope and intercept for y = m*x + b."""
    n = len(points)
    sx = sum(p[0] for p in points)
    sy = sum(p[1] for p in points)
    sxx = sum(p[0] * p[0] for p in points)
    sxy = sum(p[0] * p[1] for p in points)
    m = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    b = (sy - m * sx) / n
    return m, b


def predict(m, b, x):
    return m * x + b


def support(points):
    """The range of x the fit actually saw -- predictions outside this are extrapolation."""
    xs = [p[0] for p in points]
    return min(xs), max(xs)
```

The `support` function is three lines and it is the hero of the module — it records the one fact the fit statistics leave out, namely where the data was. Fit the curve:

```
# $ python3 extrapolate.py --fit
#   fitted line: y = 0.825 x + 10.677
#   training support (x range seen): [10, 50]
#   worst in-range residual: 2.26
```

run: 2026-08-27 · deterministic; the curve and query truths are a fixture · 5 points · `python3 extrapolate.py --fit`

The fit is good. The worst the line does on any training point is 2.26 — a tight fit to a gently curving window, exactly the kind of result that makes you trust the model. And the support line records that every one of those points had x between 10 and 50. That range is the fine print on the fit: within it, the residual of 2.26 is a fair error bar; outside it, the fit has told you nothing, because it saw nothing.

### Prediction: inside vs outside the support

Now read predictions off the line, some inside the window and some far beyond it, against the true curve.

```
# $ python3 extrapolate.py --predict
#   x       predicted  true    error   within support?
#   25      31.31      33.33   2.02    yes
#   35      39.56      41.18   1.62    yes
#   100     93.21      66.67   26.54   NO (extrapolation)
#   200     175.74     80.00   95.74   NO (extrapolation)
```

run: 2026-08-27 · deterministic · `python3 extrapolate.py --predict`

Inside the support, the line is excellent — at x=25 it predicts 31.31 against a true 33.33, an error of 2.02, right in line with the training residual. That is interpolation working exactly as advertised. Outside the support, it falls apart: at x=100 the error is 26.54, and at x=200 the line says 175.74 while the truth has saturated to 80.00 — an error of 95.74, more than forty times the in-range error. The line did not degrade gracefully; it kept climbing at its fitted slope while the real relationship bent away toward its ceiling. Same model, same fit statistics — the only thing that changed is whether the query was inside the data.

<svg viewBox="0 0 700 220" role="img" aria-label="A plot. The true curve rises steeply then saturates toward a ceiling near 80-100. Training points lie on it over x from 10 to 50, a shaded support band. The fitted line matches the curve inside the band but continues straight upward past it, diverging from the flattening true curve; at x=200 the line is near 176 while the curve is near 80, a large vertical gap.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the line matches inside the support and diverges far outside it</text>
    <line x1="60" y1="185" x2="670" y2="185" stroke="var(--line)"></line>
    <line x1="60" y1="30" x2="60" y2="185" stroke="var(--line)"></line>
    <rect x="72" y="30" width="80" height="155" fill="var(--acc-soft)" opacity="0.5"></rect><text x="112" y="200" text-anchor="middle" fill="var(--acc-ink)" font-size="7">support [10,50]</text>
    <path d="M 72 175 Q 200 150 340 120 T 660 95" fill="none" stroke="var(--s1)"></path><text x="600" y="90" fill="var(--s1)" font-size="8">true curve (saturates)</text>
    <line x1="72" y1="176" x2="660" y2="40" stroke="var(--s2)" stroke-dasharray="5 3"></line><text x="560" y="46" fill="var(--s2)" font-size="8">fitted line (keeps climbing)</text>
    <g fill="var(--ink)"><circle cx="80" cy="176" r="3"></circle><circle cx="100" cy="168" r="3"></circle><circle cx="120" cy="160" r="3"></circle><circle cx="135" cy="154" r="3"></circle><circle cx="152" cy="148" r="3"></circle></g>
    <line x1="640" y1="52" x2="640" y2="103" stroke="var(--muted)"></line><text x="648" y="80" fill="var(--muted)" font-size="7">error 96</text>
    <text x="640" y="200" text-anchor="middle" fill="var(--muted)" font-size="7">x=200</text>
  </g>
</svg>
^ Inside the shaded support the fitted line tracks the true curve; beyond it the curve saturates while the line keeps climbing, and the vertical gap at x=200 is the extrapolation error of ~96.

### The support check is the whole fix

The only new thing the support-aware predictor does is compare the query to the range the fit saw.

```
# extrapolate.py:64-65 — COMPLETE (the one check: is the query inside the fit's support?)
def in_support(x, sup):
    return sup[0] <= x <= sup[1]
```

That is the entire defense — one comparison. The naive predictor omits it and answers every query with the same confident number; the support-aware predictor runs it and flags x=100 and x=200 as extrapolation before quoting a value it cannot stand behind. The line is identical in both; the difference is whether the predictor admits where its knowledge ends.

**A fit is only grounded within the range of its training data — its support — so a prediction outside that range is an assumption that the model's shape continues forever, not a measurement; a line with a 2.26 in-range residual errs by 95.74 at x=200, and the fix is to record the support and flag or refuse any query beyond it, because a good fit vouches for interpolation and says nothing about extrapolation.**

### The self-test

The `--check` mode plants the bug — extrapolating without a support check — and proves it: the in-range error is small, the far prediction's error is many times larger, and the far query is outside the support that a support-aware predictor would have flagged.

```
# $ python3 extrapolate.py --check
#   in-range predictions are accurate = True (worst error 2.02 < tol 3.00)
#   the extrapolated prediction is far wrong = True (error 95.74 at x=200, 47x the in-range error)
#   the far query is outside the training support = True (x=200 not in [10, 50])
#   a support-aware predictor flags it while the naive one answers = True
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 extrapolate.py --check`

The `in_range_good` and `extrapolation_wrong` lines are deliberately reported together, because the danger is precisely that both are true at once: the model is genuinely accurate where it has data and genuinely disastrous where it does not, and the fit statistics only ever report the first. A practitioner who trusts the low residual and predicts at x=200 has been misled not by a bad model but by a good one used outside its warranty.

```
# extrapolate.py:117-123 — COMPLETE (in-range accurate AND extrapolation far wrong, both true)
    in_range_good = in_err < data["tolerance"]
    print("  in-range predictions are accurate = %s (worst error %.2f < tol %.2f)"
          % (in_range_good, in_err, data["tolerance"]))

    far = max(out_q, key=lambda q: abs(predict(m, b, q["x"]) - q["true_y"]))
    far_err = abs(predict(m, b, far["x"]) - far["true_y"])
    extrapolation_wrong = far_err > 10 * in_err
```

### The running tally

| query x | in support? | predicted | true | error |
|---|---|---|---|---|
| 25 | yes (interpolation) | 31.31 | 33.33 | 2.02 |
| 35 | yes (interpolation) | 39.56 | 41.18 | 1.62 |
| 100 | no (extrapolation) | 93.21 | 66.67 | 26.54 |
| 200 | no (extrapolation) | 175.74 | 80.00 | 95.74 |

The in-range error bar the fit is entitled to is just the worst it does on its own training points:

```
# extrapolate.py:70-72 — COMPLETE (the honest in-range error bar: the worst training residual)
def max_in_range_residual(points, m, b):
    """The worst the fit does on its own training points -- the honest in-range error bar."""
    return max(abs(p[1] - predict(m, b, p[0])) for p in points)
```

<svg viewBox="0 0 700 180" role="img" aria-label="A bar chart of prediction error against query x. At x=25 and x=35 (in support) the bars are tiny, near 2. At x=100 the bar is 27, and at x=200 it is 96 — the error grows monotonically the further past the support the query is.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">prediction error grows the further past the support you reach</text>
    <line x1="60" y1="150" x2="660" y2="150" stroke="var(--line)"></line>
    <line x1="60" y1="140" x2="660" y2="140" stroke="var(--acc-line)" stroke-dasharray="3 2"></line><text x="664" y="143" fill="var(--acc-ink)" font-size="7">in-range ~2</text>
    <rect x="100" y="147" width="40" height="3" fill="var(--s1)"></rect><text x="120" y="166" text-anchor="middle" fill="var(--s1)" font-size="7">x25: 2.0</text>
    <rect x="200" y="148" width="40" height="2" fill="var(--s1)"></rect><text x="220" y="166" text-anchor="middle" fill="var(--s1)" font-size="7">x35: 1.6</text>
    <rect x="330" y="109" width="40" height="41" fill="var(--s2)"></rect><text x="350" y="166" text-anchor="middle" fill="var(--s2)" font-size="7">x100: 27</text>
    <rect x="470" y="30" width="40" height="120" fill="var(--s2)"></rect><text x="490" y="166" text-anchor="middle" fill="var(--s2)" font-size="7">x200: 96</text>
    <text x="330" y="24" fill="var(--muted)" font-size="8">the two in-support bars are invisible against the two extrapolated ones</text>
  </g>
</svg>
^ In-support errors (x=25, x=35) sit right on the in-range error bar; the extrapolated errors tower over it and grow with distance — 27 at x=100, 96 at x=200. The error scales with how far past the data you reached.

Read the error column against the support column: the two in-support rows have errors near the fit's 2.26 residual, and the two out-of-support rows have errors that grow with distance past the window — 26.54 at x=100, 95.74 at x=200. The error is not random; it scales with how far you reached beyond the data, because the further out you go, the more the line's forever-straight assumption diverges from the curve that actually bends. That monotonic growth is the signature of extrapolation, and the support column predicts it perfectly while the fit statistics do not mention it.

### What we did not settle

This is the support discipline; a few refinements sit around it. A prediction interval widens as you move toward and past the edge of the data, so a proper regression already quantifies rising uncertainty near the support boundary — but it still assumes the functional form, so a widening interval is a warning, not a license. Fitting a curve that matches the true saturating shape would extrapolate better here, but only because we happen to know the shape; the general lesson is that no fit can be trusted past its data regardless of form, because the data cannot rule out a bend just beyond the last point. Domain limits help — many quantities have known ceilings or floors that bound the extrapolation. And a support check generalizes to many dimensions as the convex hull of the training inputs, where "outside the data" is far easier to stumble into than in one dimension. The invariant: record where your data was, and never quote a prediction from outside it without flagging that it is unvouched-for.

## Build

The build in one paragraph: fit your model, but also record its support — the range (or, in many dimensions, the region) of inputs the training data actually covered — and before quoting any prediction, check whether the query falls inside it; inside, report the value with the in-range residual as its error bar, and outside, flag the prediction as extrapolation or refuse it, because the fit statistics vouch only for the window they were computed on. Widen prediction intervals toward the edge, prefer a functional form justified by domain knowledge, apply known physical ceilings, and treat the convex hull as the support in higher dimensions.

We opened on the fit. The number that proves the trap is the error inside versus outside the support:

```
# modules/ai-for-science-and-data/code/data-inter-07/ — COMPLETE, run from that directory
$ python3 extrapolate.py --check
  in-range predictions are accurate = True (worst error 2.02 < tol 3.00)
  the extrapolated prediction is far wrong = True (error 95.74 at x=200, 47x the in-range error)
```

Now build your own. Take a real relationship that is locally straight but globally curved, fit a line over a window, and predict both inside and far outside it against the truth. Your number to beat is not the in-range fit — that will look great; it is **the ratio of out-of-support error to in-support error** — extrapolation should be many times worse, and your support check should flag exactly the out-of-range queries. Bring back the in-range and extrapolated errors. Good luck.

## Definition of done

- [ ] A least-squares fit and its training support (min/max of x)
- [ ] A support check: is a query inside the fitted range?
- [ ] In-range and out-of-range queries scored against the truth
- [ ] Confirmation in-range predictions are accurate (near the training residual)
- [ ] Confirmation the extrapolated prediction's error is many times larger
- [ ] Confirmation the far query is outside the support and a support-aware predictor flags it
- [ ] `python3 extrapolate.py --check` printing SELF-TEST PASS: in_range_good, extrapolation_wrong, out_of_support, flagged
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Distinguish interpolation from extrapolation. Which one does a fit's data actually support?
2. The line had a worst residual of 2.26 and an error of 95.74 at x=200. Why do the fit statistics not warn you about the second number?
3. What is a fit's "support," and what is the one check that turns a naive predictor into a support-aware one?
4. Why is it especially dangerous that the in-range accuracy and the out-of-range error are both true at once?
5. Your own relationship was fit and queried in and out of range. What was the error inside versus far outside the support?

## External resources

- Any regression textbook's section on prediction intervals and extrapolation — my summary: why the interval widens outside the data and why even so the functional-form assumption is unverified out there; read it for the uncertainty the point estimate hides.
- The Challenger O-ring analysis (extrapolating below the observed temperature range) — my summary: a catastrophic real extrapolation past the data's support; read it for the stakes when a fit is trusted outside where it was measured.
- This hub, *data-inter-06* (Anscombe's quartet) — read it for the companion lesson that summary statistics hide the shape of the data, which is exactly what makes an out-of-range bend invisible until you plot it.
