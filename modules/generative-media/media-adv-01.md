---
id: media-adv-01
title: The correct downsample — compose the box filter, linear light, and premultiplied alpha
topic: generative-media
level: advanced
status: ready
time: 12-16h
summary: Resizing an antialiased RGBA sprite is one operation — average each block of source pixels into one — and it has three independent ways to be wrong, each its own module: decimate instead of filtering and fine detail aliases into a false artifact, average sRGB bytes instead of linear light and every blend darkens, average straight-alpha color instead of premultiplied and a soft edge fringes. Composing the generative-media track's three signal-correctness fixes into one downsample and measuring against the physically-correct area average, the naive version (decimate, sRGB, straight alpha) scores 819 units of total channel error, and turning the fixes on cumulatively walks it down 819 → 688 → 268 → 0 — box filtering, then linear light, then premultiplied alpha — so only all three together reach zero. No single fix suffices: box-only leaves 688 because it now averages in the wrong space, and linear-only or premul-only leave the full 819 because without a box filter there is no average for them to correct. The correct output is then fixed by a SHA-256 content hash so the pixels that ship are the pixels that were verified. A correct resize is the conjunction of all three corrections, and every image library that gets one wrong ships a subtly broken downscale.
eli5: Shrinking a picture means blending groups of dots into single dots, and there are three ways to blend wrong that all happen at once. If you just throw away every other dot, thin patterns turn into fake stripes. If you blend the numbers the file stores instead of the actual brightness, everything comes out too dark. And if you blend the hidden color of see-through dots, edges get a dirty dark halo. Fixing one doesn't fix the others — you have to do all three right, and only then does the shrunk picture match what your eye should see. Then you fingerprint it so you can prove later it's the real one.
---

## Why this module

The generative-media track built each way an image downsample lies, one module at a time, and each was a real correction to the same act of averaging pixels. Aliasing (`media-inter-03`): halve an image by keeping every other pixel and fine texture does not blur, it folds into a false low-frequency artifact — you must low-pass filter (box-average) before you decimate. Gamma (`media-inter-04`): every byte in an image file is sRGB-encoded, a perceptual code and not the light the pixel emits, so averaging the bytes is arithmetic on the wrong quantity and comes out systematically too dark — you must decode to linear light, average, and re-encode. Premultiplied alpha (`media-inter-05`): a transparent pixel stores its invisible color as black, and averaging that stored black into a visible neighbor with straight alpha bleeds a dark fringe — you must premultiply color by alpha before blending and divide it back out after. This module composes all three into one downsample and measures the property none of them gives alone: reproducing the physically-correct area average, exactly.

The composition matters because the three fixes are independent, and fixing one does nothing for the other two. Box-filter in the wrong color space and the average still darkens; average in linear light with straight alpha and a soft edge still fringes; premultiply and decimate and the texture still aliases. Worse, the fixes interact: turning on the box filter alone — averaging where you used to decimate — actually introduces the darkening and the fringe on the pixels that decimation had accidentally left untouched, because now there is an average, and it is in the wrong space. A correct resize is not "apply the fix you remember"; it is the conjunction of all three, in the right order, on the same average.

You need the track: `media-inter-03` (aliasing), `media-inter-04` (gamma), `media-inter-05` (premultiplied alpha), plus `media-basic-01` (content-hash provenance) to fix the result. Everything runs offline against a six-pixel RGBA strip — the sRGB transfer function and the correct area average are computed in the script, so every number is from the run, not hand-derived — stdlib Python 3, `$0.00`. The instinct to unlearn is that a resize is a single well-known operation. It is three corrections stacked on one average, and a library that ships two of the three produces images that look almost right and are measurably, reproducibly wrong.

Here is the source strip and the downsample it should produce:

```
# modules/generative-media/code/media-adv-01/ — COMPLETE, run from that directory
$ python3 pipeline.py --input

INPUT — source RGBA strip (6 px) and its physically-correct downsample
----------------------------------------------------------------------
  source:
    px0  rgb(255,255,255)  a=1.00
    px1  rgb(  0,  0,  0)  a=0.00
    px2  rgb(  0,  0,  0)  a=1.00
    px3  rgb(255,255,255)  a=1.00
    px4  rgb(255,  0,  0)  a=1.00
    px5  rgb(  0,  0,  0)  a=0.00
  ground truth (box + linear + premultiplied):
    out0 rgb(255,255,255)  a=0.50
    out1 rgb(188,188,188)  a=1.00
    out2 rgb(255,  0,  0)  a=0.50
```

run: 2026-08-27 · deterministic; the RGBA strip is a fixture, the sRGB math is computed · 6 px · `python3 pipeline.py --input`

Three pairs, each built to need a different fix. Pair 0 (opaque white beside a transparent pixel) fringes without premultiplied alpha; pair 1 (opaque black beside opaque white) darkens without linear light; pair 2 (opaque red beside a transparent pixel) fringes on a color channel. All three alias without a box filter. This module is what each fix removes, and why the downsample is only correct with all three.

## Concepts

Named here so you can find them again; each fix is the core of a prior module.

- **Box filter** — average each source pair before halving; the alternative, decimation, drops the second sample and aliases (`media-inter-03`).
- **Linear light** — decode sRGB bytes to the light they represent, average there, re-encode; averaging the bytes darkens (`media-inter-04`).
- **Premultiplied alpha** — multiply color by its own alpha before averaging, divide it back out after; straight alpha bleeds a dark fringe (`media-inter-05`).
- **Ground truth** — the physically-correct area average, which is box + linear + premultiplied together.
- **Content hash** — SHA-256 of the output bytes, so provenance is a function of the pixels, not a label (`media-basic-01`).
- **The conjunction** — a correct downsample needs all three fixes; each alone is insufficient, and two of three still ships a broken image.

## Worked example

Source: the composition of the generative-media track's own signal-correctness fixes into one resize — the exact operation inside every image thumbnailer, texture mipmapper, and antialiaser. The six-pixel strip stands in for a scanline of a real antialiased sprite, so the errors are exact and checkable, and the sRGB math is computed rather than asserted.

Script and fixture: `modules/generative-media/code/media-adv-01/` — `pipeline.py`, and `sprite.json`, one RGBA strip. Every command runs from there.

### The sRGB transfer function, computed

Two of the three fixes stand on one function: the sRGB transfer that maps a stored byte to the linear light it represents. It is computed here, so the ground-truth 188 in the `--input` output is real arithmetic, not a magic number.

```
# pipeline.py:46-57 — COMPLETE (the sRGB EOTF and its inverse; media-inter-04's transfer function)
def srgb_to_linear(c8):
    """One sRGB byte (0-255) to linear light (0-1). The standard sRGB EOTF (media-inter-04)."""
    c = c8 / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    """Linear light (0-1) back to an sRGB byte (0-255)."""
    s = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return round(max(0.0, min(1.0, s)) * 255)
```

Black (0) and white (255) average, in linear light, to 0.5 linear, which re-encodes to the sRGB byte 188 — not 128. That 60-code gap is `media-inter-04` in one line, and it is why pair 1's ground truth is (188,188,188) and not the muddy (128,128,128) a byte average produces.

<svg viewBox="0 0 700 200" role="img" aria-label="The sRGB transfer curve, a concave curve from bottom-left to top-right mapping sRGB byte to linear light. The midpoint sRGB byte 128 maps to about 0.22 linear, while 0.5 linear maps back to sRGB byte 188. Averaging black and white gives 0.5 linear which is byte 188, but averaging the bytes gives 128 which is only 0.22 linear — much darker.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">sRGB byte → linear light: the midpoint byte 128 is only 0.22 of the light</text>
    <line x1="70" y1="170" x2="70" y2="30" stroke="var(--line)"></line>
    <line x1="70" y1="170" x2="640" y2="170" stroke="var(--line)"></line>
    <text x="66" y="30" text-anchor="end" fill="var(--muted)" font-size="7">1.0</text>
    <text x="66" y="174" text-anchor="end" fill="var(--muted)" font-size="7">0</text>
    <text x="640" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">255</text>
    <text x="70" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">byte 0</text>
    <path d="M 70 170 Q 360 150 400 100 T 640 30" fill="none" stroke="var(--s1)"></path>
    <line x1="355" y1="170" x2="355" y2="139" stroke="var(--s2)"></line><circle cx="355" cy="139" r="3" fill="var(--s2)"></circle><text x="355" y="184" text-anchor="middle" fill="var(--s2)" font-size="7">128→0.22</text>
    <line x1="70" y1="100" x2="475" y2="100" stroke="var(--muted)"></line><circle cx="475" cy="100" r="3" fill="var(--acc-ink)"></circle><text x="500" y="98" fill="var(--acc-ink)" font-size="7">0.5 light ← byte 188</text>
    <text x="120" y="150" fill="var(--muted)" font-size="8">byte-average of 0 and 255 lands at 128 → far below the true half-light</text>
  </g>
</svg>
^ The transfer curve is concave: the middle byte 128 carries only about a fifth of full light, while half the light re-encodes to byte 188. Averaging bytes lands at 128 and looks dark; averaging light lands at 188, the correct mid-gray.

### One downsample, three toggles

The whole composition is one function with three independent switches. Each switch is one fix; ground truth is all three on; naive is all three off.

```
# pipeline.py:60-84 — COMPLETE (one averaged output pixel, with each fix independently toggled)
def process_pair(p, q, box, linear, premul):
    """Average source pixels p and q into one, with each of the three fixes independently toggled.

    box    -- average the pair (True) vs decimate, keep p only (False)      [media-inter-03]
    linear -- average in linear light (True) vs in sRGB bytes (False)        [media-inter-04]
    premul -- premultiply alpha before averaging (True) vs straight (False)  [media-inter-05]
    """
    def decode(px):
        r, g, b, a = px
        rgb = [srgb_to_linear(c) if linear else c / 255.0 for c in (r, g, b)]
        if premul:
            rgb = [c * a for c in rgb]
        return rgb, a

    pr, pa = decode(p)
    qr, qa = decode(q)
    if box:
        avg = [(pr[i] + qr[i]) / 2 for i in range(3)]
        aa = (pa + qa) / 2
    else:                                   # decimate: keep the first sample, drop the second
        avg, aa = pr, pa
    if premul:                              # un-premultiply by the blended alpha
        avg = [c / aa if aa > 0 else 0.0 for c in avg]
    out = [linear_to_srgb(c) if linear else round(max(0.0, min(1.0, c)) * 255) for c in avg]
    return [out[0], out[1], out[2], round(aa, 4)]
```

Read the order, because it is the correct one: decode to a working space (optionally linear), optionally premultiply, average (box) or decimate, un-premultiply, re-encode. The `box` switch chooses averaging versus decimation — the aliasing fix. The `linear` switch chooses the space the average happens in — the gamma fix. The `premul` switch weights color by alpha so a transparent pixel contributes zero color — the fringe fix. Ground truth is `process_pair(..., box=True, linear=True, premul=True)`.

<svg viewBox="0 0 700 150" role="img" aria-label="The correct downsample pipeline as five stages in order: decode sRGB to linear, premultiply color by alpha, box-average the pair, un-premultiply by blended alpha, encode linear to sRGB. Each stage is labeled with the module it comes from: decode and encode are gamma (media-inter-04), premultiply and un-premultiply are premultiplied alpha (media-inter-05), the average is the box filter (media-inter-03).">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">the correct order: decode → premultiply → box-average → un-premultiply → encode</text>
    <rect x="20" y="50" width="110" height="40" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="75" y="68" text-anchor="middle" fill="var(--acc-ink)">1. decode</text><text x="75" y="82" text-anchor="middle" fill="var(--acc-ink)" font-size="7">→ linear (04)</text>
    <rect x="150" y="50" width="110" height="40" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="205" y="68" text-anchor="middle" fill="var(--acc-ink)">2. premult</text><text x="205" y="82" text-anchor="middle" fill="var(--acc-ink)" font-size="7">×alpha (05)</text>
    <rect x="280" y="50" width="110" height="40" fill="var(--s1)"></rect><text x="335" y="68" text-anchor="middle" fill="var(--panel)">3. box avg</text><text x="335" y="82" text-anchor="middle" fill="var(--panel)" font-size="7">filter (03)</text>
    <rect x="410" y="50" width="120" height="40" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="470" y="68" text-anchor="middle" fill="var(--acc-ink)">4. un-premult</text><text x="470" y="82" text-anchor="middle" fill="var(--acc-ink)" font-size="7">÷alpha (05)</text>
    <rect x="550" y="50" width="110" height="40" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="605" y="68" text-anchor="middle" fill="var(--acc-ink)">5. encode</text><text x="605" y="82" text-anchor="middle" fill="var(--acc-ink)" font-size="7">→ sRGB (04)</text>
    <line x1="130" y1="70" x2="150" y2="70" stroke="var(--ink)"></line>
    <line x1="260" y1="70" x2="280" y2="70" stroke="var(--ink)"></line>
    <line x1="390" y1="70" x2="410" y2="70" stroke="var(--ink)"></line>
    <line x1="530" y1="70" x2="550" y2="70" stroke="var(--ink)"></line>
    <text x="20" y="120" fill="var(--muted)" font-size="8">the average (stage 3) is the only place pixels combine — the other stages just put them in the right space</text>
  </g>
</svg>
^ The five-stage order composes all three fixes around one averaging step: gamma brackets it (decode/encode), premultiplied alpha brackets it (premultiply/un-premultiply), and the box filter is the average itself. Change the order and the corrections stop composing.

### The naive downsample: all three wrong at once

The strip is halved pair by pair, and ground truth is simply this with all three switches on:

```
# pipeline.py:87-94 — COMPLETE (halve the strip pair by pair; ground truth is all three fixes on)
def downsample(strip, box, linear, premul):
    """Halve an RGBA strip pair by pair."""
    return [process_pair(strip[i], strip[i + 1], box, linear, premul) for i in range(0, len(strip), 2)]


def ground_truth(strip):
    """The physically-correct downsample: box filter, in linear light, premultiplied alpha."""
    return downsample(strip, box=True, linear=True, premul=True)
```

Error against ground truth is the total absolute channel difference, with alpha rescaled to the same 0-255 range so a lost edge counts as much as a darkened one:

```
# pipeline.py:97-105 — COMPLETE (total absolute channel error vs ground truth)
def error_vs(out, truth):
    """Total absolute channel error against ground truth: RGB in 0-255, alpha rescaled to 0-255."""
    e = 0.0
    for o, t in zip(out, truth):
        e += abs(o[0] - t[0]) + abs(o[1] - t[1]) + abs(o[2] - t[2])
        e += abs(o[3] - t[3]) * 255
    return round(e, 1)
```

The naive resize decimates (keeps every other pixel), averages sRGB bytes, and uses straight alpha — every switch off.

```
# $ python3 pipeline.py --naive
#   out0  naive rgb(255,255,255) a=1.00   truth rgb(255,255,255) a=0.50
#   out1  naive rgb(  0,  0,  0) a=1.00   truth rgb(188,188,188) a=1.00
#   out2  naive rgb(255,  0,  0) a=1.00   truth rgb(255,  0,  0) a=0.50
#   total error vs ground truth: 819.0
```

run: 2026-08-27 · deterministic · `python3 pipeline.py --naive`

Read the three output pixels against their ground truth. out1 is the aliasing: decimation kept the black source pixel and dropped the white one, so a black-and-white texture pair collapsed to solid black (0,0,0) where the true average is a mid-gray 188 — the fine detail folded into a false dark artifact, exactly `media-inter-03`. out0 and out2 have the right color but the wrong alpha: decimation kept the opaque sample and its alpha 1.0, so the soft half-transparent edge became fully opaque — the antialiased edge is gone. The total channel error is 819 units. Every pixel is wrong, and it is wrong in a way that looks plausible until you compare it to the truth.

<svg viewBox="0 0 700 210" role="img" aria-label="Three output pixels compared, naive versus ground truth. out0: naive fully opaque white, truth half-transparent white — alpha wrong. out1: naive solid black, truth mid-gray 188 — aliased. out2: naive fully opaque red, truth half-transparent red — alpha wrong. Each naive pixel differs from truth in a way a different fix would correct.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">naive downsample vs ground truth — every output pixel wrong</text>
    <text x="30" y="42" fill="var(--ink)">out1 (texture pair) — aliasing</text>
    <rect x="330" y="30" width="60" height="30" fill="var(--panel)" stroke="var(--s2)"></rect><text x="360" y="50" text-anchor="middle" fill="var(--s2)" font-size="8">naive 0</text>
    <rect x="420" y="30" width="60" height="30" fill="var(--muted)"></rect><text x="450" y="50" text-anchor="middle" fill="var(--panel)" font-size="8">truth 188</text>
    <text x="500" y="50" fill="var(--s2)" font-size="8">decimation folded texture → black</text>
    <text x="30" y="92" fill="var(--ink)">out0 (white + transparent) — fringe/alpha</text>
    <rect x="330" y="80" width="60" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="360" y="100" text-anchor="middle" fill="var(--acc-ink)" font-size="8">a=1.0</text>
    <rect x="420" y="80" width="60" height="30" fill="var(--acc-soft)" stroke="var(--s1)"></rect><text x="450" y="100" text-anchor="middle" fill="var(--acc-ink)" font-size="8">a=0.5</text>
    <text x="500" y="100" fill="var(--s2)" font-size="8">soft edge became fully opaque</text>
    <text x="30" y="142" fill="var(--ink)">out2 (red + transparent) — fringe/alpha</text>
    <rect x="330" y="130" width="60" height="30" fill="var(--s2)"></rect><text x="360" y="150" text-anchor="middle" fill="var(--panel)" font-size="8">a=1.0</text>
    <rect x="420" y="130" width="60" height="30" fill="var(--s2)" opacity="0.5"></rect><text x="450" y="150" text-anchor="middle" fill="var(--ink)" font-size="8">a=0.5</text>
    <text x="500" y="150" fill="var(--s2)" font-size="8">red edge lost its transparency</text>
    <text x="30" y="190" fill="var(--muted)" font-size="8">total channel error 819 — one aliased pixel and two edges stripped of their softness</text>
  </g>
</svg>
^ The naive downsample gets every pixel wrong in a different way: out1 aliased a texture to black, and out0/out2 stripped soft edges to full opacity. Each error is the signature of one missing fix.

### The ablation: only all three reach zero

Turn the fixes on cumulatively — box, then linear, then premultiplied — and watch the total error fall.

```
# $ python3 pipeline.py --ablate
#   box    linear premul  error_vs_ground_truth
#   False  False  False   819.0
#   True   False  False   688.0
#   True   True   False   268.0
#   True   True   True    0.0
```

run: 2026-08-27 · deterministic · `python3 pipeline.py --ablate`

The ladder is 819 → 688 → 268 → 0. Adding the box filter cuts the aliasing (out1 stops collapsing to black), but the total only drops to 688, because now that the pixels are being averaged, they are averaged in the wrong space — the box filter trades the aliasing artifact for the darkening and the fringe it had not been exercising before. Adding linear light removes the darkening (688 → 268). Adding premultiplied alpha removes the last fringe (268 → 0). Every step is necessary and no step alone is sufficient — the error reaches zero only on the last row, with all three on.

<svg viewBox="0 0 700 200" role="img" aria-label="A descending bar chart of total error as fixes are added cumulatively. None: 819. Plus box filter: 688. Plus linear light: 268. Plus premultiplied alpha: 0. The bars step down to zero only when all three fixes are on.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">total error falls to zero only with all three fixes (819 → 688 → 268 → 0)</text>
    <line x1="60" y1="160" x2="660" y2="160" stroke="var(--line)"></line>
    <rect x="90" y="20" width="90" height="140" fill="var(--s2)"></rect><text x="135" y="14" text-anchor="middle" fill="var(--s2)" font-size="8">819</text><text x="135" y="176" text-anchor="middle" fill="var(--muted)" font-size="7">naive</text>
    <rect x="240" y="42" width="90" height="118" fill="var(--s2)"></rect><text x="285" y="36" text-anchor="middle" fill="var(--s2)" font-size="8">688</text><text x="285" y="176" text-anchor="middle" fill="var(--muted)" font-size="7">+ box</text>
    <rect x="390" y="114" width="90" height="46" fill="var(--muted)"></rect><text x="435" y="108" text-anchor="middle" fill="var(--muted)" font-size="8">268</text><text x="435" y="176" text-anchor="middle" fill="var(--muted)" font-size="7">+ linear</text>
    <rect x="540" y="156" width="90" height="4" fill="var(--s1)"></rect><text x="585" y="150" text-anchor="middle" fill="var(--s1)" font-size="8">0</text><text x="585" y="176" text-anchor="middle" fill="var(--s1)" font-size="7">+ premul</text>
    <text x="90" y="196" fill="var(--muted)" font-size="8">box filtering alone (688) trades aliasing for the darkening and fringe it now exposes</text>
  </g>
</svg>
^ Each fix removes one error component and only the full stack reaches zero. The step from 819 to 688 is small because the box filter, applied in the wrong color space, introduces the very errors the next two fixes remove.

**A correct downsample is the conjunction of three independent fixes — box filtering (aliasing), linear light (gamma), and premultiplied alpha (fringe) — applied to the same average, so a resize that gets two of three right still ships a subtly broken image: the error falls 819 → 688 → 268 → 0 and reaches zero only with all three, because each fix corrects a distinct signal error that the others leave untouched.**

### No single fix is sufficient

The self-test's sharpest line is that no one fix alone reaches zero — and that two of the three do nothing at all without the box filter, because there is no average for them to correct.

```
# pipeline.py:168-176 — COMPLETE (each single fix alone, measured against ground truth)
    singles = {
        "box only": downsample(strip, True, False, False),
        "linear only": downsample(strip, False, True, False),
        "premul only": downsample(strip, False, False, True),
    }
    each_insufficient = all(error_vs(o, truth) > 0 for o in singles.values())
    print("  no single fix alone reaches zero = %s (%s)"
          % (each_insufficient, {k: error_vs(v, truth) for k, v in singles.items()}))
```

The run prints `{'box only': 688.0, 'linear only': 819.0, 'premul only': 819.0}`. Box-only drops to 688 because it at least averages. Linear-only and premul-only sit at the full naive 819 — unchanged — because with decimation there is no averaging step, so choosing the color space or premultiplying the sample you kept changes nothing. That is the deepest point of the composition: the box filter is what makes an average exist, and the other two fixes only matter once it does. Order and interaction, not just presence, decide correctness.

### Provenance fixes the correct output

Once the downsample is correct, its lineage is recorded by hashing the actual output bytes — `media-basic-01`. The hash is a function of the pixels, so the correct output and the fringed naive output hash to different values, and the correct output re-verifies.

```
# pipeline.py:108-111 — COMPLETE (provenance is a content hash, not a label; media-basic-01)
def content_hash(strip):
    """SHA-256 of the actual output bytes -- provenance is a function of content, not a label."""
    payload = json.dumps(strip, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]
```

The self-test recomputes the correct output's hash (`a1b6279ea87fd69f`) and confirms it matches, and confirms the naive output hashes to something else. Provenance and correctness compose: the hash pins which pixels shipped, and the three fixes are what make those pixels right in the first place — a manifest that hashes a broken downscale is provenance for a bug.

### The self-test

The `--check` mode asserts the whole composition: the naive downsample is wrong, no single fix reaches zero, all three together do, and the correct output's content hash verifies while the naive one differs.

```
# $ python3 pipeline.py --check
#   the naive downsample differs from ground truth = True (error 819.0)
#   no single fix alone reaches zero = True ({'box only': 688.0, 'linear only': 819.0, 'premul only': 819.0})
#   all three fixes together reach zero error = True
#   the correct output's content hash re-verifies = True (a1b6279ea87fd69f)
#   the naive output hashes to a different value = True
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 pipeline.py --check`

The payoff line is that all three together hit zero exactly — not close, zero — because the composed pipeline is the ground-truth definition:

```
# pipeline.py:177-180 — COMPLETE (all three fixes reproduce ground truth exactly)
    allthree = downsample(strip, True, True, True)
    all_correct = error_vs(allthree, truth) == 0
    print("  all three fixes together reach zero error = %s" % all_correct)
```

`each_insufficient` is the conjunction proof: three fixes, none sufficient alone. `all_correct` is the payoff: their combination is exactly the physically-correct average. And the two provenance lines close the loop from `media-basic-01` — the correct pixels get a verifiable identity, and a broken downscale gets a different one, so the manifest cannot bless the wrong image.

### The running tally

| output pixel | source pair | naive result | ground truth | error cause | fix that removes it |
|---|---|---|---|---|---|
| out0 | white + transparent | opaque white (a=1.0) | white a=0.5 | soft edge stripped | box (+ premul for color) |
| out1 | black + white texture | solid black | gray 188 | aliased to black | box, then linear |
| out2 | red + transparent | opaque red (a=1.0) | red a=0.5 | fringe / edge stripped | box + premul |
| total | — | error 819 | error 0 | all three at once | box + linear + premul |

Read the last two columns. Each pixel's error traces to a specific missing fix, and no one fix appears alone — every correct output needs the box filter plus at least one of the color-space fixes. The total row is the composition: 819 down to 0, but only with all three. This is why a downscale cannot be trusted because it "uses a filter" or "works in linear" — the claim has to be all three, on the same average, in the right order, or the image that ships is the almost-right one that a pixel-diff against the truth exposes in a second.

### What we did not settle

This composes three fixes for the 2:1 downsample; a full media pipeline has more, and the track named them. Quantizing the correct output down to a small palette needs dithering (`media-inter-06`) or the smooth gradient bands — error diffusion is the fourth fix, applied after this one. The box filter here is the simplest low-pass; real resamplers use a wider kernel (Lanczos, Mitchell) that trades ringing against sharpness, but the linear-light and premultiplied requirements are identical regardless of kernel. The strip is one dimension; a real image filters in two, and the same three fixes apply per axis. And the perceptual-hash deduplication from `media-inter-02` sits downstream — once the downscale is correct and content-hashed, a perceptual hash decides whether two correct outputs are the same look. The invariant holds across all of it: an average of pixels is only correct in linear light, with alpha premultiplied, over a filtered neighborhood — and anything less ships a broken image with a straight face.

## Build

The build in one paragraph: to downsample an RGBA image, decode each source byte to linear light, premultiply each color by its own alpha, average over the source neighborhood a block covers (a box filter, not decimation), then divide the color back out by the blended alpha and re-encode to sRGB — and hash the output bytes so the result has a verifiable identity. Extend it with error diffusion when you quantize to a palette, a wider reconstruction kernel than a box if you need it, and the same three corrections along both image axes; never trust a resize that claims only one of the three fixes.

We opened on the strip. The number that proves the composition works is the error ladder collapsing to zero:

```
# modules/generative-media/code/media-adv-01/ — COMPLETE, run from that directory
$ python3 pipeline.py --ablate
  False  False  False   819.0
  True   True   True     0.0
```

Now build your own. Take a real antialiased sprite with a soft alpha edge and a fine texture, and downsample it two ways: the naive way (decimate, sRGB, straight alpha) and the composed way (box, linear, premultiplied). Your number to beat is not sharpness by eye; it is **total channel error against the physically-correct area average, naive versus composed** — the composed resize should reach zero while the naive one does not, and knocking out any single fix should lift it off zero. Bring back both error numbers and the content hash of your correct output. Good luck.

## Definition of done

- [ ] The sRGB transfer function and its inverse, computed (not a hard-coded 188)
- [ ] A downsample with three independent toggles: box filter, linear light, premultiplied alpha
- [ ] A ground-truth downsample defined as all three fixes on
- [ ] A naive downsample (decimate, sRGB bytes, straight alpha) measured against ground truth
- [ ] Confirmation no single fix alone reaches zero error, and all three together do
- [ ] A SHA-256 content hash of the correct output that re-verifies, differing from the naive output's
- [ ] `python3 pipeline.py --check` printing SELF-TEST PASS: naive_wrong, each_insufficient, all_correct, provenance
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Name the three fixes a correct RGBA downsample composes and the artifact each removes. Which module is each from?
2. Why does box filtering alone drop the error only to 688, not lower? What does averaging in the wrong space reintroduce?
3. Linear-only and premul-only both score the full naive 819 — unchanged. Why do they do nothing without the box filter?
4. What is out1 in the naive run, and why? Name the artifact and the source pair that produced it.
5. Your own sprite was downsampled both ways. What was the composed error, the naive error, and did knocking out one fix lift the composed off zero?

## External resources

- Blinn, *Dirty Pixels* / *A Trip Down the Graphics Pipeline* — my summary: the essays that put premultiplied alpha and gamma-correct compositing on record; read them for why these are not options but the definition of a correct blend.
- *A Pixel Is Not a Little Square* (Alvy Ray Smith) and the GPU Gems chapters on gamma — my summary: the sampling-theory and color-space grounding under the box filter and linear-light rules here; read them for the theory this composition operationalizes.
- This hub, *media-inter-03*, *media-inter-04*, *media-inter-05*, *media-basic-01* — the aliasing, gamma, premultiplied-alpha, and content-hash modules this pipeline composes; read each for one fix in isolation before seeing all of them run on a single downsample.
