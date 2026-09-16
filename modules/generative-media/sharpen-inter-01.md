---
id: sharpen-inter-01
title: Sharpen by adding back the detail a blur removed — raising the contrast just stretches everything
topic: generative-media
level: intermediate
status: ready
time: 20 min
summary: "Make it sharper" tempts an obvious move — turn up the contrast — but global contrast is a point operation that decides each pixel from its own value alone. It pushes darks darker and brights brighter across the whole image, changing every pixel including the flat regions, and it cannot add local sharpness: a smooth ramp stays a smooth ramp. Unsharp masking is the real thing — blur to get the low frequencies, subtract to recover the detail (detail = signal − blur), add a scaled copy back. On a flat-edge-flat signal, unsharp leaves the four flat pixels exactly 10 and 30 and turns the edge into 5 then 35 — an overshoot past the original range, the halo the eye reads as crisp. Global contrast rewrites all six pixels to 5 and 35, flat regions and all, with no localized halo.
eli5: If a picture looks soft and you just crank the contrast, you make the dark parts darker and the bright parts brighter everywhere — but the fuzzy edges are still fuzzy. Real sharpening finds where the picture changes (the edges) and pushes just those spots harder, so edges pop while smooth areas stay smooth. It does that by comparing the picture to a blurry copy of itself and adding back the difference.
---

## Why this module

Sharpness lives at edges, and the obvious "sharpen" knob — contrast — is blind to where the edges are.

Turn up the contrast and each pixel is remapped by its own value alone: darks go darker, brights go brighter, by a fixed rule applied everywhere. That is a point operation. It changes the overall look, but it cannot make a soft edge crisp, because it has no idea which pixels are near an edge and which sit in a flat region. A smooth ramp comes out a steeper smooth ramp — still smooth. Meanwhile every flat pixel gets shoved too, shifting the whole tonal balance for no gain in acutance.

**Contrast is a point operation; sharpness is a spatial phenomenon, so contrast can never actually sharpen.**

Unsharp masking is the operation that does. Blur the image to isolate its low frequencies, subtract that from the original to recover the high-frequency detail, then add a scaled copy of the detail back. In a flat region the blur equals the signal, so the detail is exactly zero and the pixel is left alone. At an edge the detail is large, and adding it back overshoots — the characteristic halo. This module builds both on one signal and measures which one is really sharpening.

## Concepts

Work in 1D — a single scanline standing in for an image, which shows the mechanism without pixel bookkeeping. The signal is a flat run at 10, a step up to 30, and a flat run at 30.

A **blur** is a local average. Here it is a normalized `[1, 2, 1] / 4` kernel: each pixel becomes a weighted average of itself and its two neighbors. In a flat run the average equals the value; near the edge it splits the difference, softening the step.

The **detail** is what the blur threw away: `detail = signal − blur`. It is the high-frequency content. In a flat run, blur equals signal, so detail is exactly zero. At the edge, detail is large and signed — negative on the low side, positive on the high side.

**Unsharp masking** is `sharpened = signal + amount × detail`. Since detail is zero in flat runs, those pixels are untouched. At the edge, adding the detail back pushes the low side lower and the high side higher — past the original range. That overshoot is the **halo**, and it is exactly what the visual system reads as "crisp."

**Global contrast** is `(value − mean) × k + mean` — a point operation that stretches every pixel away from the mean, flat regions included, with no notion of edges.

**Unsharp masking touches a pixel only in proportion to how much its neighborhood varies; a flat neighborhood means zero change.**

The whole method is one subtraction and one addition: split the signal into blur plus detail, then put the detail back with extra weight.

<svg role="img" aria-label="Signal equals blur plus detail; detail is flat at zero except a dip and spike at the edge" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="20" fill="var(--muted)" font-size="9">blur</text>
  <polyline points="55,40 95,40 135,32 175,24 215,16 255,16" fill="none" stroke="var(--muted)" stroke-width="1.5"/>
  <text x="120" y="55" fill="var(--muted)" font-size="10">+</text>
  <text x="10" y="80" fill="var(--muted)" font-size="9">detail</text>
  <line x1="55" y1="85" x2="255" y2="85" stroke="var(--grid)" stroke-width="0.8" stroke-dasharray="2 2"/>
  <polyline points="55,85 115,85 135,98 155,72 215,85 255,85" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="140" y="112" fill="var(--s1)" font-size="8">dip / spike only at the edge</text>
  <text x="200" y="80" fill="var(--muted)" font-size="8">0 in flats</text>
</svg>
^ Any signal splits into a smooth blur plus a detail that is zero in flat runs and swings only at edges; unsharp masking re-adds that detail, amplifying the swing.

The tell is not that one steepens the edge and the other doesn't — both raise the edge gradient. The tell is what each does to the flat regions and whether the edge overshoots its original range.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/sharpen-inter-01/sharpen.py

The fixture is one signal plus the two strengths. Every transform is computed.

```json filename=modules/generative-media/code/sharpen-inter-01/signal.json:1-6 COMPLETE
{
  "_meta": "A 1D brightness signal with a flat region, a step edge, and another flat region -- a single scanline standing in for an image. amount is the unsharp-mask strength (how much high-frequency detail to add back); contrast_k is the multiplier for the naive global-contrast comparison.",
  "signal": [10, 10, 10, 30, 30, 30],
  "amount": 1.0,
  "contrast_k": 1.5
}
```

The blur is a three-tap average with replicate padding at the borders; the detail is what it removed.

```python filename=modules/generative-media/code/sharpen-inter-01/sharpen.py:40-53 COMPLETE
def blur(sig):
    """A normalized [1,2,1]/4 smoothing with replicate padding at the borders."""
    out = []
    for i in range(len(sig)):
        left = sig[i - 1] if i > 0 else sig[i]
        right = sig[i + 1] if i < len(sig) - 1 else sig[i]
        out.append((left + 2 * sig[i] + right) / 4.0)
    return out


def detail(sig):
    """The high-frequency part the blur removed: signal minus blur."""
    b = blur(sig)
    return [sig[i] - b[i] for i in range(len(sig))]
```

Unsharp adds the detail back; contrast stretches about the mean. Two lines, two philosophies.

```python filename=modules/generative-media/code/sharpen-inter-01/sharpen.py:56-65 COMPLETE
def unsharp(sig, amount):
    """Add the detail back, scaled by amount: sharpened = signal + amount * detail."""
    d = detail(sig)
    return [sig[i] + amount * d[i] for i in range(len(sig))]


def contrast(sig, k):
    """A global point operation: push every pixel away from the mean by factor k."""
    m = sum(sig) / len(sig)
    return [(v - m) * k + m for v in sig]
```

Run `--sharpen` and lay the two side by side.

```text filename=--sharpen
SHARPEN — unsharp mask (amount 1.0) vs global contrast (k 1.5)
----------------------------------------------------------
  signal:      10.0  10.0  10.0  30.0  30.0  30.0
  blur:        10.0  10.0  15.0  25.0  30.0  30.0
  detail:       0.0   0.0  -5.0   5.0   0.0   0.0   (signal - blur)
  unsharp:     10.0  10.0   5.0  35.0  30.0  30.0   signal + 1.0*detail
  contrast:     5.0   5.0   5.0  35.0  35.0  35.0   (v - mean)*1.5 + mean
----------------------------------------------------------
  detail is 0 in the flat runs; unsharp only moves the edge.
```

Read the detail row: zero everywhere except the two pixels straddling the edge. Unsharp adds it back, so the flat runs stay 10 and 30 and only the edge moves — down to 5, up to 35. Contrast, by contrast, rewrites all six pixels; the flat runs become 5 and 35 too.

<svg role="img" aria-label="Three scanlines: signal steps 10 to 30; unsharp keeps flats and overshoots the edge to 5 and 35; contrast shifts all pixels to 5 and 35" viewBox="0 0 300 150" width="300" height="150">
  <text x="10" y="20" fill="var(--muted)" font-size="9">signal</text>
  <polyline points="60,45 100,45 140,45 140,20 180,20 220,20 260,20" fill="none" stroke="var(--muted)" stroke-width="1.5"/>
  <text x="10" y="75" fill="var(--muted)" font-size="9">unsharp</text>
  <polyline points="60,100 100,100 120,100 120,110 140,90 140,60 160,60 180,70 220,70 260,70" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="270" y="65" fill="var(--s1)" font-size="8">↑35</text>
  <text x="270" y="115" fill="var(--s1)" font-size="8">↓5</text>
  <text x="10" y="135" fill="var(--muted)" font-size="9">contrast</text>
  <polyline points="60,130 100,130 140,130 140,125 180,125 220,125 260,125" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="60" y="148" fill="var(--muted)" font-size="8">flat runs shifted (10→5, 30→35)</text>
</svg>
^ Unsharp holds the flat runs and spikes only at the edge (the halo overshoot); contrast lifts and drops every pixel, flat runs included, with no localized spike.

## Build

The `--edges` view counts what each method did to the flat pixels and reports the ranges.

```text filename=--edges
EDGES — flat-region change and edge overshoot
----------------------------------------------------------
  flat pixels (detail==0): indices [0, 1, 4, 5]
  unsharp changed flat pixels:  0
  contrast changed flat pixels: 4
  original range [10.0, 30.0]
  unsharp range  [5.0, 35.0]  (overshoots the edge)
  contrast range [5.0, 35.0]
----------------------------------------------------------
  max adjacent gradient: signal 20.0  unsharp 30.0  contrast 30.0
```

Unsharp changed zero of the four flat pixels; contrast changed all four. Both reach the same range [5, 35] and the same max gradient of 30 — proof that "steeper edge" alone does not distinguish them. The difference is where that range came from: unsharp reached 5 and 35 only at the edge, as an overshoot, while leaving the flats put; contrast reached 5 and 35 by dragging the flats there.

<svg role="img" aria-label="Bar chart of flat pixels changed: unsharp 0 of 4, contrast 4 of 4" viewBox="0 0 300 110" width="300" height="110">
  <line x1="90" y1="15" x2="90" y2="85" stroke="var(--grid)" stroke-width="1"/>
  <line x1="90" y1="85" x2="285" y2="85" stroke="var(--grid)" stroke-width="1"/>
  <rect x="95" y="30" width="4" height="16" fill="var(--s1)"/>
  <text x="10" y="42" fill="var(--muted)" font-size="9">unsharp</text>
  <text x="105" y="42" fill="var(--muted)" font-size="9">0 of 4</text>
  <rect x="95" y="58" width="180" height="16" fill="var(--s2)"/>
  <text x="10" y="70" fill="var(--muted)" font-size="9">contrast</text>
  <text x="120" y="70" fill="var(--panel)" font-size="9">4 of 4 flat pixels changed</text>
</svg>
^ Flat-region pixels changed by each method: unsharp masking leaves them untouched; global contrast rewrites every one.

## Definition of done

The self-test pins all five signatures: unsharp leaves flats exactly unchanged, contrast changes them, unsharp overshoots the original range, both steepen the edge, and detail is zero-in-flat / nonzero-at-edge.

```python filename=modules/generative-media/code/sharpen-inter-01/sharpen.py:115-130 COMPLETE
    unsharp_leaves_flat = all(u[i] == sig[i] for i in flat)
    print("  unsharp leaves every flat pixel unchanged = %s (flat indices %s)" % (unsharp_leaves_flat, flat))

    contrast_changes_flat = any(c[i] != sig[i] for i in flat)
    print("  contrast changes flat pixels = %s (e.g. index %d: %.1f -> %.1f)"
          % (contrast_changes_flat, flat[0], sig[flat[0]], c[flat[0]]))

    unsharp_overshoots = min(u) < min(sig) and max(u) > max(sig)
    print("  unsharp overshoots the original range (the halo) = %s ([%.1f,%.1f] vs [%.1f,%.1f])"
          % (unsharp_overshoots, min(u), max(u), min(sig), max(sig)))

    both_steepen_edge = max_gradient(u) > max_gradient(sig) and max_gradient(c) > max_gradient(sig)
    print("  both raise the edge gradient = %s (%.1f -> unsharp %.1f, contrast %.1f)"
          % (both_steepen_edge, max_gradient(sig), max_gradient(u), max_gradient(c)))

    detail_zero_in_flat = all(d[i] == 0 for i in flat) and any(d[i] != 0 for i in range(len(sig)))
    print("  detail is zero in flat runs, nonzero at the edge = %s" % detail_zero_in_flat)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — unsharp leaves flat regions exactly unchanged and overshoots the edge; contrast rewrites all
--------------------------------------------------------------------------------------------------------
  unsharp leaves every flat pixel unchanged = True (flat indices [0, 1, 4, 5])
  contrast changes flat pixels = True (e.g. index 0: 10.0 -> 5.0)
  unsharp overshoots the original range (the halo) = True ([5.0,35.0] vs [10.0,30.0])
  both raise the edge gradient = True (20.0 -> unsharp 30.0, contrast 30.0)
  detail is zero in flat runs, nonzero at the edge = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  unsharp_leaves_flat=True  contrast_changes_flat=True  unsharp_overshoots=True  both_steepen_edge=True  detail_zero_in_flat=True
```

**Done means the distinction is provable, not visual: unsharp changed 0 of 4 flat pixels and overshot to [5, 35] at the edge, while contrast changed all 4 — even though both reach the same range and gradient.**

## Boss fight

The `both_steepen_edge` flag is a trap laid for the eye. Predict which method a reviewer would call "sharper" if you only showed them the edge gradient. Both hit 30 — so by that metric they tie, and the naive conclusion is that contrast sharpens just as well.

It does not, and the fixture shows why the gradient metric misleads. A larger edge gradient can come from lifting the whole signal apart (contrast) or from a local overshoot (unsharp). Only the overshoot produces the acutance the visual system reads as crisp; the global stretch just changes exposure. If you turn the amount up, unsharp's halo grows without touching the flats, while turning k up on contrast blows out the flats and clips before the edge looks any sharper. Push `amount` to 2.0 in `signal.json` and rerun `--sharpen`: the edge goes to 0 and 40, the flats stay 10 and 30.

The mirror-image failure is unsharp masking with too much amount or on a noisy signal. Because detail includes any local variation, a big amount amplifies sensor noise and turns the edge halo into a visible ring. Sharpening is a dial with a sweet spot, not a free lunch — the point is that it is the right dial, acting where edges are, which contrast is not.

```python filename=modules/generative-media/code/sharpen-inter-01/sharpen.py:62-65 COMPLETE
def contrast(sig, k):
    """A global point operation: push every pixel away from the mean by factor k."""
    m = sum(sig) / len(sig)
    return [(v - m) * k + m for v in sig]
```

**Judge a sharpener by what it does to flat regions, not by the edge gradient: a point operation can match the gradient while doing none of the local work that makes an edge look crisp.**

## External resources

Gonzalez and Woods, "Digital Image Processing", the spatial-filtering chapter — unsharp masking and highboost filtering derived as `original + k × (original − blurred)`, with the halo/overshoot discussion.

The GIMP and Photoshop "Unsharp Mask" documentation — the radius, amount, and threshold controls map directly onto the blur kernel size, the `amount`, and a floor below which detail is ignored (to avoid amplifying noise).

Any signals text on high-pass vs point operations — why a point (memoryless) mapping cannot change local frequency content, which is the formal statement of why contrast can't sharpen.
