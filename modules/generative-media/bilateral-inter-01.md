---
id: bilateral-inter-01
title: Weight neighbors by intensity too — or a blur that removes noise also destroys the edge
topic: generative-media
level: intermediate
status: ready
time: 19 min
summary: Smoothing removes noise by averaging each pixel with its neighbors. A Gaussian blur weights those neighbors by distance only, so it happily averages across an edge, mixing a dark pixel with the bright pixels just past it. That is fine in a flat region and destruction at an edge — the sharp step from 10 to 30 smears into a ramp — and you cannot turn the blur up to kill more noise without blurring the edge more. The bilateral filter adds a second weight, range: a neighbor counts only in proportion to how similar its brightness is to the center, so neighbors on the same side of an edge contribute while neighbors across it drop to near-zero weight and are excluded. It smooths within a region but never across an edge. On a signal stepping from ~10 to ~30 with noise, a Gaussian softens the edge step from 20 to 9 while a bilateral keeps it at 18.7, and both smooth the flat-region noise identically.
eli5: To clean up a grainy photo you blend each dot with the dots around it. If you blend without looking, you smear the crisp line between a dark shape and a bright one into mush. The trick is to only blend a dot with nearby dots that are a similar shade — so a dot on the dark side never mixes with the bright side. The line stays sharp and the graininess still gets smoothed away.
---

## Why this module

Averaging a pixel with its neighbors is how you remove noise, and it is also how you destroy edges — the same operation does both, unless you tell it where the edges are.

A Gaussian blur decides each pixel's new value by weighting its neighbors by distance: the nearest count most, farther ones less. In a flat region that is exactly right — the neighbors are all similar, so averaging them cancels the noise. At an edge it is a disaster. The neighbors on the far side of the edge are very different, but distance-only weighting gives them a full vote anyway, so a dark edge pixel gets averaged with the bright pixels across the edge, and the crisp step becomes a soft ramp. Worse, the trade is locked: turning the blur up to remove more noise blurs the edges more, because the filter has no way to tell a noisy flat region from a real edge.

**A distance-only blur cannot distinguish noise from an edge, so any strength that smooths the noise also smears the edge.**

The bilateral filter breaks the trade by adding a second weight — range — that measures how similar a neighbor's brightness is to the center pixel. Neighbors within a region are similar and contribute; neighbors across an edge are dissimilar and are excluded. It smooths within regions and never between them. This module runs both filters on a noisy edge and measures what each keeps.

## Concepts

A **smoothing filter** replaces each pixel with a weighted average of its neighborhood. The weights decide what gets mixed.

The **Gaussian (spatial) weight** depends only on distance — here a `[1, 2, 1]` kernel, the center weighted double. It is applied regardless of the neighbors' values, so it averages across whatever is nearby, edge or not.

The **bilateral filter** multiplies that spatial weight by a **range weight** that depends on the intensity difference between the neighbor and the center. When the difference is small (same region) the range weight is high; when it is large (across an edge) the range weight is near zero, dropping that neighbor from the average. This toy uses a hard cutoff — a neighbor differing by more than a threshold is excluded outright — while a real bilateral filter uses a smooth Gaussian range weight; the mechanism is identical.

The mechanism of edge preservation is the exclusion. At an edge pixel, the across-edge neighbor differs by more than the threshold, so its weight goes to zero and the average is computed only from the same-side neighbors — which are similar, so the pixel barely moves and the edge holds. In a flat region, every neighbor is within threshold, so the bilateral behaves exactly like the Gaussian and smooths the noise.

**The range weight makes the filter refuse to average across a big intensity jump, so it smooths flat noise and leaves edges standing.**

At the edge pixel the two same-side neighbors keep their weight while the across-edge neighbor is zeroed, so the average is computed from one side only.

<svg role="img" aria-label="At the edge pixel valued 10, its left neighbor 10 keeps weight but its right neighbor 30 is dropped because it differs by more than the threshold" viewBox="0 0 300 110" width="300" height="110">
  <rect x="40" y="40" width="40" height="24" fill="var(--s2)"/><text x="52" y="56" fill="var(--panel)" font-size="9">10</text>
  <rect x="90" y="40" width="40" height="24" fill="var(--s2)" stroke="var(--ink)" stroke-width="2"/><text x="100" y="56" fill="var(--panel)" font-size="9">10 ⌂</text>
  <rect x="140" y="40" width="40" height="24" fill="var(--s1)" opacity="0.4" stroke="var(--s1)" stroke-dasharray="3 2"/><text x="150" y="56" fill="var(--ink)" font-size="9">30</text>
  <text x="45" y="80" fill="var(--s2)" font-size="7">diff 0 → keep</text>
  <text x="140" y="80" fill="var(--s1)" font-size="7">diff 20 &gt; 10 → drop</text>
  <text x="40" y="100" fill="var(--muted)" font-size="8">the average uses only same-side neighbors, so the edge pixel barely moves</text>
</svg>
^ The center pixel (⌂) averages with its like-valued left neighbor but not the bright neighbor across the edge, whose weight the range gate sets to zero.

The name says it: bi-lateral, two weightings — one on space, one on range — and the product is a filter that is aggressive within a region and inert across its boundary.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/bilateral-inter-01/bilateral.py

The fixture is a scanline with a step edge and a little noise on each side.

```json filename=modules/generative-media/code/bilateral-inter-01/signal.json:1-6 COMPLETE
{
  "_meta": "A 1D brightness scanline: a flat region around 10 with a little noise, a sharp step up to a flat region around 30 with a little noise. The edge is between index 2 (value 10) and index 3 (value 30). spatial_kernel is a [1,2,1] smoothing weight; range_threshold is the maximum brightness difference for which a neighbor still counts in the bilateral filter (neighbors across the big edge exceed it and are dropped).",
  "signal": [10, 12, 10, 30, 28, 30],
  "spatial_kernel": [1, 2, 1],
  "range_threshold": 10
}
```

The two filters are the same weighted average; the bilateral zeros a neighbor's weight when its intensity differs from the center by more than the threshold.

```python filename=modules/generative-media/code/bilateral-inter-01/bilateral.py:47-60 COMPLETE
def gaussian(sig, kernel, i):
    """Distance-only weights: the [1,2,1] kernel, applied regardless of intensity."""
    l, c, r = neighbors(sig, i)
    wl, wc, wr = kernel
    return (wl * l + wc * c + wr * r) / (wl + wc + wr)


def bilateral(sig, kernel, thresh, i):
    """Distance AND range weights: drop a neighbor whose intensity differs from the center by more than thresh."""
    l, c, r = neighbors(sig, i)
    wl = kernel[0] if abs(l - c) <= thresh else 0
    wc = kernel[1]
    wr = kernel[2] if abs(r - c) <= thresh else 0
    return (wl * l + wc * c + wr * r) / (wl + wc + wr)
```

The neighbor helper replicates at the borders; both filters read the same three values and differ only in the weights.

```python filename=modules/generative-media/code/bilateral-inter-01/bilateral.py:40-44 COMPLETE
def neighbors(sig, i):
    """The left, center, right values, replicating at the borders."""
    left = sig[i - 1] if i > 0 else sig[i]
    right = sig[i + 1] if i < len(sig) - 1 else sig[i]
    return left, sig[i], right
```

Run `--filter` and compare the two outputs.

```text filename=--filter
FILTER — Gaussian blur vs bilateral filter (kernel [1, 2, 1], range 10)
----------------------------------------------------------
  signal:      10.00  12.00  10.00  30.00  28.00  30.00
  gaussian:    10.50  11.00  15.50  24.50  29.00  29.50
  bilateral:   10.50  11.00  10.67  29.33  29.00  29.50
----------------------------------------------------------
  at the edge (index 2,3) the gaussian caves in; the bilateral holds.
```

Look at the edge pixels, index 2 and 3. The Gaussian pulls index 2 from 10 up to 15.50 and index 3 from 30 down to 24.50 — the step has collapsed inward. The bilateral leaves index 2 at 10.67 and index 3 at 29.33 — the step is intact. Away from the edge, the two outputs are identical (10.50, 11.00, 29.00, 29.50): the bilateral only diverges where an edge is present.

<svg role="img" aria-label="Signal steps 10 to 30; the gaussian output ramps gently across the edge while the bilateral output keeps the sharp step" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="20" fill="var(--muted)" font-size="8">signal (sharp step)</text>
  <polyline points="40,95 90,88 140,95 140,30 190,37 240,30" fill="none" stroke="var(--muted)" stroke-width="1.5"/>
  <text x="10" y="55" fill="var(--s1)" font-size="8">gaussian</text>
  <polyline points="40,92 90,90 140,68 190,48 240,33" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="150" y="62" fill="var(--s1)" font-size="7">ramp (edge lost)</text>
  <text x="10" y="120" fill="var(--s2)" font-size="8">bilateral</text>
  <polyline points="40,95 90,90 140,93 190,35 240,33" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="150" y="108" fill="var(--s2)" font-size="7">step kept</text>
</svg>
^ The Gaussian turns the vertical step into a diagonal ramp; the bilateral keeps the step nearly vertical, because it never averaged the two sides together.

## Build

Put numbers on it with `--edge`.

```text filename=--edge
EDGE — step height across the edge, and flat-region smoothing
----------------------------------------------------------
  edge step (index3 - index2): signal 20.00  gaussian 9.00  bilateral 18.66
  flat-noise pixel index1: signal 12.00 -> gaussian 11.00, bilateral 11.00
----------------------------------------------------------
  both smooth the flat noise; only the bilateral keeps the edge step.
```

The edge step was 20. The Gaussian more than halves it to 9.00 — the edge is mostly gone. The bilateral keeps it at 18.66, 93% of the original. And the noise? The flat-region pixel at index 1 was 12 (noise above the local 10); both filters pull it to 11.00. That is the whole point: the bilateral matches the Gaussian on noise removal and beats it completely on the edge, because the two goals only conflict when a filter cannot tell them apart.

<svg role="img" aria-label="Edge step under each filter: signal 20, gaussian 9, bilateral 18.66; flat noise smoothed equally by both" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="14" fill="var(--muted)" font-size="8">edge step retained</text>
  <line x1="70" y1="18" x2="70" y2="70" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="70" x2="285" y2="70" stroke="var(--grid)" stroke-width="1"/>
  <rect x="70" y="22" width="140" height="10" fill="var(--muted)"/><text x="214" y="31" fill="var(--muted)" font-size="8">signal 20</text>
  <rect x="70" y="36" width="63" height="10" fill="var(--s1)"/><text x="137" y="45" fill="var(--s1)" font-size="8">gaussian 9</text>
  <rect x="70" y="50" width="131" height="10" fill="var(--s2)"/><text x="205" y="59" fill="var(--s2)" font-size="8">bilateral 18.7</text>
  <text x="10" y="92" fill="var(--muted)" font-size="8">flat noise pixel: 12 → 11 under BOTH filters</text>
  <text x="10" y="112" fill="var(--muted)" font-size="8">equal on noise, opposite on the edge</text>
</svg>
^ On the edge the bilateral bar nearly matches the original while the Gaussian bar is less than half; on the flat noise the two filters are identical — matched where they should agree, opposite where it counts.

## Definition of done

The self-test pins the split: the Gaussian collapses the edge step, the bilateral keeps it (over 90% of original) and beats the Gaussian, both smooth the flat noise, and the across-edge neighbor genuinely exceeds the range threshold that drops it.

```python filename=modules/generative-media/code/bilateral-inter-01/bilateral.py:109-121 COMPLETE
    gaussian_blurs_edge = g_step < orig_step * 0.6
    print("  the gaussian collapses the edge step = %s (%.2f -> %.2f)" % (gaussian_blurs_edge, orig_step, g_step))

    bilateral_preserves_edge = b_step > orig_step * 0.9
    print("  the bilateral keeps the edge step = %s (%.2f, %.0f%% of original)" % (bilateral_preserves_edge, b_step, 100 * b_step / orig_step))

    bilateral_beats_gaussian_edge = b_step > g_step
    print("  the bilateral edge is sharper than the gaussian = %s (%.2f > %.2f)" % (bilateral_beats_gaussian_edge, b_step, g_step))

    both_smooth_flat = abs(g[1] - 10) < abs(sig[1] - 10) and abs(b[1] - 10) < abs(sig[1] - 10)
    print("  both smooth the flat-region noise pixel = %s (%.2f -> g %.2f, b %.2f)" % (both_smooth_flat, sig[1], g[1], b[1]))

    range_gate_drops_across_edge = abs(sig[3] - sig[2]) > thr
    print("  the across-edge neighbor exceeds the range threshold (dropped) = %s (|30-10|=%d > %d)" % (range_gate_drops_across_edge, abs(sig[3] - sig[2]), thr))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the Gaussian blurs the edge; the bilateral smooths the flat region but preserves the edge
--------------------------------------------------------------------------------------------------------
  the gaussian collapses the edge step = True (20.00 -> 9.00)
  the bilateral keeps the edge step = True (18.66, 93% of original)
  the bilateral edge is sharper than the gaussian = True (18.66 > 9.00)
  both smooth the flat-region noise pixel = True (12.00 -> g 11.00, b 11.00)
  the across-edge neighbor exceeds the range threshold (dropped) = True (|30-10|=20 > 10)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  gaussian_blurs_edge=True  bilateral_preserves_edge=True  bilateral_beats_gaussian_edge=True  both_smooth_flat=True  range_gate_drops_across_edge=True
```

**Done means the edge preservation is measured, not claimed: the bilateral keeps 93% of the 20-unit step while the Gaussian keeps 45%, and both pull the flat-noise pixel to the identical 11.00.**

## Boss fight

The range threshold here is 10, and the edge is 20 — comfortably dropped. Predict what happens to the bilateral filter if you raise the threshold to 25. It is tempting to think a bigger threshold is more forgiving and therefore better.

At threshold 25 the filter stops being edge-preserving, because the across-edge neighbors (differing by 20) now fall within range and are included again — the bilateral collapses back into a plain Gaussian and blurs the edge. The range threshold is exactly the knob that says "how big a jump counts as an edge to protect." Set it too high and every edge is averaged through; set it too low and gentle real gradients get frozen into blocky steps, because even small variations get treated as edges to preserve. The threshold must sit above the noise amplitude and below the edge amplitude, which is why it is tuned to the image, not fixed.

The mirror-image mistake is expecting the bilateral to remove the kind of noise a Gaussian cannot — like a single extreme outlier (salt-and-pepper). A lone bright speck differs sharply from its neighbors, so the bilateral's range weight treats the speck as an edge and preserves it, exactly the wrong move. Impulse noise wants a median filter; the bilateral is for smoothing gentle noise while keeping structure. Each filter defends a different notion of "signal," and using the wrong one keeps the noise you meant to remove.

```python filename=modules/generative-media/code/bilateral-inter-01/bilateral.py:54-60 COMPLETE
def bilateral(sig, kernel, thresh, i):
    """Distance AND range weights: drop a neighbor whose intensity differs from the center by more than thresh."""
    l, c, r = neighbors(sig, i)
    wl = kernel[0] if abs(l - c) <= thresh else 0
    wc = kernel[1]
    wr = kernel[2] if abs(r - c) <= thresh else 0
    return (wl * l + wc * c + wr * r) / (wl + wc + wr)
```

**Weight neighbors by intensity as well as distance so the average never reaches across an edge — and tune the range threshold above the noise and below the edge, because that one number is what separates "smooth" from "protect."**

## External resources

Tomasi and Manduchi, "Bilateral Filtering for Gray and Color Images" (1998) — the paper that introduced the filter, with the Gaussian spatial-times-range weighting this module simplifies.

Paris, Kornprobst, Tumblin, and Durand, "Bilateral Filtering: Theory and Applications" — a survey covering the parameters (spatial and range sigma), fast approximations, and uses like tone mapping and detail enhancement.

The OpenCV `bilateralFilter` documentation — the production function, its `sigmaColor` (range) and `sigmaSpace` (spatial) arguments, and guidance on choosing them, alongside `GaussianBlur` and `medianBlur` for comparison.
