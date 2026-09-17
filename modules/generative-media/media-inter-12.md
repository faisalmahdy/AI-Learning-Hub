---
id: media-inter-12
title: Upsample with bilinear interpolation, not nearest-neighbor — nearest only copies pixels and comes out blocky
topic: generative-media
level: intermediate
status: ready
time: 20 min
summary: Enlarging an image invents pixels between the old ones. Nearest-neighbor copies each from the closest sample, so the output is a staircase that emits only the original values and jumps between them. Bilinear blends the two nearest samples, filling the gaps smoothly. On a 4× upscale, nearest's biggest jump is the full 60-unit coarse gap; bilinear cuts it to 15 — the gap over the factor.
eli5: To stretch a short row of dots into a long one, you have to make up the dots in between. The lazy way copies each new dot from the nearest old one, so you get chunky blocks. The smooth way slides gradually from one old dot to the next, filling the gaps with in-between values, so it looks like a smooth ramp instead of stairs.
---

## Why this module

Every time you enlarge an image you are inventing pixels that were never measured, and the rule you use to invent them is the difference between a smooth result and a blocky one.

Upscaling maps a small grid of known samples onto a larger grid, and most of the larger grid's positions fall *between* the known samples, where there is no measured value. Something has to fill them. Nearest-neighbor upsampling fills each new position by copying the closest original sample — the simplest possible rule, and it produces a staircase: a run of new pixels all take the same original value, then jump abruptly to the next original value. That is the chunky, pixelated look of an image blown up in a naive viewer, and its defining property is that it never produces a value that was not already in the input. It can only repeat and jump.

Bilinear upsampling fills each new position by blending the two nearest samples in proportion to how close each is — a weighted average that slides smoothly from one original value to the next as you move across the gap. Instead of a run of identical pixels and a sudden jump, you get a ramp through the intermediate values that nearest-neighbor can never emit. A smooth region of the image stays smooth after enlarging, instead of fracturing into visible blocks. The cost is a slight blur — bilinear cannot invent detail that was not sampled — but for enlarging a continuous-toned image it is almost always the right default.

The two differ most exactly where the image changes fastest, because that is where the gap between adjacent samples is largest and nearest-neighbor's single abrupt jump is biggest. Bilinear takes that same gap and spreads it evenly across the new pixels, so its largest step is the gap divided by the upscale factor.

We will upscale a 4-sample signal by 4× both ways. Nearest-neighbor produces a staircase whose biggest jump is 60 — the full gap between two coarse samples, landing in a single step — and emits only the 4 original values. Bilinear spreads that gap over the new pixels, so its biggest jump is 15, and it emits 12 distinct values. Same input, same factor; only the fill rule differs.

**Upsampling invents the pixels between the samples; nearest-neighbor copies the closest and jumps, producing a blocky staircase, while bilinear blends the two nearest into a smooth ramp.**

## Concepts

The core distinction is what each rule is allowed to output. Nearest-neighbor is a lookup: for each output position, find the closest input sample and copy it. So its entire output range is the set of input values — nothing more. If the input had four distinct values, the output has four distinct values, arranged as flat plateaus. That is why it looks blocky: large regions are perfectly flat (a plateau) separated by sharp edges (the jumps), which is exactly the structure the eye reads as pixelation. It preserves the original values exactly, which is occasionally what you want — for pixel art, for label masks where you must not invent in-between labels — but for a continuous-toned photo it is a defect.

Bilinear is an interpolation: for each output position, find the two input samples it falls between, and take their weighted average with weights set by distance. An output position that is one-quarter of the way from sample A to sample B gets 0.75·A + 0.25·B. This produces every value along the line between A and B, so the output ramps continuously, and its distinct-value count is far larger than the input's. The blockiness is gone because the plateaus are gone: every gap is filled with a slope. The tradeoff is that bilinear slightly softens genuine edges too — a real sharp edge in the input becomes a short ramp — which is the blur cost, and it is why upsampling can smooth but never sharpen.

<svg role="img" aria-label="Maximum adjacent jump: nearest 60, bilinear 15" viewBox="0 0 460 140" width="460" height="140">
  <rect x="0" y="0" width="460" height="140" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">biggest jump between adjacent pixels (lower = smoother)</text>
  <line x1="60" y1="110" x2="440" y2="110" stroke="var(--line)"/>
  <rect x="100" y="35" width="90" height="75" fill="var(--s2)" stroke="var(--line)"/><text x="128" y="29" font-family="var(--mono)" font-size="11" fill="var(--s2)">60</text><text x="98" y="126" font-family="var(--mono)" font-size="9" fill="var(--muted)">nearest</text>
  <rect x="280" y="91" width="90" height="19" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="308" y="85" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">15</text><text x="278" y="126" font-family="var(--mono)" font-size="9" fill="var(--muted)">bilinear (÷4)</text>
</svg>
^ Bilinear's worst step is the coarse gap divided by the upscale factor — a quarter of nearest's at 4×, an eighth at 8×.

The smoothness gain is quantifiable through the maximum adjacent jump. In nearest-neighbor, the biggest jump between two output pixels equals the biggest gap between two input samples, because the whole gap is crossed in one step at the plateau boundary. In bilinear, that same gap is divided evenly across the new pixels the interpolation inserts, so the biggest jump is the gap divided by the upscale factor. Upscale by 4 and bilinear's worst step is a quarter of nearest's; upscale by 8 and it is an eighth. The higher the upscale factor, the more dramatically bilinear beats nearest on smoothness, because there are more intermediate pixels to spread each gap across.

This generalizes directly to two dimensions, where bilinear blends the four surrounding samples (two in each direction) instead of two, and to higher-order methods — bicubic and Lanczos blend more neighbors with smarter weights for even better results at more cost. The 1D case here is the exact core: the choice is always between copying the nearest known value and blending the neighbors, and blending is what keeps a smooth signal smooth.

**Nearest-neighbor's output is limited to the input values, so it plateaus and jumps; bilinear interpolates through the in-between values, cutting the worst jump to the coarse gap over the upscale factor.**

## Worked example

The fixture is a coarse signal and an upscale factor.

```json filename=modules/generative-media/code/media-inter-12/signal.json:7-13 COMPLETE
  "coarse": [
    10,
    30,
    90,
    50
  ],
  "factor": 4
```

Four samples — 10, 30, 90, 50 — upscaled 4×. The largest gap between adjacent samples is 60 (from 30 to 90).

```text filename=modules/generative-media/code/media-inter-12/upsample.py --coarse
COARSE — 4 samples upscaled 4x to 13
----------------------------------------------
  input:  [10, 30, 90, 50]
  largest gap between adjacent samples: 60
----------------------------------------------
  upsampling must invent 9 new samples between the originals.
```

Nine new samples must be invented between the four originals. Nearest-neighbor copies the closest.

```python filename=modules/generative-media/code/media-inter-12/upsample.py:46-48 COMPLETE
def nearest(coarse, factor):
    """Copy each output position from the closest input sample -- a staircase of flat runs."""
    return [coarse[round(i / factor)] for i in range(out_len(coarse, factor))]
```

Bilinear blends the two nearest by distance.

```python filename=modules/generative-media/code/media-inter-12/upsample.py:51-60 COMPLETE
def bilinear(coarse, factor):
    """Blend the two nearest samples by distance -- a smooth ramp through intermediate values."""
    out = []
    for i in range(out_len(coarse, factor)):
        x = i / factor
        lo = int(x)
        hi = min(lo + 1, len(coarse) - 1)
        t = x - lo
        out.append(round(coarse[lo] * (1 - t) + coarse[hi] * t, 2))
    return out
```

Smoothness is the biggest step between adjacent output samples.

```python filename=modules/generative-media/code/media-inter-12/upsample.py:63-65 COMPLETE
def max_jump(signal):
    """The largest step between adjacent output samples -- big means blocky, small means smooth."""
    return round(max(abs(signal[i] - signal[i - 1]) for i in range(1, len(signal))), 2)
```

Predict: nearest gives plateaus of 4 and a max jump of 60 (the full coarse gap); bilinear ramps through intermediate values with a max jump of 60/4 = 15. Run it.

```text filename=modules/generative-media/code/media-inter-12/upsample.py --upsample
UPSAMPLE — nearest-neighbor vs bilinear at 4x
--------------------------------------------------------------
  nearest:   [10, 10, 10, 30, 30, 30, 90, 90, 90, 90, 90, 50, 50]
    max jump 60   distinct values 4
  bilinear:  [10.0, 15.0, 20.0, 25.0, 30.0, 45.0, 60.0, 75.0, 90.0, 80.0, 70.0, 60.0, 50.0]
    max jump 15   distinct values 12
```

The nearest-neighbor row is a staircase you can read off: three 10s, three 30s, five 90s, two 50s — flat runs of the original values, and between them jumps of 20, 60, 40. Its biggest jump, 60, crosses the entire 30-to-90 gap in a single step, and it emits only the 4 values it started with. The bilinear row ramps: 10, 15, 20, 25, 30 — a smooth climb through values that were never in the input — then up to 90 and back down to 50, with a biggest jump of just 15. Twelve distinct values instead of four, and the worst step quartered. The blockiness of nearest is those big jumps and flat plateaus; bilinear has neither.

<svg role="img" aria-label="One gap filled two ways: nearest copies the left sample four times then jumps 60; bilinear inserts four values stepping by 15" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">filling the 30→90 gap (4 new samples)</text>
  <text x="20" y="52" font-family="var(--mono)" font-size="9" fill="var(--s2)">nearest</text>
  <g font-family="var(--mono)" font-size="9">
    <rect x="80" y="40" width="40" height="18" fill="var(--acc-soft)" stroke="var(--line)"/><text x="92" y="53" fill="var(--acc-ink)">30</text>
    <rect x="122" y="40" width="40" height="18" fill="var(--s2)" stroke="var(--line)"/><text x="134" y="53" fill="var(--ink)">30</text>
    <rect x="164" y="40" width="40" height="18" fill="var(--s2)" stroke="var(--line)"/><text x="176" y="53" fill="var(--ink)">30</text>
    <rect x="206" y="40" width="40" height="18" fill="var(--s2)" stroke="var(--line)"/><text x="218" y="53" fill="var(--ink)">90</text>
    <rect x="248" y="40" width="40" height="18" fill="var(--acc-soft)" stroke="var(--line)"/><text x="260" y="53" fill="var(--acc-ink)">90</text>
  </g>
  <text x="300" y="53" font-family="var(--mono)" font-size="9" fill="var(--s2)">one jump of 60</text>
  <text x="20" y="112" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">bilinear</text>
  <g font-family="var(--mono)" font-size="9">
    <rect x="80" y="100" width="40" height="18" fill="var(--acc-soft)" stroke="var(--line)"/><text x="92" y="113" fill="var(--acc-ink)">30</text>
    <rect x="122" y="100" width="40" height="18" fill="var(--acc-line)" stroke="var(--line)"/><text x="134" y="113" fill="var(--acc-ink)">45</text>
    <rect x="164" y="100" width="40" height="18" fill="var(--acc-line)" stroke="var(--line)"/><text x="176" y="113" fill="var(--acc-ink)">60</text>
    <rect x="206" y="100" width="40" height="18" fill="var(--acc-line)" stroke="var(--line)"/><text x="218" y="113" fill="var(--acc-ink)">75</text>
    <rect x="248" y="100" width="40" height="18" fill="var(--acc-soft)" stroke="var(--line)"/><text x="260" y="113" fill="var(--acc-ink)">90</text>
  </g>
  <text x="300" y="113" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">four steps of 15</text>
  <text x="20" y="150" font-family="var(--mono)" font-size="9" fill="var(--muted)">nearest repeats then leaps; bilinear inserts 45, 60, 75 — the in-between values</text>
</svg>
^ Nearest fills the gap by repeating 30 then leaping to 90 in one 60-step; bilinear inserts 45, 60, 75, so the same gap is crossed in four even 15-steps.

<svg role="img" aria-label="The upsampled signals: nearest-neighbor as a staircase of flat plateaus with big jumps, bilinear as a smooth ramp through intermediate values" viewBox="0 0 460 200" width="460" height="200">
  <rect x="0" y="0" width="460" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">4× upsample: staircase vs ramp (value on y, position on x)</text>
  <line x1="40" y1="170" x2="440" y2="170" stroke="var(--line)"/>
  <line x1="40" y1="40" x2="40" y2="170" stroke="var(--line)"/>
  <polyline points="40,161 40,161 70,161 70,141 100,141 130,141 130,81 160,81 190,81 220,81 250,81 250,121 280,121 310,121" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <text x="120" y="60" font-family="var(--mono)" font-size="9" fill="var(--s2)">nearest (staircase)</text>
  <polyline points="40,161 70,156 100,151 130,146 160,141 190,126 220,111 250,96 280,81 310,91 340,101 370,111 400,121" fill="none" stroke="var(--acc-ink)" stroke-width="2"/>
  <text x="300" y="150" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">bilinear (smooth ramp)</text>
  <text x="40" y="188" font-family="var(--mono)" font-size="8" fill="var(--muted)">nearest holds flat then jumps 60; bilinear slides through the in-between values</text>
</svg>
^ Nearest-neighbor holds each value flat then leaps the whole gap at once; bilinear glides through the intermediate values, so a smooth input stays smooth.

## Build

Reproduce the two rows. Pure standard library, deterministic, so the staircase, the ramp, and the jumps of 60 and 15 come out exactly.

Run `--coarse` for the input, `--upsample` for both outputs, `--check` for the gate. The self-test pins the mechanism: nearest jumps the full gap and copies only original values, bilinear cuts the jump to gap/factor and invents intermediate values.

```python filename=modules/generative-media/code/media-inter-12/upsample.py:106-110 COMPLETE
    nearest_jumps_full_gap = max_jump(nn) == gap
    print("  nearest's biggest jump is the full coarse gap = %s (%g = %d)" % (nearest_jumps_full_gap, max_jump(nn), gap))

    bilinear_smooths = max_jump(bl) == round(gap / f, 2)
    print("  bilinear cuts the biggest jump to gap/factor = %s (%g = %d/%d)" % (bilinear_smooths, max_jump(bl), gap, f))
```

The `bilinear_smooths` check is an exact equality — bilinear's max jump equals the coarse gap divided by the factor, to two decimals — not a vague "smoother." That exactness is the quantitative heart of the module: bilinear does not just reduce blockiness, it reduces the worst step by precisely the upscale factor, so you can predict the smoothness gain from the factor alone. The nearest-copies-only and bilinear-invents checks capture the other half — what values each can emit. Here is the full gate.

```text filename=modules/generative-media/code/media-inter-12/upsample.py --check
SELF-TEST — nearest jumps by the full coarse gap and copies only original values; bilinear smooths
--------------------------------------------------------------------------------------------
  nearest's biggest jump is the full coarse gap = True (60 = 60)
  bilinear cuts the biggest jump to gap/factor = True (15 = 60/4)
  nearest emits only the original values = True (4 distinct)
  bilinear emits intermediate values = True (12 distinct vs 4)
--------------------------------------------------------------------------------------------
SELF-TEST PASS  nearest_jumps_full_gap=True  bilinear_smooths=True  nearest_copies_only=True  bilinear_invents=True
```

Four True flags. Nearest_jumps_full_gap: nearest crosses the whole gap in one step. Bilinear_smooths: bilinear cuts that to gap/factor exactly. Nearest_copies_only: nearest's outputs are exactly the input values. Bilinear_invents: bilinear produces the intermediate values nearest cannot. The first two are about smoothness, the last two about what values are possible, and together they are the full difference between copying and blending.

**Bilinear's max jump equals the coarse gap over the factor exactly, so the smoothness gain is not vague — it is precisely the upscale factor, predictable in advance.**

## Definition of done

You are done when you reproduce the staircase and the ramp and can explain the difference.

Concretely: `--upsample` shows nearest as flat runs with a max jump of 60 and 4 distinct values, bilinear as a ramp with a max jump of 15 and 12 distinct values; `--check` prints PASS with four True flags. You can explain why nearest can only emit input values (it is a copy) while bilinear emits intermediate ones (it is a blend), and why nearest's max jump is the coarse gap while bilinear's is that over the factor. You can name bilinear's cost — a slight blur, softening real edges too — and the cases where nearest is correct (pixel art, label masks). And you can extend it: 2D bilinear blends four neighbors, bicubic and Lanczos blend more.

The habit to carry: default to bilinear (or bicubic) for enlarging continuous-toned images, and reserve nearest-neighbor for when you must not invent in-between values — labels, palettes, pixel art. When an upscaled image looks blocky, check whether the resize used nearest-neighbor before blaming the source resolution.

## Boss fight

The instructive failure is a thumbnail pipeline that ships pixelated images and gets blamed on the camera.

A service generates preview images by upscaling small thumbnails, and it uses nearest-neighbor because that is the library default for the resize call they copied. The previews come out visibly blocky — flat patches and jagged edges — and the team concludes the source thumbnails are too low-resolution and starts storing larger ones, doubling storage cost. But the resolution was fine; the blockiness was the nearest-neighbor upscaling turning every smooth gradient into a staircase. Switching the one resize flag to bilinear (or bicubic) makes the same thumbnails upscale smoothly, and the storage change is reverted. The defect was one line — the interpolation mode — and it masqueraded as a resolution problem.

Your turn, two moves. First, confirm the factor law. Change the upscale factor to 8 and predict: nearest's max jump stays 60 (it always crosses the full coarse gap in one step, regardless of factor), while bilinear's drops to 60/8 = 7.5 — so the higher the upscale, the more bilinear's smoothness advantage grows, because there are more intermediate pixels to spread each gap over. Second, find where nearest is actually right. Replace the smooth signal with a label mask — values like [1, 1, 3, 3] that are category ids, not intensities — and reason about what bilinear does: it would produce 2.0 between a 1 and a 3, a category that does not exist. Here nearest-neighbor is correct precisely because it refuses to invent in-between values; blending is wrong for labels. That is the boundary: blend continuous quantities, copy discrete ones, and the "blocky" behavior that is a defect for photos is the required behavior for masks.

## External resources

Any image-processing text covers interpolation for resampling; Szeliski's "Computer Vision" and Gonzalez and Woods' "Digital Image Processing" derive nearest, bilinear, and bicubic and their smoothness-versus-sharpness tradeoffs.

For the hands-on version, the resize documentation for Pillow, OpenCV, and Pillow-SIMD names the interpolation flags (NEAREST, BILINEAR, BICUBIC, LANCZOS) and notes that NEAREST is fast but blocky and should be reserved for masks and pixel art — exactly this module's conclusion.

For the higher-order methods, write-ups on bicubic and Lanczos resampling show how blending more neighbors with windowed-sinc weights reduces blur while staying smooth, the continuation of the copy-versus-blend spectrum past bilinear.
