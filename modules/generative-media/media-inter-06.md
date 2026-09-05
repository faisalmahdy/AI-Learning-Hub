---
id: media-inter-06
title: Dither when you quantize — error diffusion hides the banding a threshold creates
topic: generative-media
level: intermediate
status: ready
time: 8-10h
summary: Quantizing a smooth 16-pixel gradient down to two levels by a naive threshold collapses it into one hard edge — eight black pixels then eight white, a run of 8 and a max local-average error of 93.5 — because each pixel rounds independently with no memory of the error it discarded. Error diffusion carries each pixel's rounding error forward to its neighbors, so the two levels get sprinkled in proportion to brightness: the longest run drops to 4, the local-average error halves to 46.8, and the band is gone, while both methods preserve the total brightness of 2040 exactly. The two available levels are identical; what changes is that the local average of the dithered output tracks the true gradient, so the eye sees a smooth ramp made of dots instead of a banded step.
eli5: If you can only use black and white tiles to show a gray wall, painting the left half all black and the right half all white looks nothing like gray. Instead you scatter white tiles more thickly where the wall is lighter, so from a distance your eye blends them into the right shade. Dithering is that scattering, and the trick is to remember how far off each tile was and make it up with the next one.
---

## Why this module

Quantization to few levels is everywhere in media: exporting to a small palette, rendering on a 1-bit or low-bit display, compressing color depth, printing where each dot is ink-or-no-ink. The reflex is to round each pixel to the nearest available level, and on any smooth region that reflex produces the ugliest, most recognizable artifact in imaging: banding, hard steps where a gradient should be continuous. This module builds that failure and the fix, error diffusion, because the difference between them is one idea — remember the rounding error and pass it on — and it is the idea behind every good dithering algorithm.

The problem is memoryless rounding. When each pixel independently snaps to the nearest level, a whole region of similar values snaps the same way — a run of pixels just below the threshold all become the low level, then the region above it all become the high level, and the smooth transition becomes a cliff. The information about how bright each pixel actually was is discarded, pixel by pixel, with nothing carried forward. Error diffusion keeps that information: when a pixel rounds to a level, the error — the distance it had to move to get there — is added to the next pixel before it rounds. So a region that is 40 percent bright accumulates error until it tips a pixel to the high level, producing roughly 40 percent high-level pixels sprinkled through it. The local average now equals the true brightness, and the eye, which averages over small areas, sees the gradient. The levels are the same two; only the arrangement changed, and the arrangement is everything.

You need no prior module, though this is the counterpart to the quantization module in below-the-prompt — same rounding, applied to pixels, with a spatial fix. Everything runs offline against a gradient fixture — a 16-pixel ramp quantized to two levels — stdlib Python 3, `$0.00`. The instinct to unlearn is that quantizing means rounding each value to the nearest level. That is quantizing without dithering, and on smooth content it bands; quantizing well means rounding while carrying the error forward, so the local average survives.

Here is the ramp quantized both ways:

```
# modules/generative-media/code/media-inter-06/ — COMPLETE, run from that directory
$ python3 dither.py --quantize

QUANTIZE — a smooth ramp to two levels [0, 255]
------------------------------------------------------------------
  input:   [0, 17, 34, 51, 68, 85, 102, 119, 136, 153, 170, 187, 204, 221, 238, 255]
  naive:   [0, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 255, 255, 255, 255]
  dither:  [0, 0, 0, 0, 255, 0, 0, 255, 0, 255, 255, 0, 255, 255, 255, 255]
```

run: 2026-08-26 · deterministic; gradient is a fixture · 16 pixels · `python3 dither.py --quantize`

The naive output is one black block and one white block — a hard band. The dithered output sprinkles the two levels, sparse where the ramp is dark and dense where it is bright. This module is why that sprinkle looks like a gradient and the block does not.

## Concepts

Named here so you can find them again; each is built below.

- **Quantization** — mapping each pixel to the nearest of a small set of available levels.
- **Banding** — hard steps in a quantized smooth region; the artifact of memoryless rounding.
- **Error diffusion** — carrying a pixel's rounding error forward to its neighbors.
- **Floyd-Steinberg** — the classic error-diffusion dither (here reduced to one dimension).
- **Local average** — brightness averaged over a small window; what the eye perceives and dither preserves.
- **Longest run** — the length of the longest block of one level; a direct measure of banding.

## Worked example

Source: error-diffusion dithering (Floyd & Steinberg, 1976) as used in every image quantizer and printer driver, reduced to a one-dimensional ramp; the gradient here stands in for a real smooth region so the banding and the local-average fidelity are exact and checkable.

Script and fixture: `modules/generative-media/code/media-inter-06/` — `dither.py`, and `gradient.json`, a 16-pixel linear ramp quantized to two levels. Every command runs from there.

### Naive quantization: round each pixel, band the region

The naive quantizer maps every pixel to its nearest level, independently.

```
# dither.py:38-44 — COMPLETE (round each pixel to the nearest level, no memory)
def nearest_level(value, levels):
    return min(levels, key=lambda L: abs(L - value))


def quantize_naive(pixels, levels):
    """Round each pixel to the nearest level, independently. No memory -> banding."""
    return [nearest_level(v, levels) for v in pixels]
```

Every pixel below 128 rounds to 0, every pixel at or above rounds to 255, so the first eight pixels of the ramp become a solid black block and the last eight a solid white block. The transition — a smooth climb from 0 to 255 — is replaced by a single cliff at the midpoint. Each rounding decision was locally correct (each pixel really is nearer one level), and the aggregate is a lie: a region that should shade continuously is two flat blocks. The error each pixel discarded — up to 127 levels of it — simply vanished, and with it the gradient.

### The dithered quantizer: carry the error forward

Error diffusion changes one thing: it accumulates the rounding error and adds it to the next pixel.

```
# dither.py:47-55 — COMPLETE (error diffusion: carry the rounding error forward)
def quantize_dither(pixels, levels):
    """Error diffusion: carry each pixel's rounding error forward to the next."""
    out, err = [], 0.0
    for v in pixels:
        target = v + err              # the pixel plus accumulated error
        q = nearest_level(target, levels)
        err = target - q              # what we could not represent, carried forward
        out.append(q)
    return out
```

<svg viewBox="0 0 700 150" role="img" aria-label="A chain of pixels. Each box shows a pixel value plus incoming error, rounds to 0 or 255, and passes the leftover error to the next box with an arrow. Pixel 17+0 rounds to 0, carries 17; 34+17 rounds to 0, carries 51; 68+102 rounds to 255, carries -85.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">error diffusion: each pixel adds the carried error, rounds, and passes the remainder on</text>
    <rect x="40" y="50" width="90" height="30" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="85" y="63" text-anchor="middle" fill="var(--ink)">17 + 0</text><text x="85" y="75" text-anchor="middle" fill="var(--s2)">→ 0</text>
    <path d="M130 65 L175 65" stroke="var(--s2)"></path><text x="152" y="58" text-anchor="middle" fill="var(--s2)">+17</text>
    <rect x="175" y="50" width="90" height="30" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="220" y="63" text-anchor="middle" fill="var(--ink)">34 + 17</text><text x="220" y="75" text-anchor="middle" fill="var(--s2)">→ 0</text>
    <path d="M265 65 L310 65" stroke="var(--s2)"></path><text x="287" y="58" text-anchor="middle" fill="var(--s2)">+51</text>
    <rect x="310" y="50" width="95" height="30" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="357" y="63" text-anchor="middle" fill="var(--ink)">51 + 51</text><text x="357" y="75" text-anchor="middle" fill="var(--s2)">→ 0</text>
    <path d="M405 65 L450 65" stroke="var(--s2)"></path><text x="427" y="58" text-anchor="middle" fill="var(--s2)">+102</text>
    <rect x="450" y="50" width="100" height="30" rx="4" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="500" y="63" text-anchor="middle" fill="var(--acc-ink)">68 + 102</text><text x="500" y="75" text-anchor="middle" fill="var(--s1)">→ 255</text>
    <path d="M550 65 L595 65" stroke="var(--s1)"></path><text x="572" y="58" text-anchor="middle" fill="var(--s1)">−85</text>
    <rect x="595" y="50" width="70" height="30" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="630" y="68" text-anchor="middle" fill="var(--muted)">next…</text>
    <text x="40" y="120" fill="var(--muted)">error builds up through dark pixels until it tips one bright, then goes negative to compensate</text>
  </g>
</svg>
^ The carried error accumulates through the dark pixels (17, 51, 102) until it pushes one over the threshold to 255, which then carries a negative error to suppress the next few. That accumulate-and-tip is how the density of bright pixels comes to match the local brightness.

Trace the dark end. Pixel 0 is 0, rounds to 0, no error. Pixel 1 is 17; with 0 carried it is 17, rounds to 0, and carries +17 forward. Pixel 2 is 34 plus 17 is 51, rounds to 0, carries +51. Pixel 3 is 51 plus 51 is 102, rounds to 0, carries +102. Pixel 4 is 68 plus 102 is 170 — now over threshold — rounds to 255, and carries 170 minus 255 = −85 forward, which suppresses the next few pixels. The error accumulates until it tips a pixel bright, then goes negative to compensate. Over any small window, the number of white pixels is proportional to the window's true brightness, so the local average tracks the ramp. The dark end gets one white pixel in five; the bright end gets four in five.

<svg viewBox="0 0 700 210" role="img" aria-label="Three rows of 16 cells. Top row 'input': a rising ramp of bar heights, low on the left to full on the right. Middle row 'naive': eight empty (white) cells then eight filled (black) cells, a hard seam in the middle. Bottom row 'dither': filled cells sprinkled, sparse on the left growing dense on the right. Filled cells use the ink color, empty cells the panel color.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the ramp as pixels (filled=255, empty=0): input ramp, naive band, dither sprinkle</text>
    <text x="20" y="46" fill="var(--ink)">input</text>
    <g fill="var(--muted)">
      <rect x="120" y="52" width="30" height="2"></rect><rect x="153" y="50" width="30" height="4"></rect><rect x="186" y="47" width="30" height="7"></rect><rect x="219" y="44" width="30" height="10"></rect><rect x="252" y="41" width="30" height="13"></rect><rect x="285" y="38" width="30" height="16"></rect><rect x="318" y="35" width="30" height="19"></rect><rect x="351" y="32" width="30" height="22"></rect><rect x="384" y="30" width="30" height="24"></rect><rect x="417" y="27" width="30" height="27"></rect><rect x="450" y="24" width="30" height="30"></rect><rect x="483" y="21" width="30" height="33"></rect><rect x="516" y="18" width="30" height="36"></rect><rect x="549" y="15" width="30" height="39"></rect><rect x="582" y="12" width="30" height="42"></rect><rect x="615" y="9" width="30" height="45"></rect>
    </g>
    <text x="20" y="100" fill="var(--ink)">naive</text>
    <g stroke="var(--line)">
      <rect x="120" y="86" width="264" height="20" fill="var(--panel)"></rect><rect x="384" y="86" width="264" height="20" fill="var(--ink)"></rect>
    </g>
    <text x="384" y="122" text-anchor="middle" fill="var(--s2)" font-size="8">hard band edge</text>
    <text x="20" y="156" fill="var(--ink)">dither</text>
    <g stroke="var(--line)">
      <rect x="120" y="142" width="33" height="20" fill="var(--panel)"></rect><rect x="153" y="142" width="33" height="20" fill="var(--panel)"></rect><rect x="186" y="142" width="33" height="20" fill="var(--panel)"></rect><rect x="219" y="142" width="33" height="20" fill="var(--panel)"></rect><rect x="252" y="142" width="33" height="20" fill="var(--ink)"></rect><rect x="285" y="142" width="33" height="20" fill="var(--panel)"></rect><rect x="318" y="142" width="33" height="20" fill="var(--panel)"></rect><rect x="351" y="142" width="33" height="20" fill="var(--ink)"></rect><rect x="384" y="142" width="33" height="20" fill="var(--panel)"></rect><rect x="417" y="142" width="33" height="20" fill="var(--ink)"></rect><rect x="450" y="142" width="33" height="20" fill="var(--ink)"></rect><rect x="483" y="142" width="33" height="20" fill="var(--panel)"></rect><rect x="516" y="142" width="33" height="20" fill="var(--ink)"></rect><rect x="549" y="142" width="33" height="20" fill="var(--ink)"></rect><rect x="582" y="142" width="33" height="20" fill="var(--ink)"></rect><rect x="615" y="142" width="33" height="20" fill="var(--ink)"></rect>
    </g>
    <text x="120" y="188" fill="var(--muted)" font-size="8">filled pixels grow denser left to right — the local average is the gradient</text>
  </g>
</svg>
^ The naive row is two blocks with a seam; the dither row's filled pixels thicken smoothly from left to right, so squinting at it recovers the input ramp. Both use only the two levels.

### The diagnostics: banding and local error

Two numbers make the difference quantitative: the longest run of one level (banding), and the largest local-average error.

```
# dither.py:60-75 — COMPLETE (longest run = banding; max window error = local fidelity)
def longest_run(xs):
    """The longest run of identical values -- the signature of a band."""
    best = run = 1
    for i in range(1, len(xs)):
        run = run + 1 if xs[i] == xs[i - 1] else 1
        best = max(best, run)
    return best


def max_window_error(original, quantized, w=4):
    """Largest difference between the local averages of the original and the quantized."""
    worst = 0.0
    for i in range(len(original) - w + 1):
        mo = sum(original[i:i + w]) / w
        mq = sum(quantized[i:i + w]) / w
        worst = max(worst, abs(mo - mq))
    return worst
```

The self-test folds both into pass/fail conditions:

```
# dither.py:119-125 — COMPLETE (the banding and local-error assertions)
    naive_bands = longest_run(naive) >= 8
    print("  naive quantization creates a band (long identical run) = %s (run %d)" % (naive_bands, longest_run(naive)))

    dither_no_band = longest_run(dith) < longest_run(naive)
    print("  error diffusion breaks the band = %s (run %d < %d)" % (dither_no_band, longest_run(dith), longest_run(naive)))

    lower_local_error = max_window_error(px, dith) < max_window_error(px, naive)
```

Run them and the two methods separate cleanly:

```
# $ python3 dither.py --error
#   method   longest_run   max_window_error   total_brightness
#   naive    8             93.5               2040
#   dither   4             46.8               2040
#   input total brightness = 2040
```

run: 2026-08-26 · deterministic · `python3 dither.py --error`

<svg viewBox="0 0 700 160" role="img" aria-label="Two grouped bar pairs. Longest run: naive 8, dither 4. Max window error: naive 93.5, dither 46.8. In both metrics the naive bar is about double the dither bar.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">naive vs dither on the two diagnostics (lower is better)</text>
    <text x="150" y="40" text-anchor="middle" fill="var(--ink)">longest run</text>
    <rect x="110" y="60" width="30" height="80" fill="var(--s2)"></rect><text x="125" y="54" text-anchor="middle" fill="var(--s2)" font-size="8">8</text>
    <rect x="145" y="100" width="30" height="40" fill="var(--s1)"></rect><text x="160" y="94" text-anchor="middle" fill="var(--s1)" font-size="8">4</text>
    <text x="470" y="40" text-anchor="middle" fill="var(--ink)">max window error</text>
    <rect x="430" y="46" width="30" height="94" fill="var(--s2)"></rect><text x="445" y="40" text-anchor="middle" fill="var(--s2)" font-size="8">93.5</text>
    <rect x="465" y="93" width="30" height="47" fill="var(--s1)"></rect><text x="480" y="87" text-anchor="middle" fill="var(--s1)" font-size="8">46.8</text>
    <line x1="60" y1="140" x2="660" y2="140" stroke="var(--grid)"></line>
    <rect x="560" y="60" width="10" height="10" fill="var(--s2)"></rect><text x="574" y="69" fill="var(--muted)" font-size="8">naive</text>
    <rect x="560" y="76" width="10" height="10" fill="var(--s1)"></rect><text x="574" y="85" fill="var(--muted)" font-size="8">dither</text>
  </g>
</svg>
^ Both diagnostics halve under error diffusion: the banding run from 8 to 4, the local error from 93.5 to 46.8. Same two levels, same total brightness — only the arrangement improved.

The naive method has a longest run of 8 — the black block — and a max window error of 93.5, meaning some four-pixel window's average brightness is off by 93 levels from the input. Error diffusion cuts the longest run to 4 and the window error to 46.8, half. And crucially both preserve the total brightness at 2040, identical to the input: error diffusion does not brighten or darken the image overall, it only rearranges where the levels fall so the local average is right. That is the whole trick — same total ink, spread to match the gradient.

**Quantizing to few levels by rounding each pixel independently bands smooth regions, because the discarded rounding error is lost — error diffusion carries that error to the next pixel, so the local average of the two levels tracks the true gradient, killing the band while preserving total brightness.**

### The self-test

The `--check` mode asserts the fix on every axis: both outputs are valid two-level images, error diffusion preserves brightness, naive bands, error diffusion breaks the band, and its local error is lower.

```
# $ python3 dither.py --check
#   both outputs use only the available levels = True
#   error diffusion preserves total brightness = True (2040 == 2040)
#   naive quantization creates a band (long identical run) = True (run 8)
#   error diffusion breaks the band = True (run 4 < 8)
#   error diffusion has lower local-average error = True (46.8 < 93.5)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 dither.py --check`

The `brightness` line is a correctness anchor with real content: error diffusion must conserve total brightness exactly, because the error it carries is never discarded, only deferred — if the accumulation were wrong, the sum would drift. The `dither_no_band` and `lower_local_error` lines are the payoff, proving the dither both removes the banding signature (the long run) and restores local fidelity (the window error), which are the two faces of the same improvement.

### The running tally

| method | longest run | max local error | total brightness | look |
|---|---|---|---|---|
| naive threshold | 8 | 93.5 | 2040 | hard band |
| error diffusion | 4 | 46.8 | 2040 | smooth dither |

The brightness column is constant — both use the same total amount of white — so that is not where they differ. They differ in arrangement, captured by the run and the local error: the naive method piles all the white on one side (run 8, error 93.5), while error diffusion distributes it to match the gradient (run 4, error 46.8). The residual error in the dither is real — two levels cannot perfectly represent a gradient — but it is spread into high-frequency noise the eye tolerates, rather than concentrated into a low-frequency band the eye catches instantly. Dithering does not reduce the total quantization error so much as move it to where it is not seen.

### What we did not settle

This is one-dimensional error diffusion with one carry. Real Floyd-Steinberg is two-dimensional, distributing the error to four neighbors (right, and three below) with specific weights, which avoids the streaking a single-direction carry can cause. Ordered dithering (Bayer matrices) is a faster, tiling alternative that trades a fixed pattern for no per-pixel state. Blue-noise dithering shapes the error spectrum for the most pleasant texture. Color dithering diffuses error per channel, or in a perceptual space. And there is a subtlety this ramp glosses: error diffusion should happen in linear light, tying back to the gamma module, or the diffused brightness is slightly off. The core here — carry the rounding error forward so the local average survives — is the idea every one of those refines.

## Build

The practice in one paragraph: never quantize a smooth image to few levels by independent rounding; diffuse the rounding error to neighboring pixels so the local average tracks the original, using Floyd-Steinberg (two-dimensional) for images; measure banding by the longest run and fidelity by the local-average error, and confirm total brightness is preserved; and diffuse in linear light for correctness. Prefer error diffusion or blue noise over a naive threshold whenever the content has gradients.

We opened on the two quantizations. The number that proves dithering worked is the banding run and the local error:

```
# modules/generative-media/code/media-inter-06/ — COMPLETE, run from that directory
$ python3 dither.py --error
  naive    8             93.5               2040
  dither   4             46.8               2040
```

Now do it to a real image. Take a smooth gradient or a photo with a sky, quantize it to a small palette two ways — naive nearest-level, and Floyd-Steinberg error diffusion — and compare. Your number to beat is not the total quantization error; it is **the banding (longest run of one level in a smooth region) and the local-average error, which dithering cuts while preserving total brightness**. Look for the band in the naive version and its absence in the dither. Bring back both quantizations and the two diagnostics. Good luck.

## Definition of done

- [ ] A smooth gradient (or image region) quantized to few levels
- [ ] A naive nearest-level quantizer, shown to band
- [ ] An error-diffusion quantizer that carries the rounding error forward
- [ ] Banding measured by the longest run of one level
- [ ] Local-average fidelity measured by the max window error
- [ ] Confirmation both preserve total brightness while error diffusion removes the band
- [ ] `python3 dither.py --check` printing SELF-TEST PASS: binary, brightness, naive-bands, dither-no-band, lower-local-error
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does rounding each pixel independently band a smooth region?
2. What does error diffusion carry forward, and how does that make the local average track the gradient?
3. Both methods preserved total brightness. Where, then, does the difference between them live?
4. Dithering does not reduce total quantization error much. What does it actually do with the error, and why does that help the eye?
5. Your own image was quantized both ways. What were the banding and local-error numbers, and where did you see the band?

## External resources

- Floyd & Steinberg, *An Adaptive Algorithm for Spatial Greyscale* (1976) — my summary: the original error-diffusion dither, with the two-dimensional weight distribution this module reduces to one carry; read it for the real algorithm and its neighbor weights.
- Image-quantization writing on ordered vs error-diffusion vs blue-noise dithering — my summary: the family of dithering methods and their tradeoffs in speed, state, and texture; read it for the alternatives to Floyd-Steinberg and when each fits.
- This hub, *media-inter-04* — modules/generative-media/media-inter-04.md — my summary: the gamma-blending module; read it for why error diffusion, like blending, should happen in linear light for the diffused brightness to be correct.
