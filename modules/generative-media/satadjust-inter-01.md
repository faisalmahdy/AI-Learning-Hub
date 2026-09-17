---
id: satadjust-inter-01
title: Adjust saturation by scaling channels around the pixel's luma — scaling the raw RGB values shifts brightness and clips instead
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Saturation is how far a color sits from gray, and the gray a color should collapse toward is its own luma — its perceived brightness, a weighted sum of the channels where green counts most and blue least. Changing saturation means moving the channels toward or away from that gray point while leaving the brightness where it was, and the operation that does this is new = luma + factor·(channel − luma): at factor 0 the pixel becomes its gray luma, at factor 1 it is unchanged, above 1 it is pushed further from gray, and for any factor the luma is preserved because the same luma is added back to every channel. The naive approach — multiply each channel by the factor — looks like it should boost saturation because the numbers grow, but it does the wrong thing twice: it scales the color's brightness along with its chroma, so a "more saturated" image comes out glaringly brighter, and channels that exceed 255 are clipped, and clipping different channels by different amounts twists the hue too. The difference is exactly the luma: the luma-preserving formula holds brightness fixed at the original value no matter the factor, while channel scaling multiplies the luma by the factor so brightness rides along with saturation. On a fixture pushing a pixel to 1.5× saturation, the luma-preserving formula keeps the luma at 124.2 and stays in range, while multiplying the channels raises the luma to 172.8 and clips a channel past 255.
eli5: Imagine you want to make a photo's colors more vivid — punchier reds and blues — without making the whole picture brighter or darker. The wrong way is to just crank every color number up by, say, half again as much. The colors do get more intense, but the whole image also gets much brighter, and the strongest colors slam into the ceiling and get stuck at maximum, which quietly changes their shade. The right way is to think of each pixel's own "brightness level" as an anchor, and push its colors away from that anchor to make them more vivid, while keeping the anchor itself fixed. That way the picture gets more colorful but stays exactly as bright as before, and nothing crashes into the ceiling. Vividness and brightness are two separate dials, and the trick is to turn one without turning the other.
---

## Why this module

Saturation is one of the most common adjustments in any image editor, and it is the textbook case of two properties that feel independent to the eye but are entangled in the raw pixel values. Brightness and saturation are perceptually separate — you can imagine a color getting more vivid without getting brighter — but the RGB representation does not separate them, so a naive operation on the channels moves both at once.

The naive instinct is direct: to make colors more intense, make the channel values bigger, so multiply each by a factor above one. The numbers grow, the colors do look more saturated, and it seems to work. What it actually does is scale the entire color vector, including its length, and the length of the color vector is essentially its brightness. So the operation that was supposed to touch only saturation has dragged brightness along with it.

Worse, scaling pushes the largest channel past the representable maximum, where it clips, and because the channels clip by different amounts, the ratios between them change — which is the hue. A saturation slider built on channel multiplication is secretly a brightness slider with a hue glitch at the high end. This module adjusts one pixel both ways and measures the luma each method produces.

**Brightness and saturation feel independent but the raw RGB channels entangle them, so multiplying the channels to boost saturation also scales brightness and clips — the fix is to scale around the pixel's luma, which holds brightness fixed.**

## Concepts

The anchor that separates the two is luma — the weighted sum of the channels that models perceived brightness, with green weighted heavily and blue barely at all. Every pixel has a luma, and that luma is the gray it would become if fully desaturated. Saturation adjustment is then a move along the line between the pixel and its luma-gray: toward the gray to desaturate, away from it to saturate.

The formula new = luma + factor·(channel − luma) is exactly that move, and its key property is that it preserves luma for any factor. The reason is linear: the luma of the adjusted pixel is luma + factor·(luma_of_deviations), and the luma of the deviations (channel − luma) is zero by construction — the deviations are what is left after subtracting the luma, so their weighted sum cancels. So whatever the factor, the weighted brightness returns to the original. Brightness and saturation become two independent dials.

Channel scaling breaks this because it multiplies the whole pixel, luma included. The luma of factor·channel is factor·luma, so brightness scales with the factor — the two dials are welded together. That is the mathematical statement of the bug: the naive operation cannot change saturation without changing brightness, because it does not subtract the luma out before scaling and add it back after. The subtraction is the whole trick; it is what isolates the chroma from the brightness so the factor acts on chroma alone.

<svg role="img" aria-label="A color point and its gray luma point: the correct move slides the color along the line through its luma-gray, staying at the same brightness level, while channel scaling slides it toward the origin, dropping brightness toward black" viewBox="0 0 440 150">
<line x1="40" y1="120" x2="410" y2="120" stroke="var(--line)"/>
<line x1="40" y1="20" x2="40" y2="120" stroke="var(--line)"/>
<circle cx="70" cy="120" r="4" fill="var(--ink)"/>
<text x="70" y="135" fill="var(--muted)" font-size="8" text-anchor="middle">black (0)</text>
<circle cx="230" cy="70" r="5" fill="var(--ink)"/>
<text x="230" y="60" fill="var(--ink)" font-size="8" text-anchor="middle">color</text>
<circle cx="180" cy="70" r="4" fill="var(--muted)"/>
<text x="150" y="66" fill="var(--muted)" font-size="8" text-anchor="middle">its gray (luma)</text>
<line x1="130" y1="70" x2="330" y2="70" stroke="var(--s1)" stroke-dasharray="4 3"/>
<circle cx="300" cy="70" r="4" fill="var(--s1)"/>
<text x="320" y="66" fill="var(--s1)" font-size="8">around-luma: same brightness</text>
<line x1="70" y1="120" x2="300" y2="45" stroke="var(--s2)" stroke-dasharray="4 3"/>
<circle cx="335" cy="34" r="4" fill="var(--s2)"/>
<text x="360" y="30" fill="var(--s2)" font-size="8">naive: toward/away black</text>
</svg>
^ Around-luma slides the color along the constant-brightness line through its own gray; channel scaling slides it along the line to black, changing brightness.

**Luma is the gray a color desaturates to, and scaling the deviations from luma preserves it because those deviations have zero luma; channel scaling multiplies the luma too, welding brightness to saturation.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/satadjust-inter-01. The fixture is a color pixel, a saturation factor above 1, and the standard luma weights.

```json filename=modules/generative-media/code/satadjust-inter-01/satadjust.json:3-5 COMPLETE
  "pixel": [200, 100, 50],
  "factor": 1.5,
  "luma_weights": [0.299, 0.587, 0.114]
```

Luma is the weighted sum of the channels.

```python filename=modules/generative-media/code/satadjust-inter-01/satadjust.py:32-34 COMPLETE
def luma(pixel, weights):
    """Perceived brightness: the weighted sum of the channels (Rec. 601)."""
    return sum(w * c for w, c in zip(weights, pixel))
```

The correct adjustment moves each channel away from the luma by the factor.

```python filename=modules/generative-media/code/satadjust-inter-01/satadjust.py:37-40 COMPLETE
def saturate_around_luma(pixel, factor, weights):
    """Correct: move each channel away from the pixel's luma by the factor -- luma is preserved."""
    y = luma(pixel, weights)
    return [y + factor * (c - y) for c in pixel]
```

The naive adjustment multiplies each raw channel by the factor.

```python filename=modules/generative-media/code/satadjust-inter-01/satadjust.py:43-45 COMPLETE
def saturate_naive(pixel, factor):
    """Naive: multiply each raw channel by the factor -- scales brightness too, and may exceed 255."""
    return [c * factor for c in pixel]
```

Before running it, predict: scaling around luma should keep all channels in range, while naive scaling should push the red channel (200 × 1.5 = 300) past 255. Run `--adjust`:

```text filename=satadjust.py --adjust
ADJUST — pixel [200, 100, 50] at saturation factor 1.5
------------------------------------------------------------
  channel   original   around-luma   naive x1.5
  R         200        237.9         300.0
  G         100        87.9          150.0
  B         50         12.9          75.0
```

The prediction holds. Around-luma spreads the channels apart — R up to 237.9, B down to 12.9, more vivid — while all stay within 0 to 255. Naive scaling multiplies everything up, sending R to 300, which will clip to 255, and lifting every channel including the ones that should have moved toward gray.

<svg role="img" aria-label="Channel values for the pixel: original R200 G100 B50; around-luma spreads them to 238 88 13 staying under 255; naive scaling lifts all to 300 150 75 with red past the 255 ceiling" viewBox="0 0 440 170">
<line x1="40" y1="140" x2="410" y2="140" stroke="var(--line)"/>
<line x1="40" y1="30" x2="40" y2="140" stroke="var(--line)"/>
<line x1="40" y1="46" x2="410" y2="46" stroke="var(--s2)" stroke-dasharray="3 3"/>
<text x="405" y="42" fill="var(--s2)" font-size="8" text-anchor="end">255 ceiling</text>
<rect x="60" y="54" width="18" height="86" fill="var(--ink)"/>
<rect x="82" y="97" width="18" height="43" fill="var(--ink)"/>
<rect x="104" y="119" width="18" height="21" fill="var(--ink)"/>
<text x="91" y="155" fill="var(--muted)" font-size="8" text-anchor="middle">original</text>
<rect x="170" y="38" width="18" height="102" fill="var(--s1)"/>
<rect x="192" y="102" width="18" height="38" fill="var(--s1)"/>
<rect x="214" y="135" width="18" height="5" fill="var(--s1)"/>
<text x="201" y="155" fill="var(--muted)" font-size="8" text-anchor="middle">around-luma</text>
<rect x="290" y="12" width="18" height="128" fill="var(--s2)"/>
<rect x="312" y="76" width="18" height="64" fill="var(--s2)"/>
<rect x="334" y="108" width="18" height="32" fill="var(--s2)"/>
<text x="321" y="155" fill="var(--muted)" font-size="8" text-anchor="middle">naive x1.5</text>
<text x="299" y="9" fill="var(--s2)" font-size="8" text-anchor="middle">clips</text>
</svg>
^ Around-luma spreads the channels apart within range; naive scaling lifts every channel and drives red above the 255 ceiling.

Now the brightness each method produces. Run `--luma`:

```text filename=satadjust.py --luma
LUMA — perceived brightness before and after each method
------------------------------------------------------
  original luma            = 124.20
  around-luma luma         = 124.20  (change 0.00)
  naive (clipped) luma     = 172.84  (change +48.64)
```

The luma-preserving formula keeps the brightness at exactly 124.20 — the saturation changed, the brightness did not. Naive scaling raised the luma to 172.84, a 40% brightness jump on top of clipping, so the "saturation" adjustment was really a brightness adjustment in disguise.

<svg role="img" aria-label="Luma before and after: original and around-luma both at 124, naive at 173 much higher" viewBox="0 0 440 140">
<line x1="40" y1="110" x2="410" y2="110" stroke="var(--line)"/>
<rect x="70" y="48" width="60" height="62" fill="var(--ink)"/>
<text x="100" y="42" fill="var(--ink)" font-size="9" text-anchor="middle">orig 124</text>
<rect x="190" y="48" width="60" height="62" fill="var(--s1)"/>
<text x="220" y="42" fill="var(--ink)" font-size="9" text-anchor="middle">around 124</text>
<rect x="310" y="24" width="60" height="86" fill="var(--s2)"/>
<text x="340" y="18" fill="var(--ink)" font-size="9" text-anchor="middle">naive 173</text>
<text x="220" y="130" fill="var(--muted)" font-size="9" text-anchor="middle">same brightness twice, then a jump — the naive method moved the wrong dial</text>
</svg>
^ Around-luma leaves brightness at 124; naive scaling pushes it to 173, revealing that channel scaling is a brightness change wearing a saturation label.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that around-luma preserves the original luma and stays in range, that naive scaling clips a channel and changes the luma, and that around-luma really did increase saturation (the channel spread widened).

```python filename=modules/generative-media/code/satadjust-inter-01/satadjust.py:89-98 COMPLETE
    correct_preserves_luma = abs(luma(correct, w) - y0) < 1e-9
    print("  around-luma preserves the original luma = %s (%.2f)" % (correct_preserves_luma, luma(correct, w)))

    correct_in_range = all(0.0 <= c <= 255.0 for c in correct)
    print("  around-luma channels stay within 0..255 = %s" % correct_in_range)

    naive_clips = any(c > 255.0 for c in naive)
    print("  naive channel scaling pushes a channel past 255 = %s (%s)" % (naive_clips, [round(c, 1) for c in naive]))

    naive_changes_luma = abs(luma(clip(naive), w) - y0) > 1.0
    print("  naive (after clipping) changes the luma = %s (%.2f vs %.2f)" % (naive_changes_luma, luma(clip(naive), w), y0))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the around-luma formula ever stops preserving brightness or stops increasing saturation:

```text filename=satadjust.py --check
SELF-TEST — scaling around luma preserves brightness and stays in range; scaling raw channels shifts luma and clips
------------------------------------------------------------------------------------------------------------------------
  around-luma preserves the original luma = True (124.20)
  around-luma channels stay within 0..255 = True
  naive channel scaling pushes a channel past 255 = True ([300.0, 150.0, 75.0])
  naive (after clipping) changes the luma = True (172.84 vs 124.20)
  around-luma actually increases saturation (channel spread) = True
```

**The self-test asserts both that brightness is preserved and that saturation increased — proving the around-luma formula moved the right dial and only that dial, not that it simply left the pixel alone.**

## Definition of done

You can explain why brightness and saturation are perceptually separate but entangled in the raw RGB channels.
You can state the luma-preserving formula and show why it preserves luma — the deviations from luma have zero luma, so scaling them cannot change brightness.
You can explain why channel scaling welds brightness to saturation: it multiplies the luma by the factor.
You can name the two failures of naive scaling — a brightness shift and hue-distorting clipping — and say which channel clips first.
You can predict what factor 0 does (collapse to gray luma) and what factor 1 does (identity), and use the formula to desaturate as well as saturate.

## Boss fight

Take the factor to 0 and reason about it. Around-luma at factor 0 gives new = luma + 0·(channel − luma) = luma for every channel — the pixel collapses to a neutral gray at exactly its original brightness, which is the correct full desaturation. Channel scaling at factor 0 gives (0, 0, 0), pure black — it desaturates to the wrong thing, because scaling toward zero heads for black, not for the pixel's gray. The lesson sharpens across the whole range: the two methods agree only at factor 1 and diverge everywhere else, and the around-luma method is the one that means "saturation" at every setting, from full gray at 0 to boosted at 2.

Now consider gamma. This module worked in the stored (gamma-encoded) values, which is what most image code does and what most editors' saturation sliders do, but a physically correct luma is computed in linear light, not on the gamma-encoded codes. Doing the luma and the scaling in linear light changes the numbers and better preserves perceived brightness under large adjustments, at the cost of a linearize-and-re-encode round trip. The principle is unchanged — scale the deviations from luma, not the raw channels — but where you compute the luma (encoded versus linear) is a second correctness axis this module deliberately held fixed, and the more aggressive the adjustment the more the linear-light version matters.

**At factor 0 around-luma collapses to the pixel's gray while channel scaling collapses to black, so the two agree only at factor 1; and computing the luma in linear light rather than on the gamma-encoded codes is a second correctness axis that matters more the larger the adjustment.**

## External resources

Image-processing references describe saturation adjustment as scaling the chroma about the luma (or about the neutral axis in a luma/chroma space like YCbCr or HSL), which is the operation this module implements in RGB.
Poynton's "Digital Video and HD" explains luma, the Rec. 601 and 709 weights, and why perceptual brightness is a weighted sum with green dominant.
The topic's own modules on luma-weighted grayscale and on blending in linear light cover the two adjacent ideas — the luma weights themselves, and the encoded-versus-linear question raised in the boss fight.
