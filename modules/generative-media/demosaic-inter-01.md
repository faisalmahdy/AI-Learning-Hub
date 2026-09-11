---
id: demosaic-inter-01
title: Interpolate each missing color from its measured neighbors — replicating the nearest one invents false colors
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: A camera's image sensor does not measure red, green, and blue at every pixel. Over each photosite sits a single colored filter, so each site measures only one channel; the raw output is a mosaic of single-color samples in a fixed pattern (the Bayer array: half green, a quarter each red and blue). The full-color image — three channels at every pixel — must be reconstructed by estimating, at each pixel, the two channels it did not measure, from the neighbors that did. This is demosaicing, done for every photo a Bayer-sensor camera takes. The naive reconstruction fills each missing channel from the nearest pixel that measured it — copy the closest red into a pixel that only measured green. It is fast and wrong at exactly the places that matter: copying the nearest same-color sample ignores the sample on the other side, so across a gradient or an edge it produces a value too high or too low, and because the three channels are reconstructed independently with this crude copy, their errors do not match — a pixel that should be neutral gray gets too much red and too little green, which the eye sees as a colored fringe or zipper along edges. The better reconstruction interpolates: estimate a missing channel as the average of the measured samples on both sides, so it tracks the real gradient and the channels stay consistent. On a fixture where the sensor row alternates R and G filters and both channels vary linearly, bilinear interpolation recovers the ground truth exactly at interior pixels (error 0) while nearest-neighbor replication is off by up to 20 levels (interior error 40 vs 0).
eli5: Imagine a row of light meters where each one can only see ONE color — red, then green, then red, then green. To make a full-color picture you need to guess the colors each meter couldn't see. The lazy way is to just copy the nearest meter that saw that color — but if you always grab the one on your left, you ignore the one on your right, and when the color is smoothly changing you end up too high or too low. The better way is to take the average of the same-color meters on both sides of you: if the green meter to your left read 110 and the one to your right read 130, your green is 120 — smack in the middle, which is exactly right. Guessing from both sides tracks the real color; copying one side invents streaks and false tints.
---

## Why this module

A color photo begins as a grid of single-color measurements, not a color image, and the step that turns one into the other is a guess made millions of times per frame. Because each photosite is under just one colored filter, two of every pixel's three channels are missing and have to be filled in from neighbors — and the way you fill them decides whether the reconstruction is faithful or whether it paints colors into the image that the scene never had. The tempting shortcut, copy the nearest same-color sample, is where false color is born, because it makes a decision from one side while ignoring the other.

Over each photosite sits a single colored filter, so the sensor's raw output is a mosaic of single-color samples in a fixed pattern, and the full-color image must be reconstructed by estimating, at each pixel, the two channels that pixel did not measure. The naive reconstruction fills each missing channel from the nearest pixel that measured it. This is fast and wrong at exactly the places that matter: copying the nearest same-color sample ignores the sample on the other side, so across a gradient or an edge it produces a value too high or too low, and because the three channels are reconstructed independently, their errors do not match — the eye sees a colored fringe.

The better reconstruction interpolates: estimate a missing channel as the average of the measured samples of that channel on both sides. A smoothly varying channel is close to linear over a couple of pixels, so averaging the two neighbors lands on the true value, and the channels stay consistent, which is what kills the false color. This module runs both on a mosaic with a known ground truth.

**Reconstruct a missing color channel by interpolating the measured samples of that channel on both sides, not by copying the single nearest one, because independent nearest-neighbor replication invents color fringes across edges and gradients while two-sided interpolation tracks the true value and keeps the channels consistent.**

## Concepts

**The two estimators differ only in how they combine the neighbors:** nearest copies the closer measured sample; bilinear averages the two.

```python filename=modules/generative-media/code/demosaic-inter-01/demosaic.py:66-79 COMPLETE
def estimate_nearest(pattern, mosaic, i, channel):
    """Replicate the single nearest measured sample of the channel (tie -> left)."""
    left, right = neighbors(pattern, mosaic, i, channel)
    if left and right:
        return left[0] if left[1] <= right[1] else right[0]
    return (left or right)[0]


def estimate_bilinear(pattern, mosaic, i, channel):
    """Average the measured samples of the channel on both sides (one side only at an edge)."""
    left, right = neighbors(pattern, mosaic, i, channel)
    if left and right:
        return (left[0] + right[0]) / 2
    return (left or right)[0]
```

**Reconstruction keeps the measured channel exactly and estimates the missing one** at every pixel, producing a full (R, G) per position.

```python filename=modules/generative-media/code/demosaic-inter-01/demosaic.py:82-90 COMPLETE
def reconstruct(data, estimator):
    """Full (R, G) per pixel: the measured channel is kept; the missing one is estimated."""
    pattern, mosaic = data["pattern"], data["mosaic"]
    out = []
    for i, ch in enumerate(pattern):
        r = mosaic[i] if ch == "R" else estimator(pattern, mosaic, i, "R")
        g = mosaic[i] if ch == "G" else estimator(pattern, mosaic, i, "G")
        out.append((r, g))
    return out
```

<svg role="img" aria-label="A row of six photosites alternating R and G filters; the R site at position 2 is missing green, which nearest replication copies from the left green (110) while bilinear averages the greens on both sides (110 and 130) to 120" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">filling the missing green at an R site: copy-left vs average-both</text>
  <g font-size="7">
    <rect x="20" y="24" width="36" height="18" fill="var(--s2)"/><text x="30" y="37" fill="var(--panel)">R 200</text>
    <rect x="58" y="24" width="36" height="18" fill="var(--s1)"/><text x="66" y="37" fill="var(--panel)">G 110</text>
    <rect x="96" y="24" width="36" height="18" fill="var(--s2)"/><text x="104" y="37" fill="var(--panel)">R 180</text>
    <rect x="134" y="24" width="36" height="18" fill="var(--s1)"/><text x="142" y="37" fill="var(--panel)">G 130</text>
    <rect x="172" y="24" width="36" height="18" fill="var(--s2)"/><text x="180" y="37" fill="var(--panel)">R 160</text>
    <rect x="210" y="24" width="36" height="18" fill="var(--s1)"/><text x="218" y="37" fill="var(--panel)">G 150</text>
  </g>
  <text x="96" y="56" fill="var(--muted)" font-size="6">pos 2 needs green ↑</text>
  <path d="M76 46 L110 58" fill="none" stroke="var(--muted)" stroke-dasharray="1 2"/>
  <path d="M152 46 L118 58" fill="none" stroke="var(--muted)" stroke-dasharray="1 2"/>
  <text x="20" y="80" fill="var(--s2)" font-size="7">nearest: copy left 110 (wrong)</text>
  <text x="20" y="98" fill="var(--s1)" font-size="7">bilinear: (110+130)/2 = 120 (= truth)</text>
</svg>
^ The R site at position 2 measured no green; nearest replication copies the left green (110), ignoring the right, while bilinear averages the greens on both sides (110 and 130) to 120 — the true value — which is why the two-sided estimate tracks the gradient and the one-sided copy does not.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/demosaic-inter-01/demosaic.py

The fixture is the filter pattern, the single value each photosite measured, and the scene's true R and G (both linear).

```json filename=modules/generative-media/code/demosaic-inter-01/demosaic.json:2-6 COMPLETE
  "pattern": ["R", "G", "R", "G", "R", "G"],
  "mosaic": [200, 110, 180, 130, 160, 150],
  "truth_R": [200, 190, 180, 170, 160, 150],
  "truth_G": [100, 110, 120, 130, 140, 150]
```

Run `--recon`.

```text filename=--recon
RECON — reconstructed (R,G) per pixel; the measured channel is exact, the other is estimated
------------------------------------------------------------------------------
  pos  filter  nearest (R,G)   bilinear (R,G)   truth (R,G)
  0    R       (200, 110)      (200, 110)       (200, 100)
  1    G       (200, 110)      (190, 110)       (190, 110)
  2    R       (180, 110)      (180, 120)       (180, 120)
  3    G       (180, 130)      (170, 130)       (170, 130)
  4    R       (160, 130)      (160, 140)       (160, 140)
  5    G       (160, 150)      (160, 150)       (150, 150)
------------------------------------------------------------------------------
  at interior pixels bilinear matches the truth; nearest replication does not.
```

Read the three (R,G) columns for the interior pixels (1 through 4). At each, the bilinear reconstruction equals the truth exactly: pixel 1 is a G site, so R is missing, and bilinear gives (190, 110) matching truth (190, 110); pixel 2 is an R site missing G, bilinear gives (180, 120) matching truth (180, 120); and so on down. The nearest column is wrong at every one: pixel 1 nearest gives R=200 (copied from the left R site) against truth 190; pixel 2 nearest gives G=110 against truth 120. The reason bilinear is exact here is that both true channels vary linearly, and the average of two points on a line is the point exactly between them — so interpolating from both measured neighbors lands precisely on the true value, while copying one neighbor lands on that neighbor's value, which is a full step off. The measured channel (shown matching truth in every row's first or second slot) is of course exact in both methods; it is only the reconstructed channel where the methods diverge.

## Build

Score each method against the ground truth to turn the visual difference into a number.

```text filename=--error
ERROR — reconstruction error of the estimated channel vs the ground truth
--------------------------------------------------------------------
  pos  filter  missing  nearest->err       bilinear->err
  0    R       G        110->10            110->10  (edge)
  1    G       R        200->10            190->0
  2    R       G        110->10            120->0
  3    G       R        180->10            170->0
  4    R       G        130->10            140->0
  5    G       R        160->10            160->10  (edge)
--------------------------------------------------------------------
  interior total error -- nearest: 40   bilinear: 0
```

<svg role="img" aria-label="Per-pixel reconstruction error across six positions: nearest replication is 10 at every pixel, bilinear is 0 at the four interior pixels and 10 only at the two edges" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">reconstruction error per pixel: nearest vs bilinear</text>
  <line x1="30" y1="70" x2="285" y2="70" stroke="var(--grid)"/>
  <text x="10" y="40" fill="var(--muted)" font-size="6">err 10</text><line x1="30" y1="42" x2="285" y2="42" stroke="var(--grid)" stroke-dasharray="1 3"/>
  <g fill="var(--s2)"><rect x="42" y="42" width="10" height="28"/><rect x="82" y="42" width="10" height="28"/><rect x="122" y="42" width="10" height="28"/><rect x="162" y="42" width="10" height="28"/><rect x="202" y="42" width="10" height="28"/><rect x="242" y="42" width="10" height="28"/></g>
  <g fill="var(--s1)"><rect x="54" y="42" width="10" height="28"/><rect x="254" y="42" width="10" height="28"/></g>
  <text x="34" y="82" fill="var(--muted)" font-size="6">0</text><text x="74" y="82" fill="var(--muted)" font-size="6">1</text><text x="114" y="82" fill="var(--muted)" font-size="6">2</text><text x="154" y="82" fill="var(--muted)" font-size="6">3</text><text x="194" y="82" fill="var(--muted)" font-size="6">4</text><text x="234" y="82" fill="var(--muted)" font-size="6">5</text>
  <text x="34" y="98" fill="var(--s2)" font-size="6">nearest: 10 everywhere</text><text x="150" y="98" fill="var(--s1)" font-size="6">bilinear: 0 interior, 10 only at edges 0 &amp; 5</text>
</svg>
^ Nearest replication carries a 10-level error at every one of the six positions, while bilinear is exactly 0 across the four interior pixels and only rises to 10 at the two edges, where a second neighbor to average is missing — the interior is where two-sided interpolation wins outright.

The error column tells the whole story. At every interior pixel, nearest replication is off by 10 levels and bilinear is off by 0 — the interpolated channel is exactly right, the replicated one is a full gradient step wrong. Summed over the four interior pixels, nearest accumulates 40 levels of error and bilinear accumulates none. Notice the two edge pixels (0 and 5): here *both* methods have only one neighbor to work with, so bilinear degenerates to copying that single neighbor and is off by 10 just like nearest — the edges are where even good interpolation loses information, because there is no second sample to average, which is why real demosaicers use larger, asymmetric neighborhoods near borders. But across the interior, where a second neighbor exists, two-sided averaging is a categorical improvement: the false-color errors that nearest replication would paint along every gradient simply do not appear.

```python filename=modules/generative-media/code/demosaic-inter-01/demosaic.py:149-156 COMPLETE
    bilinear_exact_interior = bil_err == 0
    print("  bilinear interior reconstruction error = %g -> exact = %s" % (bil_err, bilinear_exact_interior))

    nearest_wrong_interior = near_err > 0
    print("  nearest interior reconstruction error = %g -> wrong = %s" % (near_err, nearest_wrong_interior))

    bilinear_beats_nearest = bil_err < near_err
    print("  bilinear beats nearest on interior error = %s (%g < %g)" % (bilinear_beats_nearest, bil_err, near_err))
```

## Definition of done

The self-test pins the exact interior recovery, the nearest error, and one pixel's missing green resolved correctly by averaging and wrongly by copying.

```python filename=modules/generative-media/code/demosaic-inter-01/demosaic.py:159-164 COMPLETE
    pixel2_bilinear_true = bil[2][1] == data["truth_G"][2]
    print("  pixel 2 missing G: bilinear = %g = truth %d = %s (nearest = %g)"
          % (bil[2][1], data["truth_G"][2], pixel2_bilinear_true, near[2][1]))

    nearest_invents_error = near[2][1] != data["truth_G"][2]
    print("  pixel 2 missing G: nearest replication is wrong = %s (%g vs truth %d)"
          % (nearest_invents_error, near[2][1], data["truth_G"][2]))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — nearest replication misses the interior missing channels; bilinear interpolation recovers them exactly
------------------------------------------------------------------------------------------------------------------
  bilinear interior reconstruction error = 0 -> exact = True
  nearest interior reconstruction error = 40 -> wrong = True
  bilinear beats nearest on interior error = True (0 < 40)
  pixel 2 missing G: bilinear = 120 = truth 120 = True (nearest = 110)
  pixel 2 missing G: nearest replication is wrong = True (110 vs truth 120)
```

<svg role="img" aria-label="Pixel 2's missing green: the true value 120 sits between the left green 110 and right green 130; bilinear averages to 120 exactly, nearest copies the left 110 and lands 10 below the truth" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">pixel 2 missing green: true 120 is between 110 and 130</text>
  <line x1="30" y1="50" x2="270" y2="50" stroke="var(--grid)"/>
  <circle cx="60" cy="50" r="3" fill="var(--s1)"/><text x="44" y="42" fill="var(--muted)" font-size="6">left G 110</text>
  <circle cx="240" cy="50" r="3" fill="var(--s1)"/><text x="224" y="42" fill="var(--muted)" font-size="6">right G 130</text>
  <line x1="150" y1="40" x2="150" y2="60" stroke="var(--ink)"/><text x="132" y="34" fill="var(--ink)" font-size="6">truth 120</text>
  <circle cx="150" cy="50" r="3" fill="var(--ink)"/><text x="130" y="74" fill="var(--ink)" font-size="6">bilinear = 120 ✓</text>
  <circle cx="60" cy="62" r="3" fill="var(--s2)"/><text x="44" y="86" fill="var(--s2)" font-size="6">nearest = 110 ✗ (−10)</text>
</svg>
^ Pixel 2's true green (120) lies exactly halfway between the measured greens on its left (110) and right (130); bilinear averaging lands on 120, while nearest replication copies the left sample (110) and misses by 10 — the gap is the false color the copy would introduce.

**Done means demosaicing's core is proven on a known ground truth: bilinear interpolation of each missing channel from its two measured neighbors recovers the interior pixels exactly (error 0), while nearest-neighbor replication is off by 10 levels at each interior pixel (total 40) and would paint false color across the gradient — so a missing channel must be interpolated from both sides, not copied from the nearest sample.**

## Boss fight

Predict two ways this simple interpolation is not enough, because real demosaicing has to fight the very artifacts that naive interpolation still leaves.

The first trap is that plain bilinear interpolation still blurs and fringes across edges, because averaging across a sharp boundary mixes two different colors. On the linear gradient of this fixture, two-sided averaging is exact — but at a genuine edge, where the true signal jumps rather than ramps, averaging the neighbor on the dark side with the neighbor on the light side produces a value that belongs to neither, so bilinear demosaicing softens edges and, worse, produces color fringes and a "zipper" pattern along high-contrast borders where the R, G, and B channels are sampled at different positions and interpolated across the edge inconsistently. This is why production demosaicing is EDGE-DIRECTED: it estimates the local gradient direction first and interpolates ALONG the edge (where the signal is smooth) rather than across it (where it jumps), so the reconstruction follows the boundary instead of smearing it. The lesson generalizes — the same "interpolate along the structure, not across it" idea appears in every good image reconstruction — but the specific point is that "average both neighbors" is the floor, not the ceiling, and it still needs edge awareness to avoid the artifacts a single-neighbor copy makes worse.

The second trap is that the channels are not independent, and the best demosaicers exploit that, while treating them independently (as both methods here do) leaves quality on the table and invents color where there should be none. In natural images the red, green, and blue channels are highly correlated — an edge in luminance appears in all three — and the green channel is sampled twice as densely as red or blue in the Bayer pattern, so it carries the most reliable high-frequency detail. Good demosaicing reconstructs green first, then reconstructs red and blue guided by the green channel's gradients (interpolating the *color difference* R−G and B−G, which is far smoother than R or B alone, and adding green back), so the sparse red and blue channels borrow green's detail instead of being blurred on their own. Independent per-channel interpolation, by contrast, lets the channels disagree at edges, which is exactly the false color this module warns about, just at a subtler level. So the full rule is: reconstruct from both sides (this module), along edges not across them (edge-directed), and using the cross-channel correlation with the dense green channel as a guide — the independent, isotropic average is the right first idea and the wrong final answer.

**Two-sided averaging is the floor, not the ceiling: plain bilinear still blurs and zippers across sharp edges because it averages two different colors, so real demosaicing is edge-directed — interpolate along the boundary where the signal is smooth, not across it where it jumps. And the channels are correlated, not independent: reconstruct the dense green channel first and guide red and blue from it (interpolating the smooth color differences R−G, B−G), because per-channel isotropic interpolation lets the channels disagree at edges and reintroduces false color at a subtler level than the nearest-copy this module fixed.**

## External resources

Any image-processing or computational-photography text on demosaicing (the Bayer pattern, bilinear demosaicing, and edge-directed / gradient-corrected methods such as Malvar-He-Cutler or AHD) — why single-channel interpolation is the baseline and how edge direction and cross-channel correlation improve it.

Documentation for raw-image pipelines (dcraw, LibRaw, RawTherapee) — the demosaicing algorithms offered in practice and the artifacts (zippering, false color, maze patterns) they are designed to suppress.

The companion aliasing, bilinear-upsample, and backward-mapping modules in this topic — demosaicing is a reconstruction from sparse samples like upsampling, and the "interpolate, and interpolate along the structure" principle it shares with edge-aware filtering is the same one that separates a good resample from a blurry one.
