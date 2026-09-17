---
id: data-inter-06
title: Anscombe's quartet — four datasets with identical statistics and opposite shapes
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 8-10h
summary: Four datasets share their mean of x, mean of y, variance, correlation, and least-squares regression line to two decimals — all report 9.0, 7.5, 10.0, 3.75, correlation 0.82, and the line y = 3.0 + 0.5x — yet one is a clean line, one a parabola, one a line dragged by a single outlier, and one a vertical stack whose entire correlation comes from one far-out point. The summary statistics agree while the datasets could not be more different, and a shape diagnostic exposes it: the max residual from the shared line is 1.9 for the clean and curved sets but 3.24 for the outlier set, and the fourth has only two distinct x values, a degeneracy the numbers hide entirely. Summary statistics compress a dataset, and compression discards exactly the structure — curvature, outliers, leverage — that decides whether a linear fit means anything, so a number is never a substitute for looking at the data.
eli5: Four very different drawings can have the same average brightness, the same width, and the same tilt, so if you only measured those numbers you would call the drawings identical. But one is a straight line, one is a smile, one is a line with a dot flung far away, and one is a tall stack with a single stray dot. You have to actually look at the picture — the summary numbers agree while the pictures disagree completely.
---

## Why this module

You generated real datasets, and the first thing anyone does with a dataset is summarize it — mean, variance, correlation, a regression line — and reason from those numbers. This module shows, with the most famous counterexample in statistics, why that is not enough: four datasets can share every one of those summaries and be structurally unrelated, so a conclusion drawn from the numbers alone is right for one of them and wrong for the other three. Anscombe built the quartet in 1973 to make exactly this point, and it is worth reproducing because the lesson — plot your data, summaries lie — is the cheapest, most-ignored safeguard in data analysis.

The mechanism is compression. A summary statistic maps a whole dataset to one number, and any such map is many-to-one: different datasets collapse to the same summary. Mean, variance, correlation, and a regression line are five such numbers, and Anscombe found four datasets that agree on all five while differing in the structure those five cannot see — curvature, a single outlier, and leverage from a degenerate spread of x. The consequence is concrete: all four report a strong linear correlation of 0.82 and the line y = 3 + 0.5x, so a model or decision that trusts "strong linear relationship, slope 0.5" is correct for the clean dataset, fooled by the curve in the second, dragged off by the outlier in the third, and entirely fabricated in the fourth, where the correlation exists only because of one far-flung point. The numbers do not warn you which case you are in; only the shape does, and the shape is exactly what the summary threw away.

You need only the mean, variance, and correlation. Everything runs offline against the published Anscombe quartet — four eleven-point datasets — stdlib Python 3, `$0.00`. The instinct to unlearn is that a matching set of summary statistics means matching data. It means the data agree on those particular projections, and two datasets can agree on every summary you compute and disagree on everything you did not — which is why the plot is not optional.

Here are the four, agreeing on every statistic:

```
# modules/ai-for-science-and-data/code/data-inter-06/ — COMPLETE, run from that directory
$ python3 anscombe.py --stats

STATS — the four datasets share their summary statistics (2 decimals)
------------------------------------------------------------------
  set  mean_x  mean_y  var_x  var_y  corr   line
  d1     9.00    7.50  10.00   3.75  0.816  y=3.00+0.50x
  d2     9.00    7.50  10.00   3.75  0.816  y=3.00+0.50x
  d3     9.00    7.50  10.00   3.75  0.816  y=3.00+0.50x
  d4     9.00    7.50  10.00   3.75  0.817  y=3.00+0.50x
```

run: 2026-08-26 · deterministic; the published Anscombe quartet · 4 datasets · `python3 anscombe.py --stats`

<svg viewBox="0 0 700 170" role="img" aria-label="Four different dataset icons on the left (a line, a curve, a line-with-dot, a vertical-with-dot) all feeding through a funnel labelled 'summarize' into a single identical statistics tuple on the right. The many-to-one mapping collapses four shapes to one summary.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">summarizing is many-to-one: four shapes collapse to one tuple</text>
    <g stroke="var(--s1)" fill="none"><path d="M40 40 L90 30"></path><path d="M40 70 Q65 55 90 70"></path></g>
    <g fill="var(--s1)"><circle cx="65" cy="95" r="2"></circle><circle cx="88" cy="88" r="3" fill="var(--s2)"></circle><line x1="40" y1="100" x2="80" y2="92" stroke="var(--s1)"></line></g>
    <g fill="var(--s1)"><circle cx="45" cy="120" r="2"></circle><circle cx="45" cy="128" r="2"></circle><circle cx="45" cy="136" r="2"></circle><circle cx="88" cy="118" r="3" fill="var(--s2)"></circle></g>
    <path d="M 120 85 L 240 85" stroke="var(--muted)"></path>
    <polygon points="240,60 340,78 340,92 240,110" fill="var(--panel)" stroke="var(--line)"></polygon><text x="290" y="88" text-anchor="middle" fill="var(--ink)">summarize</text>
    <path d="M 340 85 L 420 85" stroke="var(--muted)"></path>
    <rect x="420" y="66" width="250" height="38" rx="4" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="545" y="82" text-anchor="middle" fill="var(--acc-ink)">mean 9.0, 7.5 · var 10, 3.75</text><text x="545" y="96" text-anchor="middle" fill="var(--acc-ink)">corr 0.82 · y=3+0.5x</text>
    <text x="290" y="140" fill="var(--muted)">the arrow only runs one way — you cannot recover the shape from the summary</text>
  </g>
</svg>
^ Four structurally different datasets pass through the same summary and come out identical, because summarizing discards shape. The map is one-directional: the tuple on the right cannot tell you which of the four produced it.

Every column is identical to two decimals — same means, same variances, same correlation, same regression line. By the numbers, these are the same dataset four times. They are not, and this module is what the numbers cannot see.

## Concepts

Named here so you can find them again; each is built below.

- **Summary statistic** — a number compressing a dataset (mean, variance, correlation, regression line).
- **Many-to-one compression** — different datasets mapping to the same summary; why summaries can agree.
- **Correlation** — the linear-association number; identical across all four despite different shapes.
- **Regression line** — the least-squares fit; identical across all four.
- **Residual** — a point's distance from the fitted line; a shape diagnostic the summary omits.
- **Leverage** — a point with an extreme x that alone can determine the fit, as in the fourth dataset.

## Worked example

Source: Anscombe's quartet (F. J. Anscombe, "Graphs in Statistical Analysis", 1973), the canonical demonstration that summary statistics must be paired with visualization; the data here is the published quartet, reproduced so the identical statistics and differing shapes are exact and checkable.

Script and fixture: `modules/ai-for-science-and-data/code/data-inter-06/` — `anscombe.py`, and `anscombe.json`, the four eleven-point datasets. Every command runs from there.

### The statistics that agree

The five summaries are the ordinary ones. Mean and variance come first, the building blocks of all the rest:

```
# anscombe.py:40-46 — COMPLETE (mean and variance)
def mean(xs):
    return sum(xs) / len(xs)


def variance(xs):
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)
```

Correlation measures linear association; regression fits the least-squares line.

```
# anscombe.py:49-61 — COMPLETE (correlation and the least-squares regression line)
def correlation(xs, ys):
    mx, my = mean(xs), mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return cov / (sx * sy)


def regression(xs, ys):
    """Least-squares slope and intercept for y = intercept + slope * x."""
    mx, my = mean(xs), mean(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return slope, my - slope * mx
```

Both are built from the same three sums — the covariance of x and y, and the spreads of each — so they are exactly the projections Anscombe engineered to match. Every dataset in the quartet was constructed to produce the same covariance and the same spreads, which forces the same correlation (0.816) and the same line (slope 0.5, intercept 3). The stats view confirms it: four datasets, one set of numbers. If your analysis stopped at "correlation 0.82, slope 0.5", you would have four identical reports.

### The shapes that do not

Now a diagnostic the summaries omit: how far the worst point sits from the fitted line, and how many distinct x values the dataset even has.

```
# anscombe.py:66-69 — COMPLETE (the largest residual from the fitted line)
def max_abs_residual(xs, ys):
    """The largest deviation of a point from the fitted line -- big for outliers/curves."""
    slope, intercept = regression(xs, ys)
    return max(abs(y - (intercept + slope * x)) for x, y in zip(xs, ys))
```

Run it and the four datasets separate:

```
# $ python3 anscombe.py --shape
#   set  max_residual  distinct_x  what it really is
#   d1          1.92          11  clean linear
#   d2          1.90          11  a parabola (curved)
#   d3          3.24          11  linear + one outlier
#   d4          1.84           2  vertical line + one leverage point
```

run: 2026-08-26 · deterministic · `python3 anscombe.py --shape`

The residual diagnostic already tells d3 apart — its worst point sits 3.24 from the line, nearly double the others, the signature of a single outlier dragging the fit. And `distinct_x` exposes d4: it has only two distinct x values, meaning ten points stacked vertically at x=8 and one lone point at x=19, so the entire correlation is manufactured by that one leverage point — remove it and there is no relationship at all. These are not subtle differences; they are the difference between a trustworthy linear fit (d1), a wrong model (d2's curve), a fit distorted by an outlier (d3), and a fit that is an artifact of one point (d4). None of it is visible in the summary statistics.

<svg viewBox="0 0 700 220" role="img" aria-label="Four small scatter plots sharing the same regression line. d1: points scattered evenly around a rising line. d2: points forming a smooth arch (parabola) crossing the line. d3: points on a tight line with one point far above. d4: a vertical column of points at one x plus one point far to the right on the line.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="14" fill="var(--muted)">the four datasets plotted — same line, four different shapes</text>
    <g transform="translate(20,30)">
      <text x="60" y="0" text-anchor="middle" fill="var(--ink)">d1 linear</text>
      <line x1="10" y1="80" x2="130" y2="20" stroke="var(--muted)" stroke-dasharray="3 2"></line>
      <g fill="var(--s1)"><circle cx="30" cy="72" r="2.5"></circle><circle cx="45" cy="60" r="2.5"></circle><circle cx="60" cy="55" r="2.5"></circle><circle cx="75" cy="42" r="2.5"></circle><circle cx="95" cy="35" r="2.5"></circle><circle cx="110" cy="28" r="2.5"></circle><circle cx="40" cy="66" r="2.5"></circle><circle cx="85" cy="45" r="2.5"></circle></g>
    </g>
    <g transform="translate(190,30)">
      <text x="60" y="0" text-anchor="middle" fill="var(--ink)">d2 curved</text>
      <line x1="10" y1="80" x2="130" y2="20" stroke="var(--muted)" stroke-dasharray="3 2"></line>
      <g fill="var(--s1)"><circle cx="20" cy="78" r="2.5"></circle><circle cx="35" cy="58" r="2.5"></circle><circle cx="50" cy="44" r="2.5"></circle><circle cx="70" cy="34" r="2.5"></circle><circle cx="90" cy="34" r="2.5"></circle><circle cx="110" cy="44" r="2.5"></circle><circle cx="125" cy="55" r="2.5"></circle></g>
    </g>
    <g transform="translate(360,30)">
      <text x="60" y="0" text-anchor="middle" fill="var(--ink)">d3 outlier</text>
      <line x1="10" y1="80" x2="130" y2="20" stroke="var(--muted)" stroke-dasharray="3 2"></line>
      <g fill="var(--s1)"><circle cx="25" cy="70" r="2.5"></circle><circle cx="40" cy="62" r="2.5"></circle><circle cx="55" cy="54" r="2.5"></circle><circle cx="70" cy="46" r="2.5"></circle><circle cx="85" cy="38" r="2.5"></circle><circle cx="115" cy="22" r="2.5"></circle></g>
      <circle cx="60" cy="8" r="3" fill="var(--s2)"></circle><text x="60" y="6" fill="var(--s2)" font-size="7">outlier</text>
    </g>
    <g transform="translate(530,30)">
      <text x="60" y="0" text-anchor="middle" fill="var(--ink)">d4 leverage</text>
      <line x1="10" y1="80" x2="130" y2="20" stroke="var(--muted)" stroke-dasharray="3 2"></line>
      <g fill="var(--s1)"><circle cx="35" cy="70" r="2.5"></circle><circle cx="35" cy="60" r="2.5"></circle><circle cx="35" cy="50" r="2.5"></circle><circle cx="35" cy="40" r="2.5"></circle><circle cx="35" cy="30" r="2.5"></circle><circle cx="35" cy="55" r="2.5"></circle></g>
      <circle cx="120" cy="22" r="3" fill="var(--s2)"></circle><text x="118" y="16" fill="var(--s2)" font-size="7">1 point</text>
    </g>
    <text x="30" y="200" fill="var(--muted)">the dashed line is identical in all four; only d1 is a case where it honestly describes the data</text>
  </g>
</svg>
^ The same regression line runs through all four, and it is trustworthy only for d1. In d2 it misses a clear curve; in d3 one outlier pulled it off the true trend; in d4 it is fixed entirely by a single point with no support from the vertical stack. The summary statistics see none of this.

**Summary statistics compress a dataset, and compression is many-to-one, so different datasets can share every summary — Anscombe's quartet has identical means, variance, correlation, and regression line while being a line, a curve, an outlier-dragged fit, and a single-point artifact, which only a plot or a shape diagnostic reveals.**

### The self-test

The `--check` mode asserts both halves: the summary statistics are identical across all four, and a shape diagnostic separates them.

```
# $ python3 anscombe.py --check
#   all four share (mean_x, mean_y, var_x, var_y, corr, slope, intercept) = True
#      (9.0, 7.5, 10.0, 3.75, 0.82, 0.5, 3.0)
#   all four report the same strong correlation (0.82) = True
#   but the max-residual shape diagnostic differs across them = True ([1.92, 1.9, 3.24, 1.84])
#   d4 is a degenerate shape (only 2 distinct x) hidden by the stats = True
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 anscombe.py --check`

The identity check rounds each dataset's full statistic tuple and requires them all equal, while the shape check requires the residuals to differ:

```
# anscombe.py:113-125 — COMPLETE (the shared stat tuple, and the diverging residuals)
        return (round(mean(xs), 2), round(mean(ys), 2), round(variance(xs), 2),
                round(variance(ys), 2), round(correlation(xs, ys), 2), round(s, 2), round(i, 2))

    tuples = [stat_tuple(n) for n in names]
    stats_identical = all(t == tuples[0] for t in tuples)

    residuals = [round(max_abs_residual(data[n]["x"], data[n]["y"]), 2) for n in names]
    shapes_differ = len(set(residuals)) > 1
```

`stats_identical` demands one shared tuple across all four; `shapes_differ` demands the residuals not all be equal — identical summaries and non-identical shapes, proven together.

The `stats_identical` line is the demonstration's foundation: all four datasets must produce the same rounded tuple of summaries, and the whole point collapses if they do not. The `shapes_differ` line is the payoff — the max-residual diagnostic must take different values across the four, proving that structure the summaries missed is really there and really different. And `d4_degenerate` names the most extreme case: a dataset whose correlation is entirely an artifact of one point, indistinguishable by the numbers from a genuine linear relationship.

### The running tally

| dataset | correlation | regression line | true shape | is the line honest? |
|---|---|---|---|---|
| d1 | 0.82 | y = 3 + 0.5x | clean linear | yes |
| d2 | 0.82 | y = 3 + 0.5x | parabola | no — misses the curve |
| d3 | 0.82 | y = 3 + 0.5x | linear + outlier | no — dragged by one point |
| d4 | 0.82 | y = 3 + 0.5x | vertical + leverage point | no — fabricated by one point |

<svg viewBox="0 0 700 160" role="img" aria-label="Two rows of bars over the four datasets. Top row 'correlation': all four bars equal height at 0.82. Bottom row 'max residual': bars at 1.92, 1.90, 3.24 (tall), 1.84 — d3 stands out. The top row is flat, the bottom row is not.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="14" fill="var(--muted)">correlation is flat across the four; the shape diagnostic is not</text>
    <text x="20" y="44" fill="var(--ink)">corr</text>
    <g fill="var(--s1)"><rect x="120" y="30" width="60" height="24"></rect><rect x="260" y="30" width="60" height="24"></rect><rect x="400" y="30" width="60" height="24"></rect><rect x="540" y="30" width="60" height="24"></rect></g>
    <g fill="var(--panel)" text-anchor="middle"><text x="150" y="47">.82</text><text x="290" y="47">.82</text><text x="430" y="47">.82</text><text x="570" y="47">.82</text></g>
    <text x="20" y="104" fill="var(--ink)">max resid</text>
    <g fill="var(--s2)"><rect x="120" y="82" width="60" height="30"></rect><rect x="260" y="83" width="60" height="29"></rect><rect x="400" y="61" width="60" height="51"></rect><rect x="540" y="84" width="60" height="28"></rect></g>
    <g fill="var(--panel)" text-anchor="middle"><text x="150" y="102">1.9</text><text x="290" y="102">1.9</text><text x="430" y="80">3.2</text><text x="570" y="102">1.8</text></g>
    <g fill="var(--muted)" text-anchor="middle"><text x="150" y="126">d1</text><text x="290" y="126">d2</text><text x="430" y="126">d3</text><text x="570" y="126">d4</text></g>
    <text x="400" y="150" text-anchor="middle" fill="var(--muted)">the flat top row is what a summary sees; the varied bottom row is the truth it hides</text>
  </g>
</svg>
^ The correlation bars are identical across all four — a flat, uninformative row. The residual bars vary, with d3's outlier spiking to 3.24. A summary that reports only the top row certifies four different datasets as the same.

The correlation and line columns are constant — that is the whole trick — and the shape column is where the datasets actually live. Three of the four make the identical summary a lie: the same "strong linear relationship, slope 0.5" describes a curve, an outlier-distorted trend, and a one-point artifact. This is not a contrived edge case; real data has curves, outliers, and leverage points constantly, and reporting a correlation without looking at the scatter is how an analyst confidently ships the wrong model. Compute the summary, then plot the data, every time.

### What we did not settle

The quartet is a warning, not a method. The general practice it argues for is exploratory data analysis: always visualize before modeling, and pair every summary with a plot. Beyond plotting, the individual failures have diagnostics — residual plots reveal curvature (d2), leverage and influence statistics like Cook's distance flag points that dominate the fit (d3, d4), and robust regression down-weights outliers. Higher-dimensional data cannot be scatter-plotted directly, so the same danger returns in a form where visualization is harder and diagnostics matter more. And the Datasaurus dozen extended Anscombe's idea to datasets that share statistics while forming pictures (including a dinosaur), driving the point home. The rule here — a matching summary is not matching data — is the floor beneath all of exploratory analysis.

## Build

The practice in one paragraph: never conclude from summary statistics alone; plot every dataset before you model it, and pair each correlation or regression line with the scatter that produced it; check the residuals for curvature, the influence statistics for points that dominate the fit, and the spread of x for degeneracy; and remember that any summary is a many-to-one compression, so agreement on summaries is not agreement on data. When you cannot plot — high dimensions — lean harder on residual and influence diagnostics.

We opened on the identical statistics. The number that proves they are hiding something is the shape diagnostic:

```
# modules/ai-for-science-and-data/code/data-inter-06/ — COMPLETE, run from that directory
$ python3 anscombe.py --shape
  d3          3.24          11  linear + one outlier
  d4          1.84           2  vertical line + one leverage point
```

Now do it to your own data. Take a dataset you have summarized with a correlation or a regression line, and plot the scatter — then compute the max residual and the influence of each point. Your number to beat is not the correlation; it is **whether the shape matches what the summary implies: a residual plot with no structure, no single point dominating the fit, and a real spread of x**. Find your curves, outliers, and leverage points. Bring back the scatter and the shape diagnostics. Good luck.

## Definition of done

- [ ] Summary statistics (mean, variance, correlation, regression line) computed for a dataset
- [ ] The dataset actually plotted, not just summarized
- [ ] A shape diagnostic (max residual, or a residual plot) computed
- [ ] The spread of x checked for degeneracy or leverage points
- [ ] Confirmation that matching summaries would not have revealed the shape
- [ ] `python3 anscombe.py --check` printing SELF-TEST PASS: stats-identical, strong-corr, shapes-differ, d4-degenerate
- [ ] A written note of any curvature, outlier, or leverage found only by looking
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. How can four datasets share their mean, variance, correlation, and regression line yet be completely different?
2. All four report correlation 0.82 and slope 0.5. For which one is that summary honest, and what is wrong for each of the others?
3. What is leverage, and how does the fourth dataset's single far-out point manufacture the correlation?
4. Why is a summary statistic a many-to-one compression, and what follows for reasoning from summaries alone?
5. Your own dataset was summarized and plotted. Did the shape match the summary, and what did looking reveal that the numbers did not?

## External resources

- F. J. Anscombe, *Graphs in Statistical Analysis* (1973) — the original paper — my summary: the quartet's construction and Anscombe's argument that computation without graphing is dangerous; read it for the source of this demonstration and its statistical framing.
- Matejka & Fitzmaurice, *Same Stats, Different Graphs* (the Datasaurus dozen, 2017) — my summary: an algorithm that morphs a dataset into arbitrary shapes while holding its summary statistics fixed, extending Anscombe to a dozen (including a dinosaur); read it for how far the identical-stats trick can be pushed.
- This hub, *data-inter-02* — modules/ai-for-science-and-data/data-inter-02.md — my summary: the heavy-tail module, another case where a single summary statistic (the mean) misrepresents the data; read it for the shared discipline — always look at the distribution, never trust one number.
