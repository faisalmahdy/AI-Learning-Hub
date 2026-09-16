---
id: otsu-inter-01
title: Pick the threshold from the histogram, not a fixed 128 — or an object whose brightness sits below the constant vanishes
topic: generative-media
level: intermediate
status: ready
time: 17 min
summary: Binarizing a grayscale image means choosing an intensity threshold above which pixels are foreground. The lazy default is a constant — 128, the middle of the 0..255 range — which only works if foreground and background happen to straddle it. Lighting and exposure slide both populations together, and once both histogram peaks fall on the same side of 128, the constant puts nearly every pixel in one class and the object floods or disappears. Otsu's method reads the threshold off the histogram: every threshold splits the pixels into two classes, and Otsu picks the one that maximizes the between-class variance w0·w1·(μ0−μ1)², which lands in the valley between the two peaks wherever they are — no labels, no parameters. On a fixture whose background peaks near intensity 55 and foreground near 100, both below 128, a fixed threshold of 128 recovers a foreground fraction of 0.004 (the object nearly vanishes) against a true 0.40, while Otsu's threshold lands at 77 in the valley and recovers 0.406.
eli5: To split a photo into "object" and "background" you pick a brightness line: brighter is object, darker is background. If you always draw the line at the middle of the scale, it works only when the two things sit on opposite sides of the middle. But turn the lights down and both slide low — now your middle line has everything on the dark side, and the object disappears. The smart move is to look at the picture's own brightness chart, find the dip between its two humps, and draw the line there. That dip moves with the lighting, so the line follows the picture instead of a fixed number.
---

## Why this module

A binarization threshold is a decision about the image in front of you, so freezing it at a constant means that the moment lighting shifts both the object and its background to one side of that constant, the split collapses and the object is gone.

Turning a grayscale image into a foreground/background mask needs one number: the intensity above which a pixel counts as foreground. The tempting default is 128, the midpoint of the 0..255 range, and it survives exactly as long as the two populations of pixels straddle it. They rarely stay put. Exposure, ambient light, and the object's own reflectance move both the dark cluster and the bright cluster up or down together, and as soon as both peaks land on the same side of 128, the constant assigns nearly every pixel to one class. A darker capture drops both peaks below 128 and the whole frame reads as background; the object does not get harder to see, it disappears entirely from the mask. The constant answered a question about the range instead of a question about the image.

**A fixed binarization threshold works only while the foreground and background peaks straddle it, so any lighting change that slides both peaks to one side collapses the split and floods or vanishes the object — the threshold has to be read from the histogram, which is what moved.**

Otsu's method reads it off. Every candidate threshold t splits the pixels into a background class at or below t and a foreground class above it, and a good threshold makes those two classes maximally separated. Otsu scores separation with the between-class variance — w0·w1·(μ0−μ1)², the two class weights times the squared distance between their means — and picks the t that maximizes it. That maximum sits in the valley between the histogram's two peaks, wherever those peaks happen to be, so the threshold tracks the image with no labels and no tuning parameter. This module builds a bimodal histogram whose peaks both sit below 128 and shows the constant lose the object that Otsu recovers.

## Concepts

**Binarization threshold** is the intensity t that divides an image into background (≤ t) and foreground (> t). Every choice of t implies a different mask.

**Between-class variance** measures how well a threshold separates the two classes: w0·w1·(μ0 − μ1)², where w0, w1 are the fractions of pixels in each class and μ0, μ1 their mean intensities. It is large when the two classes are both substantial and far apart.

```python filename=modules/generative-media/code/otsu-inter-01/otsu.py:53-61 COMPLETE
def between_class_variance(h, t):
    """Otsu's objective at threshold t: w0*w1*(mu0-mu1)^2 for classes {<=t} and {>t}."""
    w0 = sum(h[: t + 1])
    w1 = 1.0 - w0
    if w0 == 0 or w1 == 0:
        return 0.0
    mu0 = sum(i * h[i] for i in range(t + 1)) / w0
    mu1 = sum(i * h[i] for i in range(t + 1, len(h))) / w1
    return w0 * w1 * (mu0 - mu1) ** 2
```

**Otsu's threshold** is the t that maximizes that variance. Scanning every level is exhaustive but cheap — the histogram has only 256 bins — and the maximum falls in the valley between the two peaks.

```python filename=modules/generative-media/code/otsu-inter-01/otsu.py:64-66 COMPLETE
def otsu_threshold(h):
    """The threshold that maximizes the between-class variance."""
    return max(range(len(h)), key=lambda t: between_class_variance(h, t))
```

<svg role="img" aria-label="A bimodal histogram with peaks near 55 and 100; Otsu's threshold sits in the valley at 77 while the fixed 128 sits past both peaks in the empty tail" viewBox="0 0 300 108" width="300" height="108">
  <line x1="20" y1="86" x2="292" y2="86" stroke="var(--grid)"/>
  <path d="M20 86 Q50 24 74 86" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <path d="M74 86 Q104 40 130 86" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="42" y="20" fill="var(--muted)" font-size="7">background ~55</text>
  <text x="96" y="36" fill="var(--muted)" font-size="7">foreground ~100</text>
  <line x1="93" y1="18" x2="93" y2="86" stroke="var(--ink)" stroke-dasharray="3 2"/><text x="80" y="98" fill="var(--ink)" font-size="7">Otsu 77</text>
  <line x1="188" y1="18" x2="188" y2="86" stroke="var(--muted)" stroke-dasharray="2 2"/><text x="172" y="98" fill="var(--muted)" font-size="7">fixed 128</text>
  <text x="200" y="60" fill="var(--muted)" font-size="7">← empty tail</text>
  <text x="20" y="107" fill="var(--muted)" font-size="8">Otsu lands in the valley between the peaks; 128 lands past both of them</text>
</svg>
^ Otsu's threshold sits in the valley between the two histogram peaks (77), while the fixed 128 sits in the empty tail past both peaks, where it separates nothing.

**Otsu chooses the threshold that maximizes between-class variance, which is the valley between the histogram's two peaks — so it tracks the image's own brightness distribution instead of a constant that only works when the peaks straddle it.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/otsu-inter-01/otsu.py

The fixture is two pixel populations — a dark background and a brighter foreground — both peaking below 128.

```json filename=modules/generative-media/code/otsu-inter-01/otsu.json:3-9 COMPLETE
  "clusters": [
    {"mean": 55, "std": 12, "weight": 0.60},
    {"mean": 100, "std": 12, "weight": 0.40}
  ],
  "true_fg_fraction": 0.40,
  "fixed_threshold": 128,
  "levels": 256
```

Run `--threshold` to compare Otsu's choice against the constant.

```text filename=--threshold
THRESHOLD — Otsu maximizes between-class variance; the fixed 128 does not
----------------------------------------------------------------
  cluster peaks (means):     [55, 100]
  Otsu threshold t*        =  77   between-class variance = 498.89
  fixed threshold          = 128   between-class variance = 12.46
----------------------------------------------------------------
  Otsu's t* sits in the valley between the peaks; 128 sits past both of them.
```

Otsu's threshold is 77 — squarely between the background peak at 55 and the foreground peak at 100 — and its between-class variance is 498.89. The fixed 128 sits past both peaks in the sparse right tail, where almost no pixels live, so the split it makes is lopsided and its between-class variance is 12.46, forty times smaller. That number is the whole story: between-class variance is high only when both classes hold real mass and their means are far apart, and 128 fails on the first condition because it leaves the foreground class nearly empty. Otsu did not need to be told where the object was; it found the threshold that carves the histogram at its natural seam, and the seam is nowhere near 128.

<svg role="img" aria-label="Between-class variance as a function of threshold rises to a single peak of about 499 at t=77 and falls to about 12 at t=128" viewBox="0 0 300 104" width="300" height="104">
  <line x1="20" y1="86" x2="292" y2="86" stroke="var(--grid)"/><line x1="20" y1="16" x2="20" y2="86" stroke="var(--grid)"/>
  <text x="4" y="20" fill="var(--muted)" font-size="7">var</text>
  <path d="M20 86 L40 70 L60 40 L78 22 L96 34 L130 60 L170 78 L210 83 L260 85 L288 86" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <line x1="78" y1="22" x2="78" y2="86" stroke="var(--ink)" stroke-dasharray="3 2"/><text x="66" y="98" fill="var(--ink)" font-size="7">t*=77 (499)</text>
  <circle cx="78" cy="22" r="2.5" fill="var(--ink)"/>
  <circle cx="200" cy="83" r="2.5" fill="var(--muted)"/><text x="188" y="98" fill="var(--muted)" font-size="7">128 (12)</text>
  <text x="20" y="107" fill="var(--muted)" font-size="8">the objective peaks once, at the valley threshold; 128 is far down the slope</text>
</svg>
^ The between-class variance has a single maximum at t = 77 (498.89) and has collapsed to 12.46 by t = 128 — Otsu takes the peak, the constant is stranded on the tail.

## Build

The variance gap is abstract; the split it produces is not. Run `--split` to see what fraction of the image each threshold calls foreground.

```text filename=--split
SPLIT — the foreground fraction each threshold recovers (true = 0.40)
------------------------------------------------------------
  Otsu   t*= 77 -> foreground fraction 0.406
  fixed  t =128 -> foreground fraction 0.004
------------------------------------------------------------
  both peaks are below 128, so the fixed threshold calls the object background and loses it.
```

The true foreground fraction is 0.40 — forty percent of the pixels belong to the object. Otsu's threshold recovers 0.406, within half a percent of the truth. The fixed 128 recovers 0.004: four pixels in a thousand. The object did not shrink; the threshold sat above its entire brightness range, so every foreground pixel got filed as background and the mask came back essentially blank. This is the failure mode of the constant in one line — not a slightly-off mask but a missing object — and it is silent, because 128 is a legal threshold that produces a valid-looking all-background result. Anything downstream that counts, measures, or crops the object now operates on nothing, and no error was raised. Otsu avoids it not by being cleverer about the object but by refusing to pick a threshold the histogram does not support.

<svg role="img" aria-label="Otsu recovers a foreground fraction of 0.406 matching the true 0.40, while the fixed 128 recovers only 0.004" viewBox="0 0 300 96" width="300" height="96">
  <line x1="70" y1="80" x2="292" y2="80" stroke="var(--grid)"/>
  <line x1="70" y1="18" x2="70" y2="80" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="74" y="16" fill="var(--muted)" font-size="7">true 0.40 →</text>
  <line x1="210" y1="14" x2="210" y2="80" stroke="var(--ink)" stroke-dasharray="2 2"/>
  <text x="6" y="34" fill="var(--muted)" font-size="8">Otsu 77</text>
  <rect x="70" y="26" width="142" height="14" fill="var(--s1)"/><text x="216" y="37" fill="var(--muted)" font-size="7">0.406</text>
  <text x="6" y="60" fill="var(--muted)" font-size="8">fixed 128</text>
  <rect x="70" y="52" width="2" height="14" fill="var(--s2)"/><text x="76" y="63" fill="var(--muted)" font-size="7">0.004 — object lost</text>
  <text x="6" y="92" fill="var(--muted)" font-size="8">Otsu's bar reaches the true line; the fixed threshold's is a sliver</text>
</svg>
^ Otsu's foreground fraction reaches the true 0.40 line at 0.406, while the fixed 128 recovers 0.004 — the entire object filed as background.

## Definition of done

The self-test pins every claim: Otsu's threshold is the global maximum of the objective, it lies between the two peaks, it recovers the true foreground fraction, and the fixed threshold loses the object.

```python filename=modules/generative-media/code/otsu-inter-01/otsu.py:109-122 COMPLETE
    is_maximum = all(between_class_variance(h, t) >= between_class_variance(h, u) for u in range(len(h)))
    print("  Otsu's t* maximizes between-class variance over all thresholds = %s (var=%.2f)" % (is_maximum, between_class_variance(h, t)))

    in_valley = peaks[0] < t < peaks[1]
    print("  t* lies in the valley between the two peaks = %s (%d < %d < %d)" % (in_valley, peaks[0], t, peaks[1]))

    otsu_recovers = abs(fg_fraction(h, t) - true) < 0.05
    print("  Otsu recovers the true foreground fraction = %s (%.3f vs %.2f)" % (otsu_recovers, fg_fraction(h, t), true))

    fixed_loses = fg_fraction(h, fixed) < 0.05
    print("  the fixed 128 threshold loses the object = %s (foreground %.3f)" % (fixed_loses, fg_fraction(h, fixed)))

    otsu_beats_fixed = between_class_variance(h, t) > between_class_variance(h, fixed)
    print("  Otsu's separation beats the fixed threshold's = %s (%.2f > %.2f)" % (otsu_beats_fixed, between_class_variance(h, t), between_class_variance(h, fixed)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — Otsu maximizes between-class variance, lands between the peaks, and recovers the object 128 loses
----------------------------------------------------------------------------------------------------------------
  Otsu's t* maximizes between-class variance over all thresholds = True (var=498.89)
  t* lies in the valley between the two peaks = True (55 < 77 < 100)
  Otsu recovers the true foreground fraction = True (0.406 vs 0.40)
  the fixed 128 threshold loses the object = True (foreground 0.004)
  Otsu's separation beats the fixed threshold's = True (498.89 > 12.46)
```

**Done means the data-driven threshold is proven to beat the constant: Otsu's t* = 77 is the global maximum of the between-class variance (498.89), sits in the valley between the peaks at 55 and 100, and recovers the true foreground fraction to 0.406 — while the fixed 128 sits past both peaks, scores 12.46, and loses the object at a foreground fraction of 0.004.**

## Boss fight

Predict where Otsu's own assumption breaks, and the case where reading the threshold from the whole image is exactly the wrong move. It is tempting to treat Otsu as a parameter-free binarizer that always works.

The first crack is that Otsu assumes the histogram is bimodal — two clear humps with a valley. When it is not, its answer is still a maximum of the objective but no longer a meaningful boundary. A near-uniform histogram, a single dominant mode with a faint object, or three populations instead of two all break the premise: with one mode the between-class variance is maximized by slicing the single hump roughly in half, producing a threshold that separates nothing real, and with a tiny foreground (a few percent of pixels) the w0·w1 term rewards balanced splits so heavily that Otsu drifts off the true valley toward the middle. The tell is the objective's shape — a sharp single peak means a clean bimodal split, a flat or multi-peaked objective means Otsu is guessing — so check that the histogram actually has two modes before trusting the number, and reach for a multi-level Otsu or a different method when it does not.

```python filename=modules/generative-media/code/otsu-inter-01/otsu.py:69-71 COMPLETE
def fg_fraction(h, t):
    """The fraction of pixels called foreground (intensity strictly above t)."""
    return sum(h[t + 1:])
```

The second crack is that a single global threshold assumes uniform lighting, and the whole point of this module — that lighting moves the peaks — turns against Otsu when the lighting varies across the frame. A page photographed with a shadow across one corner has a bright region and a dark region whose intensity ranges overlap: text in the shadow is darker than paper in the light, so no single threshold, Otsu's included, can separate ink from paper everywhere at once. The fix is to stop being global — compute a threshold per local window (adaptive or "local Otsu"), so each region gets a threshold matched to its own lighting — which is the same lesson as the constant-versus-Otsu one, taken one level finer: the constant fails because it ignores the image, and global Otsu fails on uneven lighting because it ignores where in the image a pixel is. The threshold should be as local as the thing that moves the peaks.

**Otsu picks the binarization threshold by maximizing between-class variance, tracking the histogram instead of a constant — but it assumes a bimodal histogram and uniform lighting, so verify the objective has a single sharp peak before trusting it (a flat objective means no real valley), and when lighting varies across the frame drop to a per-window local threshold, because one global threshold, data-driven or not, cannot follow lighting that changes within the image.**

## External resources

Otsu's 1979 paper "A Threshold Selection Method from Gray-Level Histograms" — the original derivation of the between-class-variance criterion and the equivalence between maximizing between-class variance and minimizing within-class variance.

Any image-processing reference on global vs adaptive (local) thresholding — the conditions under which a single threshold suffices and the windowed methods (adaptive mean/Gaussian, Sauvola, local Otsu) that handle uneven illumination.

The companion "equalize the histogram to gain contrast" and "gamma-encode before quantizing" modules — all three read a decision off the intensity histogram, so they share the machinery of thinking about an image as a distribution of levels rather than a grid of pixels.
