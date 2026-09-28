---
id: border-inter-01
title: Choose a border policy for the convolution — or zero-padding darkens every edge of the image
topic: generative-media
level: intermediate
status: ready
time: 21 min
summary: A convolution centers a kernel on each pixel, and at the image border the kernel hangs off the edge over pixels that do not exist. The lazy default — treat out-of-bounds as zero (black) — makes a border pixel average real pixels with black, so it comes out darker: a dark rim that was never in the picture. On a flat row of 100 blurred with a 3-wide box, zero-padding drops the two edge pixels to 67 while the interior stays 100; edge-extend and reflect keep every pixel at 100.
eli5: To blur a pixel you average it with its neighbors. But a pixel at the very edge is missing neighbors on one side — so what do you use? If you pretend the missing neighbors are black, the edge gets averaged with black and turns dark, giving the whole picture a dingy border. Instead, pretend the edge just continues (copy the last pixel, or mirror it), and the border stays the right brightness.
---

## Why this module

Every convolution has to invent pixels beyond the image edge, and the easiest choice — pretend they are black — quietly paints a dark frame around every image you filter.

A convolution slides a kernel over the image, centering it on each pixel and combining that pixel with its neighbors — a blur averages them, a sharpen contrasts them, an edge detector differences them. This works cleanly in the interior, where every pixel the kernel covers exists. At the border it does not: a kernel centered on an edge pixel hangs off the side of the image, over positions that have no pixel. The code must supply a value for those out-of-bounds positions, and that choice is the border policy.

The default that costs nothing to write is to treat everything outside the image as zero — black. It is also wrong for a blur. A border pixel's window now includes those black phantoms, so the average is pulled toward zero, and the pixel comes out darker than it should. On a bright, flat region every edge pixel gets dragged down, producing a dark rim or vignette that was never in the original. The kernel itself is correct and the interior is fine; the damage is entirely at the border, caused by the fabricated black pixels the average had no business including.

The fix is to invent plausible out-of-bounds values instead of black. Edge-extend (also called clamp or replicate) repeats the nearest real pixel, so a border pixel is averaged with copies of itself and does not move. Reflect mirrors the image across the boundary, which is smooth across the edge and also avoids the darkening. Both share the key property: past the edge they assume the image continues at roughly its edge brightness, not that it drops to black. Only zero-padding asserts that the world outside the frame is black, and only zero-padding darkens the border as a result.

On the fixture, a flat row of value 100 is blurred with a 3-wide box. Zero-padding drops the two edge pixels to 67 — a visible darkening — while the interior stays 100. Edge-extend and reflect keep every pixel at 100, edges included.

**A convolution must supply values for the out-of-bounds pixels its kernel covers at the border; zero-padding supplies black, so a blur averages border pixels toward black and darkens the edge, while edge-extend and reflect supply the image's own edge values and keep the border at its true brightness.**

## Concepts

The border problem is unavoidable because a kernel wider than one pixel always overhangs the image at the edge. For a 3-wide kernel the overhang is one pixel on each side; for a wider kernel or a bigger blur it is more, so the affected border is as thick as the kernel's radius. There is no way to center the kernel on an edge pixel without referencing positions outside the image, so every convolution implementation must choose a policy — the only question is which, and whether the choice was made deliberately or defaulted to zero.

Zero-padding is wrong for a blur specifically because a blur is a weighted average, and an average is sensitive to the values you feed it. Injecting black (zero) into the average of a bright border pixel lowers the result in proportion to how much of the window fell outside — the corner and edge pixels, whose windows overhang most, darken most. The effect is not random noise; it is a systematic, predictable darkening concentrated at the border, which reads as a vignette. The brighter the image and the larger the kernel, the more obvious the dark frame. Zero is a fine out-of-bounds value only when the image genuinely is black past its edge, which is essentially never for a photograph.

<svg role="img" aria-label="A 3-wide kernel centered on the edge pixel overhangs the image by one position; zero fills it with black, clamp repeats the edge, reflect mirrors" viewBox="0 0 470 185" width="470" height="185">
  <rect x="0" y="0" width="470" height="185" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">the window on the edge pixel: what fills the off-image slot?</text>
  <g font-family="var(--mono)" font-size="8">
    <rect x="90" y="40" width="34" height="24" fill="var(--panel)" stroke="var(--s2)" stroke-dasharray="3 2"/>
    <rect x="126" y="40" width="34" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
    <rect x="162" y="40" width="34" height="24" fill="var(--panel)" stroke="var(--line)"/>
    <text x="100" y="56" fill="var(--s2)">?</text><text x="138" y="56" fill="var(--acc-ink)">100</text><text x="172" y="56" fill="var(--ink)">100</text>
  </g>
  <text x="205" y="56" font-family="var(--mono)" font-size="8" fill="var(--muted)">← edge pixel's window (dashed = off image)</text>
  <text x="30" y="92" font-family="var(--mono)" font-size="8" fill="var(--s2)">zero:</text>
  <text x="95" y="92" font-family="var(--mono)" font-size="8" fill="var(--s2)">0 → avg (0+100+100)/3 = 67  (dark)</text>
  <text x="30" y="118" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">clamp:</text>
  <text x="95" y="118" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">100 (repeat edge) → 100  (flat)</text>
  <text x="30" y="144" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">reflect:</text>
  <text x="95" y="144" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">100 (mirror) → 100  (flat)</text>
  <text x="30" y="172" font-family="var(--mono)" font-size="8" fill="var(--muted)">only zero fills the off-image slot with something the image never had</text>
</svg>
^ The kernel on the edge pixel needs one off-image value; zero supplies black and drags the average to 67, while clamp and reflect supply the edge's own 100 and keep it flat.

Edge-extend and reflect both work by making the out-of-bounds region continue the image rather than contradict it. Edge-extend clamps the index to the nearest valid pixel, so beyond the edge you keep seeing the edge pixel's value — a border pixel averaged with copies of itself is unchanged on a flat region. Reflect mirrors the pixels across the boundary, so the out-of-bounds values are the image's own near-edge pixels flipped; on a flat region those are also the same value, and on a gradient reflect is smoother across the boundary than clamp (it continues the trend's mirror rather than freezing the edge value). Both avoid the darkening; the choice between them is usually minor and about how they behave near real edges and textures, not about the flat-region correctness this module isolates.

This is a small decision with outsized visible consequences, and it recurs across image processing. Any separable blur, Gaussian, sharpen, or morphological operation faces it; libraries expose the choice as a border mode (OpenCV's BORDER_REPLICATE, BORDER_REFLECT, BORDER_CONSTANT; NumPy/pillow "edge", "reflect", "constant"), and the sensible default for photographic filtering is replicate or reflect, not constant-zero. Zero-padding does have legitimate uses — in neural-network convolutions it is common and intentional (the network learns to account for it, and the "border" is a feature-map edge, not a visible image edge) — but for filtering a picture you will look at, defaulting to zero paints a frame you did not ask for. Choose the border policy on purpose.

**A kernel overhangs the image by its radius at every edge, so a border policy is mandatory; zero-padding injects black into the border average and darkens it systematically, while edge-extend (repeat the edge pixel) and reflect (mirror) continue the image and keep flat borders flat — reflect being smoother across real gradients.**

## Worked example

The fixture is a flat row and a blur width.

```json filename=modules/generative-media/code/border-inter-01/row.json:3-4 COMPLETE
  "kernel": 3,
  "row": [100, 100, 100, 100, 100, 100]
```

Six pixels, all 100, so any darkening after the blur is purely a border artifact — there is no real structure to explain it. The three border policies differ only in what they return for an out-of-bounds index.

```python filename=modules/generative-media/code/border-inter-01/border.py:40-57 COMPLETE
def at_zero(row, i):
    """Out-of-bounds -> 0 (black). Averaging with black darkens the border."""
    return row[i] if 0 <= i < len(row) else 0


def at_clamp(row, i):
    """Out-of-bounds -> nearest edge pixel (edge-extend)."""
    return row[min(max(i, 0), len(row) - 1)]


def at_reflect(row, i):
    """Out-of-bounds -> mirror across the edge."""
    n = len(row)
    if i < 0:
        i = -i
    elif i >= n:
        i = 2 * (n - 1) - i
    return row[min(max(i, 0), n - 1)]
```

The blur is a box average over the window, with the chosen border policy supplying any out-of-bounds pixel.

```python filename=modules/generative-media/code/border-inter-01/border.py:63-69 COMPLETE
def box_blur(row, half, border):
    at = BORDERS[border]
    out = []
    for i in range(len(row)):
        window = [at(row, j) for j in range(i - half, i + half + 1)]
        out.append(round(sum(window) / len(window), 1))
    return out
```

Predict: the interior pixels average 100 with 100 and stay 100 under every policy. The edge pixels differ — zero-padding averages 100, 100, and a phantom 0, giving 66.7; clamp and reflect average 100 with copies of 100. Run the blur.

```text filename=modules/generative-media/code/border-inter-01/border.py --blur
BLUR — a flat row of 100 blurred (width 3) under each border policy
----------------------------------------------------------
  input:   [100, 100, 100, 100, 100, 100]
  zero:    [66.7, 100.0, 100.0, 100.0, 100.0, 66.7]
  clamp:   [100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
  reflect: [100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
```

Zero-padding produced 66.7 at both ends — the two edge pixels are a third darker than the interior, purely because their window included one black phantom each. On a real image that is the dark rim you would see framing the picture. Clamp and reflect produced a flat 100 across the whole row, edges included, because past the edge they supplied 100 (the repeated or mirrored edge value), not 0. Same kernel, same interior; the only difference is what each policy invented off the edge. Now the error.

```text filename=modules/generative-media/code/border-inter-01/border.py --error
ERROR — absolute error against the true flat value 100
----------------------------------------------------------
  zero:    [33.3, 0.0, 0.0, 0.0, 0.0, 33.3]   total 66.6
  clamp:   [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]   total 0.0
  reflect: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]   total 0.0
```

Zero-padding's error is 33.3 at each edge and 0 everywhere inside — the damage is exactly at the border, the width of the kernel radius, and nowhere else. Clamp and reflect have zero error everywhere. This is the signature of a border-handling bug: a filtered image that looks right in the middle and wrong (darker) in a thin frame around the edge, thickening as you increase the blur.

<svg role="img" aria-label="A flat row at 100 with the two zero-padded edge pixels dropping to 67, while clamp and reflect stay flat at 100 across the whole row" viewBox="0 0 470 180" width="470" height="180">
  <rect x="0" y="0" width="470" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">blurred value across the row (true = 100)</text>
  <line x1="40" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <line x1="40" y1="50" x2="450" y2="50" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="360" y="46" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">true 100</text>
  <polyline points="70,50 130,50 190,50 250,50 310,50 370,50" fill="none" stroke="var(--acc-line)" stroke-width="2"/>
  <text x="150" y="42" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">clamp / reflect: flat 100</text>
  <polyline points="70,100 130,50 190,50 250,50 310,50 370,100" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <g fill="var(--s2)"><circle cx="70" cy="100" r="4"/><circle cx="370" cy="100" r="4"/></g>
  <text x="30" y="120" font-family="var(--mono)" font-size="8" fill="var(--s2)">zero: 67</text>
  <text x="300" y="120" font-family="var(--mono)" font-size="8" fill="var(--s2)">zero: 67 (dark rim)</text>
  <text x="120" y="170" font-family="var(--mono)" font-size="8" fill="var(--muted)">the dip is exactly at the two edges — a border-only artifact</text>
</svg>
^ Clamp and reflect hold the row flat at 100; zero-padding dips only at the two edge pixels to 67, the dark rim a blur paints when it averages the border with black.

## Build

Reproduce the blurs. Pure standard library, deterministic, so the 66.7 zero-padded edges and the flat clamp/reflect come out exactly.

Run `--blur` for the three outputs, `--error` for the per-pixel error, `--check` for the gate. The error against the true flat value is a per-pixel absolute difference — zero everywhere the policy got it right.

```python filename=modules/generative-media/code/border-inter-01/border.py:72-73 COMPLETE
def abs_error(a, b):
    return [round(abs(x - y), 1) for x, y in zip(a, b)]
```

<svg role="img" aria-label="Per-pixel error bars: zero-padding has a tall bar at each of the two edges and nothing inside; clamp and reflect are flat at zero" viewBox="0 0 470 160" width="470" height="160">
  <rect x="0" y="0" width="470" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">absolute error per pixel (index 0..5)</text>
  <line x1="40" y1="120" x2="450" y2="120" stroke="var(--line)"/>
  <text x="60" y="40" font-family="var(--mono)" font-size="8" fill="var(--s2)">zero (total 66.6)</text>
  <g fill="var(--s2)"><rect x="55" y="55" width="34" height="65"/><rect x="325" y="55" width="34" height="65"/></g>
  <text x="52" y="135" font-family="var(--mono)" font-size="7" fill="var(--s2)">33.3</text>
  <text x="322" y="135" font-family="var(--mono)" font-size="7" fill="var(--s2)">33.3</text>
  <text x="150" y="90" font-family="var(--mono)" font-size="7" fill="var(--muted)">interior error 0</text>
  <text x="250" y="150" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">clamp / reflect: flat line on 0</text>
  <line x1="40" y1="120" x2="450" y2="120" stroke="var(--acc-line)" stroke-width="2"/>
</svg>
^ Zero-padding's error stands only at the two edge pixels and is flat-zero across the interior; clamp and reflect are zero everywhere, so the whole error is the border artifact.

The self-test pins that zero-padding darkens the border while clamp and reflect preserve it, and that the effect is border-only.

```python filename=modules/generative-media/code/border-inter-01/border.py:109-113 COMPLETE
    zeropad_darkens_border = zero[0] < flat and zero[-1] < flat
    print("  zero-padding makes the edge pixels darker than the interior = %s (%.1f, %.1f vs %d)"
          % (zeropad_darkens_border, zero[0], zero[-1], flat))

    clamp_preserves_border = clamp[0] == flat and clamp[-1] == flat
    print("  edge-extend keeps the edge pixels at the true value = %s (%.1f)" % (clamp_preserves_border, clamp[0]))
```

```text filename=modules/generative-media/code/border-inter-01/border.py --check
SELF-TEST — zero-padding darkens the border; edge-extend and reflect leave it flat
------------------------------------------------------------------------------------------
  zero-padding makes the edge pixels darker than the interior = True (66.7, 66.7 vs 100)
  edge-extend keeps the edge pixels at the true value = True (100.0)
  reflect keeps the edge pixels at the true value = True (100.0)
  all policies agree in the interior (the effect is border-only) = True
  only zero-padding has any error = True (zero 66.6, clamp 0, reflect 0)
------------------------------------------------------------------------------------------
SELF-TEST PASS  zeropad_darkens_border=True  clamp_preserves_border=True  reflect_preserves_border=True  interior_matches=True  only_zero_has_error=True
```

Five True flags. Zeropad_darkens_border: zero-padding drops both edge pixels to 66.7. Clamp_preserves_border and reflect_preserves_border: both keep the edges at 100. Interior_matches: all three policies agree in the interior, proving the effect is confined to the border. Only_zero_has_error: zero-padding has total error 66.6 while clamp and reflect have zero. The interior-matches flag is the diagnostic one — it shows the darkening is not a property of the blur but purely of the border policy, so the same blur is correct or wrong depending only on that one choice.

**The interior-matches flag is the isolation — every policy blurs the middle identically, so the dark rim is entirely a border-handling artifact, which is why the fix is a border mode, not a change to the kernel.**

## Definition of done

You are done when you reproduce the dark edges and the flat alternatives, and can explain why only the border is affected.

Concretely: `--blur` shows zero-padding at 66.7 at the edges and clamp/reflect flat at 100; `--error` shows zero-padding with error 33.3 at each edge and 0 inside, clamp and reflect with zero error; `--check` prints PASS with five True flags. You can explain that a kernel overhangs the image by its radius so a border policy is mandatory, that zero-padding injects black into the border average and darkens it while edge-extend and reflect continue the image, and that the affected region is exactly the kernel radius. You can name the library border modes and when zero-padding is legitimate (learned network convolutions).

The habit to carry: choose a border mode deliberately for any convolution on a real image — replicate or reflect for photographic filtering, not constant-zero — and treat a dark rim after a blur or sharpen as a border-handling bug, not a lighting artifact. When a filtered image looks right in the center and dingy in a thin frame that grows with the blur radius, suspect zero-padding and switch the border mode. Do not let the world outside the frame default to black.

## Boss fight

The instructive failure is a thumbnail pipeline that adds a dark frame to every image.

A service blurs images before downscaling them to thumbnails, and every thumbnail comes out with a faint dark border — subtle on one image, obvious once you see a grid of them all framed the same way. The blur used the default zero-padding, so each image's edge pixels were averaged with black and darkened, and the wider the blur, the thicker the frame. It went unnoticed in unit tests (which checked the center) and was reported as "images look dingy" from users. The fix is a one-word change to the border mode — replicate or reflect — after which the edges keep their true brightness; the tell was that the darkening hugged the border and scaled with the blur radius.

Your turn, two moves. First, widen the kernel to 5 and confirm the dark border thickens to two pixels on each side under zero-padding (the affected width is the kernel radius) while clamp and reflect stay flat — showing the artifact scales with blur size, which is why heavy blurs frame the worst. Second, put a real gradient in the row (say ramping 100 to 200) and compare clamp and reflect at the edge: confirm both avoid the darkening but differ slightly in how they extrapolate the gradient past the edge (clamp freezes the edge value, reflect mirrors the trend) — the minor, real distinction between the two safe policies that this flat fixture hides.

## External resources

Any image-processing library's border-mode documentation (OpenCV's BorderTypes, SciPy's `mode` for ndimage filters, Pillow's filter behavior) lists constant, replicate, and reflect and shows their effect at the edge — the exact choice this module isolates.

Gonzalez and Woods' "Digital Image Processing" covers spatial filtering and padding, including why zero-padding darkens borders and the alternatives, in its chapter on convolution.

Discussions of padding in convolutional neural networks (the "same"/"valid" padding conventions) show where zero-padding is intentional and learned around, contrasting with photographic filtering where a continuation border is the right default.
