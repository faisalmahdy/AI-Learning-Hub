---
id: histmatch-inter-01
title: Match tone through the CDFs, not the mean — a brightness shift moves the average but cannot reshape the distribution
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Histogram matching (also called histogram specification) makes a source image take on the tonal character of a reference image — used to give a batch of frames one consistent look, or to grade a dull shot toward a reference's mood. The naive approach is to shift the source's brightness until its average matches the reference's, and it does not work: a brightness shift (or a linear scale) can only move and stretch the distribution, it cannot reshape it. A source that is skewed dark stays just as skewed after you brighten it — the mean moves up but the shape is still the source's, not the reference's. Matching the mean is not matching the look. The fix works through the cumulative distribution functions: the CDF at a level is the fraction of pixels at or below it, and it captures the tonal shape. To match, send each source level to the reference level that occupies the same position in the reference's CDF — for a source level whose cumulative probability is p, find the reference level whose cumulative probability first reaches p. Because the mapping is driven by matching cumulative probabilities, the remapped output distribution approximates the reference's whole shape, not just its mean; and because it is monotonic, brighter always stays brighter. On a fixture where the source is dark (histogram 4,3,2,1, mean 1.0) and the reference bright (1,2,3,4, mean 2.0), CDF matching maps source levels 0,1,2,3 to 2,3,3,3, producing an output histogram of 0,0,4,6 whose CDF distance to the reference improves from 1.0 (source) to 0.6 (output) — the distribution moved toward the reference, which a brightness shift can never do.
eli5: Imagine two stacks of blocks sorted by color from dark to light, and you want your stack to have the same mix of colors as your friend's. One way is to just make your average color match theirs — but if your blocks are mostly dark and theirs are mostly light, nudging your average lighter still leaves you with a mostly-dark pile, just shifted. The trick that actually works is to line both stacks up and ask, for each of your blocks, "how far up the pile is this one?" — then give it the color of your friend's block at the same height. Now your pile takes on their whole spread of colors, not just their average. It is not perfect when you only have a few colors to choose from, but your pile really does start to look like theirs.
---

## Why this module

Making one image look like another — giving a batch of frames a single consistent grade, or pushing a flat shot toward a reference's mood — sounds like it should be a brightness adjustment. The reference is brighter, so brighten the source until the averages line up. That instinct is wrong in a specific, mechanical way, and the reason is worth internalizing because it recurs anywhere you try to make one distribution resemble another: matching a summary statistic is not the same as matching the thing the statistic summarizes.

A brightness shift adds a constant to every pixel; a linear scale multiplies. Both are rigid moves — they can slide the whole distribution left or right and stretch it wider or narrower, but they cannot change its shape. A source that is skewed dark, with most of its pixels bunched at the low end, stays exactly that skewed after you brighten it: the pixels all move up together, the mean rises, but the pile is still leaning the same way. If the reference's pixels lean the other way, you have matched the average and matched nothing else.

Histogram matching reshapes the distribution instead, and it does so through the cumulative distribution function. This module runs both the naive mean-based reasoning and the CDF-based match on the same pair of tiny images and measures how far each output lands from the reference.

**Match one image's tone to a reference by mapping each source level through the two CDFs — send a source level to the reference level with the same cumulative probability — because this reshapes the source's whole distribution toward the reference's, whereas a brightness shift or linear scale only moves the mean and leaves the source's shape unchanged.**

## Concepts

Represent each image not as pixels but as a histogram: how many pixels sit at each intensity level. On this fixture there are four gray levels (0 = dark to 3 = bright). The source histogram is [4, 3, 2, 1] — most pixels dark, tapering off toward bright, mean 1.0. The reference is [1, 2, 3, 4] — the mirror image, tapering the other way, mean 2.0. The source is dark; the reference is bright; and critically, they are skewed in opposite directions, so no shift can turn one into the other.

The CDF is the running fraction of pixels at or below each level. It is what actually encodes the tonal shape: a dark image's CDF rises fast (it has accumulated most of its pixels by the low levels), a bright image's rises slowly.

```python filename=modules/generative-media/code/histmatch-inter-01/histmatch.py:53-70 COMPLETE
def cdf(hist):
    """Cumulative distribution: the running fraction of pixels at or below each level."""
    total = sum(hist)
    running = 0
    out = []
    for h in hist:
        running += h
        out.append(running / total)
    return out


def match_mapping(source_cdf, ref_cdf):
    """Map each source level to the reference level whose CDF first reaches the source level's CDF."""
    mapping = []
    for p in source_cdf:
        j = next(k for k, c in enumerate(ref_cdf) if c >= p)
        mapping.append(j)
    return mapping
```

The mapping is the whole idea in three lines. For each source level, take its cumulative probability p, then walk the reference's CDF until you find the first level whose cumulative probability has reached p, and send the source pixels there. You are matching positions in the two piles: a source level that sits 40% of the way up the source pile goes to whatever reference level first reaches 40% of the way up the reference pile.

Once you have the mapping, applying it is a redistribution — every pixel at a source level moves to its mapped level — and the L1 distance between two CDFs measures how different two tonal shapes are, which is how we score the result.

```python filename=modules/generative-media/code/histmatch-inter-01/histmatch.py:73-88 COMPLETE
def apply_mapping(source_hist, mapping, levels):
    """Redistribute the source pixels to their mapped levels, producing the output histogram."""
    out = [0] * levels
    for level, count in enumerate(source_hist):
        out[mapping[level]] += count
    return out


def mean_level(hist):
    total = sum(hist)
    return sum(level * count for level, count in enumerate(hist)) / total


def cdf_l1(a, b):
    """L1 distance between two CDFs -- how different the two tonal shapes are."""
    return sum(abs(x - y) for x, y in zip(a, b))
```

The two histograms are the only fixture; every CDF, the mapping, and the output distribution are computed from them.

```json filename=modules/generative-media/code/histmatch-inter-01/histmatch.json:3-4 COMPLETE
  "source_hist": [4, 3, 2, 1],
  "reference_hist": [1, 2, 3, 4]
```

<svg role="img" aria-label="Source CDF rises fast to the left; reference CDF rises slowly, staying low until the right" viewBox="0 0 320 170">
  <line x1="40" y1="20" x2="40" y2="140" stroke="var(--line)" stroke-width="1"/>
  <line x1="40" y1="140" x2="300" y2="140" stroke="var(--line)" stroke-width="1"/>
  <text x="20" y="24" font-size="9" fill="var(--muted)">1.0</text>
  <text x="20" y="144" font-size="9" fill="var(--muted)">0.0</text>
  <text x="36" y="158" font-size="9" fill="var(--muted)">0</text>
  <text x="118" y="158" font-size="9" fill="var(--muted)">1</text>
  <text x="196" y="158" font-size="9" fill="var(--muted)">2</text>
  <text x="274" y="158" font-size="9" fill="var(--muted)">level</text>
  <polyline points="40,92 118,56 196,32 274,20" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <circle cx="40" cy="92" r="3" fill="var(--s1)"/>
  <circle cx="118" cy="56" r="3" fill="var(--s1)"/>
  <circle cx="196" cy="32" r="3" fill="var(--s1)"/>
  <circle cx="274" cy="20" r="3" fill="var(--s1)"/>
  <text x="46" y="88" font-size="9" fill="var(--s1)">source CDF (rises fast — dark)</text>
  <polyline points="40,128 118,104 196,68 274,20" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="40" cy="128" r="3" fill="var(--s2)"/>
  <circle cx="118" cy="104" r="3" fill="var(--s2)"/>
  <circle cx="196" cy="68" r="3" fill="var(--s2)"/>
  <circle cx="274" cy="20" r="3" fill="var(--s2)"/>
  <text x="150" y="122" font-size="9" fill="var(--s2)">reference CDF (rises slow — bright)</text>
</svg>
^ The two CDFs are the tonal shapes matching works from: the source's climbs fast (0.4 by level 0), the reference's lags (0.1 by level 0). Matching sends each source level to the reference level at the same height.

**The CDF, not the mean, is what carries the tonal shape — matching positions in the two CDFs is what lets the output take on the reference's whole distribution.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the tonal-grading step of a media pipeline, reduced to two four-level histograms so every CDF and mapping is checkable by hand.

Run `--cdf` first: it prints the two histograms and their CDFs side by side, the raw material the match works from.

```text filename=histmatch.py --cdf
  level          0     1     2     3
  source hist    4     3     2     1
  source CDF     0.4   0.7   0.9   1.0
  reference hist 1     2     3     4
  reference CDF  0.1   0.3   0.6   1.0
  source mean = 1.0 (dark) ; reference mean = 2.0 (bright)
```

The source CDF has reached 0.4 by level 0 and 0.7 by level 1 — most of its mass is already spent on the dark levels. The reference CDF is still at 0.1 and 0.3 there; it holds its mass back for the bright end. These are the opposite shapes, which is exactly why a brightness shift (which would move the source CDF bodily rightward but keep its fast-rising shape) cannot make one look like the other.

Now `--match` computes the CDF-driven mapping and applies it.

```text filename=histmatch.py --match
  source level 0 (CDF 0.4) -> reference level 2 (CDF 0.6)
  source level 1 (CDF 0.7) -> reference level 3 (CDF 1.0)
  source level 2 (CDF 0.9) -> reference level 3 (CDF 1.0)
  source level 3 (CDF 1.0) -> reference level 3 (CDF 1.0)
  output histogram = [0, 0, 4, 6]   output CDF = ['0.0', '0.0', '0.4', '1.0']
  CDF distance to reference: source 1.0 -> output 0.6 (closer is better)
```

Read the first line: source level 0 has cumulative probability 0.4, and the first reference level whose CDF reaches 0.4 is level 2 (its CDF is 0.6, the first value ≥ 0.4). So the four darkest pixels, all at level 0, jump to level 2. Level 1 (CDF 0.7) needs the first reference level at ≥ 0.7, which is level 3. Every source level ends up at 2 or 3 — the dark image has been pushed bright. The output histogram [0, 0, 4, 6] puts nothing at the two dark levels, and its CDF distance to the reference is 0.6, down from the source's 1.0. The distribution genuinely moved toward the reference.

**The mapping [2, 3, 3, 3] is not a shift — it collapses and redistributes the source levels by matching CDF positions, which is why the output takes on the reference's bright skew instead of merely a higher average.**

## Build

The mapping is what a shift can never produce: it is many-to-one (three source levels all land on 3) and it is driven entirely by cumulative position. The self-test asserts the properties that make it a valid tonal match rather than an arbitrary remap — the source really is darker, the mapping is monotonic so tones never invert, and the darkest level is pushed brighter.

```python filename=modules/generative-media/code/histmatch-inter-01/histmatch.py:130-137 COMPLETE
    source_darker = mean_level(s) < mean_level(r)
    print("  the source is darker than the reference = %s (mean %.1f < %.1f)" % (source_darker, mean_level(s), mean_level(r)))

    mapping_monotonic = all(mapping[i] <= mapping[i + 1] for i in range(len(mapping) - 1))
    print("  the mapping is monotonic (brighter stays brighter) = %s (%s)" % (mapping_monotonic, mapping))

    maps_dark_to_bright = mapping[0] > 0
    print("  the darkest source level is remapped brighter = %s (level 0 -> %d)" % (maps_dark_to_bright, mapping[0]))
```

<svg role="img" aria-label="Arrows from four source levels collapsing onto reference levels 2 and 3" viewBox="0 0 320 160">
  <text x="20" y="20" font-size="10" fill="var(--muted)">source level</text>
  <text x="200" y="20" font-size="10" fill="var(--muted)">reference level</text>
  <text x="40" y="52" font-size="11" fill="var(--ink)">0 (0.4)</text>
  <text x="40" y="82" font-size="11" fill="var(--ink)">1 (0.7)</text>
  <text x="40" y="112" font-size="11" fill="var(--ink)">2 (0.9)</text>
  <text x="40" y="142" font-size="11" fill="var(--ink)">3 (1.0)</text>
  <text x="250" y="82" font-size="11" fill="var(--ink)">2 (0.6)</text>
  <text x="250" y="112" font-size="11" fill="var(--ink)">3 (1.0)</text>
  <line x1="90" y1="48" x2="245" y2="78" stroke="var(--s1)" stroke-width="1.5"/>
  <line x1="90" y1="78" x2="245" y2="108" stroke="var(--s2)" stroke-width="1.5"/>
  <line x1="90" y1="108" x2="245" y2="108" stroke="var(--s2)" stroke-width="1.5"/>
  <line x1="90" y1="138" x2="245" y2="108" stroke="var(--s2)" stroke-width="1.5"/>
</svg>
^ The mapping collapses source levels onto the bright end: level 0 to reference 2, levels 1–3 all to reference 3. Three-to-one is impossible for a shift; it is what reshaping looks like.

Run the check and every flag comes back true — the match has the structural properties a valid tonal specification requires.

```text filename=histmatch.py --check
  the source is darker than the reference = True (mean 1.0 < 2.0)
  the mapping is monotonic (brighter stays brighter) = True ([2, 3, 3, 3])
  the darkest source level is remapped brighter = True (level 0 -> 2)
  the output CDF is closer to the reference than the source was = True (0.6 < 1.0)
  no pixels are created or lost by the remap = True (10 == 10)
SELF-TEST PASS  source_darker=True  mapping_monotonic=True  maps_dark_to_bright=True  output_closer=True  pixels_conserved=True
```

**A valid match is monotonic and pixel-conserving — it never inverts tone and never invents or drops a pixel; it only redistributes the ones it has, driven by CDF position.**

## Definition of done

Two properties close the loop. First, the output must actually be closer to the reference than the source was — otherwise the match did nothing. The CDF L1 distance drops from 1.0 to 0.6, so the output distribution measurably moved toward the reference's shape. Second, the remap must conserve pixels: redistributing intensities can never create or destroy a pixel, so the output histogram must sum to the same total as the source.

```python filename=modules/generative-media/code/histmatch-inter-01/histmatch.py:139-144 COMPLETE
    output_closer = cdf_l1(cdf(out), rc) < cdf_l1(sc, rc)
    print("  the output CDF is closer to the reference than the source was = %s (%.1f < %.1f)"
          % (output_closer, cdf_l1(cdf(out), rc), cdf_l1(sc, rc)))

    pixels_conserved = sum(out) == sum(s)
    print("  no pixels are created or lost by the remap = %s (%d == %d)" % (pixels_conserved, sum(out), sum(s)))
```

The improvement is real but not perfect — 0.6 is closer to the reference than 1.0, not equal to it. That is the honest catch of the mechanism: matching is exact only in the continuous limit. With four discrete levels the CDFs cannot line up perfectly (the reference reaches 0.6 at level 2, but no source level asks for exactly that), so the output approximates the reference rather than equalling it. The fewer levels, the coarser the match; with 256 levels the residual would be tiny, but it never reaches zero.

<svg role="img" aria-label="Three histograms: source skewed dark, output pushed bright, reference bright, output resembling reference" viewBox="0 0 330 150">
  <text x="10" y="16" font-size="9" fill="var(--muted)">source [4,3,2,1]</text>
  <rect x="14" y="60" width="14" height="60" fill="var(--s1)"/>
  <rect x="30" y="75" width="14" height="45" fill="var(--s1)"/>
  <rect x="46" y="90" width="14" height="30" fill="var(--s1)"/>
  <rect x="62" y="105" width="14" height="15" fill="var(--s1)"/>
  <text x="120" y="16" font-size="9" fill="var(--muted)">output [0,0,4,6]</text>
  <rect x="124" y="120" width="14" height="0" fill="var(--ink)"/>
  <rect x="140" y="120" width="14" height="0" fill="var(--ink)"/>
  <rect x="156" y="60" width="14" height="60" fill="var(--ink)"/>
  <rect x="172" y="30" width="14" height="90" fill="var(--ink)"/>
  <text x="235" y="16" font-size="9" fill="var(--muted)">reference [1,2,3,4]</text>
  <rect x="239" y="105" width="14" height="15" fill="var(--s2)"/>
  <rect x="255" y="90" width="14" height="30" fill="var(--s2)"/>
  <rect x="271" y="75" width="14" height="45" fill="var(--s2)"/>
  <rect x="287" y="60" width="14" height="60" fill="var(--s2)"/>
  <line x1="10" y1="120" x2="320" y2="120" stroke="var(--line)" stroke-width="1"/>
</svg>
^ The output has abandoned the source's dark skew and now leans bright like the reference — approximately, since four levels cannot match exactly, but unmistakably toward the reference's shape rather than merely its mean.

**Done means the output CDF is provably closer to the reference and the pixel count is conserved — an approximate match that moved the whole distribution, not a shift that moved only the average.**

## Boss fight

Your grading pipeline matches every incoming frame to a single reference still so a sequence has one consistent look. One day a colorist reports that the matched frames look right on average but "flat" — the shadows and highlights are not landing where the reference has them, even though the overall brightness is correct. You check the code and find that someone replaced the CDF match with a step that computes each frame's mean, computes the reference's mean, and adds the difference to every pixel. The means match perfectly. Why do the frames still look wrong, and what one measurement would you print to prove to the colorist that the mean-shift is the problem and the CDF match is the fix?

The mean-shift moves the average and nothing else: a frame skewed dark stays skewed dark after the shift, so its shadows stay crushed and its highlights stay missing relative to the reference — the shape never changed. The measurement that proves it is the CDF L1 distance to the reference, printed for both methods on the same frame. The mean-shift will show a distance essentially as large as the unmatched source's (it only slid the CDF sideways, preserving its shape), while the CDF match shows a distance that has dropped toward zero. On this fixture the source-to-reference distance is 1.0; a pure mean-shift would leave it near 1.0, while the CDF match brings it to 0.6. Show the colorist the two distances side by side and the flatness has a number: the mean-shift matched a single statistic and left the distribution's shape — the thing they were actually looking at — untouched.

## External resources

Gonzalez and Woods, *Digital Image Processing*, the histogram processing chapter — the standard derivation of histogram equalization and specification (matching) through the CDF, including why the match is exact only in the continuous case.

The scikit-image `exposure.match_histograms` documentation and source — a production implementation of exactly this CDF-based mapping, generalized to multi-channel images and 256 levels, useful for seeing how the tiny mechanism here scales to real photographs.
