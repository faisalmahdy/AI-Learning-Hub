---
id: ringing-inter-01
title: Cubic interpolation overshoots at a sharp edge — the sharpness that beats bilinear is the same ringing that needs clamping
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Upscaling an image invents new samples between the known pixels, and the interpolation choice is a tradeoff. Linear interpolation (bilinear in 2-D) takes a weighted average of the two nearest samples with non-negative weights summing to one — a convex combination — so every interpolated value lies between the samples that produced it, making it safe (it can never leave the surrounding pixels' range) and soft (averaging blurs). Cubic interpolation (bicubic, Catmull-Rom, Lanczos) fits a higher-order curve through more neighbors to recover sharpness, and that sharpness comes from a kernel with negative lobes — weights that go below zero. Those negative weights make it no longer a convex combination, and they let the fitted curve overshoot: at a high-contrast edge the interpolated values swing below the darker sample and above the brighter one, a ring — a bright halo just past a dark-to-light edge and a dark halo just before it — that can push pixel values outside the valid [0, 255] range and must be clamped. The overshoot is not a bug; it is the inherent, unavoidable cost of the sharper kernel, and clamping removes the out-of-range values without removing the ring, just flattening it at the extremes. So the real choice is a tradeoff: linear is soft but monotone (no ringing), cubic is sharp but rings and needs clamping. On a fixture where a 0-to-255 step edge is interpolated, cubic reaches about 272.9 (above 255) and about −17.9 (below 0) — a ring roughly 7% of the range past each side — while linear stays within [0, 255].
eli5: When you stretch a picture bigger, the computer has to guess the colors for the new dots it adds between the old ones. One way (linear) just blends the two nearest dots, so the guess is always somewhere between them — smooth, but a little blurry. A fancier way (cubic) looks at more neighbors and draws a curve to keep edges crisp, but to make the curve sharp it has to swing a bit too far right at edges — a little brighter than the brightest dot just after an edge, a little darker than the darkest just before it. That overshoot shows up as a faint glowing outline (a "ring" or halo) around sharp edges, and sometimes the guess goes past pure white or pure black, so you have to clip it back. The crispness and the halo are the same thing — you can't get one without the other.
---

## Why this module

Choosing an interpolation kernel feels like choosing "how good" the upscale is, with cubic simply better than linear. It is not a quality axis; it is a tradeoff axis, and the two ends trade opposite artifacts. The reason is mathematical and worth seeing directly: linear interpolation is a convex combination — the interpolated value is a weighted average with weights that are non-negative and sum to one — and a convex combination of numbers can never fall outside their range. That is exactly why bilinear upscaling is safe and also why it is soft: an average pulls toward the middle, which blurs edges.

Cubic interpolation buys back sharpness by fitting a curve through four neighbors instead of averaging two, and the curve is sharp because its kernel dips negative between its main lobe and its tails. Those negative weights are precisely what breaks the convex-combination guarantee. When the curve crosses a high-contrast edge, the negative lobes pull it past the samples — below the dark side and above the bright side — producing an overshoot. That overshoot is visible as a ring or halo hugging the edge, and it can exceed the pixel range, requiring a clamp back into [0, 255].

The key realization is that the sharpness and the ringing are the same property: you cannot have a kernel that sharpens edges without one that overshoots them. This module interpolates a step edge both ways and measures the overshoot.

**Cubic interpolation's sharpness comes from a kernel with negative lobes, which is not a convex combination — so it overshoots the sample range at an edge (ringing, and out-of-range values needing clamping) where linear interpolation, a convex combination, stays contained; the crispness and the ring are inseparable.**

## Concepts

The fixture is a step edge — three samples at 0, then three at 255.

```json filename=modules/generative-media/code/ringing-inter-01/ringing.json:3-3 COMPLETE
  "samples": [0, 0, 0, 255, 255, 255]
```

Two interpolators. Catmull-Rom cubic fits a curve between the two middle samples using all four neighbors — the standard sharp kernel. Linear is the convex combination of the two nearest samples. `interpolate` evaluates both at quarter positions across every interior interval.

```python filename=modules/generative-media/code/ringing-inter-01/ringing.py:32-52 COMPLETE
def catmull_rom(p0, p1, p2, p3, t):
    """Cubic interpolation between p1 and p2 (t in [0,1]) using neighbors p0, p3."""
    return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)


def linear(p1, p2, t):
    """Linear interpolation between p1 and p2 -- a convex combination."""
    return p1 * (1 - t) + p2 * t


def interpolate(samples):
    """Interpolate at t = 0.25, 0.5, 0.75 in every interior interval; return (position, cubic, linear)."""
    out = []
    for i in range(1, len(samples) - 2):
        for k in (1, 2, 3):
            t = k / 4
            out.append((i + t,
                        catmull_rom(samples[i - 1], samples[i], samples[i + 1], samples[i + 2], t),
                        linear(samples[i], samples[i + 1], t)))
    return out
```

The cubic formula's coefficients include subtractions of neighbors — the negative lobes — while the linear formula is `p1*(1-t) + p2*t`, two non-negative weights. That structural difference is what produces or prevents the overshoot.

<svg role="img" aria-label="A step edge from 0 to 255: linear interpolation rises monotonically between the samples, while cubic interpolation dips below 0 before the edge and rises above 255 after it, the ringing overshoot" viewBox="0 0 320 140">
  <line x1="30" y1="20" x2="30" y2="120" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="120" x2="300" y2="120" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="40" x2="300" y2="40" stroke="var(--line)" stroke-width="0.5" stroke-dasharray="2 2"/><text x="2" y="42" font-size="7" fill="var(--muted)">255</text>
  <line x1="30" y1="100" x2="300" y2="100" stroke="var(--line)" stroke-width="0.5" stroke-dasharray="2 2"/><text x="10" y="102" font-size="7" fill="var(--muted)">0</text>
  <polyline points="40,100 120,100 160,40 240,40 290,40" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="200" y="52" font-size="7" fill="var(--s1)">linear (monotone)</text>
  <path d="M 40 100 L 110 100 Q 130 112 150 104 L 160 40 Q 180 28 200 34 L 290 40" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <circle cx="135" cy="110" r="2.5" fill="var(--s2)"/><text x="96" y="126" font-size="7" fill="var(--s2)">undershoot &lt; 0</text>
  <circle cx="185" cy="30" r="2.5" fill="var(--s2)"/><text x="190" y="26" font-size="7" fill="var(--s2)">overshoot &gt; 255</text>
</svg>
^ Across the 0-to-255 step, linear interpolation rises straight between the samples and stays within the band. Cubic interpolation dips below 0 just before the edge and rises above 255 just after — the ring. The two bulges past the dashed limits are the overshoot the negative lobes create.

**The cubic kernel subtracts neighbor values (its negative lobes), so it is not a convex combination and can overshoot; the linear kernel is two non-negative weights and cannot.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the resampling step of an image upscaler, reduced to a 1-D step edge so every interpolated value is checkable by hand.

Run `--interp` to see the values across the edge.

```text filename=ringing.py --interp
  position   cubic      linear     cubic out of range?
  1.25       -5.98      0.00       yes  <- OUT OF RANGE
  1.50       -15.94     0.00       yes  <- OUT OF RANGE
  1.75       -17.93     0.00       yes  <- OUT OF RANGE
  2.25       51.80      63.75      no
  2.50       127.50     127.50     no
  2.75       203.20     191.25     no
  3.25       272.93     255.00     yes  <- OUT OF RANGE
  3.50       270.94     255.00     yes  <- OUT OF RANGE
  3.75       260.98     255.00     yes  <- OUT OF RANGE
```

In the interval just before the edge (positions 1.25–1.75), the samples on both sides are 0, so linear returns 0 — flat. Cubic, anticipating the coming rise, dips negative, down to −17.93: a dark undershoot below the darkest sample. In the interval just after the edge (3.25–3.75), both samples are 255, so linear returns 255, while cubic overshoots up to 272.93 — a bright halo above the brightest sample. Right at the edge (2.25–2.75) the two are close, with cubic slightly steeper (203.20 vs 191.25 at 2.75) — that extra steepness is the sharpness. The over/undershoot and the sharpness are the same curve.

Now `--range` takes the extremes of each interpolant.

```python filename=modules/generative-media/code/ringing-inter-01/ringing.py:74-75 COMPLETE
    cmin, cmax = min(c for _, c, _ in pts), max(c for _, c, _ in pts)
    lmin, lmax = min(l for _, _, l in pts), max(l for _, _, l in pts)
```

Only one of them leaves the sample range.

```text filename=ringing.py --range
  cubic  interp range = [-17.93, 272.93]   overshoot 17.93 past each side
  linear interp range = [0.00, 255.00]
```

Cubic's interpolated values span −17.93 to 272.93 — about 7% of the range past each end. Linear's span exactly [0, 255], the sample range, because a convex combination cannot leave it. The 17.93 of overshoot on each side is the ring, and the parts of it outside [0, 255] must be clamped before the image can be stored or displayed; clamping flattens those tips at 0 and 255 but the halo band leading up to them remains.

<svg role="img" aria-label="Range bars: cubic interpolation spans -17.93 to 272.93, exceeding the sample range on both sides, while linear spans exactly 0 to 255" viewBox="0 0 320 110">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">interpolated value range vs samples [0, 255]</text>
  <line x1="60" y1="24" x2="60" y2="90" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="46" y="102" font-size="7" fill="var(--muted)">0</text>
  <line x1="250" y1="24" x2="250" y2="90" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="240" y="102" font-size="7" fill="var(--muted)">255</text>
  <text x="10" y="40" font-size="8" fill="var(--s2)">cubic</text>
  <rect x="47" y="32" width="217" height="12" fill="var(--s2)"/><text x="266" y="42" font-size="7" fill="var(--s2)">−18 … 273</text>
  <text x="10" y="66" font-size="8" fill="var(--s1)">linear</text>
  <rect x="60" y="58" width="190" height="12" fill="var(--s1)"/><text x="200" y="80" font-size="7" fill="var(--s1)">0 … 255 (contained)</text>
  <text x="10" y="104" font-size="7.5" fill="var(--ink)">cubic spills past both dashed limits — the ring that needs clamping</text>
</svg>
^ Cubic's range spills past both dashed sample limits — that spill is the ring, and its out-of-bounds portions need clamping. Linear's range sits exactly on [0, 255] because a convex combination is confined to its inputs.

**Cubic interpolation spans [−17.93, 272.93], overshooting the sample range by about 7% on each side, while linear spans exactly [0, 255] — the overshoot is the ring, and its out-of-range parts must be clamped.**

## Build

The self-test establishes that all inputs are in range, then that cubic exceeds the max sample and drops below the min.

```python filename=modules/generative-media/code/ringing-inter-01/ringing.py:93-100 COMPLETE
    samples_in_range = all(lo <= s <= hi for s in samples)
    print("  every input sample is within [%d, %d] = %s" % (lo, hi, samples_in_range))

    cubic_overshoots_high = cmax > hi
    print("  cubic interpolation exceeds the max sample = %s (%.2f > %d)" % (cubic_overshoots_high, cmax, hi))

    cubic_undershoots_low = cmin < lo
    print("  cubic interpolation drops below the min sample = %s (%.2f < %d)" % (cubic_undershoots_low, cmin, lo))
```

Then the contrast and the point: linear stays within the sample range, and the overshoot appears even though every input was in range — so it is inherent to the kernel, not caused by bad data.

```python filename=modules/generative-media/code/ringing-inter-01/ringing.py:102-106 COMPLETE
    linear_stays_in_range = lo <= lmin and lmax <= hi
    print("  linear interpolation stays within the sample range = %s ([%.2f, %.2f])" % (linear_stays_in_range, lmin, lmax))

    overshoot_inherent = cubic_overshoots_high and samples_in_range
    print("  the overshoot appears even though all samples are in range (it is inherent) = %s" % overshoot_inherent)
```

Running the check confirms every clause.

```text filename=ringing.py --check
  every input sample is within [0, 255] = True
  cubic interpolation exceeds the max sample = True (272.93 > 255)
  cubic interpolation drops below the min sample = True (-17.93 < 0)
  linear interpolation stays within the sample range = True ([0.00, 255.00])
  the overshoot appears even though all samples are in range (it is inherent) = True
```

**The check shows cubic exceeding the range on both sides from in-range inputs while linear stays contained — proving the overshoot is a property of the sharp kernel, the same property that makes it sharp.**

## Definition of done

Done means cubic interpolation is shown to overshoot the sample range on both sides while linear stays within it, from inputs that are all in range. The clause tying the overshoot to in-range inputs is the crux: it rules out "the data was bad" and pins the ringing on the kernel itself, which is what makes it a tradeoff to understand rather than a bug to fix.

Two clarifications make this actionable. First, the overshoot is not a defect to eliminate but a knob to choose, and the choice depends on the content. Cubic and Lanczos give sharper, more detailed upscales and are the right default for photographic images, where a little edge halo is invisible and the extra sharpness is worth it; the out-of-range values are simply clamped to the valid range. Linear (or area-averaging for downscaling) is better where ringing is unacceptable — a hard-edged logo, a UI element, a medical or scientific image where a halo could be read as signal — because its monotonicity guarantees no invented over/undershoot. Lanczos has stronger negative lobes than cubic and so rings more but sharpens more; the family trades the same way. Second, the same overshoot is why you clamp after cubic interpolation and, in some pipelines, why interpolation for values that must stay bounded (an alpha channel, a depth map, a normalized field) is done with a non-overshooting kernel or clamped immediately — an out-of-[0,1] alpha or a negative depth from ringing can break downstream math, not just look wrong. The rule is to match the kernel to the content and to clamp cubic results into the valid range.

<svg role="img" aria-label="A decision: photographic content prefers cubic or Lanczos for sharpness with clamping, hard-edged or bounded content prefers linear to avoid ringing" viewBox="0 0 320 118">
  <rect x="14" y="22" width="140" height="40" fill="none" stroke="var(--s2)"/>
  <text x="22" y="37" font-size="7.5" fill="var(--s2)">photos, natural images</text>
  <text x="22" y="49" font-size="7" fill="var(--ink)">cubic / Lanczos (sharp),</text>
  <text x="22" y="58" font-size="7" fill="var(--ink)">clamp to [0, 255]</text>
  <rect x="166" y="22" width="140" height="40" fill="none" stroke="var(--s1)"/>
  <text x="174" y="37" font-size="7.5" fill="var(--s1)">logos, UI, bounded fields</text>
  <text x="174" y="49" font-size="7" fill="var(--ink)">linear (no ringing),</text>
  <text x="174" y="58" font-size="7" fill="var(--ink)">monotone, safe</text>
  <text x="14" y="82" font-size="7.5" fill="var(--muted)">match the kernel to the content; the ring is a choice, not a defect</text>
  <text x="14" y="102" font-size="7.5" fill="var(--ink)">always clamp cubic output; use non-overshooting kernels for alpha/depth</text>
</svg>
^ The kernel is a content-dependent choice: cubic or Lanczos for photographic sharpness (clamped), linear for hard edges and bounded fields where ringing would corrupt the signal. The overshoot is inherent to the sharp kernels, so clamp their output and avoid them where over/undershoot breaks downstream math.

**Done means cubic overshoots the range from in-range inputs while linear stays contained — so the kernel is a content-dependent tradeoff (cubic/Lanczos sharp-but-ringing, linear soft-but-monotone), with cubic output clamped and non-overshooting kernels used where values must stay bounded.**

## Boss fight

A team upgrades their thumbnail pipeline from bilinear to bicubic resizing for sharper images. Most thumbnails look better, but for images containing hard-edged graphics — logos, screenshots, charts — reviewers notice faint bright and dark outlines hugging the high-contrast edges, and a few pixels near pure-white edges look "wrong." What is causing the outlines, and how would you handle it?

The outlines are ringing from the bicubic kernel's overshoot. Bicubic interpolation is sharp because its kernel has negative lobes, which means at a high-contrast edge the interpolated values swing past the samples — brighter than the brightest pixel just past a dark-to-light edge and darker than the darkest just before it — producing the bright and dark halo bands the reviewers see. On hard-edged graphics those edges are frequent and high-contrast, so the ringing is pronounced and obvious, whereas on photographs the edges are softer and the halo blends in, which is why only the graphics look wrong. The "wrong" pixels near pure white are the overshoot exceeding 255 and being clamped, flattening the tip of the ring at white. This is inherent to bicubic, not a bug to patch out of the kernel. How to handle it: make the interpolation content-aware. Keep bicubic (or Lanczos, if even more sharpness is wanted, accepting more ringing) for photographic thumbnails where the extra crispness helps and the halo is invisible, and always clamp its output into the valid range. But route hard-edged content — logos, screenshots, charts, anything with large flat regions and sharp boundaries — to bilinear (or area-averaging for downscaling), whose convex-combination property guarantees no ringing, trading a little softness for clean edges. If content type is not known in advance, a reasonable heuristic is to detect high-edge-contrast images or offer per-asset overrides. The general principle: cubic's sharpness and its ringing are the same property, so the kernel is a per-content choice, and the artifact you can tolerate — softness or halos — decides which kernel is correct for a given image.

## External resources

Signal-processing and graphics references on interpolation kernels (the Mitchell-Netravali family of cubic filters, Catmull-Rom, and Lanczos resampling) — how the negative lobes that sharpen a kernel also cause overshoot, and the classic B-parameter/C-parameter tradeoff between blurring and ringing.

Documentation for image-resampling filters in imaging libraries (Pillow's `BICUBIC`, `LANCZOS`, and `BILINEAR`, and the resize-filter guidance in ImageMagick and GPU samplers) — the practical selection of a filter by content, the need to clamp cubic/Lanczos output, and why bilinear or box filters are preferred where ringing is unacceptable.
