---
id: media-inter-05
title: Premultiply alpha before blending, or a transparent pixel bleeds a dark fringe
topic: generative-media
level: intermediate
status: ready
time: 8-10h
summary: A fully transparent pixel has no visible color, so tools store its color as black, and that stored black is harmless until you do arithmetic on it — averaging an opaque red pixel with a transparent one to downsample an edge blends the invisible black into the visible color and the red channel drops from 1.0 to 0.5, a dark fringe. Premultiplied alpha fixes it: multiply each color by its own alpha before blending so the transparent pixel contributes zero color weight, average in premultiplied space, then divide the color back out by the blended alpha, and the edge comes out full red 1.0 with the same alpha 0.5. The fringe is a 0.5 error in the red channel, and it appears wherever a soft or antialiased edge meets transparency, which is every cutout and every rendered glyph.
eli5: A see-through pixel still secretly has a color written down, usually black, even though you can't see it. If you mix it with a red neighbor to shrink a picture, that hidden black sneaks into the red and muddies the edge. The trick is to first fade each pixel's color by how see-through it is, so a fully see-through pixel adds no color at all, then mix, then un-fade. Now the edge stays bright.
---

## Why this module

Anything with a soft edge on a transparent background — a cutout sticker, an antialiased glyph, a rendered sprite, a masked layer — is stored as RGBA, color plus alpha. The moment you resize it, composite it, or filter it, you blend pixels together, and blending RGBA has a trap that produces a specific, recognizable artifact: a dark halo around every edge. This module builds that artifact on a single edge pixel, measures it, and builds the standard fix, premultiplied alpha, which every correct compositor uses and which is worth understanding because the bug is invisible until an edge meets transparency.

The trap is that a transparent pixel still has a stored color. Alpha zero means invisible, so its color is undefined and by convention tools write black. That black costs nothing as long as no arithmetic touches the color of a transparent pixel — but blending is exactly that arithmetic. Average an opaque red pixel with a transparent black one and the red channel comes out halfway to black, even though the transparent pixel contributes nothing you can see. The result is a color darker than any visible input, a dark fringe. Premultiplied alpha fixes it by weighting each color by its own alpha before the blend: a transparent pixel, multiplied by alpha zero, contributes zero color, so its black cannot bleed in. You average in that premultiplied space, then un-premultiply — divide the blended color by the blended alpha — to recover the straight color, which now comes out correct.

You need no prior module, though this is a cousin of the gamma-blending module: both are about doing pixel arithmetic in the right space. Everything runs offline against an RGBA fixture — one opaque pixel, one transparent pixel — stdlib Python 3, `$0.00`. The instinct to unlearn is that a transparent pixel's color does not matter. Its color is invisible, but it is still a number, and the moment you average it in, its invisibility is exactly what makes the bug hard to see coming.

Here is the fringe, on one edge pixel:

```
# modules/generative-media/code/media-inter-05/ — COMPLETE, run from that directory
$ python3 alpha.py --blend

BLEND — average an opaque-red pixel with a transparent one (the edge)
------------------------------------------------------------------
  inputs:        [1.00, 0.00, 0.00  a=1.00]  +  [0.00, 0.00, 0.00  a=0.00]
  straight avg:  [0.50, 0.00, 0.00  a=0.50]   <- red channel darkened to 0.50
  premultiplied: [1.00, 0.00, 0.00  a=0.50]   <- red channel stays 1.00
```

run: 2026-08-26 · deterministic; RGBA values are a fixture · 2 pixels · `python3 alpha.py --blend`

<svg viewBox="0 0 700 150" role="img" aria-label="Two horizontal strips showing a red shape fading to transparent across an edge. The straight strip has a dark band at the edge (the fringe). The premultiplied strip fades cleanly from red to transparent with no dark band.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the edge of a red shape fading into transparency</text>
    <text x="20" y="48" fill="var(--s2)" font-size="8">straight</text>
    <rect x="120" y="34" width="140" height="24" fill="var(--s1)"></rect>
    <rect x="260" y="34" width="60" height="24" fill="var(--muted)"></rect>
    <rect x="320" y="34" width="140" height="24" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="290" y="72" text-anchor="middle" fill="var(--s2)" font-size="7">dark fringe band</text>
    <text x="20" y="108" fill="var(--s1)" font-size="8">premul</text>
    <rect x="120" y="94" width="140" height="24" fill="var(--s1)"></rect>
    <rect x="260" y="94" width="60" height="24" fill="var(--s1)" opacity="0.5"></rect>
    <rect x="320" y="94" width="140" height="24" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="290" y="132" text-anchor="middle" fill="var(--s1)" font-size="7">clean fade, no band</text>
  </g>
</svg>
^ Straight blending inserts a dark band where color meets transparency; premultiplied fades the same edge cleanly. The only difference is whether the transparent pixels' black was allowed into the color.

Straight averaging drops the visible red from 1.0 to 0.5; premultiplied keeps it at 1.0, with the identical alpha of 0.5. This module is where that 0.5 darkening comes from and why premultiplying removes it.

## Concepts

Named here so you can find them again; each is built below.

- **RGBA** — a pixel's color plus its alpha (opacity); the color of a transparent pixel is undefined.
- **Straight (non-premultiplied) alpha** — color stored independently of alpha; the usual file format.
- **Premultiplied alpha** — color scaled by alpha, so a transparent pixel carries zero color weight.
- **Dark fringe** — the halo from blending a transparent pixel's stored black into the visible color.
- **Un-premultiply** — dividing the blended color back out by the blended alpha to recover straight color.
- **Blend correctness** — the recovered edge color must match the opaque source, not darken toward black.

## Worked example

Source: the premultiplied-alpha convention every correct compositor and GPU uses (Porter-Duff compositing, and the reason image libraries premultiply before resizing RGBA); the RGBA values here stand in for a real edge so the fringe is exact and checkable.

Script and fixture: `modules/generative-media/code/media-inter-05/` — `alpha.py`, and `rgba.json`, an opaque red pixel and a transparent pixel to average into one. Every command runs from there.

### The setup: a transparent pixel is not colorless

The fixture is the edge of a red shape: one opaque red pixel next to one fully transparent pixel whose stored color is black. Averaging them is what a 2× downsample does at that edge.

```
# alpha.py:50-53 — COMPLETE (channel-wise mean of RGBA pixels)
def average(pixels):
    """Channel-wise mean of a list of [r,g,b,a] pixels."""
    n = len(pixels)
    return [sum(px[c] for px in pixels) / n for c in range(4)]
```

The average function is innocent — it is the same box filter as any downsample. The problem is what it is fed. The transparent pixel's stored color is `[0, 0, 0]`, black, because alpha zero made its color meaningless to store. Average that black into the red and the red channel halves. The average did nothing wrong; the data it averaged carried an invisible black that should never have entered a color computation.

### The bug: straight averaging

Blending the stored RGBA directly is the straightforward, wrong approach.

```
# alpha.py:58-60 — COMPLETE (the bug: average non-premultiplied RGBA directly)
def blend_straight(pixels):
    """The bug: average the stored (non-premultiplied) RGBA directly."""
    return average(pixels)
```

It returns `[0.5, 0, 0, 0.5]`: a red of 0.5 at alpha 0.5. When that pixel is later composited onto a background, its visible color is that 0.5 red — a dark, muddy red where the edge should be a clean, half-transparent full red. Do this along a whole antialiased edge and you get a dark halo tracing every boundary between the shape and transparency. The darkening is proportional to how much transparent area a blend touches, so it is worst exactly at soft edges, where transparency and color meet.

### The fix: premultiply, blend, un-premultiply

Premultiplied alpha weights each color by its own alpha before blending, so a transparent pixel adds no color.

```
# alpha.py:36-47 — COMPLETE (premultiply and its inverse)
def premultiply(px):
    """Scale color by alpha: a transparent pixel's color becomes zero-weighted."""
    r, g, b, a = px
    return [r * a, g * a, b * a, a]


def unpremultiply(px):
    """Divide color back out by alpha; a zero-alpha pixel stays transparent (color undefined)."""
    r, g, b, a = px
    if a == 0:
        return [0.0, 0.0, 0.0, 0.0]
    return [r / a, g / a, b / a, a]
```

Premultiplying the red pixel leaves it `[1, 0, 0, 1]` (alpha 1, no change), and premultiplying the transparent pixel gives `[0, 0, 0, 0]` — its black is now weighted by alpha zero, so it contributes nothing. The blend runs in premultiplied space and un-premultiplies at the end.

```
# alpha.py:63-66 — COMPLETE (premultiply, average, then un-premultiply)
def blend_premultiplied(pixels):
    """Premultiply, average in premultiplied space, then un-premultiply."""
    pm = [premultiply(px) for px in pixels]
    return unpremultiply(average(pm))
```

The premultiplied average is `[0.5, 0, 0, 0.5]` — red 0.5, alpha 0.5 — and un-premultiplying divides the color by the alpha: `0.5 / 0.5 = 1.0`. The edge comes out full red, alpha 0.5. The transparent pixel's black never reached the visible color, because it was zeroed out before the average and the division restored the straight color afterward. Same downsample, same alpha, no fringe.

<svg viewBox="0 0 700 210" role="img" aria-label="Two paths for averaging red (alpha 1) with transparent black (alpha 0). Straight path: average colors directly, red goes to 0.5, dark fringe. Premultiplied path: red stays 1,0,0; transparent becomes 0,0,0 weighted by alpha 0; average premultiplied gives 0.5 red at 0.5 alpha; un-premultiply divides 0.5 by 0.5 to recover 1.0 red, no fringe.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">averaging opaque red with transparent black — two paths</text>
    <text x="30" y="52" fill="var(--s2)" font-size="9">straight</text>
    <rect x="30" y="60" width="46" height="22" fill="var(--panel)" stroke="var(--line)"></rect><text x="53" y="75" text-anchor="middle" fill="var(--ink)">red a1</text>
    <rect x="86" y="60" width="60" height="22" fill="var(--panel)" stroke="var(--line)"></rect><text x="116" y="75" text-anchor="middle" fill="var(--ink)">black a0</text>
    <path d="M 150 71 L 200 71" stroke="var(--muted)"></path><text x="175" y="66" text-anchor="middle" fill="var(--muted)" font-size="7">avg</text>
    <rect x="204" y="60" width="90" height="22" fill="var(--panel)" stroke="var(--s2)"></rect><text x="249" y="75" text-anchor="middle" fill="var(--s2)">red 0.50 (dark)</text>
    <text x="310" y="75" fill="var(--s2)" font-size="8">&lt;- fringe</text>
    <text x="30" y="122" fill="var(--s1)" font-size="9">premultiplied</text>
    <rect x="30" y="130" width="46" height="22" fill="var(--panel)" stroke="var(--line)"></rect><text x="53" y="145" text-anchor="middle" fill="var(--ink)">1,0,0</text>
    <rect x="86" y="130" width="60" height="22" fill="var(--panel)" stroke="var(--line)"></rect><text x="116" y="145" text-anchor="middle" fill="var(--ink)">0,0,0 (×a0)</text>
    <path d="M 150 141 L 200 141" stroke="var(--muted)"></path><text x="175" y="136" text-anchor="middle" fill="var(--muted)" font-size="7">avg</text>
    <rect x="204" y="130" width="90" height="22" fill="var(--panel)" stroke="var(--line)"></rect><text x="249" y="145" text-anchor="middle" fill="var(--ink)">0.5 red, a0.5</text>
    <path d="M 298 141 L 348 141" stroke="var(--muted)"></path><text x="323" y="136" text-anchor="middle" fill="var(--muted)" font-size="7">÷a</text>
    <rect x="352" y="130" width="100" height="22" fill="var(--panel)" stroke="var(--s1)"></rect><text x="402" y="145" text-anchor="middle" fill="var(--s1)">red 1.00 (clean)</text>
    <text x="30" y="190" fill="var(--muted)" font-size="8">weighting color by alpha before the average is what stops the black from bleeding in</text>
  </g>
</svg>
^ Straight averaging lets the transparent pixel's black halve the red. Premultiplying zeroes that black before the average, and un-premultiplying restores the color — full red at half alpha, no fringe.

**A transparent pixel's stored color is invisible but still enters any blend, so averaging straight RGBA bleeds its black into the visible color as a dark fringe — premultiply each color by its alpha before blending so a transparent pixel contributes zero color, then un-premultiply to recover the correct edge.**

### The self-test

The `--check` mode asserts the fringe and the fix: premultiplied recovers the source red, straight darkens it, both agree on alpha, and the error is substantial.

```
# $ python3 alpha.py --check
#   premultiplied edge red == opaque source red = True (1.00 == 1.00)
#   straight edge red is darker than the source = True (0.50 < 1.00)
#   both methods agree on the blended alpha = True (0.50)
#   the dark-fringe error is substantial = True (red off by 0.50)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 alpha.py --check`

The two decisive assertions compare each method's edge red against the opaque source:

```
# alpha.py:95-99 — COMPLETE (premultiplied matches the source; straight darkens)
    premul_correct = abs(p[0] - opaque_red) < 1e-9

    straight_darkens = s[0] < opaque_red - 1e-9
```

`premul_correct` demands the premultiplied red equal the source (1.0); `straight_darkens` demands the straight red fall below it — the fringe present in one method and absent in the other.

The `premul_correct` line is the correctness anchor: the premultiplied edge's red must equal the opaque source's red exactly, because the transparent pixel should not affect the visible color at all, and if the premultiply or the division were wrong that equality would break. The `same_alpha` line confirms the fix changes only the color, not the coverage — both methods produce alpha 0.5, so premultiplying is not hiding the transparency, only correcting the color that transparency corrupted.

### The running tally

| method | edge red | edge alpha | visible result |
|---|---|---|---|
| straight (non-premultiplied) | 0.50 | 0.50 | dark red fringe |
| premultiplied | 1.00 | 0.50 | clean half-transparent red |

<svg viewBox="0 0 700 150" role="img" aria-label="Two bars for the edge red channel against the source red of 1.0 (dashed line). Straight: bar at 0.5, well below the line. Premultiplied: bar at 1.0, exactly on the line. Both labelled alpha 0.5.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="18" fill="var(--muted)">edge red channel vs the opaque source (1.0)</text>
    <line x1="540" y1="28" x2="540" y2="128" stroke="var(--acc)" stroke-dasharray="4 3"></line>
    <text x="540" y="142" text-anchor="middle" fill="var(--acc-ink)" font-size="8">source 1.0</text>
    <text x="20" y="52" fill="var(--ink)">straight</text><rect x="150" y="40" width="195" height="18" fill="var(--s2)"></rect><text x="352" y="54" fill="var(--s2)" font-size="9">0.50 (a=0.5)</text>
    <text x="20" y="92" fill="var(--ink)">premultiplied</text><rect x="150" y="80" width="390" height="18" fill="var(--s1)"></rect><text x="548" y="94" fill="var(--s1)" font-size="9">1.00 (a=0.5)</text>
    <text x="150" y="122" fill="var(--muted)" font-size="8">same alpha, different color — a pure color-space bug</text>
  </g>
</svg>
^ The premultiplied bar lands on the source line; the straight bar falls to half. Identical alpha, so the transparency is fine — only the color was corrupted, and only premultiplying protects it.

The two rows share an alpha of 0.5 — the same coverage, the same softness of edge — and differ only in the visible color. Straight gives 0.5 red, a color halfway to black that no input pixel had; premultiplied gives 1.0 red, the true color of the opaque side, correctly shown at half opacity. The alpha being identical is the tell that this is purely a color-space bug: the transparency was never in question, only whether the invisible black was allowed to contaminate the color, and premultiplying is the discipline that forbids it.

### What we did not settle

Premultiplied alpha is a whole convention, not a single trick. Compositing operators (the Porter-Duff "over", "in", "out", and friends) are all defined in premultiplied space, where they reduce to simple linear combinations; that is much of why GPUs and compositors store premultiplied. Un-premultiplying loses precision at low alpha — dividing by a tiny alpha amplifies rounding — so pipelines often stay premultiplied end to end and only un-premultiply at display. And this stacks with the gamma module: strictly, you premultiply and blend in linear light, so a fully correct edge does both. The core here — weight color by alpha before any blend — is the invariant; the operators and the linear-light pairing build on it.

## Build

The practice in one paragraph: never blend, resize, or filter straight RGBA; premultiply each pixel's color by its alpha first, do the arithmetic in premultiplied space, and un-premultiply only when you need straight color back (ideally just at display); test on an edge where opaque color meets transparency, checking that the blended visible color matches the opaque source rather than darkening toward the transparent pixel's stored black. Combine with linear-light blending for a fully correct edge.

We opened on the fringe. The number that proves the fix is the recovered edge red:

```
# modules/generative-media/code/media-inter-05/ — COMPLETE, run from that directory
$ python3 alpha.py --blend
  straight avg:  [0.50, 0.00, 0.00  a=0.50]
  premultiplied: [1.00, 0.00, 0.00  a=0.50]
```

Now do it to a real cutout. Take an image with a soft alpha edge, downscale it two ways — average straight RGBA, and premultiply-average-unpremultiply — and inspect the edge pixels. Your number to beat is not sharpness; it is **the visible-color difference at the edge between the two methods, which straight averaging darkens and premultiplying keeps true to the opaque source**. Look for the dark halo in the straight version. Bring back both edges and the color gap. Good luck.

## Definition of done

- [ ] An RGBA edge where an opaque color meets a transparent (black-stored) pixel
- [ ] A straight blend averaging the non-premultiplied RGBA
- [ ] A premultiplied blend: premultiply, average, un-premultiply
- [ ] Confirmation the premultiplied edge color matches the opaque source
- [ ] Confirmation the straight edge color is darkened (the fringe), with both alphas equal
- [ ] `python3 alpha.py --check` printing SELF-TEST PASS: premul-correct, straight-darkens, same-alpha, real-fringe
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does a fully transparent pixel still have a stored color, and why is that color harmless until you blend?
2. Averaging an opaque red pixel with a transparent black one gives red 0.5. Explain where the darkening comes from.
3. How does premultiplying stop the transparent pixel's black from bleeding into the visible color?
4. The two methods agreed on alpha but not on color. Why does that tell you it is a color-space bug, not a transparency one?
5. Your own cutout was downscaled both ways. What was the edge-color difference, and where was the dark halo visible?

## External resources

- Porter & Duff, *Compositing Digital Images* (1984) — my summary: the paper defining alpha compositing in premultiplied space, where the over operator and its siblings become simple linear combinations; read it for why premultiplied alpha is the native space for compositing.
- Image-library notes on premultiplied alpha and resizing (e.g. Pillow, skia) — my summary: how libraries premultiply before resampling RGBA to avoid fringing, and the precision tradeoff of un-premultiplying at low alpha; read it for the production handling of the bug here.
- This hub, *media-inter-04* — modules/generative-media/media-inter-04.md — my summary: the gamma-blending module, the other case where pixel arithmetic must happen in the right space (linear light) or the blend is wrong; read it for the pairing — a fully correct edge premultiplies and works in linear light.
