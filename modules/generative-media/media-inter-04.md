---
id: media-inter-04
title: Blend pixels in linear light, or averaging sRGB bytes darkens the image
topic: generative-media
level: intermediate
status: ready
time: 8-10h
summary: Every pixel byte in an image file is sRGB-encoded — a perceptually-spaced code, not the light the pixel emits — so averaging the bytes is arithmetic on the wrong quantity and comes out systematically too dark. Blending black (0) and white (255) 50/50 by byte average gives 128, a muddy gray, when the true blend in linear light is 188, a 60-code difference, because half of white's light is still a bright perceived gray. Every blend the wrong way is darker than the right way, worst at high contrast, and the fix is three steps: decode each byte to linear light with the sRGB transfer function, average in linear light, re-encode. This is the bug behind resizers, alpha compositors, and antialiasers that make thin or checkered content go dim.
eli5: The numbers stored for each pixel are not how much light comes out — they are squished so that dark shades get more of the number range, because your eyes care more about darks. If you just average two of those squished numbers you get the wrong brightness, always too dark. Black and white should blend to a bright gray, but averaging the stored numbers gives a dull middle gray. You have to un-squish first, average the real light, then re-squish.
---

## Why this module

Blending two pixels is one of the most common operations in any media pipeline: resizing averages neighbouring pixels, alpha compositing mixes a foreground over a background, antialiasing averages coverage at edges. It looks like the simplest arithmetic there is — add two values, divide by two — and it is wrong almost everywhere it is done naively, in a way that darkens images and that most people never diagnose because the result looks plausible. This module builds the failure on a single pair of pixels, measures the darkening, and builds the three-step fix that correct engines use.

The reason is that the number stored for each pixel is not light. Image files are sRGB-encoded: the byte is a perceptually-spaced code, compressed so that more of the 0–255 range is spent on darks, where the eye is more sensitive, which is exactly why 8 bits per channel looks smooth instead of banded. But a perceptual code is not proportional to the light the pixel emits, and blending is a statement about light — if you cover half a region with white and half with black, the light reaching your eye is the average of their light, not the average of their codes. Average the codes and you get a value that is too dark, dramatically so at high contrast: black and white blend to a bright code 188 in light, but only 128 in bytes. The fix is to decode each byte to linear light with the sRGB transfer function, do the averaging in linear light where arithmetic corresponds to physics, and re-encode the result.

You need no prior module, though this is the missing half of the downsampling module — its box filter averaged pixels, and it must average them in linear light. Everything runs offline against a pixel fixture — four sRGB byte pairs — stdlib Python 3, `$0.00`. The instinct to unlearn is that a pixel's value is its brightness. The value is a perceptual code; brightness is what you get after decoding it, and only brightness may be averaged.

Here is the same blend done both ways:

```
# modules/generative-media/code/media-inter-04/ — COMPLETE, run from that directory
$ python3 gamma.py --blend

BLEND — 50/50 of each pair: average the bytes (wrong) vs blend in light (right)
------------------------------------------------------------------
  a    b     wrong(byte avg)   correct(linear)   too dark by
  0    255   127.5             187.5             60.0
  64   192   128.0             146.4             18.4
  0    128   64.0              92.4              28.4
  100  200   150.0             160.2             10.2
```

run: 2026-08-26 · deterministic; sRGB byte pairs are a fixture · 4 pairs · `python3 gamma.py --blend`

Every pair is darker done the byte-average way, and the gap is largest at the highest contrast — 60 codes for black and white. This module is where that 60 comes from and why the byte average is never the right answer.

## Concepts

Named here so you can find them again; each is built below.

- **sRGB encoding** — the perceptual, non-linear code stored in image bytes; denser in the darks.
- **Linear light** — the physical light quantity, proportional to photons; where blending is valid.
- **Transfer function** — the sRGB decode/encode that converts between code and light.
- **Byte-average blend** — the bug: averaging sRGB codes as if they were light.
- **Linear blend** — decode to light, average, re-encode; the correct blend.
- **Systematic darkening** — the byte average is always darker, worst at high contrast.

## Worked example

Source: the color-management rule every correct renderer and image library follows (the sRGB transfer function, and "resize in linear light"), reduced to a single blend; the byte pairs here stand in for real pixels so the darkening is exact and checkable.

Script and fixture: `modules/generative-media/code/media-inter-04/` — `gamma.py`, and `pixels.json`, four sRGB byte pairs to blend 50/50. Every command runs from there.

### The transfer functions: code to light and back

The sRGB standard defines exactly how a stored byte maps to linear light and back. It is nearly a power law with exponent 2.4, plus a small linear segment near black.

```
# gamma.py:39-48 — COMPLETE (the sRGB transfer functions, code <-> linear light)
def srgb_to_linear(code):
    """Decode an 8-bit sRGB value to linear light in [0, 1]."""
    c = code / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(light):
    """Encode linear light in [0, 1] back to an 8-bit sRGB value."""
    v = 12.92 * light if light <= 0.0031308 else 1.055 * (light ** (1 / 2.4)) - 0.055
    return v * 255.0
```

The exponent is the whole story. Because light goes as roughly code to the 2.4, the midpoint code 128 is not half the light — it is about 0.22 of the light, since (128/255)^2.4 ≈ 0.22. Perceptual middle gray sits far below physical half-light, which is precisely the perceptual compression that makes sRGB efficient. Decoding undoes it; only after decoding do the numbers behave like light.

### The two blends

The wrong blend averages the codes; the right blend averages the light.

```
# gamma.py:53-61 — COMPLETE (byte-average vs decode-average-encode)
def blend_wrong(a, b):
    """The bug: average the sRGB bytes directly, as if they were light."""
    return (a + b) / 2.0


def blend_correct(a, b):
    """Decode to linear light, average THERE, re-encode to sRGB."""
    light = (srgb_to_linear(a) + srgb_to_linear(b)) / 2.0
    return linear_to_srgb(light)
```

`blend_wrong` is the one everyone writes first, because the values look like brightness and averaging brightness is obviously right — except they are not brightness. `blend_correct` decodes 0 and 255 to linear 0.0 and 1.0, averages to linear 0.5 — genuinely half the light — and re-encodes 0.5 light, which in sRGB is code 188, because half of maximum light is a bright perceived gray. The wrong version stops at 128 because it averaged the codes, and code 128 is only a fifth of the light.

The self-test pins the black-and-white gap directly:

```
# gamma.py:92-100 — COMPLETE (the black+white gap, measured)
    correct_bw = blend_correct(0, 255)
    is_bright = correct_bw > 180

    wrong_bw = blend_wrong(0, 255)

    big_gap = correct_bw - wrong_bw > 50
```

`correct_bw` is 187.5, `wrong_bw` is 127.5, and their difference clears 50 — the darkening is not a rounding wobble, it is 60 codes.

<svg viewBox="0 0 700 200" role="img" aria-label="A curve of linear light against sRGB code, bowed below the diagonal. Black at code 0 maps to light 0, white at code 255 maps to light 1. The true blend point sits at light 0.5, which reads across to code 188. The byte-average point at code 128 sits far below on the curve at light 0.22. An arrow shows the gap between code 128 and code 188.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">linear light vs sRGB code — averaging code lands too dark</text>
    <line x1="60" y1="170" x2="640" y2="170" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="170" stroke="var(--grid)"></line>
    <text x="350" y="192" fill="var(--muted)" font-size="8">sRGB code -></text>
    <path d="M60 170 Q 300 150 380 100 T 640 30" fill="none" stroke="var(--s1)" stroke-width="2"></path>
    <line x1="60" y1="100" x2="380" y2="100" stroke="var(--s2)" stroke-dasharray="3 3"></line>
    <line x1="380" y1="100" x2="380" y2="170" stroke="var(--s2)" stroke-dasharray="3 3"></line>
    <circle cx="380" cy="100" r="4" fill="var(--s2)"></circle><text x="386" y="96" fill="var(--s2)" font-size="8">true blend: light 0.5 = code 188</text>
    <line x1="60" y1="140" x2="290" y2="140" stroke="var(--muted)" stroke-dasharray="2 2"></line>
    <line x1="290" y1="140" x2="290" y2="170" stroke="var(--muted)" stroke-dasharray="2 2"></line>
    <circle cx="290" cy="140" r="4" fill="var(--muted)"></circle><text x="150" y="135" fill="var(--muted)" font-size="8">byte avg: code 128 = light 0.22</text>
    <g fill="var(--muted)" text-anchor="middle"><text x="60" y="185">0</text><text x="290" y="185">128</text><text x="380" y="185">188</text><text x="640" y="185">255</text></g>
  </g>
</svg>
^ The curve is the sRGB encoding: code 128 is only 0.22 of full light, not half. The true 50/50 blend is at light 0.5, which re-encodes to code 188. Averaging the codes lands at 128, far down the curve — too dark.

### The checkerboard, revisited

This is the missing piece of the downsampling module. Shrinking a black-and-white checkerboard to one pixel should give its true average brightness.

```
# $ python3 gamma.py --checker
#   averaging the stored bytes:   (0+255)/2      = 127.5  (muddy, too dark)
#   averaging the LIGHT:          linear then re = 187.5  (true perceived gray)
```

run: 2026-08-26 · deterministic · `python3 gamma.py --checker`

<svg viewBox="0 0 700 150" role="img" aria-label="Three horizontal swatches. Top: pure black on the left, pure white on the right. Middle: the byte-average result, a medium-dark gray labelled 128. Bottom: the linear-light result, a noticeably brighter gray labelled 188.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the 50/50 gray of black and white — two answers</text>
    <rect x="150" y="26" width="60" height="24" fill="var(--ink)"></rect><rect x="210" y="26" width="60" height="24" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="290" y="43" fill="var(--muted)" font-size="8">inputs: black + white</text>
    <rect x="150" y="60" width="120" height="24" fill="var(--muted)"></rect><text x="290" y="77" fill="var(--s2)" font-size="8">byte average = code 128 (muddy, too dark)</text>
    <rect x="150" y="94" width="120" height="24" fill="var(--line)"></rect><text x="290" y="111" fill="var(--s1)" font-size="8">linear blend = code 188 (true bright gray)</text>
    <text x="150" y="138" fill="var(--muted)" font-size="8">a naive resizer produces the top gray; the correct one produces the bottom</text>
  </g>
</svg>
^ The lower swatch is the honest 50/50 of black and white; the middle one is what averaging the bytes gives — the same darkening a naive resizer bakes into every high-contrast region.

A fine checkerboard of black and white pixels emits, on average, half the maximum light — it should shrink to the bright gray at code 188. A resizer that box-filters in sRGB bytes produces 128 instead, so every region of high-contrast fine detail goes visibly dark as you scale it down. This is why thin bright lines on dark backgrounds dim when downscaled in a naive pipeline, and why correct image resizing is specified to happen in linear light. The box filter from the downsampling module was right to average — it just has to average the light, not the codes.

**A pixel byte is an sRGB code, not light, and blending is arithmetic on light — so decode to linear light, average there, and re-encode; average the codes directly and every blend comes out too dark, worst at high contrast, dimming resized and composited images.**

### The self-test

The `--check` mode asserts the gap and the machinery: the linear blend of black and white is bright, the byte average is 128, the gap is large, the transfer functions round-trip, and the byte average is never brighter than the linear blend.

```
# $ python3 gamma.py --check
#   linear blend of 0 and 255 is a bright gray = True (187.5)
#   byte-average blend of 0 and 255 is 127.5 = True (127.5)
#   the gap between them is large = True (60.0 codes darker)
#   sRGB decode/encode round-trips exactly = True
#   byte-average is never brighter than the linear blend = True
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 gamma.py --check`

The two structural guarantees are one line each:

```
# gamma.py:104-108 — COMPLETE (transfer functions round-trip; darkening is directional)
    roundtrip = all(abs(linear_to_srgb(srgb_to_linear(v)) - v) < 1e-6 for v in (0, 64, 128, 200, 255))

    # The wrong blend is never brighter than the correct one -- it is a systematic darkening.
    systematic = all(blend_wrong(a, b) <= blend_correct(a, b) + 1e-9 for a, b in pairs)
```

The `roundtrip` line is the correctness anchor for the transfer functions: decoding then re-encoding any code must return it exactly, and if a sign or exponent were wrong that assertion would fail first, before any blend. The `systematic` line makes the darkening a property rather than an anecdote — it requires the byte average to be no brighter than the linear blend on every pair, so the bug is proven directional, always dimming, never brightening.

### The running tally

| pair | byte-average blend | linear blend | too dark by |
|---|---|---|---|
| black + white (0, 255) | 127.5 | 187.5 | 60.0 |
| dark + light gray (64, 192) | 128.0 | 146.4 | 18.4 |
| black + mid (0, 128) | 64.0 | 92.4 | 28.4 |

<svg viewBox="0 0 700 160" role="img" aria-label="Darkening error in codes plotted against the contrast of each pair. High contrast (255 spread, black+white) has the tallest bar at 60. Medium spreads have shorter bars: 128 spread gives 28, 128 spread gives 18, 100 spread gives 10. The error grows with contrast.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">how much the byte average darkens, by pair contrast</text>
    <line x1="60" y1="130" x2="650" y2="130" stroke="var(--grid)"></line>
    <rect x="90" y="46" width="70" height="84" fill="var(--s2)"></rect><text x="125" y="42" text-anchor="middle" fill="var(--s2)" font-size="8">60</text><text x="125" y="145" text-anchor="middle" fill="var(--muted)" font-size="8">0/255</text>
    <rect x="230" y="90" width="70" height="40" fill="var(--s2)"></rect><text x="265" y="86" text-anchor="middle" fill="var(--muted)" font-size="8">28</text><text x="265" y="145" text-anchor="middle" fill="var(--muted)" font-size="8">0/128</text>
    <rect x="370" y="104" width="70" height="26" fill="var(--s2)"></rect><text x="405" y="100" text-anchor="middle" fill="var(--muted)" font-size="8">18</text><text x="405" y="145" text-anchor="middle" fill="var(--muted)" font-size="8">64/192</text>
    <rect x="510" y="116" width="70" height="14" fill="var(--s2)"></rect><text x="545" y="112" text-anchor="middle" fill="var(--muted)" font-size="8">10</text><text x="545" y="145" text-anchor="middle" fill="var(--muted)" font-size="8">100/200</text>
  </g>
</svg>
^ The darkening scales with contrast: black-and-white loses 60 codes, low-contrast pairs only 10 to 28. The bug is loudest exactly on edges and text, where contrast is highest.

Read the "too dark by" column against contrast. The highest-contrast pair, black and white, is off by 60 codes; the lower-contrast pairs by 10 to 30. The error grows with the spread between the two values, because the sRGB curve bends most between them there. This is why the darkening is invisible on smooth, low-contrast images — where every blend is between near neighbours — and glaring on edges, text, and fine texture, exactly the content where blending happens most and matters most. Test on high contrast, and always average in light.

### What we did not settle

Linear light is the rule for more than blending. Alpha compositing must premultiply and composite in linear light, or edges of transparent images get dark or light fringes. Adding light for glows and additive effects is only correct in linear space. Color beyond grayscale needs the same transfer function applied per channel, plus a defined color space (sRGB primaries, or wider gamuts like Display P3) so the light values mean the same thing. And higher bit depths or floating-point buffers hold linear light directly, which is why professional pipelines work in linear and only encode to sRGB at the very end. The single-channel blend here is the atom; every one of those is the same rule — do light arithmetic in linear light — applied more broadly.

## Build

The practice in one paragraph: never average, resize, composite, or blend sRGB pixel values directly; decode each to linear light with the sRGB transfer function, do the arithmetic in linear light, and re-encode to sRGB only at the end; work in linear throughout a pipeline and encode once, at output, if you can; and test on high-contrast content — black and white, text, thin lines — because that is where averaging in the wrong space darkens visibly. The stored byte is a code, not a brightness.

We opened on the blends. The number that proves the space matters is the black-and-white gap:

```
# modules/generative-media/code/media-inter-04/ — COMPLETE, run from that directory
$ python3 gamma.py --checker
  averaging the stored bytes:   (0+255)/2      = 127.5  (muddy, too dark)
  averaging the LIGHT:          linear then re = 187.5  (true perceived gray)
```

Now do it to a real image. Take a high-contrast image — text, a checkerboard, thin bright lines on dark — and downscale it two ways: box-filter the raw sRGB bytes, and decode to linear, box-filter, re-encode. Your number to beat is not sharpness; it is **the mean brightness difference between the two downscales, which the linear version keeps and the byte version loses** — the byte version will be measurably and visibly darker. Bring back both downscales and the brightness gap. Good luck.

## Definition of done

- [ ] The sRGB decode and encode transfer functions implemented and round-trip-tested
- [ ] A blend done both ways: averaging sRGB bytes, and averaging in linear light
- [ ] The black+white case measured, showing byte-average 128 versus linear 188
- [ ] Confirmation the byte average is systematically darker, worst at high contrast
- [ ] The checkerboard/high-contrast downscale shown to darken in sRGB and hold in linear
- [ ] `python3 gamma.py --check` printing SELF-TEST PASS: bright, byte-dark, big-gap, roundtrip, systematic
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why is a stored pixel byte not proportional to the light the pixel emits, and what is that encoding good for?
2. Black and white blend to code 188 in light but 128 in bytes. Explain where each number comes from.
3. What are the three steps of a correct blend, and which one does the buggy version skip?
4. Why is the darkening invisible on smooth low-contrast images but obvious on text and edges?
5. Your own high-contrast image was downscaled both ways. What was the mean brightness gap, and where was the byte version visibly darker?

## External resources

- The sRGB specification / *What every coder should know about gamma* (John Novak) — my summary: the definitive explanation of sRGB encoding and why blending, resizing, and lighting must happen in linear light, with the same black+white demonstration; read it for the full color-management picture this module opens.
- Pillow / image-library notes on resizing in linear light — my summary: how production libraries expose (or fail to expose) linear-light resampling, and the visible darkening when they do not; read it for how real resizers handle the transfer function.
- This hub, *media-inter-03* — modules/generative-media/media-inter-03.md — my summary: the downsampling module whose box filter averages pixels; read it for the operation this module corrects — that averaging must happen in linear light, or the recovered gray is too dark.
