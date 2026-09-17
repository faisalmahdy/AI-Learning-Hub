---
id: lumagray-inter-01
title: Convert color to grayscale with luma weights, not a channel average — the eye weights green far more than blue
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Turning a color image to grayscale looks like it should be the average of the R, G, B channels — add them, divide by three — which treats the channels as equally important to brightness, and they are not. Human vision is most sensitive to green, less to red, least to blue, by large factors, so equal intensities of the three primaries do not look equally bright: pure green looks bright, pure red middling, pure blue distinctly dark. A grayscale conversion is meant to capture how bright each pixel looks, and a plain channel average captures how much total signal is present regardless of how the eye weights it — a different and wrong thing. The failure is sharpest on saturated colors: because the average weights every channel the same, all three fully-saturated primaries collapse to the identical gray (a third of full), though they span a huge range of perceived brightness, so a bright green region and a dark blue region become the same shade, indistinguishable. The fix is to weight the channels by their contribution to perceived brightness (luma): the Rec. 601 coefficients 0.299 R + 0.587 G + 0.114 B, summing to 1, come from measurements of human sensitivity — green at 0.587 dominates, blue at 0.114 barely registers — so the primaries map to well-separated grays that match perception and the grayscale preserves the original's brightness structure. On the three primaries, the naive average maps red, green, and blue all to 85 (identical), while luma weighting maps them to 76.2, 149.7, and 29.1, spanning the real range of perceived brightness.
eli5: Imagine you're turning a colorful picture into a black-and-white one, and to do it you decide how "bright" each color should look in gray. It's tempting to treat red, green, and blue as equally bright — but your eyes don't. Green looks much brighter to you than blue does, even at the same strength. If you ignore that and just average the colors, then a vivid green and a deep blue both come out as the exact same medium gray, so you can't tell them apart in the black-and-white version, even though in color one was clearly much brighter. The fix is to count green a lot, red a medium amount, and blue only a little — matching how bright each really looks to your eyes — so the gray picture keeps the brightness differences you actually see.
---

## Why this module

Grayscale conversion is a one-liner people write from memory, and the memorized version — average the channels — is wrong in a way that is invisible until you hit saturated color, at which point it destroys contrast. It is worth getting right because grayscale is a preprocessing step under an enormous amount of downstream work: thresholding, edge detection, OCR, feature matching, thumbnails. If the grayscale flattens brightness differences the eye would see, everything built on it inherits the flattening, and the bug is subtle because the gray image still looks like a plausible gray image.

The root cause is that "brightness" is a fact about human vision, not about the pixel values. The eye's sensitivity is dominated by green, with red secondary and blue a distant third — the differences are large, roughly 0.59 / 0.30 / 0.11. So the perceived brightness of a color is a weighted sum with those weights, and a plain average (weights 1/3, 1/3, 1/3) is a different quantity that happens to share the same units. On grayish, low-saturation content the two nearly agree; on saturated content they diverge hard, because that is where the channel weights matter most.

The correction is to use the perceptual weights, and this module shows the two conversions on the three pure primaries, where the divergence is starkest.

**Convert color to grayscale with a perceptual luma weighting (about 0.299 R + 0.587 G + 0.114 B), not a plain channel average, because the eye weights green far above red and blue — so an average maps colors of very different perceived brightness (all three saturated primaries) to the same gray, flattening contrast the luma weighting preserves.**

## Concepts

The fixture is the three pure RGB primaries and the standard luma weights.

```json filename=modules/generative-media/code/lumagray-inter-01/lumagray.json:3-8 COMPLETE
  "colors": {
    "red": [255, 0, 0],
    "green": [0, 255, 0],
    "blue": [0, 0, 255]
  },
  "luma_weights": [0.299, 0.587, 0.114]
```

The two conversions differ only in the weights. The naive gray averages the channels — implicit weights of 1/3 each; the luma gray weights each channel by the eye's sensitivity.

```python filename=modules/generative-media/code/lumagray-inter-01/lumagray.py:32-39 COMPLETE
def naive_gray(rgb):
    """Plain channel average -- treats all channels as equally bright."""
    return sum(rgb) / 3


def luma_gray(rgb, weights):
    """Perceptual luma -- weights each channel by the eye's sensitivity."""
    return sum(w * c for w, c in zip(weights, rgb))
```

Because the naive weights are all equal, any color whose channels sum to the same total gets the same naive gray — and all three saturated primaries sum to 255, so they map to one value. The luma weights break that tie by how bright each channel actually looks.

<svg role="img" aria-label="Three primary swatches red green blue; below, naive gray shows all three as the identical medium gray, while luma gray shows red medium, green bright, blue dark" viewBox="0 0 320 130">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">the three primaries</text>
  <rect x="20" y="22" width="60" height="20" fill="var(--s2)"/><text x="40" y="36" font-size="8" fill="var(--panel)">red</text>
  <rect x="90" y="22" width="60" height="20" fill="var(--s1)"/><text x="108" y="36" font-size="8" fill="var(--panel)">green</text>
  <rect x="160" y="22" width="60" height="20" fill="var(--muted)"/><text x="180" y="36" font-size="8" fill="var(--panel)">blue</text>
  <text x="10" y="66" font-size="8.5" fill="var(--s2)">naive gray: all 85 (identical)</text>
  <rect x="20" y="72" width="60" height="16" fill="var(--muted)"/><rect x="90" y="72" width="60" height="16" fill="var(--muted)"/><rect x="160" y="72" width="60" height="16" fill="var(--muted)"/>
  <text x="10" y="110" font-size="8.5" fill="var(--s1)">luma gray: 76 / 150 / 29 (separated)</text>
  <rect x="20" y="114" width="60" height="12" fill="var(--muted)"/><rect x="90" y="108" width="60" height="18" fill="var(--s1)"/><rect x="160" y="118" width="60" height="8" fill="var(--muted)" opacity="0.6"/>
</svg>
^ The three primaries are visibly different in brightness. Naive gray renders them as one identical shade (85), erasing that; luma gray renders green bright (150), red medium (76), blue dark (29), matching what the eye sees.

**A grayscale value should encode perceived brightness, which is a weighted sum tuned to the eye — a plain average is a different quantity that agrees only when the color is near-neutral.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the grayscale-conversion step of an image pipeline, reduced to the three primaries so every gray value is checkable by hand.

Run `--gray` to see both conversions.

```text filename=lumagray.py --gray
  color   rgb              naive   luma
  red     [255, 0, 0]      85.0    76.2
  green   [0, 255, 0]      85.0    149.7
  blue    [0, 0, 255]      85.0    29.1
  naive weights channels equally; luma weights green most, blue least
```

The naive column is 85 for all three — red, green, and blue become the identical gray, because each has one channel at 255 and the average is 255/3 regardless of which channel it is. The luma column tells the truth the eye sees: green is 149.7 (bright), red 76.2 (medium), blue 29.1 (dark). Same three colors; the naive conversion says they are equally bright, the luma conversion says green is more than five times as bright as blue.

The `--collapse` view computes each method's spread — the gap between the brightest and darkest gray.

```python filename=modules/generative-media/code/lumagray-inter-01/lumagray.py:56-62 COMPLETE
    colors, w = data["colors"], data["luma_weights"]
    naive = {name: naive_gray(rgb) for name, rgb in colors.items()}
    luma = {name: luma_gray(rgb, w) for name, rgb in colors.items()}
    print("COLLAPSE — naive maps the primaries together; luma keeps them apart")
    print("-" * 60)
    print("  naive grays: %s -> spread %.1f" % ({n: round(v, 1) for n, v in naive.items()}, max(naive.values()) - min(naive.values())))
    print("  luma  grays: %s -> spread %.1f" % ({n: round(v, 1) for n, v in luma.items()}, max(luma.values()) - min(luma.values())))
```

Running it measures the flattening.

```text filename=lumagray.py --collapse
  naive grays: {'red': 85.0, 'green': 85.0, 'blue': 85.0} -> spread 0.0
  luma  grays: {'red': 76.2, 'green': 149.7, 'blue': 29.1} -> spread 120.6
  the naive average flattens all contrast to spread 0; luma keeps a spread of 120.6 gray levels
```

The naive grays have a spread of zero — the three primaries are indistinguishable in the naive grayscale, all one shade. The luma grays span 120.6 levels, nearly half the full 0–255 range. If these three colors sat side by side in an image, the naive grayscale would show a flat gray rectangle and the luma grayscale would show three clearly different bands. The contrast the color carried is preserved by luma and destroyed by the average.

**The naive average collapses the three primaries to a single gray (spread 0), while luma keeps them 120 levels apart — the average did not dim the contrast, it deleted it, and only the perceptual weighting keeps it.**

## Build

The self-test asserts the weights and the failure: the luma weights sum to 1 with green largest, and the naive average maps all three primaries to the same gray.

```python filename=modules/generative-media/code/lumagray-inter-01/lumagray.py:75-85 COMPLETE
    weights_sum_one = abs(sum(w) - 1.0) < 1e-9
    print("  the luma weights sum to 1 = %s (%.3f)" % (weights_sum_one, sum(w)))

    green_weight_largest = w[1] == max(w)
    print("  green has the largest luma weight = %s (%.3f)" % (green_weight_largest, w[1]))

    naive_all_equal = max(naive) - min(naive) < 1e-9
    print("  the naive average maps all three primaries to the SAME gray = %s (%.1f)" % (naive_all_equal, naive[0]))

    luma_all_different = len({round(v, 1) for v in luma.values()}) == 3
    print("  luma weighting gives all three DIFFERENT grays = %s (%s)" % (luma_all_different, {n: round(v, 1) for n, v in luma.items()}))
```

<svg role="img" aria-label="Two rows of three gray swatches: naive row all the same shade, luma row with green light, red medium, blue dark" viewBox="0 0 320 110">
  <text x="10" y="18" font-size="8.5" fill="var(--s2)">naive: spread 0</text>
  <rect x="130" y="8" width="40" height="16" fill="var(--muted)"/><rect x="172" y="8" width="40" height="16" fill="var(--muted)"/><rect x="214" y="8" width="40" height="16" fill="var(--muted)"/>
  <text x="10" y="62" font-size="8.5" fill="var(--s1)">luma: spread 120.6</text>
  <rect x="130" y="48" width="40" height="16" fill="var(--muted)"/><text x="138" y="60" font-size="7" fill="var(--panel)">red 76</text>
  <rect x="172" y="48" width="40" height="16" fill="var(--s1)"/><text x="178" y="60" font-size="7" fill="var(--panel)">grn 150</text>
  <rect x="214" y="48" width="40" height="16" fill="var(--muted)" opacity="0.55"/><text x="220" y="60" font-size="7" fill="var(--panel)">blu 29</text>
  <text x="10" y="96" font-size="7.5" fill="var(--ink)">same three colors — the average erases their brightness order, luma keeps it</text>
</svg>
^ The naive row is three identical swatches; the luma row ranks them green > red > blue by perceived brightness. The weighting is the only difference between a flat gray and a faithful one.

Running the check confirms every clause, including the perceptual ranking and the preserved contrast.

```text filename=lumagray.py --check
  the luma weights sum to 1 = True (1.000)
  green has the largest luma weight = True (0.587)
  the naive average maps all three primaries to the SAME gray = True (85.0)
  luma weighting gives all three DIFFERENT grays = True ({'red': 76.2, 'green': 149.7, 'blue': 29.1})
  luma ranks green > red > blue (matching perception) = True (149.7 > 76.2 > 29.1)
  luma preserves brightness contrast the average flattens = True (spread 120.6 vs 0.0)
```

**The check ties the collapse to the equal naive weights and the recovery to the perceptual ones — same colors, and only the weighting decides whether the grayscale carries their brightness order.**

## Definition of done

Two properties close it. The naive average must map all three primaries to the same gray (the flattening in full), and luma must give three different grays ranked green > red > blue matching perception (the fix in full). The perceptual ranking is what makes luma correct rather than merely different — any non-equal weights would separate the primaries, but only the sensitivity-based ones separate them the way the eye does.

```python filename=modules/generative-media/code/lumagray-inter-01/lumagray.py:87-91 COMPLETE
    green_brightest = luma["green"] > luma["red"] > luma["blue"]
    print("  luma ranks green > red > blue (matching perception) = %s (%.1f > %.1f > %.1f)" % (green_brightest, luma["green"], luma["red"], luma["blue"]))

    luma_preserves_contrast = (max(luma.values()) - min(luma.values())) > (max(naive) - min(naive))
    print("  luma preserves brightness contrast the average flattens = %s (spread %.1f vs %.1f)"
          % (luma_preserves_contrast, max(luma.values()) - min(luma.values()), max(naive) - min(naive)))
```

Two refinements keep the tool precise. First, the exact coefficients depend on the color standard: Rec. 601 (used here, 0.299/0.587/0.114) is the classic SDTV set, while Rec. 709 for HDTV/sRGB uses 0.2126/0.7152/0.0722 — the weights differ slightly but the story is identical, green dominates and blue barely counts; the average (1/3 each) is wrong under every standard. Second, and more subtly, truly correct luminance should be computed on linear-light RGB, not the gamma-encoded values stored in a typical image: applying luma weights directly to gamma-encoded pixels (as this module and most quick conversions do) is the standard fast approximation, good enough for display and most vision preprocessing, but a color-accurate pipeline linearizes first, applies the weights, then re-encodes. The essential point holds at every level of rigor: the channels must be weighted by perceptual contribution, never averaged, or saturated colors of different brightness collapse together.

<svg role="img" aria-label="Two sets of weights: naive equal thirds for R G B, and luma with a large green bar, medium red, tiny blue" viewBox="0 0 320 110">
  <text x="10" y="16" font-size="8.5" fill="var(--s2)">naive weights: 0.33 each</text>
  <rect x="20" y="24" width="40" height="16" fill="var(--muted)"/><text x="26" y="36" font-size="7" fill="var(--panel)">R .33</text>
  <rect x="64" y="24" width="40" height="16" fill="var(--muted)"/><text x="70" y="36" font-size="7" fill="var(--panel)">G .33</text>
  <rect x="108" y="24" width="40" height="16" fill="var(--muted)"/><text x="114" y="36" font-size="7" fill="var(--panel)">B .33</text>
  <text x="10" y="66" font-size="8.5" fill="var(--s1)">luma weights: tuned to the eye</text>
  <rect x="20" y="74" width="36" height="16" fill="var(--muted)"/><text x="24" y="86" font-size="7" fill="var(--panel)">R .30</text>
  <rect x="60" y="74" width="70" height="16" fill="var(--s1)"/><text x="80" y="86" font-size="7" fill="var(--panel)">G .59</text>
  <rect x="134" y="74" width="14" height="16" fill="var(--muted)" opacity="0.6"/><text x="150" y="86" font-size="7" fill="var(--muted)">B .11</text>
  <text x="10" y="104" font-size="7.5" fill="var(--ink)">the eye's green dominance is the whole difference between the two</text>
</svg>
^ The naive weights are equal thirds; the luma weights put more than half on green and almost nothing on blue. That green dominance — a measured fact about the eye — is exactly what the average ignores and luma encodes.

**Done means the naive average maps all three primaries to one gray while luma separates them in the perceptual order green > red > blue — a weighting fix (perceptual coefficients, not equal ones) that preserves brightness contrast, with the standard's exact weights and linearization as refinements.**

## Boss fight

A team builds an OCR pipeline that converts scanned documents to grayscale (channel average) before thresholding text from background. It works on black-on-white documents but fails badly on documents with colored highlights — text under a blue highlight is read fine, but text under a green or yellow highlight vanishes or turns to garbage. What is going wrong, and what one change fixes it?

The grayscale conversion is averaging the channels, which does not reflect how bright the colored highlights actually are, and that breaks the thresholding step that separates text from background. Under a green or yellow highlight, the background is perceptually bright (green has the dominant luma weight, and yellow is red+green, both high), so the real contrast between dark text and bright highlight is large — but the channel average underweights green, pulling the highlighted background's gray value down toward the text's, collapsing the contrast the threshold relies on, so the text merges into the background and is lost or garbled. Blue highlights happen to work because blue is perceptually dark and the average roughly agrees there, so contrast survives. The fix is to convert to grayscale with perceptual luma weights (0.299 R + 0.587 G + 0.114 B, or the Rec. 709 set) instead of the channel average: that maps the green/yellow highlighted background to its true high brightness, restoring the large text-vs-background contrast the threshold needs, and the text separates cleanly under highlights of any color. For a fully color-robust pipeline you would also consider linearizing before weighting, or adaptive/local thresholding, but the single change that fixes the reported failure is replacing the average with luma weighting — the OCR was losing contrast that the correct brightness weighting preserves.

## External resources

The Rec. 601 and Rec. 709 luma coefficient definitions (ITU-R BT.601 / BT.709) and the OpenCV `cvtColor` COLOR_RGB2GRAY documentation — the authoritative sources for the perceptual weights used in standard grayscale conversion and why they differ from a channel average.

Charles Poynton's "Frequently Asked Questions about Color" and *Digital Video and HD* — the definitive treatment of luma, perceived brightness, and the gamma/linear-light subtlety, explaining why the eye's green dominance sets the weights and when linearization matters for correct luminance.
