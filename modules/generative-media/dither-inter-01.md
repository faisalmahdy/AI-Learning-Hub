---
id: dither-inter-01
title: Diffuse the quantization error to neighbors — rounding each pixel alone flattens a region and loses its brightness
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Reducing an image to a few levels — printing to a black-and-white device, shrinking to a tiny palette — means mapping each pixel to the nearest available level, and done pixel by pixel in isolation that rounding throws away everything between the levels: a smooth mid-gray region, with no value close to black or white, rounds every pixel the same way and becomes a solid block. The detail is gone and, worse, the average brightness is wrong — a 50%-gray region can become 100% white because every pixel individually rounded up. Error-diffusion dithering fixes this by not letting the rounding error vanish: when a pixel is quantized, the difference between its true value and the level it was forced to is carried forward and added to the neighboring pixels not yet processed, so if a 128 pixel is forced up to 255 (an error of −127) that error pushes the next pixel down to 0, compensating. Over a region the pushed-forward errors cancel, so the local average of the output matches the input even though every pixel is pure black or white — the mid-gray becomes a fine pattern that averages to mid-gray, which is how newspapers print photographs with only black ink. On a fixture of a uniform mid-gray 128 row, naive quantization sends every pixel to 255 (solid white, average 255, off by 127) while error diffusion produces [255,0,255,0,255,0] (average 127.5, off by 0.5).
eli5: Suppose you can only use black or white tiles to show a gray wall. If you decide each tile on its own, a medium-gray wall rounds every tile to white, and now it looks solid white — the gray is gone. The trick is to remember your mistake: each time you place a tile that's too light, you owe some darkness, so you make the next tile black to pay it back. Keep passing that debt along and the tiles come out half black, half white, which from a distance looks exactly like the medium gray you wanted. Newspapers print photos this way, with nothing but black ink dots.
---

## Why this module

Cutting an image down to a few colors looks like independent rounding — send each pixel to its nearest level — and that is exactly the version that destroys the picture. A region with no value near any available level rounds uniformly and turns into a flat block of the wrong brightness. The fix is not a better rounding rule per pixel; it is to stop treating pixels independently and let each one's error inform the next.

Reducing an image to a few levels — printing to a black-and-white device, shrinking to a tiny palette — means mapping each pixel to the nearest available level. Done pixel by pixel in isolation, that rounding throws away everything between the levels: a smooth mid-gray region, with no value close to black or white, rounds every pixel the same way and becomes a solid block of one level. The detail is gone, and worse, the average brightness is wrong — a region that was 50% gray can become 100% white, because every pixel individually rounded up. Naive quantization is locally "correct" (each pixel went to its nearest level) and globally a disaster (the region's tone is destroyed).

Error-diffusion dithering fixes this by not letting the rounding error vanish. When a pixel is quantized, the quantization error — the difference between its true value and the level it was forced to — is carried forward and added to the neighboring pixels not yet processed. So if a 128 pixel is forced up to 255 (an error of −127, meaning we output 127 too much light), that −127 is pushed onto the next pixel, which now sees 128 − 127 = 1 and rounds to 0 (black), compensating. Over a region the pushed-forward errors cancel, so the local average of the output matches the input even though every individual pixel is pure black or white — the mid-gray becomes a fine pattern that averages to mid-gray, which is exactly how newspapers print photographs with only black ink. This module quantizes a mid-gray row both ways.

**Quantizing each pixel to the nearest of a few levels independently flattens a region and loses its average brightness; carrying each pixel's quantization error forward to its neighbors (dithering) preserves the local average, rendering a tone as a pattern instead of a solid block.**

## Concepts

**Nearest-level rounding** maps a value to whichever output level is closest — the single-pixel operation both methods use; the difference is only what happens to the error afterward.

```python filename=modules/generative-media/code/dither-inter-01/dither.py:46-48 COMPLETE
def nearest_level(value, levels):
    """Round a value to the nearest available output level."""
    return min(levels, key=lambda L: abs(value - L))
```

**Naive quantization** rounds each pixel independently and discards the error, so a region with no near-level value rounds uniformly to a flat block.

```python filename=modules/generative-media/code/dither-inter-01/dither.py:51-53 COMPLETE
def naive_quantize(row, levels):
    """Round each pixel to its nearest level independently -- no memory of the error."""
    return [nearest_level(v, levels) for v in row]
```

<svg role="img" aria-label="A value axis with levels at 0 and 255 and the input 128 sitting between them; naive rounding snaps 128 to the nearest level (255), losing the mid-gray" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">128 has no near level, so naive rounding snaps it to one</text>
  <line x1="30" y1="52" x2="285" y2="52" stroke="var(--line)"/>
  <circle cx="30" cy="52" r="4" fill="var(--ink)"/><text x="20" y="72" fill="var(--muted)" font-size="7">0 (black)</text>
  <circle cx="280" cy="52" r="4" fill="var(--muted)"/><text x="258" y="72" fill="var(--muted)" font-size="7">255 (white)</text>
  <circle cx="158" cy="52" r="4" fill="var(--s2)"/><text x="140" y="44" fill="var(--muted)" font-size="7">128 (mid-gray)</text>
  <path d="M158,52 L275,52" stroke="var(--s2)" stroke-dasharray="3 2"/><text x="196" y="40" fill="var(--muted)" font-size="6">naive → 255</text>
  <text x="30" y="88" fill="var(--muted)" font-size="7">the whole region rounds the same way → a flat block, brightness lost</text>
</svg>
^ With only 0 and 255 available, the mid-gray 128 has no nearby level, so naive rounding snaps every pixel to 255 — the region collapses to solid white and its 50%-gray brightness is gone.

**Error diffusion** carries the quantization error forward: after forcing a pixel to a level, it adds the leftover error to the next pixel, so the choices compensate over the region.

```python filename=modules/generative-media/code/dither-inter-01/dither.py:56-66 COMPLETE
def diffuse_quantize(row, levels):
    """Error diffusion: quantize each pixel, then push its quantization error onto the next pixel."""
    work = [float(v) for v in row]
    out = []
    for i in range(len(work)):
        q = nearest_level(work[i], levels)
        error = work[i] - q
        out.append(q)
        if i + 1 < len(work):
            work[i + 1] += error
    return out
```

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/dither-inter-01/dither.py

The fixture is a uniform mid-gray row and the two output levels.

```json filename=modules/generative-media/code/dither-inter-01/dither.json:3-4 COMPLETE
  "row": [128, 128, 128, 128, 128, 128],
  "levels": [0, 255]
```

Run `--quantize`.

```text filename=--quantize
QUANTIZE — a mid-gray [128, 128, 128, 128, 128, 128] row to levels [0, 255]
------------------------------------------------------------
  input            = [128, 128, 128, 128, 128, 128]   avg 128.0
  naive quantize   = [255, 255, 255, 255, 255, 255]   avg 255.0   <- solid, wrong brightness
  error diffusion  = [255, 0, 255, 0, 255, 0]   avg 127.5   <- pattern, right brightness
```

The input is a flat mid-gray, average 128. Naive quantization sends every pixel to 255 (128 rounds to the nearer of 0 and 255) and produces solid white with average 255 — off by 127, more than half the full range. A viewer would see a white block where there should be gray, and the region's tone is simply gone. Error diffusion produces [255, 0, 255, 0, 255, 0], an alternating pattern with average 127.5, essentially the true 128. Every output pixel is still pure black or white — the palette is unchanged — but their *arrangement* carries the brightness: half white, half black averages to mid-gray, so from any distance the region reads as the gray it was. The naive result is off by 127; the diffused result is off by 0.5. This is the difference between a quantization that destroys the picture and one that preserves it as texture, and it is why every real image-to-few-colors conversion (printing, GIF export, low-bit displays) dithers.

## Build

The mechanism is the error being carried forward, one pixel at a time. Run `--trace`.

```text filename=--trace
TRACE — error diffusion carries each pixel's error forward
--------------------------------------------------------------
  pixel  sees (value+carried)   output   error pushed forward
  0      128.0                255      -127.0
  1      1.0                  0        +1.0
  2      129.0                255      -126.0
  3      2.0                  0        +2.0
  4      130.0                255      -125.0
  5      3.0                  0        +3.0
```

Follow the carried error. Pixel 0 is 128, rounds up to 255, and has error 128 − 255 = −127 (it output 127 too much light), which is pushed to pixel 1. Pixel 1 now sees 128 + (−127) = 1, rounds down to 0, and pays back the debt — its own tiny error +1 goes to pixel 2. Pixel 2 sees 129, rounds to 255, pushes −126 forward, and so on. The error alternates sign, so the outputs alternate 255 and 0, and each white pixel's over-brightness is immediately cancelled by the next black pixel's under-brightness. That is why the average lands on 127.5 instead of 255: the method never loses light, it only moves it to a neighbor, so the total (and hence the local average) is conserved. Naive quantization threw the −127 away at every pixel; diffusion keeps it and spends it, which is the whole idea — a quantization that conserves the quantity it is quantizing.

<svg role="img" aria-label="Naive output is a solid white bar, error-diffusion output is an alternating black-and-white pattern, both rendering the same mid-gray input but only the pattern keeps the brightness" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same mid-gray input, two renderings to black/white</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">naive</text>
  <g transform="translate(60,24)">
  <rect x="0" y="0" width="180" height="16" fill="var(--muted)"/>
  <text x="244" y="12" fill="var(--muted)" font-size="7">all white → 255</text>
  </g>
  <text x="10" y="64" fill="var(--muted)" font-size="7">diffused</text>
  <g transform="translate(60,54)">
  <rect x="0" y="0" width="30" height="16" fill="var(--muted)"/><rect x="30" y="0" width="30" height="16" fill="var(--ink)"/><rect x="60" y="0" width="30" height="16" fill="var(--muted)"/><rect x="90" y="0" width="30" height="16" fill="var(--ink)"/><rect x="120" y="0" width="30" height="16" fill="var(--muted)"/><rect x="150" y="0" width="30" height="16" fill="var(--ink)"/>
  <text x="244" y="12" fill="var(--muted)" font-size="7">avg → 127.5</text>
  </g>
  <text x="10" y="94" fill="var(--muted)" font-size="7">the pattern averages to the true mid-gray; the solid block does not</text>
</svg>
^ Naive quantization renders the mid-gray as a solid white bar (brightness 255), while error diffusion renders it as an alternating black/white pattern that averages to 127.5 — the same two ink levels, but only the pattern preserves the tone.

## Definition of done

The self-test pins the naive flattening and wrong brightness, and the diffusion's preserved average and pattern.

```python filename=modules/generative-media/code/dither-inter-01/dither.py:112-119 COMPLETE
    naive_flattens = len(set(n)) == 1
    print("  naive output is a single flat level = %s (%s)" % (naive_flattens, n))

    naive_brightness_wrong = abs(average(n) - inp_avg) > 50
    print("  naive average brightness is far from the input = %s (%.1f vs %.1f)" % (naive_brightness_wrong, average(n), inp_avg))

    diffusion_preserves = abs(average(d) - inp_avg) < 1
    print("  diffusion average brightness matches the input = %s (%.1f vs %.1f)" % (diffusion_preserves, average(d), inp_avg))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — naive quantization flattens the region and gets the brightness wrong; error diffusion preserves it as a pattern
------------------------------------------------------------------------------------------------------------------------
  naive output is a single flat level = True ([255, 255, 255, 255, 255, 255])
  naive average brightness is far from the input = True (255.0 vs 128.0)
  diffusion average brightness matches the input = True (127.5 vs 128.0)
  diffusion output is a pattern, not a flat block = True ([255, 0, 255, 0, 255, 0])
  diffusion is closer to the true brightness than naive = True (0.5 < 127.0 error)
```

**Done means the flattening and its fix are proven on real values: naive quantization collapses the mid-gray row to a single flat level (255, brightness off by 127) while error diffusion produces a black/white pattern ([255,0,255,0,255,0]) whose average (127.5) matches the input 128 to within 0.5 — so quantizing to few levels must diffuse the error to preserve brightness, not round each pixel alone.**

## Boss fight

Predict two ways real dithering is more than "push the error to the next pixel," because the spread pattern and the color space both matter.

The first trap is that spreading all the error to a single neighbor (the 1-D core shown here) produces visible artifacts — directional streaks and worm-like patterns — so real dithering spreads it to several neighbors with tuned weights. Floyd–Steinberg, the standard, pushes 7/16 of the error to the pixel on the right, and 3/16, 5/16, 1/16 to the three pixels below-left, below, and below-right, so the error diffuses in two dimensions and the fractions sum to 1 (conserving brightness) while breaking up the regular pattern into a more organic dot texture. Other kernels (Jarvis, Stucki, Atkinson) spread further for smoother results at more cost, and processing rows in a boustrophedon (alternating left-to-right then right-to-left, "serpentine") order avoids the error consistently drifting one direction. The choice of kernel trades sharpness, artifact visibility, and speed — but all of them share this module's principle: quantize, then distribute the residual with weights that sum to 1. There is also blue-noise/ordered dithering (a fixed threshold matrix) which is faster and parallelizable but lower quality; error diffusion wins on quality precisely because it is sequential and adaptive.

<svg role="img" aria-label="The Floyd-Steinberg kernel: the current pixel pushes 7/16 of its error right, and 3/16, 5/16, 1/16 to the three pixels below-left, below, below-right; the weights sum to 16/16" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">Floyd–Steinberg spreads the error to 4 neighbors (weights sum to 1)</text>
  <g transform="translate(90,24)" font-size="8" fill="var(--muted)">
  <rect x="40" y="0" width="40" height="26" fill="var(--s2)"/><text x="48" y="17" fill="var(--panel)" font-size="7">pixel</text>
  <rect x="80" y="0" width="40" height="26" fill="none" stroke="var(--line)"/><text x="94" y="17">7/16</text>
  <rect x="0" y="28" width="40" height="26" fill="none" stroke="var(--line)"/><text x="12" y="45">3/16</text>
  <rect x="40" y="28" width="40" height="26" fill="none" stroke="var(--line)"/><text x="52" y="45">5/16</text>
  <rect x="80" y="28" width="40" height="26" fill="none" stroke="var(--line)"/><text x="94" y="45">1/16</text>
  </g>
  <text x="90" y="92" fill="var(--muted)" font-size="7">7+3+5+1 = 16/16: all the error is spread, none lost → brightness conserved</text>
</svg>
^ Floyd–Steinberg pushes 7/16 of a pixel's error to its right neighbor and 3/16, 5/16, 1/16 to the row below, spreading the residual in two dimensions; the weights sum to 1 so brightness is still conserved, but the pattern is far less streaky than pushing all the error one direction.

The second trap is that dithering, like resizing, must respect the color space and the alpha, or it conserves the wrong quantity. Diffusing error on gamma-encoded values conserves encoded brightness, not light, so a dithered gradient can come out subtly too dark or too light exactly as the gamma module describes — high-quality dithering diffuses in linear light and re-encodes. Color images dither each channel (or into a palette in a perceptual space), and naive per-channel diffusion can shift hue, so palette dithering measures error in a color-distance metric rather than per-channel independently. And dithering interacts with downstream compression badly: the high-frequency dither pattern is exactly what lossy compressors (JPEG) discard or waste bits on, so you dither at the final output resolution and bit depth, not before compression. The unifying rule is the same one behind gamma and premultiplied alpha: an operation that averages or accumulates pixel values is only correct in the representation where the quantity it conserves is linear, so dither in linear light, spread the error with weights that sum to 1, and apply it last in the pipeline.

**Real dithering spreads the quantization error to several neighbors with weights that sum to 1 (Floyd–Steinberg's 7/3/5/1 over sixteenths, serpentine order) to avoid streak artifacts, and it must diffuse in linear light and a perceptual color space (like the gamma and premultiplied-alpha rules) and be applied at the final resolution before compression — because it conserves whatever quantity it accumulates, so that quantity must be the linear one you actually mean.**

## External resources

Any image-processing reference on error-diffusion dithering — the Floyd–Steinberg kernel (7/16, 3/16, 5/16, 1/16), serpentine scanning, and alternatives (Jarvis, Stucki, Atkinson, ordered/blue-noise dithering).

Writing on halftoning and 1-bit/low-palette rendering — how newspapers and printers reproduce continuous tone with few ink levels, and why the dither pattern must be applied at output resolution.

The companion gamma, premultiplied-alpha, and aliasing modules in this topic — dithering is another operation that accumulates pixel values, so it shares their rule: conserve the quantity in linear light and apply it correctly in the pipeline, or the brightness comes out wrong.
