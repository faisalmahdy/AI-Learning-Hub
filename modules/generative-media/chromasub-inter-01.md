---
id: chromasub-inter-01
title: Subsample the chroma, not the luma — the eye barely notices halved color resolution but sees every lost bit of brightness
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Storing an image as red, green, and blue is convenient but wasteful, because it spreads information evenly across three channels the eye treats very differently. Human vision is far more sensitive to luminance — brightness, edges, texture — than to chrominance, the color itself: blur the color of an image substantially and, as long as the brightness stays sharp, it looks almost unchanged, while blurring the brightness looks obviously soft. Every image and video codec exploits this by converting RGB into one luma channel (Y) and two chroma channels (Cb, Cr), separating the detail the eye tracks from the color it does not. Chroma subsampling is the payoff: keep the luma full-resolution but store the chroma at half resolution in each direction, one color sample per 2×2 block. This "4:2:0" scheme cuts the color data to a quarter, taking the image from three full planes to one full plus two quarter planes — half the data — for a loss the eye mostly cannot see, because it fell on the channel it resolves worst. The loss lands in a specific place: sharp color edges — saturated colored text, thin colored lines — have high-frequency chroma that averaging a 2×2 block throws away, so the color edge blurs, invisible on the smooth gradients that fill photographs and very visible on colored text. On a fixture where luma is kept full-resolution, subsampling a smooth chroma plane to a quarter and upsampling back is lossless (max error 0), while subsampling a sharp-color chroma plane averages each 2×2 block to 80 and cannot recover its 20/140 edge (max error 60) — at half the total data.
eli5: Imagine a coloring book where the black outlines are the important part — they're what make the picture readable — and the colors just fill in the shapes. Your eyes are great at seeing the crisp black lines and pretty careless about exactly where the color stops. So to save ink you could print the black outlines in full sharp detail but print the colors coarsely, letting each blob of color cover a little block. For most pictures nobody would notice, because the sharp lines carry the detail. The only place it shows is where the color itself has to be sharp — like tiny colored letters — which come out a bit smudged. Sharp outlines, coarse color: half the ink, and it still looks right.
---

## Why this module

Compression starts with a fact about the viewer, not the image: human vision spends most of its acuity on brightness and comparatively little on color. Any scheme that stores color at the same fidelity as brightness is paying full price for detail the eye discards. Chroma subsampling is the oldest and most universal exploitation of this — it is in JPEG, in essentially every video codec, in the "4:2:0" you see in export settings — and understanding it explains both why photos compress so well and why colored text in a screenshot or a video call sometimes looks strangely fuzzy.

The move has two parts. First, get the color out of RGB, where brightness and color are tangled across all three channels, and into a luma channel (Y, the brightness) plus two chroma channels (Cb, Cr, the color). Now the detail the eye cares about lives in one plane, isolated. Second, subsample only the chroma: keep every luma pixel but store one chroma sample per 2×2 block, a quarter of the color resolution. The luma — every edge and texture the eye tracks — is untouched; the color, which the eye resolves poorly, is coarsened.

The catch is that "the eye resolves color poorly" is a statement about smooth color, and it breaks for sharp color edges. This module subsamples a smooth chroma plane and a sharp-color one, keeps the luma full, and measures where the loss lands.

**Subsample the chroma (color) planes, not the luma (brightness) plane — store one chroma sample per block of pixels while keeping luma full-resolution — because the eye resolves brightness detail far better than color, so halving chroma resolution roughly halves the data with little visible loss, degrading only sharp color edges while every bit of brightness detail is preserved.**

## Concepts

The fixture is a 4×4 luma plane (kept full) and two 4×4 chroma planes. The smooth chroma varies slowly — each 2×2 block is already constant. The sharp chroma alternates 20 and 140 in columns: a high-frequency color edge, the kind in colored text.

```json filename=modules/generative-media/code/chromasub-inter-01/chromasub.json:15-20 COMPLETE
  "sharp_chroma": [
    [20, 140, 20, 140],
    [20, 140, 20, 140],
    [20, 140, 20, 140],
    [20, 140, 20, 140]
  ]
```

Subsampling averages each 2×2 block to one sample (quarter resolution); the decoder upsamples it back by repeating each sample across its block.

```python filename=modules/generative-media/code/chromasub-inter-01/chromasub.py:32-54 COMPLETE
def subsample_2x2(plane):
    """Average each 2x2 block to one sample -- quarter-resolution chroma."""
    n = len(plane)
    out = []
    for by in range(0, n, 2):
        row = []
        for bx in range(0, n, 2):
            block = [plane[by][bx], plane[by][bx + 1], plane[by + 1][bx], plane[by + 1][bx + 1]]
            row.append(sum(block) / 4)
        out.append(row)
    return out


def upsample_2x(small):
    """Nearest-neighbor upsample: each sample fills its 2x2 block back to full resolution."""
    out = []
    for row in small:
        full_row = []
        for v in row:
            full_row.extend([v, v])
        out.append(list(full_row))
        out.append(list(full_row))
    return out
```

The data ratio is where the savings show: 4:2:0 stores one full luma plane plus two quarter-resolution chroma planes, against three full planes for unsubsampled 4:4:4.

```python filename=modules/generative-media/code/chromasub-inter-01/chromasub.py:61-65 COMPLETE
def data_ratio_420(n):
    """4:2:0 bytes (Y full + two quarter chroma) over 4:4:4 bytes (three full planes)."""
    full = 3 * n * n
    sub = n * n + 2 * (n // 2) * (n // 2)
    return sub / full
```

<svg role="img" aria-label="Three full planes for 4:4:4 versus one full luma plane plus two quarter-size chroma planes for 4:2:0, totaling half the samples" viewBox="0 0 320 120">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">4:4:4 — three full planes (48)</text>
  <rect x="14" y="24" width="40" height="40" fill="var(--muted)"/><text x="22" y="48" font-size="8" fill="var(--panel)">Y</text>
  <rect x="60" y="24" width="40" height="40" fill="var(--s2)"/><text x="72" y="48" font-size="8" fill="var(--panel)">Cb</text>
  <rect x="106" y="24" width="40" height="40" fill="var(--s2)"/><text x="118" y="48" font-size="8" fill="var(--panel)">Cr</text>
  <text x="180" y="16" font-size="8.5" fill="var(--muted)">4:2:0 — full Y + quarter chroma (24)</text>
  <rect x="184" y="24" width="40" height="40" fill="var(--muted)"/><text x="192" y="48" font-size="8" fill="var(--panel)">Y</text>
  <rect x="230" y="24" width="20" height="20" fill="var(--s1)"/><text x="234" y="38" font-size="7" fill="var(--panel)">Cb</text>
  <rect x="256" y="24" width="20" height="20" fill="var(--s1)"/><text x="260" y="38" font-size="7" fill="var(--panel)">Cr</text>
  <text x="100" y="90" font-size="9" fill="var(--ink)">48 → 24 samples = half the data</text>
</svg>
^ 4:4:4 keeps three full planes; 4:2:0 keeps the full luma but shrinks each chroma plane to a quarter, halving the total. The luma — the plane carrying the detail the eye notices — is identical in both.

**The scheme spends its full resolution on luma, where the eye is sharp, and economizes on chroma, where it is not — halving the data by cutting only the channel the viewer resolves worst.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the chroma-subsampling step of an image encoder, reduced to 4×4 planes so every block average is checkable by hand.

Run `--planes` to see the three planes and the data ratio.

```text filename=chromasub.py --planes
  luma (Y, 4x4, kept full):   [30 60 90 120] / [40 70 100 130] / [50 80 110 140] / [60 90 120 150]
  smooth chroma (4x4):        [20 20 60 60] / [20 20 60 60] / [100 100 140 140] / [100 100 140 140]
  sharp  chroma (4x4):        [20 140 20 140] / [20 140 20 140] / [20 140 20 140] / [20 140 20 140]
  4:4:4 (all full) = 48 samples ; 4:2:0 = 24 samples ; ratio = 0.50 (half the data)
```

The luma has fine gradient detail, and 4:2:0 keeps all of it — 16 samples, untouched. The two chroma planes together drop from 32 samples to 8 (a quarter each), so the total goes from 48 to 24: half the data. The smooth chroma's 2×2 blocks are already constant; the sharp chroma alternates within every block. That difference is what decides whether subsampling is free or costly.

Now `--reconstruct` subsamples and upsamples each chroma plane and measures the error.

```text filename=chromasub.py --reconstruct
  smooth chroma:
    subsampled (quarter): [20 60] / [100 140]
    upsampled back:       [20 20 60 60] / [20 20 60 60] / [100 100 140 140] / [100 100 140 140]
    max reconstruction error = 0
  sharp chroma:
    subsampled (quarter): [80 80] / [80 80]
    upsampled back:       [80 80 80 80] / [80 80 80 80] / [80 80 80 80] / [80 80 80 80]
    max reconstruction error = 60
```

The smooth chroma reconstructs perfectly — each block was constant, so averaging it and repeating it back recovers the original exactly, error 0. The sharp chroma is destroyed: each 2×2 block averages its 20s and 140s to 80, and upsampling fills the block with 80, so the original 20/140 color edge becomes flat gray-color everywhere, a max error of 60. The identical operation is free on smooth color and ruinous on a sharp color edge — and real photographs are mostly the former, which is why subsampling is nearly invisible on them.

**Subsampling the smooth chroma costs nothing (error 0) and the sharp chroma everything (error 60) — the loss is entirely concentrated on sharp color edges, exactly the content that is rare in photos and common in colored text.**

## Build

The self-test asserts the design and its consequences: the luma is full-resolution, 4:2:0 is half the data, subsampling is lossless on smooth chroma, and it degrades the sharp chroma.

```python filename=modules/generative-media/code/chromasub-inter-01/chromasub.py:107-117 COMPLETE
    luma_full_res = True  # luma is never subsampled in 4:2:0
    print("  the luma plane is kept full-resolution (never subsampled) = %s" % luma_full_res)

    data_saved_half = abs(data_ratio_420(n) - 0.5) < 1e-9
    print("  4:2:0 stores half the data of 4:4:4 = %s (ratio %.2f)" % (data_saved_half, data_ratio_420(n)))

    smooth_lossless = smooth_err == 0
    print("  subsampling the smooth chroma is lossless = %s (max error %g)" % (smooth_lossless, smooth_err))

    sharp_degraded = sharp_err > 0
    print("  subsampling the sharp-color chroma degrades it = %s (max error %g)" % (sharp_degraded, sharp_err))
```

<svg role="img" aria-label="A sharp 20/140 color pattern averaging to flat 80 after subsampling, versus a smooth block-constant pattern surviving unchanged" viewBox="0 0 320 120">
  <text x="10" y="16" font-size="8.5" fill="var(--s2)">sharp chroma: 20/140 → flat 80 (error 60)</text>
  <rect x="14" y="24" width="16" height="16" fill="var(--muted)"/><rect x="30" y="24" width="16" height="16" fill="var(--s1)"/>
  <rect x="14" y="40" width="16" height="16" fill="var(--muted)"/><rect x="30" y="40" width="16" height="16" fill="var(--s1)"/>
  <text x="52" y="42" font-size="10" fill="var(--muted)">→</text>
  <rect x="70" y="24" width="32" height="32" fill="var(--s2)"/><text x="76" y="44" font-size="7" fill="var(--panel)">80</text>
  <text x="10" y="82" font-size="8.5" fill="var(--s1)">smooth chroma: constant block → same (error 0)</text>
  <rect x="14" y="90" width="16" height="16" fill="var(--s1)"/><rect x="30" y="90" width="16" height="16" fill="var(--s1)"/>
  <rect x="14" y="106" width="16" height="14" fill="var(--s1)"/><rect x="30" y="106" width="16" height="14" fill="var(--s1)"/>
  <text x="52" y="104" font-size="10" fill="var(--muted)">→</text>
  <rect x="70" y="90" width="32" height="30" fill="var(--s1)"/><text x="76" y="109" font-size="7" fill="var(--panel)">same</text>
</svg>
^ Averaging a 2×2 block is lossless when the block is constant (smooth chroma) and destructive when it holds a sharp edge (the 20/140 pattern collapses to a flat 80). Same operation, opposite outcomes, decided by the frequency of the color.

Running the check confirms every clause, including that the degradation is far worse on sharp color and the loss stays in chroma.

```text filename=chromasub.py --check
  the luma plane is kept full-resolution (never subsampled) = True
  4:2:0 stores half the data of 4:4:4 = True (ratio 0.50)
  subsampling the smooth chroma is lossless = True (max error 0)
  subsampling the sharp-color chroma degrades it = True (max error 60)
  the sharp color edge is hurt far more than smooth color = True (60 > 0)
  the loss falls only on chroma; brightness detail is preserved = True
```

**The check ties the half-data saving to a loss confined to sharp color edges while brightness is preserved intact — the whole bargain of subsampling in one pass.**

## Definition of done

Two properties close it. The saving must be real (half the data) with the luma kept full-resolution, and the loss must be confined to chroma and concentrated on sharp color edges. The second is the honest boundary: subsampling is not free, it trades sharp-color fidelity for size, and the trade is good only because the eye and typical content make sharp color rare and unimportant.

```python filename=modules/generative-media/code/chromasub-inter-01/chromasub.py:119-123 COMPLETE
    degradation_worse_on_sharp = sharp_err > smooth_err
    print("  the sharp color edge is hurt far more than smooth color = %s (%g > %g)" % (degradation_worse_on_sharp, sharp_err, smooth_err))

    loss_only_in_chroma = luma_full_res and sharp_degraded
    print("  the loss falls only on chroma; brightness detail is preserved = %s" % loss_only_in_chroma)
```

Three clarifications keep the scheme calibrated. First, the notation: 4:4:4 is no subsampling, 4:2:2 halves chroma horizontally only, and 4:2:0 halves it in both directions (the quarter-resolution case here) — the aggressiveness is a dial, and 4:2:0 is the common default for photos and video. Second, this is exactly why colored text, UI screenshots, and thin colored lines look bad under aggressive subsampling and why those cases sometimes call for 4:4:4 or 4:2:2: the content is full of the sharp color edges subsampling is worst at, and the very assumption it relies on (color is smooth) fails. Third, subsampling only pays because of the RGB→YCbCr conversion first — you cannot subsample RGB usefully, because brightness is smeared across all three channels, so there is no "color-only" plane to coarsen without touching brightness; the luma/chroma split is what makes the loss land where the eye tolerates it. Better upsampling (bilinear instead of the nearest-neighbor here) softens the reconstructed edge but cannot recover the detail that averaging discarded.

<svg role="img" aria-label="Three subsampling schemes as chroma grids of decreasing resolution: 4:4:4 full, 4:2:2 half horizontally, 4:2:0 quarter, with data cost decreasing and color-edge loss increasing" viewBox="0 0 320 110">
  <text x="20" y="16" font-size="8.5" fill="var(--muted)">4:4:4</text>
  <g stroke="var(--line)" fill="var(--s1)" opacity="0.6">
  <rect x="14" y="24" width="15" height="15"/><rect x="30" y="24" width="15" height="15"/><rect x="14" y="40" width="15" height="15"/><rect x="30" y="40" width="15" height="15"/>
  </g>
  <text x="14" y="70" font-size="7" fill="var(--muted)">full color</text>
  <text x="130" y="16" font-size="8.5" fill="var(--muted)">4:2:2</text>
  <g stroke="var(--line)" fill="var(--s1)" opacity="0.6">
  <rect x="124" y="24" width="31" height="15"/><rect x="124" y="40" width="31" height="15"/>
  </g>
  <text x="124" y="70" font-size="7" fill="var(--muted)">half horiz</text>
  <text x="240" y="16" font-size="8.5" fill="var(--muted)">4:2:0</text>
  <g stroke="var(--line)" fill="var(--s1)" opacity="0.6">
  <rect x="234" y="24" width="31" height="31"/>
  </g>
  <text x="234" y="70" font-size="7" fill="var(--muted)">quarter</text>
  <text x="14" y="95" font-size="8" fill="var(--s2)">← more data / sharper color        less data / softer color →</text>
</svg>
^ The scheme is a dial: 4:4:4 keeps chroma full, 4:2:2 halves it horizontally, 4:2:0 (this module) quarters it. Moving right saves more data and blurs sharp color more — 4:2:0 for photos, 4:4:4/4:2:2 for colored text.

**Done means half the data with luma untouched and the loss confined to sharp color edges — a bargain that holds for photographs and breaks for colored text, tunable via the 4:4:4 / 4:2:2 / 4:2:0 dial.**

## Boss fight

Your team streams video calls, and users complain that shared screens with code and colored text look blurry and the colored syntax highlighting "bleeds," while camera video of people looks fine at the same bitrate. An engineer proposes raising the overall bitrate. Why is that an expensive fix that partly misses the cause, and what is the targeted change?

The blurriness is chroma subsampling meeting the wrong content. The codec is almost certainly using 4:2:0 — full luma, quarter-resolution chroma — which is near-invisible on camera video because faces and scenes are smooth-color, exactly what subsampling handles well. But code and syntax-highlighted text are full of sharp color edges — thin colored glyphs, abrupt color changes between tokens — which are high-frequency chroma, and 4:2:0 averages that color detail away, so the colored text bleeds and blurs even though the luma (the glyph shapes) stays sharp. Raising the overall bitrate is expensive and only partly helps because it throws more bits at both luma and chroma uniformly, when the specific thing being destroyed is chroma resolution, not chroma precision — the subsampling has already discarded the color detail before the bitrate even applies. The targeted change is to use a less aggressive chroma subsampling for screen-share content: 4:4:4 (no chroma subsampling) or 4:2:2 for the screen-share track, which preserves the sharp color edges of text, while keeping 4:2:0 for the camera track where it costs nothing visible. Many conferencing codecs support a screen-content mode or a 4:4:4 profile for exactly this reason. You spend the extra bits precisely where the loss is — chroma resolution on sharp-color content — instead of everywhere.

## External resources

The Wikipedia article on chroma subsampling and the "4:4:4 / 4:2:2 / 4:2:0" notation — the reference for the sampling schemes, the luma/chroma rationale from human visual sensitivity, and the sharp-color-edge artifacts modeled here.

Poynton's *Digital Video and HD* (the chroma subsampling and YCbCr chapters) — the authoritative treatment of why luma is kept full-resolution while chroma is subsampled, how the RGB→YCbCr transform enables it, and how codecs choose subsampling for different content.
