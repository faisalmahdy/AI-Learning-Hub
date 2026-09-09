---
id: aliasing-inter-01
title: Low-pass filter before you decimate — dropping every Nth pixel aliases fine detail into a false pattern that flips with phase
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Downsampling means representing an image on a coarser grid, and the tempting way is decimation — keep every Nth pixel, throw the rest away. It is fast and it is wrong whenever the image holds detail finer than the new grid can represent. A pixel grid can only carry frequencies up to half its sampling rate (the Nyquist limit); a coarser grid drops that limit, so any pattern above the new limit cannot be represented — and decimation does not discard it, it aliases it, folding the high frequency down into a false low frequency that was never in the scene. A fine checker becomes broad bands (moiré), a striped shirt shimmers on video, and the smooth gray the eye would have blended appears as a bold wrong pattern. Worse, the aliased result is not even stable: it depends on the sub-pixel phase, on where the coarse grid lands, so a one-pixel shift can flip it from solid white to solid black. The fix is to remove the too-fine frequencies before decimating with a low-pass filter — the simplest being a box filter that averages each group of N pixels, exactly the area an output pixel covers — so the checker correctly becomes its mean and the result no longer depends on phase. On a fixture row of alternating 255,0 pixels, decimating by 2 yields all 255 at phase 0 and all 0 at phase 1 (both wrong), while box-filtering each pair yields 127.5 everywhere, the true average, regardless of phase.
eli5: Imagine a fence with very thin, closely spaced posts, and you photograph it from far away with a camera that can only record a few dots across. If each dot just grabs whatever happens to be right at that spot, you might catch all posts (looks solid) or all gaps (looks empty) or a weird wide striping that isn't really on the fence — and which one you get depends on exactly where you stood. That fake pattern is aliasing. The fix is to let each dot record the AVERAGE of everything in its little area, not one spot — then thin posts correctly blur to a smooth gray, and it doesn't matter where you stood.
---

## Why this module

Shrinking an image feels like it should only lose a little detail, gracefully. Done by the obvious method — keep every Nth pixel — it does something worse: it invents structure that was never there, a moiré or a shimmer, and the exact false pattern you get changes if the image shifts by a single pixel. The bug is not that detail is lost; it is that lost detail comes back disguised as a lie.

Downsampling an image means representing it on a coarser grid of pixels, and the tempting way to do it is decimation: keep every Nth pixel and throw the rest away. It is fast, it is one line, and it is wrong whenever the image contains detail finer than the new grid can represent. A grid of pixels can only represent frequencies up to half its sampling rate — the Nyquist limit — so make the grid coarser and that limit drops, and any pattern that was fine enough to sit above the new limit cannot be represented. Decimation does not drop it; it aliases it, folding that high frequency down into a false low frequency that was never in the scene. A fine checkerboard becomes broad bands, a picket fence photographed at the wrong scale becomes a few thick posts, a striped shirt on video shimmers with color. The signal the eye would have blended to a smooth gray instead turns into a bold, wrong pattern.

The worst part is that the aliased result is not even a stable wrong answer: it depends on the sub-pixel phase, on exactly where the coarse sampling grid happens to land. Shift the grid by one input pixel and the same fine pattern decimates to a completely different output. The fix is to remove the frequencies the new grid cannot hold before you decimate, by low-pass filtering. The simplest low-pass filter is a box filter: average each group of N pixels, exactly the area the output pixel covers, so the output is the true average of what it represents — the fine checker correctly becomes its mean gray, and because every group is fully averaged, the result no longer depends on phase. This module downsamples an alternating row both ways and shows the alias and its phase-dependence.

**Decimating (keeping every Nth pixel) without a low-pass pre-filter aliases detail above the new Nyquist limit into a false pattern that also depends on sub-pixel phase, so band-limit first with a filter — a box filter averages each group to its true value, which is correct and phase-stable.**

## Concepts

**Decimation** keeps one sample per group and discards the rest — reading a single arbitrary pixel to stand for the whole area it now covers, which is exactly why it aliases.

```python filename=modules/generative-media/code/aliasing-inter-01/aliasing.py:49-51 COMPLETE
def decimate(signal, factor, phase=0):
    """Downsample by keeping every factor-th sample starting at `phase` -- no pre-filter (the aliasing bug)."""
    return signal[phase::factor]
```

**Box downsampling** averages each group of N pixels first, then takes one per group. The average is a low-pass filter: it removes the fine variation the coarse grid cannot hold, so what remains is representable.

```python filename=modules/generative-media/code/aliasing-inter-01/aliasing.py:54-56 COMPLETE
def box_downsample(signal, factor):
    """Downsample by averaging each group of `factor` samples first (a box low-pass), then taking one per group."""
    return [sum(signal[i:i + factor]) / factor for i in range(0, len(signal), factor)]
```

<svg role="img" aria-label="A fine alternating checker of pixels sampled by a coarse grid: the grid lands on either all the white pixels or all the black ones, producing a solid color, while averaging each pair gives gray" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">a coarse grid can't hold the fine checker — it reads one per pair</text>
  <g transform="translate(20,22)">
  <rect x="0" y="0" width="16" height="16" fill="var(--panel)" stroke="var(--line)"/><rect x="16" y="0" width="16" height="16" fill="var(--ink)"/><rect x="32" y="0" width="16" height="16" fill="var(--panel)" stroke="var(--line)"/><rect x="48" y="0" width="16" height="16" fill="var(--ink)"/><rect x="64" y="0" width="16" height="16" fill="var(--panel)" stroke="var(--line)"/><rect x="80" y="0" width="16" height="16" fill="var(--ink)"/>
  <text x="0" y="-2" fill="var(--muted)" font-size="6">input row (255,0,255,0,…)</text>
  </g>
  <text x="130" y="34" fill="var(--muted)" font-size="7">grid samples ↓ one per pair</text>
  <g transform="translate(20,56)">
  <rect x="0" y="0" width="32" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="34" y="0" width="32" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="68" y="0" width="32" height="14" fill="var(--panel)" stroke="var(--line)"/>
  <text x="104" y="10" fill="var(--muted)" font-size="7">decimate → solid (aliased)</text>
  </g>
  <g transform="translate(20,80)">
  <rect x="0" y="0" width="32" height="14" fill="var(--muted)"/><rect x="34" y="0" width="32" height="14" fill="var(--muted)"/><rect x="68" y="0" width="32" height="14" fill="var(--muted)"/>
  <text x="104" y="10" fill="var(--muted)" font-size="7">box filter → gray (correct)</text>
  </g>
</svg>
^ The coarse grid takes one sample per pair of the fine checker, so decimation reports a solid color; averaging each pair (the box filter) reports the mid-gray the pattern actually blends to.

**Decimation reads one pixel to represent a whole group, so a pattern finer than the group aliases; a box filter averages the group, band-limiting the signal so the output represents what the pixel actually covers.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/aliasing-inter-01/aliasing.py

The fixture is the finest pattern a pixel row can hold — alternating white and black — downsampled by 2.

```json filename=modules/generative-media/code/aliasing-inter-01/aliasing.json:3-4 COMPLETE
  "signal": [255, 0, 255, 0, 255, 0, 255, 0],
  "factor": 2
```

Run `--downsample` to shrink it both ways.

```text filename=--downsample
DOWNSAMPLE — decimate vs box-filter, factor 2
------------------------------------------------------------
  input row              = [255, 0, 255, 0, 255, 0, 255, 0]
  decimate (phase 0)     = [255, 255, 255, 255]   <- solid white: aliased
  box-filter then take   = [127.5, 127.5, 127.5, 127.5]   <- 127.5 mid-gray: correct
```

The input is a fine checker that a person, or a correct resizer, would blend to a uniform mid-gray — 127.5, the average of 255 and 0. Decimation by 2 keeps pixels 0, 2, 4, 6, which in this phase are all the 255s, so it returns solid white: `[255, 255, 255, 255]`. The fine pattern did not shrink to gray; it aliased to the brightest possible constant, a value that appears nowhere as an average of the scene. Box-filtering averages each pair — `(255+0)/2 = 127.5` — before taking one per pair, so it returns `[127.5, 127.5, 127.5, 127.5]`, the true gray. The two results are not close: one is the correct average of the region, the other is a solid color that misrepresents it completely. And the failure is not specific to a checker — any texture, hair, foliage, or text fine enough to approach the new pixel spacing will alias the same way, which is why a naively downscaled photo of a brick wall or a distant crowd fills with moiré that was never in the original.

<svg role="img" aria-label="A high-frequency wave above the Nyquist limit, and the coarse samples of it that trace out a false low-frequency wave — the moiré pattern aliasing creates" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">a frequency above Nyquist folds down to a false low frequency</text>
  <line x1="10" y1="50" x2="290" y2="50" stroke="var(--line)"/>
  <path d="M10,50 Q17,26 24,50 T38,50 T52,50 T66,50 T80,50 T94,50 T108,50 T122,50 T136,50 T150,50 T164,50 T178,50 T192,50 T206,50 T220,50 T234,50 T248,50 T262,50 T276,50" fill="none" stroke="var(--s2)" stroke-width="0.8"/>
  <text x="180" y="24" fill="var(--muted)" font-size="7">true signal (fine)</text>
  <g fill="var(--ink)">
  <circle cx="10" cy="50" r="2"/><circle cx="45" cy="38" r="2"/><circle cx="80" cy="50" r="2"/><circle cx="115" cy="62" r="2"/><circle cx="150" cy="50" r="2"/><circle cx="185" cy="38" r="2"/><circle cx="220" cy="50" r="2"/><circle cx="255" cy="62" r="2"/>
  </g>
  <path d="M10,50 Q45,38 80,50 T150,50 T220,50 T290,50" fill="none" stroke="var(--s1)"/>
  <text x="120" y="86" fill="var(--muted)" font-size="7">coarse samples (dots) trace a false slow wave — moiré</text>
</svg>
^ The coarse samples of a too-fine signal do not reconstruct it; they connect into a false low-frequency wave that was never present — the frequency-folding that turns fine texture into broad moiré bands when you decimate without filtering.

## Build

The decimated answer is worse than merely wrong — it is unrepeatable, because it depends on where the grid lands. Run `--phase`.

```text filename=--phase
PHASE — decimation depends on where the grid lands; the box filter does not
--------------------------------------------------------------
  decimate phase 0 = [255, 255, 255, 255]
  decimate phase 1 = [0, 0, 0, 0]
  box-filter       = [127.5, 127.5, 127.5, 127.5]   (same regardless of phase)
```

The only change between the two decimation lines is the starting offset: phase 0 keeps pixels 0, 2, 4, 6 (all white), phase 1 keeps pixels 1, 3, 5, 7 (all black). Same input, same downsample factor, and the output flips from solid white to solid black on a one-pixel shift. That is aliasing's signature: the result is not a property of the image, it is an artifact of the arbitrary alignment between the fine pattern and the coarse grid, so panning the image or shifting the crop by a single pixel makes the whole region jump between colors — the shimmer you see when a striped surface moves slowly on screen. The box filter returns 127.5 in both cases and would in every phase, because it averages the entire group rather than sampling one point of it; it has no phase to depend on. That phase-stability is the correct average shown against the aliased constants.

```python filename=modules/generative-media/code/aliasing-inter-01/aliasing.py:59-61 COMPLETE
def average(signal):
    """The true average level of the row -- what a correctly-downsampled uniform region should approach."""
    return sum(signal) / len(signal)
```

<svg role="img" aria-label="Decimation at phase 0 gives solid white, at phase 1 gives solid black, while the box filter gives gray in both phases" viewBox="0 0 300 112" width="300" height="112">
  <text x="6" y="12" fill="var(--muted)" font-size="8">one-pixel shift flips the alias; the box filter is stable</text>
  <text x="10" y="32" fill="var(--muted)" font-size="7">decimate φ0</text>
  <g transform="translate(80,22)"><rect x="0" y="0" width="120" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="204" y="11" fill="var(--muted)" font-size="7">solid white 255</text></g>
  <text x="10" y="58" fill="var(--muted)" font-size="7">decimate φ1</text>
  <g transform="translate(80,48)"><rect x="0" y="0" width="120" height="14" fill="var(--ink)"/><text x="204" y="11" fill="var(--muted)" font-size="7">solid black 0</text></g>
  <text x="10" y="84" fill="var(--muted)" font-size="7">box filter</text>
  <g transform="translate(80,74)"><rect x="0" y="0" width="120" height="14" fill="var(--muted)"/><text x="204" y="11" fill="var(--muted)" font-size="7">gray 127.5 (any φ)</text></g>
  <text x="10" y="104" fill="var(--muted)" font-size="7">the aliased result is an artifact of grid alignment, not of the image</text>
</svg>
^ Decimation returns solid white at phase 0 and solid black at phase 1 — the wrong answer even flips — while the box filter returns 127.5 at every phase, because averaging the whole group leaves no alignment to depend on.

## Definition of done

The self-test pins the aliasing, the phase-dependence, and the box filter's correct, stable average.

```python filename=modules/generative-media/code/aliasing-inter-01/aliasing.py:94-103 COMPLETE
    d0 = decimate(sig, f, 0)
    decimate_aliases_constant = len(set(d0)) == 1 and d0[0] != average(sig)
    print("  decimation collapses the checker to a single wrong value = %s (%s)" % (decimate_aliases_constant, d0))

    d1 = decimate(sig, f, 1)
    phase_dependent = d0 != d1
    print("  a one-pixel phase shift changes the aliased result = %s (%s vs %s)" % (phase_dependent, d0[0], d1[0]))

    box = box_downsample(sig, f)
    box_is_true_average = all(abs(v - average(sig)) < 1e-9 for v in box)
    print("  the box filter yields the true average everywhere = %s (%.1f)" % (box_is_true_average, box[0]))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — decimation aliases to a phase-dependent constant; the box filter preserves the true average and is phase-stable
--------------------------------------------------------------------------------------------------------------------------
  decimation collapses the checker to a single wrong value = True ([255, 255, 255, 255])
  a one-pixel phase shift changes the aliased result = True (255 vs 0)
  the box filter yields the true average everywhere = True (127.5)
  the box-filtered result does not depend on phase = True
  the true average of the row is 127.5 = True
```

**Done means the alias and its fix are proven on real values: decimation collapses the alternating checker to a single wrong constant (all 255) that flips to all 0 under a one-pixel phase shift, while the box filter returns the true average 127.5 everywhere and does not depend on phase — so downsampling must low-pass filter before decimating, or it aliases fine detail into a false, unstable pattern.**

## Boss fight

Predict two ways this is deeper than "average before you shrink," because the right filter depends on the factor and the failure connects to the other resize rules.

The first trap is that the pre-filter must match the downsample factor and be a good filter, not just any average — because band-limiting is a claim about frequency, and a too-narrow or too-crude filter still leaves artifacts. A box filter averaging N pixels is the minimal fix for a factor-of-N downsample, but it is a weak low-pass: it passes some frequencies it should cut (its frequency response has ripples), so it reduces aliasing without eliminating it, and high-quality resamplers use better kernels (Lanczos, Gaussian, cubic) that approximate an ideal low-pass more closely. Crucially, the filter width must scale with the downsample factor: shrinking by 4× requires averaging over 4-pixel neighborhoods, not 2, because the new Nyquist limit is four times lower and there is four times as much high-frequency content to remove. This is why downsampling by repeatedly halving with a filter at each step (mipmap generation) is common: each halving is a factor-2 box or better, and the chain band-limits correctly at every level, whereas a single naive stride-by-4 aliases badly. Get the filter width wrong for the factor and you either alias (too narrow) or blur more than necessary (too wide).

The second trap is that this is one of three separate correctness rules a resize must obey together, and doing this one alone is not enough. Downsampling with transparency must premultiply alpha before averaging (the premultiplied-alpha module) or edges fringe; downsampling gamma-encoded pixels must linearize before averaging (the gamma module) or the result darkens; and downsampling any detailed image must low-pass before decimating (this module) or it aliases. A fully correct downscale therefore linearizes, premultiplies, low-pass filters, decimates, un-premultiplies, and re-encodes — three averaging disciplines stacked, each guarding a different artifact (dark blends, colored fringes, false patterns), and skipping any one produces its signature defect. And the same sampling theorem runs in the other direction too: aliasing appears not just on downscale but wherever a continuous or high-resolution signal is sampled too coarsely — rendering thin lines, rasterizing text, sampling a texture in 3D at a distance — which is why anti-aliasing (supersampling, MSAA, mipmapped texture filtering) exists throughout graphics. The unifying rule is the sampling theorem: never sample a signal that has not first been band-limited to below half your sampling rate, whether you are shrinking a photo, drawing a line, or fetching a texel.

**The low-pass filter must scale its width to the downsample factor (a box is the minimal fix; Lanczos/Gaussian are better, and repeated filtered halving/mipmaps band-limit correctly at each level), and it is only one of three stacked resize rules — linearize (gamma), premultiply (alpha), and band-limit (this) — each guarding a different artifact; more broadly it is the sampling theorem, so any too-coarse sampling (downscaling, rasterizing lines or text, distant textures) needs anti-aliasing, i.e. band-limit before you sample.**

## External resources

Any signal-processing or computer-graphics reference on the sampling theorem and aliasing — the Nyquist limit, why decimation without a low-pass filter aliases, and the filters (box, Gaussian, Lanczos) used to band-limit before downsampling.

Writing on image resampling and mipmapping — why the pre-filter width scales with the downsample factor, why repeated filtered halving avoids the single-step aliasing, and how texture filtering applies the same idea in 3D rendering.

The companion gamma and premultiplied-alpha modules in this topic — a correct downscale stacks all three averaging rules (linearize, premultiply, band-limit), each preventing a different resize artifact.
