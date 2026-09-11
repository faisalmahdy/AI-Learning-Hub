---
id: histeq-inter-01
title: Equalize the histogram to gain contrast — a linear stretch uses the full range and still looks flat
topic: generative-media
level: intermediate
status: ready
time: 21 min
summary: A low-contrast image has its pixel values bunched into a narrow band. The obvious fix, a linear min-max stretch, spans the full range but is affine — it preserves the distribution's shape, so the crowded tones stay crowded. Histogram equalization maps values through the cumulative histogram, allocating output range in proportion to pixel density, so the dense tones are spread apart. On 8 pixels bunched around one gray level, both span 0-7, but the stretch leaves the dominant tone at 2 while equalization lifts it to 5 — contrast (std) rises from 2.236 to 2.472.
eli5: Imagine most people in a photo are wearing nearly the same shade of gray. Stretching just makes the darkest a bit darker and the lightest a bit lighter, but the big middle crowd is still all one shade. Equalization instead gives the crowded shades their own separate slots, so you can finally tell them apart — it spends the range where the pixels actually are.
---

## Why this module

Spreading an image across the full brightness range is not the same as making it look higher-contrast, and the obvious stretch does the first without the second.

A low-contrast image has its pixel values bunched into a narrow band — a foggy photo where everything is some shade of mid-gray, or a scan where the tones cluster in a small part of the scale. The natural fix is to stretch: find the darkest and lightest values present and linearly remap them to pure black and pure white, so the image now spans the whole range. Run it and the histogram does span the full range afterward. And the image still looks flat.

It looks flat because a linear stretch is an affine map — multiply by a scale, add an offset — and an affine map preserves the shape of the distribution. It moves the endpoints apart, but every value keeps its relative position between them, so tones that were bunched together are still bunched together, just at a larger scale. The dense cluster of mid-grays that the eye most needs to separate is still a dense cluster; it has been slid and stretched as a block, not spread internally. Using the full range at the endpoints does nothing for the crowded middle where the actual detail lives.

Histogram equalization spreads the crowded region by allocating output levels in proportion to how many pixels sit there. It maps each value through the cumulative histogram — the running total of pixel counts, the CDF. Where many pixels share a tonal region, the CDF climbs steeply, so that region is mapped to a wide slice of the output range; where few pixels sit, the CDF is shallow and the region gets a narrow slice. The effect is that the dense, important tones are pulled apart — exactly where contrast was missing — and the sparse tones are compressed. Both methods reach pure black and pure white; only equalization redistributes the tones in between by their density.

On the fixture, 8 pixels are bunched around one dominant gray level. The linear stretch spans the full 0-7 range but leaves the four dominant pixels crowded near the bottom, mapped to 2. Equalization spans the same range but spreads those four to the middle, mapped to 5, separating them from the darks — a larger contrast (standard deviation 2.472 versus 2.236) and a wider output gap around the busy tone.

**A linear min-max stretch is affine, so it spans the range but preserves the bunching and the crowded tones stay crowded; histogram equalization maps through the CDF, allocating output range by pixel density, so the dense tones are spread apart and contrast actually rises.**

## Concepts

The key idea is that contrast is about local separation of tones, not about the overall range. Two images can both use the full 0-to-white range and look completely different: one with its pixels spread evenly reads as high-contrast, one with its pixels piled in a narrow clump (plus a couple of outliers hitting the endpoints) reads as flat. What the eye registers as contrast is how far apart neighboring tones are in the regions where there is detail. So the goal of a contrast operation is to increase separation among the tones that actually occur, and an operation that only touches the endpoints cannot do that for the crowded middle.

A linear stretch fails on exactly this point because it is shape-preserving by construction. An affine map sends value v to a·v + b; the difference between any two values scales by the same factor a, so the ratio of gaps is unchanged. If four tones were packed into a small interval and one outlier sat far away, after stretching the four are still packed (in a proportionally larger but still small interval) and the outlier still sits far away. The stretch cannot give the dense cluster more of the range than its original share, because a single global scale applies everywhere. It is the right tool only when the distribution is already roughly uniform and merely offset or scaled.

<svg role="img" aria-label="The CDF climbs steeply where pixels are dense and shallowly where sparse; a value's output level is its CDF height, so the dense region gets a wide output slice" viewBox="0 0 470 185" width="470" height="185">
  <rect x="0" y="0" width="470" height="185" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">equalization maps a value to its CDF height</text>
  <line x1="45" y1="155" x2="440" y2="155" stroke="var(--line)"/>
  <line x1="45" y1="155" x2="45" y2="35" stroke="var(--line)"/>
  <text x="10" y="42" font-family="var(--mono)" font-size="7" fill="var(--muted)">out 7</text>
  <text x="20" y="168" font-family="var(--mono)" font-size="7" fill="var(--muted)">value 0</text>
  <text x="410" y="168" font-family="var(--mono)" font-size="7" fill="var(--muted)">7</text>
  <polyline points="45,155 150,150 200,150 260,55 320,40 380,35 440,35" fill="none" stroke="var(--acc-line)" stroke-width="2"/>
  <text x="205" y="120" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">steep here (dense) → wide output slice</text>
  <line x1="200" y1="150" x2="200" y2="155" stroke="var(--s2)"/>
  <line x1="260" y1="55" x2="260" y2="155" stroke="var(--s2)" stroke-dasharray="2 2"/>
  <text x="150" y="80" font-family="var(--mono)" font-size="7" fill="var(--s2)">the 4 pixels at value 3 jump from ~2 to ~5</text>
  <text x="330" y="60" font-family="var(--mono)" font-size="7" fill="var(--muted)">shallow (sparse) → narrow slice</text>
</svg>
^ The CDF rises steeply through the densely populated tones, so those values map to a wide span of output levels; the sparse tones, where the CDF is nearly flat, are compressed into a narrow span.

Equalization is non-linear and density-driven, which is what lets it help. Its mapping is the cumulative distribution function: the output level for a value is (roughly) the fraction of pixels at or below that value, scaled to the range. This has a precise meaning — it aims to make the output histogram uniform, so every output level holds about the same number of pixels. Achieving a uniform output means each tonal region gets output range proportional to its pixel count, which is exactly "spend the range where the pixels are." A region with four times as many pixels gets four times the output width, so those pixels are pulled four times as far apart as an equal stretch would.

Two honest caveats keep this from being magic. First, on discrete data equalization cannot truly flatten the histogram — it can move a bin of pixels to a new level but cannot split it, so a single dominant value stays a single spike, just relocated. The gain shows up as increased spread and separation (a higher standard deviation, a wider gap around the dense tones), not as a literally uniform histogram. Second, equalization can over-enhance: by spreading dense mid-tones aggressively it can amplify noise and produce a harsh, unnatural look, which is why practical variants (contrast-limited adaptive equalization, CLAHE, working on local tiles with a clip limit) temper it. The core insight stands: to add contrast you must redistribute tones by density, and only a CDF-based, non-linear map does that.

**Contrast is separation among the tones that occur, not the endpoint range; an affine stretch preserves gap ratios so it cannot spread a dense cluster, while equalization's CDF map allocates output range by density — spreading the crowded tones — bounded by the fact that discrete bins move but do not split.**

## Worked example

The fixture is a small low-contrast image and a level count.

```json filename=modules/generative-media/code/histeq-inter-01/image.json:3-4 COMPLETE
  "levels": 8,
  "pixels": [2, 2, 3, 3, 3, 3, 4, 5]
```

Eight pixels on a 0-7 scale, bunched around the dominant value 3 (four of the eight). The linear stretch maps the min and max present to 0 and 7; equalization maps each value through the normalized CDF.

```python filename=modules/generative-media/code/histeq-inter-01/histeq.py:58-69 COMPLETE
def linear_stretch(pixels, levels):
    """Affine map [min,max] -> [0, levels-1] -- spans the range but keeps the distribution's shape."""
    lo, hi = min(pixels), max(pixels)
    return {v: round((v - lo) / (hi - lo) * (levels - 1)) for v in set(pixels)}


def equalize(pixels, levels):
    """Map each value through the normalized CDF -- allocates output range by pixel density."""
    c = cdf(histogram(pixels, levels))
    n = len(pixels)
    cmin = min(x for x in c if x > 0)
    return {v: round((c[v] - cmin) / (n - cmin) * (levels - 1)) for v in set(pixels)}
```

Predict: both map 2 to 0 and 5 to 7 (the endpoints). But the dominant value 3 — where four pixels sit — should map low under the stretch (it is near the bottom of the input range) and high under equalization (four of eight pixels are at or below it, so its CDF is large). Look at the mappings.

```text filename=modules/generative-media/code/histeq-inter-01/histeq.py --map
MAP — how each method maps the input values (levels 0..7)
--------------------------------------------------
  value   count   stretch   equalize
  2       2       0         0
  3       4       2         5
  4       1       5         6
  5       1       7         7
--------------------------------------------------
  the dominant value goes low under stretch, mid under equalize.
```

Both methods send 2 to 0 and 5 to 7 — identical at the endpoints. The difference is entirely in the middle. The stretch maps the dominant value 3 to 2, keeping it close to the darks it was near; equalization maps 3 to 5, because four of the eight pixels are at or below 3, so its CDF sits high and it earns a place in the upper-middle of the range. Equalization gave the densest tone the most room. Now the outputs.

```text filename=modules/generative-media/code/histeq-inter-01/histeq.py --output
OUTPUT — pixels, histogram, and contrast per method
----------------------------------------------------------
  input:     [2, 2, 3, 3, 3, 3, 4, 5]   hist [0, 0, 2, 4, 1, 1, 0, 0]   std 0.927
  stretch:   [0, 0, 2, 2, 2, 2, 5, 7]   hist [2, 0, 4, 0, 0, 1, 0, 1]   std 2.236
  equalize:  [0, 0, 5, 5, 5, 5, 6, 7]   hist [2, 0, 0, 0, 0, 4, 1, 1]   std 2.472
----------------------------------------------------------
  gap around the dominant tone: stretch 2, equalize 5 (more contrast where the pixels are).
```

The input has a standard deviation of 0.927 — low contrast, tones packed. The stretch raises it to 2.236 by pushing the endpoints out, but the four dominant pixels land at 2, only two levels above the darks at 0. Equalization raises it further to 2.472, and the four dominant pixels land at 5, a full five levels above the darks — the crowded tone has been separated from the shadows. The gap around the dominant tone tells the story: 2 under the stretch, 5 under equalization. Same endpoints, same range used; equalization simply spent more of that range on the region where the pixels actually were.

<svg role="img" aria-label="Histograms: input bunched around level 3; stretch keeps the dominant spike near the bottom at level 2; equalization moves the dominant spike to the middle at level 5" viewBox="0 0 470 200" width="470" height="200">
  <rect x="0" y="0" width="470" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">where the dominant tone (4 pixels) lands, 0..7</text>
  <text x="20" y="42" font-family="var(--mono)" font-size="8" fill="var(--muted)">input</text>
  <g fill="var(--muted)"><rect x="150" y="34" width="14" height="16"/></g>
  <text x="168" y="46" font-family="var(--mono)" font-size="7" fill="var(--muted)">level 3, bunched (std 0.93)</text>
  <text x="20" y="92" font-family="var(--mono)" font-size="8" fill="var(--s2)">stretch</text>
  <g fill="var(--s2)"><rect x="70" y="84" width="14" height="16"/><rect x="150" y="76" width="14" height="24"/></g>
  <text x="60" y="112" font-family="var(--mono)" font-size="7" fill="var(--s2)">darks 0</text>
  <text x="170" y="92" font-family="var(--mono)" font-size="7" fill="var(--s2)">dominant → 2 (gap 2)</text>
  <text x="20" y="152" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">equalize</text>
  <g fill="var(--acc-line)"><rect x="70" y="144" width="14" height="16"/><rect x="310" y="136" width="14" height="24"/></g>
  <text x="60" y="172" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">darks 0</text>
  <text x="250" y="130" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">dominant → 5 (gap 5, std 2.47)</text>
  <line x1="60" y1="180" x2="440" y2="180" stroke="var(--line)"/>
  <text x="60" y="193" font-family="var(--mono)" font-size="7" fill="var(--muted)">0</text>
  <text x="430" y="193" font-family="var(--mono)" font-size="7" fill="var(--muted)">7</text>
</svg>
^ Both send the darks to 0, but the stretch parks the four dominant pixels at level 2 (a gap of 2 from the darks) while equalization moves them to level 5 (a gap of 5) — the crowded tone is finally separated.

## Build

Reproduce the mappings. Pure standard library, deterministic, so the stretch's 2 and equalization's 5 for the dominant tone, and the standard deviations, come out exactly.

Run `--map` for the value mappings, `--output` for the pixels and contrast, `--check` for the gate. The dense-region gap measures contrast right where the pixels are — the output distance from the dominant tone to the next-lower value.

```python filename=modules/generative-media/code/histeq-inter-01/histeq.py:95-99 COMPLETE
def dense_gap(pixels, mapping):
    """Output gap between the dominant tone and the next-lower value -- contrast around the busy region."""
    dom = max(set(pixels), key=pixels.count)
    below = max((v for v in set(pixels) if v < dom), default=dom)
    return mapping[dom] - mapping[below]
```

The equalization map is built from the cumulative histogram — the running total of pixel counts.

```python filename=modules/generative-media/code/histeq-inter-01/histeq.py:50-56 COMPLETE
def cdf(hist):
    out, run = [], 0
    for c in hist:
        run += c
        out.append(run)
    return out
```

<svg role="img" aria-label="Contrast (standard deviation) rising from input 0.927 to stretch 2.236 to equalize 2.472 as three bars" viewBox="0 0 470 150" width="470" height="150">
  <rect x="0" y="0" width="470" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">contrast (pixel std) — higher is more contrast</text>
  <line x1="50" y1="120" x2="450" y2="120" stroke="var(--line)"/>
  <rect x="80" y="98" width="70" height="22" fill="var(--muted)"/>
  <text x="82" y="92" font-family="var(--mono)" font-size="8" fill="var(--muted)">input 0.927</text>
  <rect x="200" y="66" width="70" height="54" fill="var(--s2)"/>
  <text x="200" y="60" font-family="var(--mono)" font-size="8" fill="var(--s2)">stretch 2.236</text>
  <rect x="320" y="59" width="70" height="61" fill="var(--acc-line)"/>
  <text x="318" y="53" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">equalize 2.472</text>
</svg>
^ The stretch lifts contrast well above the flat input by pushing the endpoints out, and equalization adds a further increment by spreading the dense mid-tones the stretch left bunched.

The self-test pins that both methods use the full range but equalization adds more contrast, lifts the dominant tone, and widens the gap where the pixels are.

```python filename=modules/generative-media/code/histeq-inter-01/histeq.py:123-127 COMPLETE
    both_use_full_range = min(st) == 0 and max(st) == L - 1 and min(eq) == 0 and max(eq) == L - 1
    print("  both methods span the full 0..%d range = %s" % (L - 1, both_use_full_range))

    equalize_more_contrast = stdev(eq) > stdev(st)
    print("  equalization spreads the pixels more (higher std) = %s (%.3f > %.3f)"
          % (equalize_more_contrast, stdev(eq), stdev(st)))
```

```text filename=modules/generative-media/code/histeq-inter-01/histeq.py --check
SELF-TEST — the linear stretch keeps the dense tones bunched low; equalization spreads them for contrast
--------------------------------------------------------------------------------------------------------
  both methods span the full 0..7 range = True
  equalization spreads the pixels more (higher std) = True (2.472 > 2.236)
  both raise contrast above the flat input = True (input 0.927)
  the stretch leaves the dominant tone crowded low, equalize lifts it = True (2 vs 5)
  equalize gives the densest region the wider output gap = True (5 vs 2)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  both_use_full_range=True  equalize_more_contrast=True  both_beat_input=True  equalize_lifts_dominant=True  equalize_widens_dense_gap=True
```

Five True flags. Both_use_full_range: the stretch and equalization both hit 0 and 7, so the win is not about the range. Equalize_more_contrast: equalization's std is 2.472 versus the stretch's 2.236. Both_beat_input: both raise contrast above the flat input's 0.927, but not equally. Equalize_lifts_dominant: the dominant tone goes to 2 under the stretch and 5 under equalization. Equalize_widens_dense_gap: the gap around the dense region is 5 versus 2. The full-range flag is the one that reframes the lesson: since both use the whole range, spanning the range was never the point — spending it by density is.

**The full-range flag is the reframing — both methods reach pure black and white, so "use the whole range" is not what adds contrast; equalization wins by giving the densest tones the widest output slice, which the affine stretch structurally cannot do.**

## Definition of done

You are done when you reproduce the two mappings and can explain why the affine stretch cannot spread the dense tones.

Concretely: `--map` shows both sending 2→0 and 5→7 but the dominant 3 going to 2 (stretch) versus 5 (equalize); `--output` shows std rising 0.927 → 2.236 → 2.472 with the dense gap 2 versus 5; `--check` prints PASS with five True flags. You can explain that contrast is separation among the tones that occur (not the endpoint range), that an affine map preserves gap ratios so it cannot give a dense cluster more of the range, and that equalization's CDF map allocates output range by density to spread the crowded tones. You can also state the honest limits: discrete bins move but do not split, and equalization can over-enhance noise (hence CLAHE).

The habit to carry: when an image looks flat despite using the full range, reach for histogram equalization (or a local, clip-limited variant), not a linear stretch — the stretch only helps when the distribution is already uniform. When a contrast boost amplifies noise or looks harsh, suspect global equalization over-spreading a dense region, and switch to a clip-limited adaptive version. Spend the range where the pixels are.

## Boss fight

The instructive failure is a medical or satellite image that looks blank after a "contrast fix" that only stretched it.

An analyst has a 16-bit scan whose meaningful tissue (or terrain) all sits in a narrow band of values, with a few bright specular pixels at the top. They apply a min-max stretch to "use the full dynamic range," and the image still looks uniformly gray, because the stretch mapped the two extreme outliers to black and white and left the entire diagnostic band packed into a sliver in the middle — the outliers ate the whole range. The fix is histogram equalization, which ignores where the outliers are and allocates range by how many pixels sit at each level, spreading the dense diagnostic band across most of the output; in practice CLAHE is used so the spreading is local and noise is clipped.

Your turn, two moves. First, add the outlier failure to the fixture: append one pixel at 0 and one at 7 to the bunched image and re-run the stretch; confirm the stretch now barely changes the bunched middle (the outliers already defined the endpoints, so the affine map has nothing to do) while equalization still spreads the dense band — showing that the stretch is fragile to outliers and equalization is not. Second, expose the over-enhancement risk: make one value hold almost all the pixels and confirm equalization spreads it so aggressively that a tiny difference becomes a large one, which for noisy data would amplify the noise — the motivation for the clip limit in CLAHE.

## External resources

Any image-processing text (Gonzalez and Woods, "Digital Image Processing") derives histogram equalization from the CDF and proves the uniform-output property, alongside the contrast-stretching methods it improves on.

The CLAHE paper (Zuiderveld, "Contrast Limited Adaptive Histogram Equalization," 1994) is the standard local, clip-limited variant used in practice, and reading it shows the two fixes to plain equalization — go local, and cap the spreading — that this module's caveats point to.

OpenCV's and scikit-image's histogram-equalization documentation shows the global and CLAHE functions side by side with example images, which makes the "full range but still flat" versus "spread by density" distinction concrete on real photographs.
