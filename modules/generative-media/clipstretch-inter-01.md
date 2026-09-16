---
id: clipstretch-inter-01
title: Clip the extremes before you stretch contrast — one bright outlier makes a min-max stretch do almost nothing
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Contrast stretching brightens a dull image by remapping its values to fill the full range: find the darkest and lightest pixels and rescale so the darkest becomes 0 and the lightest 255. When the image genuinely uses a narrow band — everything between 100 and 140 — this is exactly right: the band expands to fill 0–255 and faint differences become visible. The method is fragile in one specific way: it defines the range by the single minimum and single maximum pixel, so a lone outlier destroys it. One specular highlight (a glint off metal), one hot or dead pixel, one dust speck, sets the max to 255 or the min to 0, and the stretch maps that outlier to the endpoint and leaves the real content almost exactly where it was, compressed into a thin slice of the range. The stretch ran; it just spent its entire dynamic range on two stray pixels. Percentile clipping fixes this by defining the range robustly: instead of the absolute min and max, use a low and high percentile — clip the darkest 10% and lightest 10% — and stretch that range to fill 0–255, saturating the outliers to pure black or white. Because a couple of outlier pixels are a tiny fraction of the image, they fall outside the 10th-to-90th-percentile band and no longer define the range. On a fixture where the content sits in 100–140 but the row also has a 0 (dead pixel) and a 255 (specular highlight), naive min-max stretching leaves the content in a 40-wide band (16% of the range), while clipping the 10% extremes stretches the robust range 100–140 to the full 0–255 (100%), giving the content 6.4× the contrast.
eli5: Imagine you want to spread out a group of people standing very close together so you can see each one clearly, and you decide to space them evenly from one wall to the other. But if one person is pressed against the far wall (a glint of light) and one against the near wall (a dead pixel), then "wall to wall" is already full, and spacing "from the closest to the farthest person" leaves the tight middle group just as bunched up as before — you spread out the two loners and did nothing for everyone else. The fix is to ignore the couple of people jammed against the walls and spread out the main group from wall to wall instead. You lose track of exactly where the two loners were (they just go to the walls), but now the crowd you actually care about is nicely spread out and easy to see.
---

## Why this module

Contrast stretching is one of the most basic image operations, and it fails on the most common real-world images for a reason that is easy to miss: it trusts the two most extreme pixels to define the whole scale. Real photographs almost always have a few pixels that are not representative of anything — a specular highlight where light glints off a surface, a dead or hot sensor pixel, a speck of dust — and those pixels are, by definition, at the extremes. So the one operation that reaches for the min and max to set its range is the one operation most likely to have its range hijacked by exactly the pixels that should be ignored. The result is a stretch that technically executed and visibly did nothing.

The method defines the range by the single minimum and single maximum pixel, so a lone outlier destroys it. One specular highlight sets the max to 255, and the stretch maps that outlier to the endpoint and leaves the real content — which occupied, say, 100 to 140 — almost exactly where it was, compressed into a thin slice of the range. The stretch spent its entire dynamic range on two stray pixels and gave the actual image nothing.

Percentile clipping fixes this by defining the range robustly: use a low and high percentile — clip the darkest 10% and lightest 10% — and stretch that clipped range to fill 0–255, saturating the outliers to pure black or white. Because the outliers are a tiny fraction of the image, they fall outside the percentile band and no longer set the scale. This module stretches the same row both ways.

**Stretch contrast to a percentile-clipped range (e.g. the 10th to 90th percentile), not the absolute min and max, because min-max stretching lets a single outlier pixel — a specular highlight, a dead pixel — define the range and leave the real content compressed into a sliver, while clipping the extremes first stretches the band the content actually occupies to full contrast.**

## Concepts

**The robust range comes from a percentile, and the stretch maps that range to 0–255, clamping outside it.**

```python filename=modules/generative-media/code/clipstretch-inter-01/clipstretch.py:54-66 COMPLETE
def percentile(values, p):
    """Nearest-rank percentile: sort, take the value at rank ceil(p/100 * n)."""
    s = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(s)))
    return s[rank - 1]


def stretch(value, lo, hi):
    """Map [lo, hi] to [0, 255], clamping anything outside to the endpoints."""
    if hi == lo:
        return 0.0
    scaled = (value - lo) / (hi - lo) * 255
    return max(0.0, min(255.0, scaled))
```

**The two methods differ only in the range they choose** — naive uses min/max, clipping uses the percentiles — and we score them by the content's spread.

```python filename=modules/generative-media/code/clipstretch-inter-01/clipstretch.py:69-80 COMPLETE
def naive_range(row):
    return min(row), max(row)


def clipped_range(row, clip_percentile):
    return percentile(row, clip_percentile), percentile(row, 100 - clip_percentile)


def content_spread(row, lo, hi):
    """The spread (max - min) of the real-content pixels after stretching -- how much contrast the content got."""
    stretched = [stretch(v, lo, hi) for v in row if CONTENT_LO <= v <= CONTENT_HI]
    return max(stretched) - min(stretched)
```

<svg role="img" aria-label="A 0-255 value axis: the content sits tightly in 100-140, with one outlier at 0 and one at 255; the naive range spans the whole axis while the clipped range hugs the content band" viewBox="0 0 300 112" width="300" height="112">
  <text x="6" y="12" fill="var(--muted)" font-size="8">content is in 100-140; outliers at 0 and 255 set the naive range</text>
  <line x1="20" y1="52" x2="285" y2="52" stroke="var(--grid)"/>
  <text x="16" y="66" fill="var(--muted)" font-size="6">0</text><text x="272" y="66" fill="var(--muted)" font-size="6">255</text>
  <circle cx="20" cy="52" r="3" fill="var(--s2)"/><text x="10" y="44" fill="var(--s2)" font-size="6">0 dead</text>
  <circle cx="285" cy="52" r="3" fill="var(--s2)"/><text x="256" y="44" fill="var(--s2)" font-size="6">255 glint</text>
  <g fill="var(--s1)"><circle cx="124" cy="52" r="2.5"/><circle cx="129" cy="52" r="2.5"/><circle cx="134" cy="52" r="2.5"/><circle cx="139" cy="52" r="2.5"/><circle cx="144" cy="52" r="2.5"/><circle cx="149" cy="52" r="2.5"/><circle cx="154" cy="52" r="2.5"/></g>
  <text x="118" y="42" fill="var(--s1)" font-size="6">content 100-140</text>
  <line x1="20" y1="80" x2="285" y2="80" stroke="var(--s2)"/><text x="120" y="90" fill="var(--s2)" font-size="6">naive range: 0-255 (whole axis)</text>
  <line x1="124" y1="98" x2="154" y2="98" stroke="var(--s1)"/><text x="160" y="101" fill="var(--s1)" font-size="6">clipped range: 100-140</text>
</svg>
^ The real content clusters in 100–140, but the two outliers at 0 and 255 make the naive range span the entire axis, so the stretch barely moves the content; the clipped range hugs the 100–140 band, so stretching it fills the axis with the content.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/clipstretch-inter-01/clipstretch.py

The fixture is a row whose content is 100–140 plus two outliers, and the clip percentage.

```json filename=modules/generative-media/code/clipstretch-inter-01/clipstretch.json:3-4 COMPLETE
  "row": [0, 100, 105, 110, 115, 120, 125, 130, 135, 140, 255],
  "clip_percentile": 10
```

Run `--stretch`.

```text filename=--stretch
STRETCH — the row remapped by naive min-max vs 10%-clipped percentile
--------------------------------------------------------------------------
  input           = [0, 100, 105, 110, 115, 120, 125, 130, 135, 140, 255]
  naive range     = [0, 255]  (the outliers!)
  naive stretched = [0, 100, 105, 110, 115, 120, 125, 130, 135, 140, 255]
  clipped range   = [100, 140]  (the robust content band)
  clip  stretched = [0, 0, 32, 64, 96, 128, 159, 191, 223, 255, 255]
```

<svg role="img" aria-label="The content pixels before and after each stretch: naive leaves them bunched in a narrow band, clipped spreads them across the full axis" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">where the content pixels land after each stretch</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">naive</text>
  <line x1="60" y1="34" x2="285" y2="34" stroke="var(--grid)"/>
  <g fill="var(--s2)"><circle cx="148" cy="34" r="2.5"/><circle cx="153" cy="34" r="2.5"/><circle cx="158" cy="34" r="2.5"/><circle cx="163" cy="34" r="2.5"/><circle cx="168" cy="34" r="2.5"/><circle cx="173" cy="34" r="2.5"/><circle cx="178" cy="34" r="2.5"/></g>
  <text x="150" y="26" fill="var(--s2)" font-size="6">still bunched (40 wide)</text>
  <text x="10" y="64" fill="var(--muted)" font-size="7">clipped</text>
  <line x1="60" y1="64" x2="285" y2="64" stroke="var(--grid)"/>
  <g fill="var(--s1)"><circle cx="60" cy="64" r="2.5"/><circle cx="97" cy="64" r="2.5"/><circle cx="134" cy="64" r="2.5"/><circle cx="171" cy="64" r="2.5"/><circle cx="208" cy="64" r="2.5"/><circle cx="245" cy="64" r="2.5"/><circle cx="285" cy="64" r="2.5"/></g>
  <text x="120" y="56" fill="var(--s1)" font-size="6">spread across the full axis</text>
  <text x="60" y="82" fill="var(--muted)" font-size="6">0</text><text x="275" y="82" fill="var(--muted)" font-size="6">255</text>
  <text x="10" y="96" fill="var(--muted)" font-size="6">same content pixels — the range choice decides whether they spread</text>
</svg>
^ The identical content pixels stay bunched in a 40-wide band under the naive stretch (its range was already the full axis) but spread evenly across the whole 0–255 axis under the clipped stretch — the pixels did not change, only the range they were mapped through.

Compare the two stretched rows. The naive stretch uses the range [0, 255] — but those are the outlier values, the dead pixel and the highlight, so mapping 0→0 and 255→255 is an identity on the endpoints and very nearly an identity on everything in between. The content 100–140 comes out as 100–140, unchanged: the stretch did nothing, because the range it was given already spanned the full axis. The clipped stretch uses the range [100, 140] — the actual content band, found by taking the 10th and 90th percentiles, which skip the outliers. Now 100 maps to 0 and 140 maps to 255, so the content that was crammed into a 40-value band is spread across the full 0–255: [0, 32, 64, 96, 128, 159, 191, 223, 255]. The two outliers clamp to the endpoints (0 stays 0, 255 stays 255), which is the deliberate sacrifice — a blown highlight and a dead pixel have no detail worth keeping — in exchange for revealing the whole image.

## Build

Put a number on how much contrast the content actually received.

```text filename=--contrast
CONTRAST — spread of the real content (values in [100,140]) after each stretch
----------------------------------------------------------------
  naive min-max:   content spans 40 of 255  (16% of the range)
  percentile clip: content spans 255 of 255  (100% of the range)
----------------------------------------------------------------
  clipping gives the content 6.4x the contrast of the naive stretch.
```

The content spread is the honest measure of what a contrast stretch is for: how much of the output range the real image occupies. Under naive min-max, the content spans 40 of 255 — just 16% of the range, barely more contrast than the original — because the outliers ate the other 84%. Under percentile clipping, the content spans the full 255, using 100% of the range. That is a 6.4× improvement in contrast on the pixels that matter, from nothing but changing how the range is estimated. The general lesson is that a scale set by extremes is a scale set by outliers, and outliers are the least representative points in the data — so any operation that normalizes to a range (contrast stretch here, but also feature scaling in machine learning, axis limits in a plot, a color map's domain) should estimate that range robustly, from percentiles or a trimmed statistic, not from the raw min and max, whenever a stray extreme value is possible. The specular highlight in an image is the same problem as the one billionaire in an income histogram: let it set the scale and everything else is squashed to invisibility.

```python filename=modules/generative-media/code/clipstretch-inter-01/clipstretch.py:123-131 COMPLETE
    outliers_present = min(row) < CONTENT_LO and max(row) > CONTENT_HI
    print("  the row has outliers outside the content band = %s (min %d, max %d vs band %d-%d)"
          % (outliers_present, min(row), max(row), CONTENT_LO, CONTENT_HI))

    naive_range_is_outliers = (nlo, nhi) == (min(row), max(row)) and (nlo < CONTENT_LO and nhi > CONTENT_HI)
    print("  naive range is set by the outliers = %s ([%d, %d])" % (naive_range_is_outliers, nlo, nhi))

    naive_low_contrast = ns < 100
    print("  naive stretch leaves the content low-contrast = %s (spread %.0f of 255)" % (naive_low_contrast, ns))
```

## Definition of done

The self-test pins the outliers, the outlier-set naive range, the low naive contrast, and the full clipped contrast.

```python filename=modules/generative-media/code/clipstretch-inter-01/clipstretch.py:133-137 COMPLETE
    clip_full_contrast = cs == 255
    print("  percentile clip gives the content full contrast = %s (spread %.0f of 255)" % (clip_full_contrast, cs))

    clip_beats_naive = cs > ns
    print("  clipping beats naive on content contrast = %s (%.0f vs %.0f)" % (clip_beats_naive, cs, ns))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the outliers make min-max stretch leave the content flat; percentile clipping gives it full contrast
--------------------------------------------------------------------------------------------------------------------
  the row has outliers outside the content band = True (min 0, max 255 vs band 100-140)
  naive range is set by the outliers = True ([0, 255])
  naive stretch leaves the content low-contrast = True (spread 40 of 255)
  percentile clip gives the content full contrast = True (spread 255 of 255)
  clipping beats naive on content contrast = True (255 vs 40)
```

<svg role="img" aria-label="Content contrast after each stretch: naive fills 40 of 255, percentile clip fills the full 255" viewBox="0 0 300 88" width="300" height="88">
  <text x="6" y="12" fill="var(--muted)" font-size="8">content contrast: naive 40/255 vs clipped 255/255</text>
  <text x="10" y="36" fill="var(--muted)" font-size="7">naive</text>
  <rect x="70" y="26" width="200" height="14" fill="none" stroke="var(--line)"/>
  <rect x="70" y="26" width="31" height="14" fill="var(--s2)"/><text x="105" y="37" fill="var(--muted)" font-size="7">40 (16%)</text>
  <text x="10" y="64" fill="var(--muted)" font-size="7">clipped</text>
  <rect x="70" y="54" width="200" height="14" fill="none" stroke="var(--line)"/>
  <rect x="70" y="54" width="200" height="14" fill="var(--s1)"/><text x="120" y="64" fill="var(--panel)" font-size="7">255 (100%)</text>
  <text x="10" y="84" fill="var(--muted)" font-size="6">6.4x more contrast on the pixels that matter, just from a robust range</text>
</svg>
^ The naive stretch gives the content 40 of 255 (16%) because the outliers claimed the rest, while percentile clipping gives it the full 255 (100%) — a 6.4× gain purely from estimating the range robustly instead of from the raw min and max.

**Done means the fragility and its fix are proven on real pixels: with content in 100–140 and outliers at 0 and 255, naive min-max stretching sets its range to [0,255] (the outliers) and leaves the content spanning only 40 of 255 (16%), while clipping the 10% extremes uses the robust range [100,140] and stretches the content to the full 255 (100%) — so contrast must be stretched to a percentile-clipped range, not the absolute min and max.**

## Boss fight

Predict two ways percentile clipping has to be tuned, because clipping too little fails to fix the problem and clipping too much throws away real content.

The first trap is that the clip percentage is a bias-variance knob, and both extremes are wrong: too little and the outliers survive, too much and you clip real content. If the clip is smaller than the fraction of outlier pixels — clip 1% when 3% of the image is blown-out highlight — the surviving outliers still stretch the range and you have not fixed anything; if it is larger than needed — clip 20% when the content genuinely uses the darkest and lightest 15% — you saturate real detail to pure black and white and permanently lose it (clipping is destructive; the clamped pixels cannot be recovered). So the right clip depends on how much of the image is genuinely outlier versus content, which varies per image, and a fixed percentage is a compromise. Better systems estimate it from the histogram — clip where the histogram is essentially flat at the tails (the outlier shelf) rather than a fixed percentile — or use an even more robust range estimator. And it interacts with the image's actual dynamic range: an image that legitimately spans the full 0–255 needs little or no clipping, while a low-contrast one needs aggressive clipping, so the same clip percentage over-processes the first and under-processes the second. The knob has to be matched to the image, not set once globally.

The second trap is that a global stretch — clipped or not — is still one mapping for the whole image, and many images have no single good range because different regions need different treatment. A photo with a bright sky and a shadowed foreground has content in two separate bands; any global stretch that reveals the shadows blows out the sky, or vice versa, because it must pick one range for both. This is why the more powerful tools are LOCAL: adaptive histogram equalization (and its contrast-limited variant, CLAHE) computes a separate mapping for each region and blends them, so each part of the image gets a range matched to its own content, and tone-mapping operators do this for high-dynamic-range images. Those methods bring their own hazards — local processing can amplify noise in flat regions (which CLAHE's contrast limit specifically guards against) and can create halos at strong edges — so they are not a free upgrade. But the lesson is that percentile clipping robustly fixes the outlier problem for a global stretch, and the next problem up — content that occupies multiple disjoint ranges — needs a spatially-varying map, at the cost of more computation and new artifacts to control. Robust range estimation and local adaptation are two different fixes for two different failures of the naive global min-max stretch.

**The clip percentage is a bias-variance knob matched per image, not a global constant: clip less than the outlier fraction and the outliers still hijack the range; clip more than the content's true tails and you destroy real detail (clipping is irreversible) — so estimate the clip from the histogram's flat tails or the image's actual dynamic range rather than a fixed percentile. And a clipped stretch is still one global mapping, which fails when content occupies multiple disjoint bands (bright sky plus dark foreground): that needs local/adaptive equalization (CLAHE) or tone mapping, which match a range to each region at the cost of amplified noise and edge halos to control.**

## External resources

Image-processing references on contrast stretching, percentile/histogram clipping, and adaptive histogram equalization (CLAHE) — the min-max fragility, robust range estimation, and the local methods for multi-band content.

Documentation for image libraries' contrast tools (OpenCV `normalize` with clipping, scikit-image `rescale_intensity` with percentile `in_range`, and CLAHE implementations) — how percentile clipping and adaptive equalization are configured in practice.

The companion histogram-equalization, otsu-threshold, and gamma modules in this topic — clipped stretching is the robust cousin of equalization (a linear remap to a robust range vs a histogram-flattening remap), and the "let extremes set the scale" failure it fixes is the same one a fixed threshold or an outlier-sensitive statistic faces.
