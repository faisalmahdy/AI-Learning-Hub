---
id: gamma-inter-01
title: Blend in linear light, not on the stored codes — averaging gamma-encoded pixels makes the result too dark
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: The number stored for a pixel is not proportional to the light it represents. Images are gamma-encoded so the codes are roughly perceptually uniform, which packs most codes into the darks — a stored 128 is not half the light of 255 but only about 0.5^2.2 = 22% of it. Averaging is arithmetic on light: blending two pixels, resizing (every output pixel is a weighted average of inputs), alpha-compositing, and blurring all add and average pixel values, and they are correct only on linear values proportional to actual light. Do them on the gamma-encoded codes and the result is systematically too dark, because the encoding curve is convex: the average of two codes decodes to less light than the average of the two lights. The fix is decode to linear (raise the normalized code to gamma), average in linear light, re-encode (raise to 1/gamma). On a fixture, blending black (0) and white (255) should give the light halfway between them, which is 186 (a bright mid-gray), but averaging the codes directly gives (0+255)/2 = 128 — far darker, because 128 is only 22% of full light. A dark+light pair (51, 204) blends to 152 correctly but 128 naively; only equal inputs agree.
eli5: The brightness number saved for each pixel isn't the real amount of light — it's squished so that dark shades get more of the number range, because your eyes notice differences in the dark more. So a "half" value like 128 is actually much dimmer than half the light. If you mix two colors by just averaging their saved numbers, you're averaging the squished values, and the answer comes out too dark and muddy — which is why photos sometimes get darker when you shrink them. The right way is to un-squish both numbers back into real light, mix the light, then squish the answer back. Same amount of work, but now white mixed with black gives a proper bright gray instead of a dingy one.
---

## Why this module

Resizing an image, fading between two frames, blurring, compositing a logo — all of these average pixels, and averaging pixels is one of the most common operations in all of graphics. It is also, done the obvious way, wrong, and wrong in a direction that darkens and muddies every result, because the numbers being averaged are not the light they look like.

The number stored for a pixel is not proportional to the light it represents. Images are gamma-encoded: the stored code is roughly perceptually uniform, spread so codes land where the eye can tell colors apart, which packs most of the codes into the darks. The consequence is that a stored 128 is not half the light of a stored 255 — decode it and (128/255) raised to the gamma of 2.2 is only 0.22, so "half the code" is about a fifth of the light. The encoding is a curve, not a straight line, and that curve is exactly why you cannot do arithmetic on the stored codes as if they were light.

Averaging is arithmetic on light. Blending two pixels, resizing an image (every output pixel is a weighted average of inputs), alpha-compositing, blurring — all of these add and average pixel values, and they are only correct on linear values, values proportional to actual light. Do them on the gamma-encoded codes and the result is systematically too dark, because the encoding curve is convex: the average of two codes decodes to less light than the average of the two lights. The fix is three steps — decode each code to linear (raise the normalized code to gamma), average in linear light, then re-encode (raise to 1/gamma). Skip the decode/encode and you get the classic bugs: images that darken when downscaled, blends that turn muddy, antialiased edges that look dirty. This module blends a few pairs both ways and shows the darkening.

**Stored pixel codes are gamma-encoded and not proportional to light, so any averaging operation — blending, resizing, compositing, blurring — must be done in linear light (decode, average, re-encode); averaging the codes directly is systematically too dark because the encoding curve is convex.**

## Concepts

**Decode and encode** convert between the stored code and linear light. Decoding raises the normalized code to gamma; encoding raises linear light to 1/gamma. Light is where averaging is valid.

```python filename=modules/generative-media/code/gamma-inter-01/gamma.py:44-51 COMPLETE
def decode(code, gamma):
    """Gamma-encoded 8-bit code -> linear light in [0,1]: (code/255) ** gamma."""
    return (code / 255.0) ** gamma


def encode(light, gamma):
    """Linear light in [0,1] -> gamma-encoded 8-bit code: round((light ** (1/gamma)) * 255)."""
    return round((light ** (1.0 / gamma)) * 255)
```

**Naive blend** averages the stored codes directly — the bug. It treats the perceptual codes as if they were light.

```python filename=modules/generative-media/code/gamma-inter-01/gamma.py:54-56 COMPLETE
def blend_naive(a, b):
    """WRONG: average the stored codes directly, as if they were light."""
    return round((a + b) / 2)
```

**Correct blend** decodes both codes to light, averages the light, and re-encodes — the fix, and the template for every averaging operation on images.

```python filename=modules/generative-media/code/gamma-inter-01/gamma.py:59-61 COMPLETE
def blend_linear(a, b, gamma):
    """RIGHT: decode both to linear light, average the light, re-encode."""
    return encode((decode(a, gamma) + decode(b, gamma)) / 2, gamma)
```

<svg role="img" aria-label="The gamma decoding curve: the horizontal axis is the stored code fraction, the vertical axis is linear light, and the convex curve shows code 0.5 mapping to only about 0.22 light" viewBox="0 0 300 130" width="300" height="130">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the encoding is a convex curve: code 0.5 is only 0.22 light</text>
  <line x1="34" y1="108" x2="280" y2="108" stroke="var(--line)"/>
  <line x1="34" y1="24" x2="34" y2="108" stroke="var(--line)"/>
  <text x="28" y="28" fill="var(--muted)" font-size="7" text-anchor="end">1.0</text>
  <text x="28" y="111" fill="var(--muted)" font-size="7" text-anchor="end">0</text>
  <text x="150" y="122" fill="var(--muted)" font-size="7">code fraction →</text>
  <path d="M34,108 C120,104 180,80 280,24" fill="none" stroke="var(--s1)"/>
  <line x1="34" y1="24" x2="280" y2="108" stroke="var(--grid)" stroke-dasharray="2 2"/>
  <line x1="157" y1="108" x2="157" y2="90" stroke="var(--s2)" stroke-dasharray="2 2"/>
  <line x1="34" y1="90" x2="157" y2="90" stroke="var(--s2)" stroke-dasharray="2 2"/>
  <circle cx="157" cy="90" r="3" fill="var(--s2)"/>
  <text x="120" y="104" fill="var(--muted)" font-size="7">0.5</text>
  <text x="40" y="88" fill="var(--muted)" font-size="7">0.22</text>
</svg>
^ Decoding bends the straight code axis into the convex light curve, so the midpoint code (0.5) maps to only 0.22 of full light, far below the dashed straight line — the gap between curve and line is exactly the darkening that code-averaging introduces.

**Averaging is valid only in linear light, so blend by decode-average-encode; averaging the codes directly falls below the true light-average because the decoding curve is convex.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/gamma-inter-01/gamma.py

The fixture is pairs of 8-bit codes to blend: opposite extremes, a dark/light pair, and an equal pair as a control.

```json filename=modules/generative-media/code/gamma-inter-01/gamma.json:4-8 COMPLETE
  "pairs": [
    {"name": "black+white", "a": 0, "b": 255},
    {"name": "dark+light", "a": 51, "b": 204},
    {"name": "equal-grays", "a": 128, "b": 128}
  ]
```

Run `--blend` to average each pair both ways.

```text filename=--blend
BLEND — average the codes (naive) vs average the light (correct), gamma=2.2
--------------------------------------------------------------
  pair          a    b    naive   correct   naive is
  black+white   0    255  128     186       58 darker
  dark+light    51   204  128     152       24 darker
  equal-grays   128  128  128     128       same
--------------------------------------------------------------
  averaging the codes lands below the correct light-average -- the image darkens.
```

Blend black and white: the light halfway between "no light" and "full light" is 0.5, which re-encodes to code 186 — a bright mid-gray, the color a 50/50 mix of black and white ink actually reflects. Averaging the codes gives (0+255)/2 = 128, which is 58 codes darker, because 128 is only 22% of full light, not 50%. The dark+light pair (51, 204) tells the same story: correct blend 152, naive blend 128, 24 codes too dark. And the control, equal-grays, is identical under both methods at 128 — when the two inputs are the same there is no curve to distort between them, so the bug vanishes exactly where it cannot show. That is the signature of this bug in the wild: it is invisible on flat regions and worst at high-contrast edges and between distant colors, so a downscaled image looks fine in the sky and dingy along every sharp boundary.

<svg role="img" aria-label="Blending black and white: the naive code-average is a darker gray at 128 while the correct light-average is a lighter gray at 186" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">black + white → naive 128 (too dark) vs correct 186</text>
  <rect x="20" y="24" width="40" height="40" fill="var(--ink)"/><text x="24" y="78" fill="var(--muted)" font-size="7">0 (black)</text>
  <text x="66" y="48" fill="var(--muted)" font-size="10">+</text>
  <rect x="80" y="24" width="40" height="40" fill="var(--panel)" stroke="var(--line)"/><text x="82" y="78" fill="var(--muted)" font-size="7">255 (white)</text>
  <text x="128" y="48" fill="var(--muted)" font-size="10">→</text>
  <rect x="150" y="24" width="40" height="40" fill="var(--ink)" opacity="0.5"/><text x="150" y="78" fill="var(--muted)" font-size="7">naive 128</text><text x="150" y="90" fill="var(--s2)" font-size="7">too dark</text>
  <rect x="220" y="24" width="40" height="40" fill="var(--muted)"/><text x="220" y="78" fill="var(--muted)" font-size="7">correct 186</text><text x="220" y="90" fill="var(--s1)" font-size="7">right</text>
</svg>
^ The correct blend of black and white is the lighter mid-gray 186 (the true 50% light point), while averaging the codes gives the darker 128 — the same too-dark result that darkens images blended or resized in the encoded space.

## Build

The reason the codes lie is worth seeing directly: what fraction of light does each code actually carry? Run `--intensity`.

```text filename=--intensity
INTENSITY — what stored codes really are in linear light (gamma=2.2)
--------------------------------------------------------
  code    fraction of code   fraction of LIGHT
  64      0.251              0.048
  128     0.502              0.220
  192     0.753              0.536
  255     1.000              1.000
```

<svg role="img" aria-label="For codes 64, 128, and 192, a pair of bars comparing the code fraction against the much smaller light fraction, showing the two rulers disagree everywhere except the endpoints" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">code fraction vs light fraction — two different rulers</text>
  <line x1="40" y1="96" x2="290" y2="96" stroke="var(--line)"/>
  <g transform="translate(70,0)">
  <rect x="0" y="72" width="14" height="24" fill="var(--s1)"/><rect x="16" y="91" width="14" height="5" fill="var(--s2)"/>
  <text x="0" y="108" fill="var(--muted)" font-size="7">64</text><text x="-2" y="68" fill="var(--muted)" font-size="6">.25/.05</text>
  </g>
  <g transform="translate(150,0)">
  <rect x="0" y="48" width="14" height="48" fill="var(--s1)"/><rect x="16" y="75" width="14" height="21" fill="var(--s2)"/>
  <text x="0" y="108" fill="var(--muted)" font-size="7">128</text><text x="-2" y="44" fill="var(--muted)" font-size="6">.50/.22</text>
  </g>
  <g transform="translate(230,0)">
  <rect x="0" y="24" width="14" height="72" fill="var(--s1)"/><rect x="16" y="45" width="14" height="51" fill="var(--s2)"/>
  <text x="0" y="108" fill="var(--muted)" font-size="7">192</text><text x="-2" y="20" fill="var(--muted)" font-size="6">.75/.54</text>
  </g>
  <text x="40" y="20" fill="var(--s1)" font-size="7">■ code</text><text x="90" y="20" fill="var(--s2)" font-size="7">■ light</text>
</svg>
^ At each code the code-fraction bar (left) towers over the light-fraction bar (right) — 64 is a quarter of the code range but 5% of the light, 128 is half the codes but 22% of the light — so averaging on the code ruler systematically overweights the darks.

The two columns are the whole lesson. Code 64 is a quarter of the way up the code range but carries under 5% of full light; code 128 is halfway up in code but only 22% of the light; code 192 is three-quarters up in code but only 54% of the light. The code axis and the light axis are wildly different rulers, and only the endpoints (0 and 255) agree. So when you average two codes, you are measuring with the code ruler — which crams the darks — and the answer lands far darker than the light halfway point. This is also why the encoding exists and is not a bug to remove: spending more codes on the darks matches the eye's greater sensitivity there, giving smoother gradients in shadows for a given bit depth. The encoding is right for storage and display; it is only wrong to compute averages on, and the whole fix is to step into linear light for the arithmetic and step back out.

## Definition of done

The self-test pins the black+white numbers, the darkening direction, and the equal-input control.

```python filename=modules/generative-media/code/gamma-inter-01/gamma.py:99-107 COMPLETE
    naive_bw = blend_naive(bw["a"], bw["b"])
    naive_bw_is_128 = naive_bw == 128
    print("  naive blend of black+white is 128 = %s" % naive_bw_is_128)

    correct_bw = blend_linear(bw["a"], bw["b"], gamma)
    correct_bw_is_186 = correct_bw == 186
    print("  correct (linear) blend of black+white is 186 = %s" % correct_bw_is_186)

    naive_darker = all(blend_naive(p["a"], p["b"]) <= blend_linear(p["a"], p["b"], gamma) for p in g)
    print("  naive blend is never brighter than the correct blend = %s" % naive_darker)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — naive code-averaging is darker than linear-light blending except when the inputs are equal; black+white is 128 vs 186
----------------------------------------------------------------------------------------------------------------------------------
  naive blend of black+white is 128 = True
  correct (linear) blend of black+white is 186 = True
  naive blend is never brighter than the correct blend = True
  for unequal pairs the naive blend is strictly darker = True
  when the two inputs are equal, both methods agree = True (128)
```

**Done means the bug and the fix are proven on real codes: blending black and white gives 128 by code-averaging but 186 in linear light, the naive blend is never brighter than the correct one and is strictly darker for every unequal pair, and equal inputs agree at 128 — so image averaging must be done in linear light, and code-averaging is a systematic darkening.**

## Boss fight

Predict two ways this bites beyond a single blend, because the same convexity runs through every averaging operation and the correction has its own edges.

The first trap is that this is not really about "blending" — it is about every operation that sums pixel values, which is most of the imaging pipeline. Downscaling averages neighborhoods, so an image resized in encoded space darkens, and thin bright features on dark backgrounds (stars, specular highlights, white text) lose energy fastest because their high-contrast neighborhoods are where the convex gap is largest. Gaussian blur, mipmap generation, anti-aliasing coverage (a 50%-covered edge pixel should be the linear-light average of foreground and background, not the code average), and alpha compositing over a background all have the same requirement: convert to linear, operate, convert back. The famous case is alpha compositing with straight (non-premultiplied) alpha in encoded space, which produces dark fringes around anti-aliased edges — the "dark halo" bug — for exactly this reason. So the rule generalizes past this module: if a step adds or averages pixels and you did not first linearize, it is wrong, and it is wrong toward dark.

The second trap is that the correction has to use the right transfer function and the right precision, or you trade one error for another. Real sRGB is not a pure power of 2.2 — it is a piecewise curve with a linear segment near black and an exponent of 2.4 on the rest — so a plain 2.2 power is an approximation that is slightly off in the deep shadows, and color-managed pipelines use the exact sRGB function (or the display's actual profile) to decode and encode. And you cannot linearize into 8-bit and back: linear light needs more precision in the darks (that is what the encoding was buying you), so the decode-average-encode round trip must happen in floating point or at least 16-bit, or you reintroduce banding in the shadows that the gamma encoding existed to prevent. Finally, only light-linear channels should be linearized this way — an alpha channel or a normal map stored in the same 8-bit container is not perceptual light and must not be gamma-decoded, so "linearize everything" is as wrong as "linearize nothing." The discipline is precise: decode the color channels with the correct transfer function, compute in high-precision linear light, and re-encode — no more, no less.

**The darkening is not specific to blending: every pixel-averaging step (downscale, blur, mipmaps, anti-aliasing, alpha compositing) must run in linear light or it darkens and fringes, and the correction must use the correct transfer function (true sRGB, not just a 2.2 power) at high precision (float or 16-bit, not 8-bit) and only on genuine light channels — so linearize the color, compute, and re-encode, rather than linearizing everything or nothing.**

## External resources

Any color-management or rendering reference on gamma and linear-light compositing — the sRGB transfer function (its piecewise form versus the 2.2 approximation), why resizing and blending must happen in linear space, and the precision needed to avoid shadow banding.

Writing on the "dark fringe" alpha-compositing bug and premultiplied alpha — the same linear-light requirement applied to compositing, and why straight alpha over a background in encoded space produces halos.

The companion white-balance and histogram modules in this topic — like white balance, gamma is a case where the stored pixel values encode something other than raw scene light, so operating on them correctly requires knowing and inverting the encoding first.
