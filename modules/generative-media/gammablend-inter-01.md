---
id: gammablend-inter-01
title: Blend and resize colors in linear light, not in the gamma-encoded values — averaging pixel values directly comes out too dark
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: The 8-bit number stored for a pixel is not proportional to physical light. It is gamma-encoded — roughly the intensity raised to the power 1/2.2 — a perceptual curve that spends more of the 256 code values on darks, where the eye is more sensitive, so the image looks right on a display that applies the inverse curve. But physical light adds linearly, and the encoding is a curve, so any operation that mixes light — blending two colors, resizing (which averages neighboring pixels), alpha compositing, anti-aliasing — must be done on linear intensities, not on the stored gamma-encoded values. Average the encoded values directly and you are mixing in the wrong space: the arithmetic mean of two encoded values is not the encoded value of the mean intensity, because the curve is concave, so encoded midpoints sit below the true midpoint and the result is systematically too dark. The symptom is unmistakable once you know it — a 50/50 blend of black (0) and white (255) in gamma space gives mid-gray 128, which feels right but is wrong; the physically-correct blend decodes both to linear (0.0 and 1.0), averages to 0.5, and re-encodes to 186, a much lighter gray, a 58-level gap. The fix is three steps: decode each value to linear (linear = (v/255)^gamma), do the math on linear values, then encode back (encoded = 255 * result^(1/gamma)); the decode/encode round-trip is exact, so the only change is that the mixing happens where light actually adds. On a fixture blending black with white and 64 with 192, the naive gamma-space average is 128 for both while the correct linear-space blends are 186 and 146.
eli5: The brightness number stored for each dot in a picture is a little bit of a lie — it's stretched so that dark shades get more of the number range, because your eyes care more about darks. That's fine for showing the picture, but it means you can't just average two numbers to mix two colors. If you take black (0) and white (255) and average them, you get 128, a middle gray — which seems obviously right, but it actually comes out too dark, because of the stretch. To mix colors correctly you have to first "un-stretch" both numbers back to true brightness, average those, then "re-stretch" the answer — which gives 186, a noticeably lighter gray. This is why a lot of software makes images look muddy when it shrinks them or fades between colors: it mixed in the stretched space instead of the true one.
---

## Why this module

A pixel's stored value looks like it should mean "how bright" — 0 is off, 255 is full, 128 is halfway. The first two are right; the third is a trap. The stored value is gamma-encoded: it is roughly the physical intensity raised to the power 1/2.2, a deliberately non-linear curve. The encoding exists for a good reason — it allocates more of the 256 available code values to the dark tones the eye discriminates best, so 8 bits look smooth instead of banded — and displays undo it on the way to the screen. But it means the number and the light it stands for are related by a curve, not a straight line, and 128 is not half the light of 255.

That matters the moment you mix light. Blending two colors, resizing an image (the resampler averages neighboring pixels), alpha compositing a transparent layer, anti-aliasing an edge — every one of these adds and averages intensity, and intensity adds linearly in the physical world. If you do the averaging on the gamma-encoded values, you are averaging points on a curve, and the average of two points on a concave curve lies below the curve. The result is darker than the true mix, every time.

This module takes the simplest possible mix — a 50/50 blend of two colors — and runs it both ways: naively on the stored values, and correctly in linear light. The gap is not subtle.

**Pixel values are gamma-encoded, so averaging them directly mixes light in the wrong (non-linear) space and comes out systematically too dark — any operation that mixes light must decode to linear intensity, do the math there, and re-encode.**

## Concepts

The fixture is a gamma exponent and two pairs of 8-bit values to blend 50/50. One pair is the canonical black-and-white case; the other is two mid-tones.

```json filename=modules/generative-media/code/gammablend-inter-01/gammablend.json:3-8 COMPLETE
  "gamma": 2.2,
  "pairs": [
    {"a": 0, "b": 255},
    {"a": 64, "b": 192}
  ]
```

Two conversions define the encoding. Decoding takes a stored value to the linear intensity it represents by raising the normalized value to the power gamma; encoding does the inverse, raising the linear intensity to 1/gamma and scaling back to 8 bits. Gamma here is 2.2, the standard approximation to the sRGB curve.

```python filename=modules/generative-media/code/gammablend-inter-01/gammablend.py:34-41 COMPLETE
def decode(v, gamma):
    """Gamma-encoded 8-bit value -> linear intensity in [0, 1]."""
    return (v / 255.0) ** gamma


def encode(lin, gamma):
    """Linear intensity in [0, 1] -> gamma-encoded 8-bit value."""
    return round(255.0 * (lin ** (1.0 / gamma)))
```

The two blends differ only in where the averaging happens. The naive blend averages the stored values directly. The correct blend decodes both to linear, averages there, and re-encodes — the same arithmetic mean, but taken in the space where light actually adds.

```python filename=modules/generative-media/code/gammablend-inter-01/gammablend.py:44-51 COMPLETE
def naive_blend(a, b):
    """Average the encoded values directly -- the wrong space."""
    return round((a + b) / 2.0)


def linear_blend(a, b, gamma):
    """Decode to linear, average, re-encode -- the right space."""
    return encode((decode(a, gamma) + decode(b, gamma)) / 2.0, gamma)
```

The difference between these two functions is the whole module — one averages on the curve, the other averages under it.

<svg role="img" aria-label="A concave gamma curve mapping encoded value to linear intensity; the midpoint of two encoded values sits above the curve, so its linear value is higher than the naive encoded midpoint suggests" viewBox="0 0 320 150">
  <line x1="40" y1="20" x2="40" y2="120" stroke="var(--line)" stroke-width="1"/>
  <line x1="40" y1="120" x2="300" y2="120" stroke="var(--line)" stroke-width="1"/>
  <text x="2" y="24" font-size="7.5" fill="var(--muted)">linear</text>
  <text x="250" y="134" font-size="7.5" fill="var(--muted)">encoded value</text>
  <path d="M 40 120 Q 200 108 300 20" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <text x="250" y="42" font-size="7" fill="var(--s1)">gamma curve</text>
  <line x1="40" y1="120" x2="300" y2="20" stroke="var(--s2)" stroke-width="1" stroke-dasharray="3 3"/>
  <circle cx="170" cy="70" r="3" fill="var(--ink)"/>
  <text x="130" y="64" font-size="7" fill="var(--ink)">true mix (on curve)</text>
  <circle cx="170" cy="70" r="0"/>
  <circle cx="170" cy="70.5" r="0"/>
  <circle cx="170" cy="103" r="3" fill="var(--s2)"/>
  <text x="176" y="108" font-size="7" fill="var(--s2)">naive midpoint (too dark)</text>
</svg>
^ Encoded value maps to linear intensity along a concave curve. The naive blend takes the midpoint on the straight dashed line between the two encoded points, which falls below the curve — a lower linear intensity than the true mix. That gap below the curve is the darkening.

**Decoding raises the normalized value to gamma, encoding raises intensity to 1/gamma; the naive blend averages on the curve, the correct blend averages the decoded intensities and re-encodes.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the pixel-mixing step of an image pipeline, reduced to two blends so every value is checkable by hand.

Run `--decode` to see what the stored values actually mean in linear light.

```text filename=gammablend.py --decode
  value   0  ->  linear 0.0000
  value  64  ->  linear 0.0478
  value 192  ->  linear 0.5356
  value 255  ->  linear 1.0000
```

The endpoints behave as expected — 0 is no light, 255 is full light. The interior values reveal the curve. A stored 64, a quarter of the way up the code values, is only 0.0478 of the light — under a twentieth. A stored 192, three-quarters up, is 0.5356 — barely over half the light. The encoding has pushed enormous code range into the darks: most of the light lives in the top of the scale, and the numbers underneath it are compressed.

Now `--blend` runs both blends on both pairs.

```text filename=gammablend.py --blend
  pair        naive   correct   diff (correct - naive)
  (  0,255)   128     186       +58
  ( 64,192)   128     146       +18
```

Both pairs average to the same naive value, 128, because both pairs are symmetric around the midpoint of the code range — naive averaging only sees the stored numbers. But in linear light the pairs are not the same. Black and white average to linear 0.5, which encodes to 186: a blend 58 levels lighter than the naive 128. The mid-tones 64 and 192 average to linear 0.29, encoding to 146 — 18 levels lighter. The naive blend is too dark in both cases, and by different amounts, because the darkening depends on where on the curve the values sit.

<svg role="img" aria-label="For the black-white blend, a bar showing naive result at 128 and correct result at 186 on a 0 to 255 scale, with the correct value clearly lighter" viewBox="0 0 320 120">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">50/50 blend of black (0) and white (255), on a 0–255 scale</text>
  <rect x="20" y="30" width="255" height="14" fill="none" stroke="var(--line)"/>
  <line x1="148" y1="26" x2="148" y2="48" stroke="var(--s2)" stroke-width="2"/>
  <text x="112" y="60" font-size="8" fill="var(--s2)">naive 128</text>
  <line x1="206" y1="26" x2="206" y2="48" stroke="var(--s1)" stroke-width="2"/>
  <text x="190" y="74" font-size="8" fill="var(--s1)">correct 186</text>
  <text x="20" y="98" font-size="7.5" fill="var(--ink)">the naive blend sits 58 levels darker than the physically-correct one</text>
</svg>
^ On the 0–255 scale, the naive blend lands at 128 and the correct linear-space blend at 186 — 58 levels apart. The naive result is a distinctly darker gray than the true 50/50 mix of black and white.

**Both pairs blend naively to 128, but their correct linear-space blends are 186 and 146 — the naive average is too dark, by an amount that depends on where the colors sit on the gamma curve.**

## Build

The self-test asserts the encoding is sound and the failure is real. First, the round-trip: decoding then encoding any value must return it exactly, so the correction adds no loss of its own. Then the black-white case, pinned to exact numbers — naive 128, correct 186.

```python filename=modules/generative-media/code/gammablend-inter-01/gammablend.py:93-100 COMPLETE
    roundtrip_exact = all(encode(decode(v, gamma), gamma) == v for v in (0, 64, 128, 192, 255))
    print("  decode then encode is identity (round-trip is lossless) = %s" % roundtrip_exact)

    black_white_naive_is_midgray = bw_naive == 128
    print("  naive black+white blend is mid-gray 128 = %s (%d)" % (black_white_naive_is_midgray, bw_naive))

    black_white_correct_is_lighter = bw_correct == 186
    print("  correct black+white blend is 186, much lighter = %s (%d)" % (black_white_correct_is_lighter, bw_correct))
```

The last two clauses generalize it across every pair: the naive blend is darker than the correct one everywhere, and the two disagree everywhere — the darkening is systematic, not a fluke of one input.

```python filename=modules/generative-media/code/gammablend-inter-01/gammablend.py:102-106 COMPLETE
    naive_too_dark = all(naive_blend(p["a"], p["b"]) < linear_blend(p["a"], p["b"], gamma) for p in pairs)
    print("  every naive blend is darker than the correct one = %s" % naive_too_dark)

    naive_wrong = all(naive_blend(p["a"], p["b"]) != linear_blend(p["a"], p["b"], gamma) for p in pairs)
    print("  the naive and correct blends disagree on every pair = %s" % naive_wrong)
```

Running the check confirms every clause.

```text filename=gammablend.py --check
  decode then encode is identity (round-trip is lossless) = True
  naive black+white blend is mid-gray 128 = True (128)
  correct black+white blend is 186, much lighter = True (186)
  every naive blend is darker than the correct one = True
  the naive and correct blends disagree on every pair = True
```

**The check pins the darkening to exact numbers (128 vs 186) and proves it holds on every pair, while confirming the decode/encode round-trip is lossless — so the correction fixes the space without adding error.**

## Definition of done

Done means the naive blend is provably too dark on every pair and the linear-space blend is the correct, lighter result, with the round-trip shown lossless so the fix costs nothing but the two conversions. The `roundtrip_exact` clause is what makes decoding-and-re-encoding a free correction rather than a lossy detour — you are not degrading the image, only moving the averaging into the right space.

Two clarifications keep the scope honest. First, real sRGB is not a pure power law: it is a piecewise curve with a small linear segment near black (below about 0.04 encoded) and a 2.4 exponent on the rest, which together approximate an effective gamma of 2.2. The pure 2.2 power used here is the standard teaching approximation and behaves identically in spirit — the exact breakpoints do not change the lesson. Second, the correction matters most where the two colors are far apart on the curve: blending near-equal colors barely differs between the two spaces (the curve is locally almost straight), which is why the error is largest for the black-white pair (58 levels) and smaller for the closer mid-tones (18). The error is worst exactly where blends are most visible — high-contrast edges and gradients.

<svg role="img" aria-label="Two blend errors compared: black-white pair shows a 58-level gap, the 64-192 mid-tone pair shows an 18-level gap, illustrating larger error for more separated colors" viewBox="0 0 320 120">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">how much too dark the naive blend is (levels)</text>
  <text x="10" y="42" font-size="8" fill="var(--s1)">black+white</text>
  <rect x="95" y="32" width="174" height="14" fill="var(--s1)"/><text x="272" y="43" font-size="8" fill="var(--ink)">58</text>
  <text x="10" y="72" font-size="8" fill="var(--s2)">64+192</text>
  <rect x="95" y="62" width="54" height="14" fill="var(--s2)"/><text x="152" y="73" font-size="8" fill="var(--ink)">18</text>
  <text x="10" y="100" font-size="7.5" fill="var(--muted)">farther-apart colors sit on more-curved regions — larger darkening</text>
</svg>
^ The darkening grows with how far apart the colors are on the curve: the black-white blend is off by 58 levels, the closer 64-192 blend by only 18. High-contrast blends — edges, gradients, anti-aliasing — are exactly where the error is largest and most visible.

**Done means every naive blend is measurably too dark and the linear-space blend is the correct lighter value, with the round-trip proven lossless — the fix is to decode, mix, and re-encode, and it costs only the two conversions.**

## Boss fight

A team reports that when their image service resizes photos to thumbnails, the thumbnails come out noticeably darker and muddier than the originals — especially images with fine high-contrast detail like tree branches against a bright sky or white text on a dark background. The resizing library is standard and the code looks correct. What is happening, and how would you fix it?

It is gamma-space averaging in the resampler. Downsizing an image averages groups of neighboring pixels into each output pixel, and if the library averages the gamma-encoded values directly — as many do by default — it is mixing light in the wrong space, so every averaged pixel comes out too dark. The effect is worst exactly where the team sees it: high-contrast detail. A branch (dark) against sky (bright) or white text on black is a set of pixels far apart on the gamma curve, and blending far-apart values is where the darkening is largest — the bright and dark pixels average to something much darker than the true mix, so thin bright features dim and thin dark features thicken, reading as muddy loss of detail. Uniform or low-contrast regions barely change, which is why only the detailed areas look wrong. The fix is to resize in linear light: decode the image from its gamma encoding to linear intensities, run the resampling filter on the linear values, then re-encode the result. Many imaging libraries have a flag or a linear-light color-management path for exactly this; where the library cannot, the manual decode/resize/encode wrapping produces the correct result. The same correction applies to any pixel-mixing step in the pipeline — alpha compositing, blurring, generating mipmaps — all of which must average in linear space to avoid the same darkening.

## External resources

The classic writeups on gamma and linear-light image processing (for example, "What every coder should know about gamma" and the GPU Gems chapter on the importance of being linear) — the full sRGB piecewise curve, why displays and cameras encode the way they do, and worked examples of resizing and compositing gone dark.

Documentation for the linear-light or color-management modes in imaging libraries and engines (Pillow, ImageMagick's `-colorspace RGB`/`sRGB`, and the linear-workflow settings in renderers and compositors) — the production controls that move blending, resizing, and compositing into linear space so results stop coming out too dark.
