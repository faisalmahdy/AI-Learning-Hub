---
id: media-inter-03
title: Downsample with a filter, or fine texture aliases into a false artifact
topic: generative-media
level: intermediate
status: ready
time: 8-10h
summary: Halving an image row by keeping every other pixel is decimation, and on detail finer than the new grid it does not lose the detail — it aliases, folding it into a false low-frequency artifact, so a one-pixel checkerboard texture sampled every other pixel always lands on the same phase and becomes a fake uniform brightness shift of +5 rather than averaging to gray. A box filter — average each pair before decimating — cancels the texture and recovers the smooth gradient exactly, zero error against the ideal, while naive decimation carries 200 units of aliased energy. The lesson is that you must low-pass filter before you downsample, which is exactly why every correct image resize and audio downsample filters first.
eli5: If you shrink a photo of a striped shirt by just skipping pixels, the stripes do not smoothly blur — they turn into weird bands or a flat wrong color that was never there. That is aliasing. The fix is to blur a little first, averaging neighbours together, so the fine stripes melt into the right average color before you shrink. Blur, then shrink — never just shrink.
---

## Why this module

Resizing images is everywhere in a generative-media pipeline: thumbnails, model input resolutions, preview grids, downscaling a generation to ship it. The naive way to halve resolution — keep every other pixel — is wrong in a way that is invisible on smooth images and glaring on textured ones, and the failure is not a blur or a loss but the appearance of structure that was never in the scene. This module builds the failure on a single image row, measures the false artifact it creates, and builds the one-line fix that every correct resize uses.

The phenomenon is aliasing. An image grid can only represent detail up to a certain fineness — the Nyquist limit, half the sampling rate. Detail finer than that, when you sample it, does not disappear; it masquerades as coarser detail, folding down into a low frequency that looks real but is fabricated. A one-pixel-wide checkerboard texture is exactly at that limit, and if you decimate by keeping every other pixel, you always sample the same phase of the checker, so instead of the texture averaging away to a neutral gray it becomes a constant brightness offset — a flat, false shift the scene never had. The fix is to low-pass filter before decimating: average each group of pixels so the fine texture cancels and only the coarse structure the new grid can hold survives. That pre-filter is not optional polish; it is the difference between a correct downsample and a corrupted one.

You need no prior module, only the idea of an image as numbers. Everything runs offline against a signal fixture — one 16-pixel row, a smooth gradient plus a fine checkerboard — stdlib Python 3, `$0.00`. The instinct to unlearn is that shrinking an image just means keeping fewer pixels. Keeping fewer pixels without filtering first invents detail; the pixels you keep must be averages of the pixels you drop.

Here are the two downsamples against the truth:

```
# modules/generative-media/code/media-inter-03/ — COMPLETE, run from that directory
$ python3 alias.py --downsample

DOWNSAMPLE — halve the row: naive decimation vs box filter (factor=2)
------------------------------------------------------------------
  input row (16 px): [6, -4, 10, 0, 14, 4, 18, 8, 22, 12, 26, 16, 30, 20, 34, 24]
  ideal (scene avg): [1.0, 5.0, 9.0, 13.0, 17.0, 21.0, 25.0, 29.0]
  naive decimate:    [6, 10, 14, 18, 22, 26, 30, 34]
  box filtered:      [1.0, 5.0, 9.0, 13.0, 17.0, 21.0, 25.0, 29.0]
```

run: 2026-08-26 · deterministic; signal is a fixture · 16 px → 8 px · `python3 alias.py --downsample`

The box-filtered row equals the ideal exactly; the naive row is the same shape shifted up by 5 everywhere — the checkerboard texture, aliased into a false brightness. This module is that offset and where it comes from.

## Concepts

Named here so you can find them again; each is built below.

- **Decimation** — downsampling by keeping every Nth pixel and discarding the rest; no filtering.
- **Aliasing** — detail finer than the new grid folding into a false low-frequency artifact.
- **Nyquist limit** — the finest detail a sampling grid can represent; half the sampling rate.
- **Low-pass filter** — smoothing that removes detail too fine to survive, before downsampling.
- **Box filter** — the simplest low-pass: average each group of pixels.
- **Ideal downsample** — the real scene (its coarse content) averaged per output pixel; the target.

## Worked example

Source: the resampling step every image library performs (Pillow, OpenCV, and the mip-mapping in every GPU), and the sampling theorem beneath it, reduced to one row; the gradient-plus-checker signal here stands in for a real textured image so the aliasing error is exact and checkable.

Script and fixture: `modules/generative-media/code/media-inter-03/` — `alias.py`, and `signal.json`, a 16-pixel row given as a smooth `gradient` plus a fine `checker`, with their sum as the actual `row`. Every command runs from there.

### The scene: coarse structure plus fine texture

The row is two things added together. The gradient — `0, 2, 4, …, 30` — is the real scene, coarse enough to survive at half resolution. The checker — `+6, -6, +6, -6, …` — is a one-pixel texture, too fine to represent in the smaller image, which a correct downsample should average away to nothing. Their sum is the pixels the camera actually recorded.

<svg viewBox="0 0 700 190" role="img" aria-label="A 16-pixel row shown as bars. The underlying gradient rises smoothly left to right. The checker adds a plus-6, minus-6 zigzag on top, so the actual pixels alternate high and low around the rising gradient. Below, an arrow marks 'sample every other pixel' hitting only the plus-6 phase.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">the row = smooth gradient + fine checker (+6/-6)</text>
    <line x1="40" y1="120" x2="660" y2="120" stroke="var(--grid)"></line>
    <polyline points="52,120 90,112 128,104 166,96 204,88 242,80 280,72 318,64 356,56 394,48 432,40 470,32 508,24 546,16 584,8 622,0" fill="none" stroke="var(--muted)" stroke-dasharray="3 2" transform="translate(0,40)"></polyline>
    <text x="360" y="150" fill="var(--muted)" font-size="8">dashed = the gradient (real scene); bars = gradient+checker (recorded pixels)</text>
    <g fill="var(--s1)"><rect x="48" y="112" width="8" height="8"></rect><rect x="124" y="104" width="8" height="8"></rect><rect x="200" y="96" width="8" height="8"></rect><rect x="276" y="88" width="8" height="8"></rect><rect x="352" y="80" width="8" height="8"></rect><rect x="428" y="72" width="8" height="8"></rect><rect x="504" y="64" width="8" height="8"></rect><rect x="580" y="56" width="8" height="8"></rect></g>
    <text x="60" y="178" fill="var(--s1)" font-size="8">naive samples only these (every other pixel — all the +6 phase)</text>
  </g>
</svg>
^ The dashed line is the scene we want to keep; the checker rides on top of it. Naive decimation samples only the marked pixels — and because the checker has period two, those are all the same `+6` phase, so the texture never cancels.

### The naive way: keep every other pixel

Decimation is the obvious downsample and the wrong one.

```
# alias.py:39-41 — COMPLETE (naive decimation: keep every factor-th pixel)
def decimate(row, factor):
    """Naive: keep every `factor`-th pixel, discard the rest. No filtering -> aliasing."""
    return [row[i] for i in range(0, len(row), factor)]
```

Because it keeps pixels 0, 2, 4, … and the checker is `+6` at every even index, every kept pixel carries the same `+6` from the texture. The texture, which should have averaged to zero, instead becomes a constant `+6`-ish offset baked into the output. That is aliasing in its simplest form: a frequency at the Nyquist limit folds all the way down to zero frequency — a DC shift — and rides out looking like a real change in scene brightness.

### The correct way: average, then decimate

A box filter averages each group before collapsing it, so the texture cancels.

```
# alias.py:44-51 — COMPLETE (box filter: average each group, that average is the pixel)
def box_downsample(row, factor):
    """Correct: average each group of `factor` pixels (low-pass), then that IS the pixel."""
    out = []
    for i in range(0, len(row), factor):
        group = row[i:i + factor]
        out.append(sum(group) / len(group))
    return out
```

<svg viewBox="0 0 700 160" role="img" aria-label="Two adjacent pixels: the first is gradient plus 6, the second is gradient minus 6. Naive keeps only the first, carrying the plus 6. Box averages them: the plus 6 and minus 6 cancel, leaving the gradient average, no texture.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">one output pixel from two inputs: keep-one vs average</text>
    <rect x="60" y="34" width="120" height="30" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="120" y="53" text-anchor="middle" fill="var(--ink)" font-size="8">px0 = grad +6</text>
    <rect x="200" y="34" width="120" height="30" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="260" y="53" text-anchor="middle" fill="var(--ink)" font-size="8">px1 = grad -6</text>
    <text x="60" y="96" fill="var(--s2)" font-size="9">naive: keep px0 -> grad +6</text><text x="360" y="96" fill="var(--s2)" font-size="8">the +6 texture rides through (alias)</text>
    <text x="60" y="126" fill="var(--s1)" font-size="9">box: (px0+px1)/2 -> grad</text><text x="360" y="126" fill="var(--s1)" font-size="8">+6 and -6 cancel; only the scene remains</text>
  </g>
</svg>
^ Keeping one pixel carries whichever checker phase it landed on; averaging the pair cancels the `+6` against the `-6` and leaves the gradient. The cancellation is why the filter must come before the discard, not after.

Averaging pixels 0 and 1 gives `(gradient + 6) + (gradient - 6)` over two — the `+6` and `-6` cancel exactly, leaving the gradient's local average. The checker is gone, the coarse structure remains, and the result equals the ideal downsample of the scene. One extra operation, averaging before discarding, is the entire difference between aliasing and not.

### Measuring the artifact

The ideal is the target we score against: the real scene, with no texture, averaged per output pixel — which is just the box filter applied to the gradient alone.

```
# alias.py:53-55 — COMPLETE (the target: the coarse scene averaged per output pixel)
def ideal_downsample(gradient, factor):
    """The right answer: the scene (gradient only, no texture) averaged per output pixel."""
    return box_downsample(gradient, factor)
```

Score each method against that ideal.

```
# alias.py:64-65 — COMPLETE (aliased content: squared deviation from the ideal)
def alias_energy(result, ideal):
    """Total squared deviation of a downsample from the ideal -- the aliased content."""
    return sum((x - y) ** 2 for x, y in zip(result, ideal))
```

The two errors are not close:

```
# $ python3 alias.py --error
#   naive decimate: max abs error = 5.0   alias energy = 200.0
#   box filtered:   max abs error = 0.0   alias energy = 0.0
```

run: 2026-08-26 · deterministic · `python3 alias.py --error`

The box filter has zero error and zero aliased energy — a perfect recovery of the scene. Naive decimation has a max error of 5 and 200 units of alias energy, all of it the checker texture folded into the output as a false signal. And that error is systematic, not noise: it is the same offset at every output pixel, which is what makes it so deceptive — it looks exactly like the scene really was a little brighter, not like corruption.

<svg viewBox="0 0 700 180" role="img" aria-label="Two downsampled rows plotted against the ideal. The ideal and the box-filtered line coincide, rising smoothly. The naive decimated line runs parallel above them, shifted up by a constant 5 at every point.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">downsampled output vs the ideal scene</text>
    <line x1="50" y1="150" x2="650" y2="150" stroke="var(--grid)"></line>
    <line x1="50" y1="30" x2="50" y2="150" stroke="var(--grid)"></line>
    <polyline points="90,142 160,126 230,110 300,94 370,78 440,62 510,46 580,30" fill="none" stroke="var(--s1)" stroke-width="3"></polyline>
    <text x="400" y="76" fill="var(--s1)" font-size="8">ideal = box filtered (exact)</text>
    <polyline points="90,122 160,106 230,90 300,74 370,58 440,42 510,26 580,12" fill="none" stroke="var(--s2)" stroke-width="2" stroke-dasharray="5 3"></polyline>
    <text x="360" y="30" fill="var(--s2)" font-size="8">naive: shifted up by 5 everywhere (the alias)</text>
    <text x="90" y="170" fill="var(--muted)" font-size="8">the two lines never converge — the offset is constant, a false brightness</text>
  </g>
</svg>
^ The box-filtered output lands exactly on the ideal; the naive output is a parallel line shifted up by the aliased texture. A constant gap that never closes is the signature of a Nyquist-frequency detail folding to DC.

**Downsampling keeps fewer pixels, but the pixels you keep must be averages of the pixels you drop — decimate without a low-pass filter and detail finer than the new grid aliases into a false low-frequency artifact, here a checkerboard texture becoming a phantom brightness shift.**

### The self-test

The `--check` mode asserts the recovery and the failure: box filtering matches the ideal exactly, naive decimation carries a large error, that error is a systematic offset, and box filtering removes the aliased energy.

```
# $ python3 alias.py --check
#   box filter recovers the ideal exactly = True (max err 0.0000)
#   naive decimation carries a large alias error = True (max err 5.0)
#   the alias error is a systematic offset (a false brightness shift) = True (5.0 everywhere)
#   box filtering removes the aliased energy = True (0.0 < 200.0)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 alias.py --check`

The `box_exact` line is the correctness anchor: the filtered downsample must equal the ideal to floating-point tolerance, and if a refactor broke the averaging that assertion would fail first. The `systematic` line names why aliasing is dangerous rather than merely wrong — the error is identical at every pixel, indistinguishable from a real property of the scene, so nothing downstream would flag it as corruption.

### The running tally

| method | max error vs ideal | alias energy | what happened |
|---|---|---|---|
| box filter (average, then decimate) | 0.0 | 0.0 | texture cancelled, scene recovered |
| naive decimate (keep every other) | 5.0 | 200.0 | texture aliased to a false brightness |

The two rows are one operation apart — whether you average before you discard. The box filter spends one addition and one division per output pixel and gets the scene exactly; decimation skips that and fabricates a signal. There is no regime where naive decimation of textured content is acceptable; the only reason it is ever shipped is that on smooth images, where there is no fine texture to alias, it happens to look fine — which is exactly how the bug survives to production.

### What we did not settle

A box filter is the cheapest low-pass, not the best. It has its own frequency response with leakage, so high-quality resizers use better kernels — triangle (bilinear), cubic, Lanczos — that trade sharpness against ringing. Two dimensions need the filter applied both horizontally and vertically, and separable kernels do this efficiently. Non-integer scale factors need interpolation between filtered samples, not just grouping. And upsampling has the dual problem — inventing detail you do not have, where the filter's job is to avoid blocky artifacts. The principle here — filter to the target resolution before you resample — is the invariant under all of them; only the filter shape changes.

## Build

The practice in one paragraph: never downsample by dropping pixels; low-pass filter to the target resolution first, so detail too fine to represent is averaged out rather than aliased in, then take the filtered samples; measure the result against the ideal (the coarse scene averaged per output pixel) and check the aliased energy is near zero; and remember the failure hides on smooth content and appears on texture, so test on a textured image, not a gradient. Use a better kernel than a box when quality matters, but always filter.

We opened on the two downsamples. The number that proves the filter works is the error against the ideal:

```
# modules/generative-media/code/media-inter-03/ — COMPLETE, run from that directory
$ python3 alias.py --error
  naive decimate: max abs error = 5.0   alias energy = 200.0
  box filtered:   max abs error = 0.0   alias energy = 0.0
```

Now do it to a real image. Take a textured photo — fabric, foliage, a brick wall — and downsample it two ways: drop every other pixel, and box-filter then decimate. Your number to beat is not sharpness; it is **the aliased energy, the squared difference from a properly filtered reference, which naive decimation inflates and filtering drives toward zero**. Look for moiré or false banding in the naive version. Bring back both downsamples and the energy gap. Good luck.

## Definition of done

- [ ] A textured signal or image with detail finer than the target resolution
- [ ] Naive decimation (keep every Nth pixel) implemented
- [ ] Box-filter-then-decimate implemented
- [ ] Both scored against the ideal downsample of the coarse scene
- [ ] Confirmation the filtered result matches the ideal and decimation carries an alias error
- [ ] The alias error shown to be systematic (a false artifact), not random noise
- [ ] `python3 alias.py --check` printing SELF-TEST PASS: box-exact, naive-aliases, systematic, energy-removed
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What is aliasing, and why does a one-pixel checkerboard become a constant brightness shift under naive decimation rather than just disappearing?
2. What does a low-pass filter do before downsampling, and why is it not optional?
3. The box filter recovered the scene exactly here. Explain the cancellation that made the texture vanish.
4. Why is the aliasing error more dangerous than a simple blur or brightness change would be?
5. Your own textured image was downsampled both ways. What was the aliased-energy gap, and where did you see moiré or false structure in the naive version?

## External resources

- Nyquist–Shannon sampling theorem (any signal-processing reference) — my summary: the theorem that fixes the finest detail a grid can represent and predicts exactly how finer detail folds down; read it for why the checker at the Nyquist limit aliases to DC and what the general folding rule is.
- Pillow / OpenCV resize documentation on resampling filters — my summary: the production resizers and their kernel options (nearest, bilinear, bicubic, Lanczos), where "nearest" is the decimation this module warns against; read it for the better filters and when each is worth its cost.
- This hub, *media-inter-02* — modules/generative-media/media-inter-02.md — my summary: the other generative-media module about what survives a transform of an image (perceptual hashing under brightness shifts); read it for the shared theme — which information a downstream operation preserves versus destroys, and measuring it rather than assuming.
