---
id: media-inter-09
title: Pick the palette from the image's colors, not a fixed grid — adaptive quantization slashes the error
topic: generative-media
level: intermediate
status: ready
time: 5-8h
summary: Reducing an image to a small palette forces a choice — which colors go in it — and the lazy answer is a fixed grid, spacing the levels evenly across the range (0, 85, 170, 255 for four gray levels), which ignores that an image's colors are not spread evenly but cluster. A photo living near black and near a warm highlight, with almost nothing between, has a uniform palette waste half its entries on the empty middle and quantize the crowded regions coarsely. An adaptive palette puts its entries where the colors are: median cut sorts the colors, recursively splits the set at its median into as many boxes as there are palette slots, and takes each box's mean, so dense regions get finely spaced entries and empty regions get none. On the fixture the pixels cluster near 30 and 220; the uniform 4-level palette [0, 85, 170, 255] scores a mean quantization error of 32.1 with two levels stranded at 85 and 170 that no pixel is near, while the adaptive palette [27, 32, 218, 223] places all four among the clusters and cuts the error to 1.3 — a 25× reduction from the same four levels on the same pixels, because the palette went where the data was.
eli5: If you get only four crayons to redraw a picture that's mostly dark blue and bright yellow, you'd be silly to pick black, gray, light-gray, and white spaced out evenly — two of your crayons would be useless colors the picture barely has. The smart move is to look at the picture first and pick four crayons near the dark blue and the bright yellow, where all the color actually is. Choosing your few colors to match what's in the image, instead of a fixed even set, makes the copy far closer to the original.
---

## Why this module

Palette quantization is the act of representing an image with a small fixed set of colors — 4, 16, 256 — instead of the millions it might contain. It is what GIF does, what an indexed-color format does, what a constrained display forces. The mechanical part is easy: map each pixel to the nearest palette color. The part that decides the quality is upstream and easy to get lazily wrong: choosing which colors the palette contains.

The lazy choice is a uniform grid — space the palette levels evenly across the whole range. For four gray levels that is 0, 85, 170, 255; for a color palette it is an evenly-spaced lattice in the RGB cube. It is simple and it is oblivious, because it assumes the image's colors are spread evenly across the range, and they never are. Real images cluster: a portrait is mostly skin tones and background, a dusk photo is mostly dark with a bright sky, and vast regions of the color space are empty. A uniform palette spends its precious few entries on that grid regardless, so entries land in empty regions where no pixel will ever use them, while the crowded regions — where every pixel actually is — get only whatever grid points happen to fall nearby, and are quantized coarsely.

The fix is to choose the palette adaptively, from the image's own color distribution. Median cut is the classic algorithm: treat all the image's colors as a set, recursively split the set at its median along its widest axis into as many boxes as you have palette slots, and take each box's mean color as a palette entry. Because the splitting follows the data, dense regions get subdivided into many finely-spaced entries and empty regions get none. This module makes the difference exact: the same four levels placed by a uniform grid versus by median cut, on pixels that cluster near 30 and 220, and the quantization error each produces. Everything runs offline against a pixel fixture, stdlib Python 3, `$0.00`, with both palettes and errors computed. The instinct to unlearn is that a palette should cover the range. A palette should cover the *data*, and a fixed grid covers the range at the data's expense.

## Concepts

Named here so you can find them again; each is built below.

- **Palette** — the small fixed set of colors an image is reduced to.
- **Quantization** — mapping each pixel to its nearest palette color.
- **Uniform palette** — levels spaced evenly across the range; oblivious to the image.
- **Adaptive palette** — levels chosen from the image's color distribution.
- **Median cut** — recursively split the color set at its median into boxes; each box's mean is a level.
- **Quantization error** — mean distance from each pixel to its nearest palette color.

## Worked example

Source: the palette-selection step of image quantization — choosing the colors before mapping pixels to them. The pixel values stand in for a real image's colors, kept grayscale (one dimension) so the median cut and the errors are exact.

Script and fixture: `modules/generative-media/code/media-inter-09/` — `palette.py`, and `pixels.json`, twenty clustered pixel values. Every command runs from there.

### The colors cluster

The image's pixels are not spread across the range; they pile up in two places.

```
# $ python3 palette.py --pixels
#     0-31   #######              7
#    32-63   ###                  3
#    64-95                        0
#   128-159                       0
#   192-223  ########             8
#   224-255  ##                   2
```

run: 2026-08-27 · deterministic; the pixel values are a fixture · 20 pixels · `python3 palette.py --pixels`

Ten of the twenty pixels sit in the 0–63 range (near 30) and ten in the 192–255 range (near 220). The entire middle of the range — 64 through 191, more than half of it — is empty: not one pixel lives there. This is the shape real images have, and it is the shape a uniform palette is blind to. Any palette that puts entries in that empty middle is spending them on colors the image does not contain.

### The two palettes

A uniform palette spaces levels across the range; median cut splits the data.

```
# palette.py:44-62 — COMPLETE (a fixed grid vs recursive median-split of the pixel set)
def uniform_palette(k):
    """A fixed grid: k levels spaced evenly across 0..255, ignoring where the colors are."""
    if k == 1:
        return [128]
    return [round(i * 255 / (k - 1)) for i in range(k)]


def median_cut_palette(pixels, k):
    """Adaptive: recursively split the pixel set at its median into k boxes; each box's mean is a level."""
    boxes = [sorted(pixels)]
    while len(boxes) < k:
        # split the box with the widest spread
        box = max(boxes, key=lambda b: (b[-1] - b[0], b))
        boxes.remove(box)
        mid = len(box) // 2
        boxes.append(box[:mid])
        boxes.append(box[mid:])
        boxes.sort()
    return [round(mean(b)) for b in boxes if b]
```

`uniform_palette` computes its levels from the range alone — it never looks at the pixels. `median_cut_palette` starts with all the pixels in one box and repeatedly splits the widest box at its median, so it always subdivides wherever the data is most spread out, following the colors. The error is the mean distance from each pixel to the nearest level it was assigned:

```
# palette.py:67-69 — COMPLETE (quantization error: mean distance to the nearest palette level)
def quantize_error(pixels, palette):
    """Mean absolute distance from each pixel to its nearest palette level."""
    return round(mean([min(abs(p - c) for c in palette) for p in pixels]), 4)
```

<svg viewBox="0 0 700 170" role="img" aria-label="Median cut splitting the pixel set into four boxes. Step 1: one box of all 20 pixels. Step 2: split at the median into a dark box and a bright box. Step 3: split each of those into two, giving four boxes clustered on the data. Each box's mean becomes a palette level.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">median cut: split the widest box at its median until you have k boxes</text>
    <text x="30" y="46" fill="var(--muted)" font-size="8">1 box</text>
    <rect x="90" y="34" width="540" height="16" fill="var(--panel)" stroke="var(--line)"></rect><text x="360" y="46" text-anchor="middle" fill="var(--muted)" font-size="7">all 20 pixels</text>
    <text x="30" y="86" fill="var(--muted)" font-size="8">2 boxes</text>
    <rect x="90" y="74" width="120" height="16" fill="var(--s1)" opacity="0.4"></rect><text x="150" y="86" text-anchor="middle" fill="var(--ink)" font-size="7">dark ~30</text>
    <rect x="510" y="74" width="120" height="16" fill="var(--s1)" opacity="0.4"></rect><text x="570" y="86" text-anchor="middle" fill="var(--ink)" font-size="7">bright ~220</text>
    <text x="30" y="126" fill="var(--muted)" font-size="8">4 boxes</text>
    <rect x="90" y="114" width="56" height="16" fill="var(--s1)"></rect><rect x="154" y="114" width="56" height="16" fill="var(--s1)"></rect><rect x="510" y="114" width="56" height="16" fill="var(--s1)"></rect><rect x="574" y="114" width="56" height="16" fill="var(--s1)"></rect>
    <text x="118" y="126" text-anchor="middle" fill="var(--panel)" font-size="6">27</text><text x="182" y="126" text-anchor="middle" fill="var(--panel)" font-size="6">32</text><text x="538" y="126" text-anchor="middle" fill="var(--panel)" font-size="6">218</text><text x="602" y="126" text-anchor="middle" fill="var(--panel)" font-size="6">223</text>
    <text x="90" y="152" fill="var(--muted)" font-size="8">each final box's mean is a palette level — all four land on the data, none in the empty middle</text>
  </g>
</svg>
^ Median cut splits the pixel set at its median, always subdividing the widest box, so the four final boxes cluster on the two dense regions. Each box's mean (27, 32, 218, 223) becomes a level — the algorithm follows the data.

Compute both and their errors:

```
# $ python3 palette.py --palettes
#   uniform:  [0, 85, 170, 255]        error 32.10
#   adaptive: [27, 32, 218, 223]       error 1.30
```

run: 2026-08-27 · deterministic · `python3 palette.py --palettes`

The uniform palette is [0, 85, 170, 255], and two of those four levels — 85 and 170 — sit in the empty middle where no pixel is; they are dead weight. The two dark-cluster pixels (near 30) get quantized to 0, and the bright-cluster pixels (near 220) to 255, both far away, for a mean error of 32.1. The adaptive palette is [27, 32, 218, 223]: all four levels land inside the two clusters, giving each cluster two finely-spaced entries, so every pixel is within a few units of a level and the mean error is 1.3. Same four levels, same pixels — the adaptive palette cut the error by a factor of 25 purely by putting the levels where the pixels were.

<svg viewBox="0 0 700 200" role="img" aria-label="A value axis 0 to 255 with two pixel clusters near 30 and 220. The uniform palette marks levels at 0, 85, 170, 255 — two of them (85, 170) sit in the empty middle away from any pixel. The adaptive palette marks four levels clustered at 27, 32, 218, 223, all inside the two pixel clusters.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">where the palette levels land, against the pixel clusters (0–255 axis)</text>
    <rect x="70" y="40" width="70" height="30" fill="var(--s1)" opacity="0.3"></rect><text x="105" y="34" text-anchor="middle" fill="var(--muted)" font-size="7">cluster ~30</text>
    <rect x="540" y="40" width="70" height="30" fill="var(--s1)" opacity="0.3"></rect><text x="575" y="34" text-anchor="middle" fill="var(--muted)" font-size="7">cluster ~220</text>
    <text x="20" y="95" fill="var(--s2)" font-size="8">uniform</text>
    <line x1="70" y1="90" x2="640" y2="90" stroke="var(--line)"></line>
    <line x1="70" y1="84" x2="70" y2="96" stroke="var(--s1)"></line><text x="70" y="108" text-anchor="middle" fill="var(--s1)" font-size="7">0</text>
    <line x1="260" y1="84" x2="260" y2="96" stroke="var(--s2)"></line><text x="260" y="108" text-anchor="middle" fill="var(--s2)" font-size="7">85 ✗</text>
    <line x1="450" y1="84" x2="450" y2="96" stroke="var(--s2)"></line><text x="450" y="108" text-anchor="middle" fill="var(--s2)" font-size="7">170 ✗</text>
    <line x1="640" y1="84" x2="640" y2="96" stroke="var(--s1)"></line><text x="640" y="108" text-anchor="middle" fill="var(--s1)" font-size="7">255</text>
    <text x="330" y="128" fill="var(--s2)" font-size="8">two levels wasted in the empty middle → error 32.1</text>
    <text x="20" y="155" fill="var(--s1)" font-size="8">adaptive</text>
    <line x1="70" y1="150" x2="640" y2="150" stroke="var(--line)"></line>
    <line x1="130" y1="144" x2="130" y2="156" stroke="var(--s1)"></line><line x1="141" y1="144" x2="141" y2="156" stroke="var(--s1)"></line><text x="135" y="168" text-anchor="middle" fill="var(--s1)" font-size="7">27,32</text>
    <line x1="558" y1="144" x2="558" y2="156" stroke="var(--s1)"></line><line x1="569" y1="144" x2="569" y2="156" stroke="var(--s1)"></line><text x="563" y="168" text-anchor="middle" fill="var(--s1)" font-size="7">218,223</text>
    <text x="330" y="188" fill="var(--s1)" font-size="8">all four levels inside the clusters → error 1.3</text>
  </g>
</svg>
^ The uniform palette drops levels at 85 and 170 in the empty middle, far from every pixel; the adaptive palette places all four levels inside the two clusters. Same count, and the error falls from 32.1 to 1.3.

**An image's colors cluster rather than spreading evenly, so a uniform palette wastes entries on empty regions of the range while quantizing the crowded regions coarsely — choosing the palette adaptively from the data (median cut: recursively split the color set at its median, take box means) places every entry where pixels are, cutting the quantization error from 32.1 to 1.3 on the same four levels, because a palette should cover the data, not the range.**

### The self-test

The `--check` mode plants the bug — the uniform grid — and proves it: the adaptive palette has lower error, roughly halves it or better, the uniform palette strands a level far from every pixel, and every adaptive level sits near real pixels.

```
# $ python3 palette.py --check
#   the adaptive palette has lower quantization error = True (1.30 vs 32.10)
#   it roughly halves the error or better = True (24.69x)
#   the uniform palette strands a level far from every pixel = True ([85, 170])
#   every adaptive level sits near real pixels (none wasted) = True ([27, 32, 218, 223])
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 palette.py --check`

The headline is the error ratio — the adaptive palette does not shave the error, it collapses it:

```
# palette.py:110-113 — COMPLETE (adaptive has lower error, by a wide factor)
    adaptive_better = e_ada < e_uni
    print("  the adaptive palette has lower quantization error = %s (%.2f vs %.2f)" % (adaptive_better, e_ada, e_uni))

    roughly_halves = e_ada < e_uni / 1.8
    print("  it roughly halves the error or better = %s (%.2fx)" % (roughly_halves, e_uni / e_ada))
```

<svg viewBox="0 0 700 150" role="img" aria-label="Two error bars. Uniform palette: 32.1, a tall bar. Adaptive palette: 1.3, a tiny sliver. The adaptive error is about 25 times smaller for the same four levels.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">mean quantization error, same 4 levels, same pixels</text>
    <line x1="60" y1="120" x2="660" y2="120" stroke="var(--line)"></line>
    <rect x="120" y="30" width="120" height="90" fill="var(--s2)"></rect><text x="180" y="24" text-anchor="middle" fill="var(--s2)" font-size="9">32.1</text><text x="180" y="138" text-anchor="middle" fill="var(--muted)" font-size="8">uniform</text>
    <rect x="420" y="116" width="120" height="4" fill="var(--s1)"></rect><text x="480" y="108" text-anchor="middle" fill="var(--s1)" font-size="9">1.3</text><text x="480" y="138" text-anchor="middle" fill="var(--muted)" font-size="8">adaptive</text>
    <text x="300" y="70" fill="var(--acc-ink)" font-size="8">25× smaller →</text>
  </g>
</svg>
^ For the same four levels the adaptive palette's error is about 25 times smaller — a difference in kind, not degree, because two of the uniform palette's levels were doing no work at all.

The `uniform_wastes` and `adaptive_uses_all` lines are the mechanism, stated as two complementary facts: the uniform palette has entries (85, 170) that no pixel is within 40 of — pure waste — while every adaptive entry is near real pixels. The error difference is not luck; it is the direct consequence of where the entries landed. A palette entry far from all the data does nothing but reduce your effective palette size, so the uniform 4-level palette is really a 2-level palette on this image, which is why its error is so much worse.

```
# palette.py:117-120 — COMPLETE (uniform strands far-from-data levels; adaptive uses them all)
    empty_levels = [c for c in uni if min(abs(p - c) for p in pixels) > 40]
    uniform_wastes = len(empty_levels) > 0
    print("  the uniform palette strands a level far from every pixel = %s (%s)" % (uniform_wastes, empty_levels))

    adaptive_uses_all = all(min(abs(p - c) for p in pixels) <= 40 for c in ada)
```

### The running tally

| palette | levels | levels in empty middle | error |
|---|---|---|---|
| uniform | 0, 85, 170, 255 | 85, 170 (2 wasted) | 32.10 |
| adaptive | 27, 32, 218, 223 | none | 1.30 |

Read the middle column against the error column: the uniform palette wastes two of its four levels on the empty middle, so only two levels do any work, and the error is high; the adaptive palette wastes none, so all four work, and the error is tiny. The relationship is direct — quantization error is set by how close the palette entries are to the pixels, and a uniform grid guarantees some entries are far because it places them without looking. Adaptive selection is not a small refinement; on clustered data (which is all real data) it is the difference between a usable palette and a wasteful one, at the same palette size.

### What we did not settle

This is median cut in one dimension; real palette quantization has more. Colors are three-dimensional, so median cut splits boxes along whichever channel (R, G, or B) has the widest spread, and the boxes are 3D — the principle is identical but the bookkeeping grows. Median cut is one adaptive method; k-means (cluster the colors, take centroids) often gives lower error at more compute cost, and octree quantization trades quality for speed. Perceptual distance matters: nearest should ideally be measured in a perceptually-uniform space (and weighted by luma, `media-inter-07`) rather than raw RGB, so the error the eye sees is minimized rather than the numeric error. And adaptive palettes compose with dithering (`media-inter-06`): pick the palette adaptively, then dither the mapping to hide the banding a small palette still causes. The invariant: choose palette entries from the data's distribution, never from a fixed grid, because clustered data makes a grid waste entries where nothing lives.

## Build

The build in one paragraph: choose a quantization palette adaptively from the image's own color distribution rather than a fixed grid — median cut (recursively split the color set at its median along its widest channel, take each box's mean) places entries where the colors cluster, so none are wasted in empty regions and the crowded regions are finely resolved, cutting quantization error dramatically on the clustered data real images have. Extend median cut to three color dimensions, consider k-means for lower error, measure nearest in a perceptual (luma-weighted) space, and dither the final mapping to hide residual banding.

We opened on the clusters. The number that proves the fix is the quantization error of each palette:

```
# modules/generative-media/code/media-inter-09/ — COMPLETE, run from that directory
$ python3 palette.py --palettes
  uniform:  [0, 85, 170, 255]        error 32.10
  adaptive: [27, 32, 218, 223]       error 1.30
```

Now build your own. Take a real image whose colors cluster (most do), and quantize it with a uniform palette and an adaptive (median-cut or k-means) palette of the same size. Your number to beat is not palette size; it is **the quantization error, uniform versus adaptive** — adaptive should be far lower, with no palette entry stranded away from the data. Confirm the uniform palette wastes entries in empty regions. Bring back both errors. Good luck.

## Definition of done

- [ ] A uniform palette (evenly spaced levels) and an adaptive one (median cut)
- [ ] A quantization error: mean distance from each pixel to its nearest palette level
- [ ] Pixels that cluster, with an empty region between clusters
- [ ] Confirmation the adaptive palette has substantially lower error
- [ ] Confirmation the uniform palette strands levels far from any pixel (wasted)
- [ ] Confirmation every adaptive level sits near real pixels
- [ ] `python3 palette.py --check` printing SELF-TEST PASS: adaptive_better, roughly_halves, uniform_wastes, adaptive_uses_all
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does a uniform palette waste entries on real images? What assumption does it make that is false?
2. How does median cut decide where to place palette entries?
3. On the fixture, which uniform levels were wasted and why?
4. Why is a uniform 4-level palette "really a 2-level palette" on the clustered image?
5. Your own image was quantized with both palettes. What error did each produce, and did the uniform one strand entries?

## External resources

- Heckbert, *Color Image Quantization for Frame Buffer Display* (the median-cut paper) — my summary: the original adaptive palette algorithm and its 3D box-splitting; read it for the color-dimension mechanics this 1-D version abstracts.
- Any comparison of median cut, k-means, and octree quantization — my summary: the quality/speed tradeoffs among adaptive palette methods; read it for when to prefer each.
- This hub, *media-inter-06* (dither when you quantize) and *media-inter-07* (perceptual luma weights) — read them for the dithering that pairs with an adaptive palette and the perceptual distance the nearest-color search should use.
