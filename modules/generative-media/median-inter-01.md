---
id: median-inter-01
title: Remove salt-and-pepper noise with a median filter — a mean filter smears the speck and blurs the edge
topic: generative-media
level: intermediate
status: ready
time: 21 min
summary: Impulse noise is a single pixel jammed to pure white or black. A mean (box) filter is the wrong tool twice: it spreads the outlier into every window it touches (one bad pixel becomes a smudge) and blurs every real edge. The median filter is a rank statistic — it picks the middle value, so a lone outlier is never selected and a true edge passes through unblurred. On a row with a 10-to-80 step and a 200 speck, the mean filter leaves total error 236.7; the median filter leaves 0.0.
eli5: If one person in a group shouts a crazy wrong number, averaging everyone's answers gets dragged toward the crazy number. But if you line the answers up and take the middle one, the shouter is ignored completely. A median filter does that for pixels — a single blown-out speck is thrown away, and real edges stay crisp.
---

## Why this module

A single blown-out pixel is best deleted, not blurred, and blurring it makes two problems where there was one.

Impulse noise — salt and pepper — is a pixel stuck at an extreme: pure white (salt) or pure black (pepper), wildly far from everything around it. It comes from a dead sensor cell, a bit flip in transmission, a compression glitch. The natural instinct is to smooth it away with a mean filter (a box blur), replacing each pixel with the average of its neighborhood. That instinct fails for impulse noise, and it fails twice.

First, averaging does not remove the outlier; it spreads it. A lone 200 sitting among 10s gets pulled into the average of every window that overlaps it — so a 3-wide mean turns one bad pixel into three pixels of about 73. The speck did not disappear; it smeared into a smudge, and now three pixels are wrong instead of one. The extreme value still contributes its full weight to each average; the mean has no defense against an outlier, because an outlier is exactly what a mean is most sensitive to.

Second, the same averaging blurs every real edge. A mean filter straddling a light-to-dark boundary returns a value halfway between the two sides, so a crisp step from 10 to 80 becomes a gradual ramp through the intermediate values. You wanted to remove a defect and you softened the actual structure of the image instead. A mean filter cannot tell a noise spike from a real edge — both are large local changes — so it damages both.

The median filter fixes both problems with one change: take the median of the neighborhood, not the mean. On the fixture, a row of pixels has a clean step from 10 to 80 and one salt speck — a 200 where a 10 should be. The mean filter leaves total error 236.7: it smears the speck across three pixels and softens the step to 33 and 57. The median filter leaves total error 0.0 — the speck is gone and the step is exactly 10-to-80, pixel for pixel.

**Impulse noise is a single extreme pixel, and a mean filter both spreads it into a smudge and blurs real edges; the median filter, a rank statistic, discards the lone outlier and passes true edges through unblurred.**

## Concepts

The median works because it is a rank statistic, not an arithmetic one. To take a median you sort the values in the window and pick the middle one; the actual magnitudes of the others never enter the result, only their order. So a single value that is the largest or smallest in its window — which is exactly what a salt or pepper speck is — sits at an end of the sorted list and is never the middle element. It is discarded by construction. The mean, by contrast, sums every value, so the more extreme an outlier is, the more it moves the result. One 200 barely nudges a median and completely dominates a mean; that difference is the whole reason the median filter exists.

<svg role="img" aria-label="A window of three values 10, 200, 10: the mean sums to 73 pulled up by the outlier, the median sorts and picks the middle 10, ignoring the outlier" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">one window [10, 200, 10]: mean vs median</text>
  <g fill="var(--muted)"><rect x="40" y="50" width="40" height="26"/><rect x="90" y="50" width="40" height="26"/><rect x="140" y="50" width="40" height="26"/></g>
  <text x="52" y="68" font-family="var(--mono)" font-size="10" fill="var(--ink)">10</text>
  <text x="98" y="68" font-family="var(--mono)" font-size="10" fill="var(--ink)">200</text>
  <text x="152" y="68" font-family="var(--mono)" font-size="10" fill="var(--ink)">10</text>
  <text x="200" y="42" font-family="var(--mono)" font-size="9" fill="var(--s2)">mean = (10+200+10)/3</text>
  <rect x="200" y="50" width="60" height="26" fill="var(--s2)"/>
  <text x="212" y="68" font-family="var(--mono)" font-size="10" fill="var(--panel)">73.3</text>
  <text x="280" y="68" font-family="var(--mono)" font-size="8" fill="var(--s2)">dragged up by the 200</text>
  <text x="40" y="112" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">median = sort [10, 10, 200] → pick middle</text>
  <g fill="var(--muted)"><rect x="40" y="120" width="40" height="26"/><rect x="90" y="120" width="40" height="26"/><rect x="140" y="120" width="40" height="26"/></g>
  <rect x="90" y="120" width="40" height="26" fill="var(--acc-line)"/>
  <text x="52" y="138" font-family="var(--mono)" font-size="10" fill="var(--ink)">10</text>
  <text x="102" y="138" font-family="var(--mono)" font-size="10" fill="var(--panel)">10</text>
  <text x="150" y="138" font-family="var(--mono)" font-size="10" fill="var(--ink)">200</text>
  <text x="200" y="138" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">the 200 sits at the end, never chosen → 10</text>
</svg>
^ The mean adds all three so the 200 drags it to 73.3; the median sorts and takes the middle, where the 200 sits harmlessly at the end and the result is a true 10.

Edge preservation falls out of the same property. Consider a window centered near a step edge, containing some pixels from the dark side and some from the light side. The median of that mixed window is whichever side has more members — a value that actually occurs on one side of the edge, not an average that occurs on neither. As the window slides across the boundary, the median jumps cleanly from the dark value to the light value at the crossover, reproducing the step. The mean, summing across the boundary, returns in-between values that blur the transition. The median keeps edges because it always outputs a real sample from the neighborhood, never a manufactured intermediate.

This makes the median filter nonlinear, which is why it can do something no linear filter can. Every linear filter — box blur, Gaussian, any convolution — computes a weighted sum of inputs, and a weighted sum cannot both reject an outlier and preserve a step, because those require ignoring an extreme value in one case and following it in another, and a fixed set of weights does the same thing to every window. The median's behavior depends on the values themselves (through their ranks), so it can treat a lone spike and a genuine edge differently. That data-dependence is the source of its power and also why it has no impulse response and does not obey superposition — it is genuinely not a convolution.

The trade-offs are worth naming. The median is the right tool specifically for impulse noise; for Gaussian (fine, everywhere) noise a linear blur is usually better, because there the noise is not a rare outlier but a small perturbation on every pixel, and averaging genuinely reduces it. The median also has costs: it requires a sort per window (more expensive than a sum), it can round off fine corners and thin lines that are narrower than half the window, and a very large window will erase small real features along with the noise. As with any filter, the window size trades noise removal against detail loss — but for knocking out sparse specks while keeping edges crisp, nothing linear competes.

**The median is a rank statistic, so it discards the extreme value a speck represents and outputs a real neighborhood sample rather than an average — which is why it removes impulses and preserves edges, and why, being nonlinear, it does something no convolution can.**

## Worked example

The fixture is a row of pixels with a real edge and one speck.

```json filename=modules/generative-media/code/median-inter-01/row.json:3-7 COMPLETE
  "clean": [10, 10, 10, 10, 80, 80, 80, 80],
  "speck_index": 1,
  "speck_value": 200,
  "edge_index": 4,
  "window": 3
```

A clean step from 10 to 80 between indices 3 and 4, with a salt speck of 200 dropped at index 1. The window is 3 — each pixel plus its two neighbors, edges extended. The two filters differ in one line: the mean averages the window, the median sorts it and takes the middle.

```python filename=modules/generative-media/code/median-inter-01/median.py:50-59 COMPLETE
def mean_filter(row, half):
    return [sum(window(row, i, half)) / (2 * half + 1) for i in range(len(row))]


def median_filter(row, half):
    out = []
    for i in range(len(row)):
        w = sorted(window(row, i, half))
        out.append(w[len(w) // 2])
    return out
```

Both filters share one window helper, which extends the edge pixel for out-of-bounds indices so the filter is defined at the ends.

```python filename=modules/generative-media/code/median-inter-01/median.py:41-47 COMPLETE
def at(row, i):
    """Clamp out-of-bounds indices to the edge pixel (edge-extend padding)."""
    return row[min(max(i, 0), len(row) - 1)]


def window(row, i, half):
    return [at(row, j) for j in range(i - half, i + half + 1)]
```

Predict: the mean will drag the 200 into the three windows around index 1 (turning them to ~73) and will soften the step at indices 3-4; the median will drop the 200 entirely and keep the step sharp. Run it.

```text filename=modules/generative-media/code/median-inter-01/median.py --filter
FILTER — one row of pixels (window 3), clean vs noisy vs filtered
--------------------------------------------------------------
  clean:   [ 10.0  10.0  10.0  10.0  80.0  80.0  80.0  80.0]
  noisy:   [ 10.0 200.0  10.0  10.0  80.0  80.0  80.0  80.0]   (speck of 200 at index 1)
  mean:    [ 73.3  73.3  73.3  33.3  56.7  80.0  80.0  80.0]
  median:  [ 10.0  10.0  10.0  10.0  80.0  80.0  80.0  80.0]
```

The mean row is wrong in five places. The speck at index 1 became three pixels of 73.3 (indices 0, 1, 2) — the outlier smeared across its whole neighborhood. And the step got blurred: index 3 dropped to 33.3 and index 4 to 56.7, so the sharp 10-to-80 boundary became a ramp. The median row is the clean row, exactly — every pixel restored. The 200 was the largest value in each window it appeared in, so it was never the middle element and never selected; the step survived because the median of a window straddling the edge is a real value from one side.

<svg role="img" aria-label="The noisy row's speck spike and edge; the mean output spreads the spike into a bump and ramps the edge; the median output matches the clean step exactly" viewBox="0 0 470 200" width="470" height="200">
  <rect x="0" y="0" width="470" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">pixel value across the row (speck at index 1, edge at 3-4)</text>
  <line x1="30" y1="170" x2="450" y2="170" stroke="var(--line)"/>
  <polyline points="55,163 105,40 155,163 205,163 255,107 305,107 355,107 405,107" fill="none" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3 3"/>
  <text x="95" y="36" font-family="var(--mono)" font-size="8" fill="var(--muted)">noisy: 200 speck</text>
  <polyline points="55,116 105,116 155,116 205,146 255,132 305,107 355,107 405,107" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <text x="70" y="108" font-family="var(--mono)" font-size="8" fill="var(--s2)">mean: bump + ramped edge</text>
  <polyline points="55,163 105,163 155,163 205,163 255,107 305,107 355,107 405,107" fill="none" stroke="var(--acc-line)" stroke-width="2"/>
  <text x="300" y="150" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">median: clean step restored</text>
  <text x="45" y="185" font-family="var(--mono)" font-size="8" fill="var(--muted)">0</text>
  <text x="395" y="185" font-family="var(--mono)" font-size="8" fill="var(--muted)">7</text>
</svg>
^ The mean output (solid, upper) turns the speck into a broad bump and slopes the edge; the median output (solid, lower) lies exactly on the clean step, speck gone and boundary intact.

## Build

Reproduce the filters. Pure standard library, deterministic, so the 236.7 mean error and the 0.0 median error come out exactly.

Run `--filter` for the rows, `--error` for the per-pixel error against clean, `--check` for the gate. The error view shows where each filter goes wrong.

```text filename=modules/generative-media/code/median-inter-01/median.py --error
ERROR — absolute error against the clean row
--------------------------------------------------------------
  mean err:   [ 63.3  63.3  63.3  23.3  23.3   0.0   0.0   0.0]   total 236.7
  median err: [  0.0   0.0   0.0   0.0   0.0   0.0   0.0   0.0]   total 0.0
--------------------------------------------------------------
  the mean spreads the speck's error across pixels; the median leaves none.
```

<svg role="img" aria-label="Per-pixel absolute error bars: the mean has three tall bars at the speck and two shorter ones at the edge; the median has no bars at all" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">absolute error per pixel (index 0..7)</text>
  <line x1="30" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <text x="60" y="36" font-family="var(--mono)" font-size="9" fill="var(--s2)">mean (total 236.7)</text>
  <g fill="var(--s2)"><rect x="45" y="55" width="34" height="95"/><rect x="95" y="55" width="34" height="95"/><rect x="145" y="55" width="34" height="95"/><rect x="195" y="115" width="34" height="35"/><rect x="245" y="115" width="34" height="35"/></g>
  <text x="60" y="70" font-family="var(--mono)" font-size="7" fill="var(--panel)">speck</text>
  <text x="200" y="130" font-family="var(--mono)" font-size="7" fill="var(--panel)">edge</text>
  <text x="330" y="150" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">median (total 0.0): no bars</text>
  <line x1="300" y1="150" x2="440" y2="150" stroke="var(--acc-line)" stroke-width="3"/>
</svg>
^ The mean's error stands in two groups — three tall bars where the speck smeared and two at the blurred edge — while the median's error is a flat line on zero.

The mean error has two clusters — three pixels near the speck (63.3 each) and two at the edge (23.3 each) — the two failures made visible. The median error is zero everywhere. The self-test pins both failures of the mean and both wins of the median.

```python filename=modules/generative-media/code/median-inter-01/median.py:110-113 COMPLETE
    median_removes_speck = md[si] == 0
    print("  median restores the speck pixel exactly = %s (%.1f vs clean %.1f)" % (median_removes_speck, median_out[si], clean[si]))

    mean_smears_speck = sum(1 for i in range(len(clean)) if abs(i - si) <= half and me[i] > 1) >= 2
    print("  mean spreads the speck's error to multiple pixels = %s (%d affected)"
          % (mean_smears_speck, sum(1 for i in range(len(clean)) if abs(i - si) <= half and me[i] > 1)))
```

The edge-preservation flags read the two pixels straddling the boundary and demand the median restore them exactly while the mean does not.

```python filename=modules/generative-media/code/median-inter-01/median.py:117-120 COMPLETE
    median_keeps_edge = md[ei] == 0 and md[ei - 1] == 0
    print("  median preserves the edge exactly = %s (%.1f, %.1f)" % (median_keeps_edge, median_out[ei - 1], median_out[ei]))

    mean_blurs_edge = me[ei] > 1
    print("  mean blurs the edge = %s (edge error %.1f)" % (mean_blurs_edge, me[ei]))
```

```text filename=modules/generative-media/code/median-inter-01/median.py --check
SELF-TEST — the mean filter smears the speck and blurs the edge; the median removes it and keeps the edge
----------------------------------------------------------------------------------------------------------
  median restores the speck pixel exactly = True (10.0 vs clean 10.0)
  mean spreads the speck's error to multiple pixels = True (3 affected)
  median preserves the edge exactly = True (10.0, 80.0)
  mean blurs the edge = True (edge error 23.3)
  median's total error beats the mean's = True (0.0 vs 236.7)
----------------------------------------------------------------------------------------------------------
SELF-TEST PASS  median_removes_speck=True  mean_smears_speck=True  median_keeps_edge=True  mean_blurs_edge=True  median_beats_mean=True
```

Five True flags. Median_removes_speck: the median restores the speck pixel to exactly 10. Mean_smears_speck: the mean spreads the speck's error to 3 pixels. Median_keeps_edge: the median reproduces the 10 and 80 across the boundary exactly. Mean_blurs_edge: the mean puts 23.3 of error on the edge. Median_beats_mean: total error 0.0 versus 236.7. The pairing is the lesson — the mean fails on both the speck and the edge, the median wins on both, because one is a data-blind sum and the other a rank statistic.

**The two mean-error clusters — three pixels at the speck, two at the edge — are the two failures a mean filter cannot avoid, and the all-zero median error is the proof a rank statistic escapes both at once.**

## Definition of done

You are done when you reproduce both filters and can explain why the median removes the speck and keeps the edge.

Concretely: `--filter` shows the mean turning the speck into three pixels of 73.3 and ramping the edge to 33.3 and 56.7, while the median reproduces the clean row exactly; `--error` shows total error 236.7 versus 0.0; `--check` prints PASS with five True flags. You can explain that the median is a rank statistic that discards the extreme value a speck represents, that it outputs a real neighborhood sample so an edge survives as a clean step, and that being nonlinear it can treat a spike and an edge differently in a way no convolution can. You can also state when not to use it: for Gaussian noise a linear blur is usually better, and a too-large median window rounds off fine detail.

The habit to carry: reach for a median filter when the noise is sparse and extreme (dead pixels, salt-and-pepper, dropout), and a linear blur when the noise is fine and everywhere. When a denoise step leaves smudges where single bad pixels were, or softens edges you meant to keep, suspect you averaged where you should have taken a median. Match the filter to the noise's shape, not to habit.

## Boss fight

The instructive failure is a "denoise" pass that makes a speckled scan look worse.

A document-scanning pipeline has salt-and-pepper speckle from a dusty sensor, and someone adds a Gaussian blur to clean it. The output is worse: every speck is now a soft gray blob instead of a sharp black dot, the specks are more visible rather than less, and the crisp text edges have gone fuzzy so OCR accuracy drops. The blur spread each impulse over its neighborhood and softened the strokes it was supposed to preserve — exactly the two failures this module shows. The fix is a median filter sized to the speck: it deletes each isolated speck outright (an isolated dot is always the extreme in its window) and leaves the text edges sharp, so the page looks clean and OCR improves.

Your turn, two moves. First, add pepper as well as salt — drop a 0 somewhere on the light (80) side — and confirm the median removes both a high and a low impulse (each is an extreme in its window, so each is discarded), while the mean smears both; impulse noise of either polarity is the median's home ground. Second, stress the edge case: put two adjacent specks (a clump of two 200s) and shrink the window to 3, then confirm the median no longer fully removes them, because with two outliers in a 3-window the median can be an outlier — the rule is that a length-w median survives fewer than w/2 outliers per window, so a wider window is needed for denser noise, at the cost of more detail loss.

## External resources

Any image-processing text (Gonzalez and Woods, "Digital Image Processing") covers median and order-statistic filters, with the salt-and-pepper example and the analysis of how many outliers a given window can reject.

The original median-filter work in signal processing (Tukey introduced running medians for time series) frames it as a robust, edge-preserving smoother, and reading it shows the rank-statistic idea outside of images.

Comparisons of median with edge-preserving successors (the bilateral filter, non-local means, and modern learned denoisers) show where the simple median stops and why: those methods generalize "average only over similar nearby values," which is the same instinct — do not average across an edge — carried further.
