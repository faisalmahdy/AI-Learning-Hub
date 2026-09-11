---
id: nms-inter-01
title: Thin edges with non-maximum suppression — or thresholding a gradient gives a fuzzy band instead of a line
topic: generative-media
level: intermediate
status: ready
time: 17 min
summary: An edge detector reports gradient magnitude at every pixel, and where the image steps from dark to light the magnitude rises to a peak and falls over several pixels — so a real one-pixel edge shows up as a ridge several pixels wide. Thresholding the magnitude keeps every pixel on the ridge that clears the cutoff, handing you a three- or four-pixel-thick fuzzy band; thresholding harder erodes the whole edge, not the fuzz. Non-maximum suppression thins the ridge to its crest: keep a pixel only if its magnitude is a local maximum along the gradient direction and above the threshold, so only the single peak survives — a one-pixel edge at the true location. On a magnitude ridge 0 2 4 7 5 2 0 peaking at index 3, thresholding at 3 keeps indices 2, 3, 4 (three pixels thick) while non-maximum suppression keeps only index 3, the peak.
eli5: If you run your finger across the edge of a table, you don't feel a single sharp line — you feel the edge "start," peak, and fade over a small width. If you marked every spot that felt edge-ish, you'd draw a fat smudge, not a line. To get the real edge, mark only the single highest point of that bump. That's non-maximum suppression: keep the peak of the ridge, ignore the slopes leading up to it.
---

## Why this module

A gradient magnitude map does not have thin edges to threshold — it has ridges — so any cutoff you apply keeps the whole ridge and returns a band, and the fix is not a better threshold but a different question.

An edge detector like Sobel outputs, at each pixel, how steeply the image is changing there. At a real edge the image transitions over a small distance, so the gradient magnitude is not a spike on one pixel; it climbs to a peak at the edge and tapers off on both sides — a ridge two, three, four pixels wide. Threshold that magnitude to decide "edge or not," and every pixel on the ridge above the cutoff is labeled an edge, so a one-pixel feature comes back as a multi-pixel smear. Raising the threshold does not sharpen it; it just trims the ridge symmetrically from both sides and eventually deletes the peak too. The problem is that thresholding asks "is this pixel edgy enough," and the shoulders of the ridge honestly are edgy — they are just not where the edge *is*.

**Gradient magnitude turns a one-pixel edge into a multi-pixel ridge, so thresholding it returns a thick band no matter the cutoff — the shoulders clear the threshold as truly as the peak.**

Non-maximum suppression asks the right question: is this pixel the *peak* of the ridge? Keep a pixel only if its magnitude is a local maximum — at least as large as its neighbors along the gradient direction — and above the threshold. On the ridge, only the crest is a local maximum; the shoulders are smaller than the peak beside them, so they are suppressed even though they cleared the threshold. What remains is a single pixel sitting on the crest, at the true edge location. This module thresholds a magnitude ridge and then suppresses it, and shows the thick band collapse to one pixel.

## Concepts

**Gradient magnitude** is the edge detector's output per pixel: how steeply the image changes there. At an edge it forms a ridge, peaking at the edge and tapering on both sides.

**Thresholding** keeps every pixel whose magnitude clears a cutoff. It answers "is this pixel edgy enough," so it keeps the whole ridge — peak and shoulders — as a thick band.

```python filename=modules/generative-media/code/nms-inter-01/nms.py:46-48 COMPLETE
def thresholded(mag, threshold):
    """Indices whose magnitude clears the threshold -- the thick edge."""
    return [i for i, m in enumerate(mag) if m >= threshold]
```

**A local maximum** is a pixel at least as large as its neighbors along the gradient direction. On a ridge, only the crest qualifies; the shoulders are dominated by the peak.

**Non-maximum suppression** keeps a pixel only if it is both above the threshold and a local maximum. It answers "is this the pixel where the edge is," so it returns the one-pixel crest.

**Thresholding and NMS answer different questions, and only NMS gives a thin edge.** Thresholding decides membership (edgy or not); suppression decides localization (the exact edge pixel), and a crisp edge needs the second.

<svg role="img" aria-label="Thresholding asks is this pixel edgy enough and keeps the whole ridge; non-maximum suppression asks is this the peak and keeps one pixel" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">two questions about the same ridge</text>
  <text x="15" y="32" fill="var(--s2)" font-size="8">threshold: "edgy enough?"</text>
  <text x="25" y="46" fill="var(--muted)" font-size="7">→ yes for the peak AND its shoulders → thick band</text>
  <text x="15" y="72" fill="var(--s1)" font-size="8">NMS: "is this the peak?"</text>
  <text x="25" y="86" fill="var(--muted)" font-size="7">→ yes only for the crest → one-pixel edge</text>
</svg>
^ Thresholding's membership question says yes to the whole ridge; suppression's localization question says yes only to the crest, which is why one returns a band and the other a line.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/nms-inter-01/nms.py

The fixture is a 1D slice of gradient magnitude across an edge — a ridge peaking at index 3.

```json filename=modules/generative-media/code/nms-inter-01/nms.json:1-5 COMPLETE
{
  "_meta": "A 1D slice of gradient magnitude across an edge. An edge detector (Sobel and the like) outputs the gradient magnitude at every pixel; where the image steps from dark to light the magnitude rises to a peak and falls again, so a true one-pixel edge shows up as a RIDGE several pixels wide. Thresholding the magnitude keeps every pixel on the ridge above the cutoff, giving a thick, fuzzy edge several pixels across. Non-maximum suppression thins it: keep a pixel only if its magnitude is a local maximum (>= both neighbors along the gradient direction, here the 1D neighbors) AND above the threshold, so only the ridge's peak survives -- a crisp one-pixel edge at the true location. magnitudes is the profile; threshold is the cutoff; peak_index is where the real edge is.",
  "magnitudes": [0, 2, 4, 7, 5, 2, 0],
  "threshold": 3,
  "peak_index": 3
}
```

A pixel is a local maximum when it dominates both neighbors; NMS keeps the pixels that are both local maxima and above the threshold.

```python filename=modules/generative-media/code/nms-inter-01/nms.py:51-58 COMPLETE
def is_local_max(mag, i):
    """Is pixel i at least as large as both neighbors along the profile?"""
    return mag[i] >= at(mag, i - 1) and mag[i] >= at(mag, i + 1)


def suppressed(mag, threshold):
    """Non-maximum suppression: keep pixels that are both above threshold and a local maximum."""
    return [i for i, m in enumerate(mag) if m >= threshold and is_local_max(mag, i)]
```

Run `--profile` to see the ridge judged two ways.

```text filename=--profile
PROFILE — gradient magnitude across the edge (threshold 3)
------------------------------------------------------------
  index      0  1  2  3  4  5  6
  magnitude  0  2  4  7  5  2  0
  >= thresh  .  .  Y  Y  Y  .  .
  local max  .  .  .  Y  .  .  .
------------------------------------------------------------
  the ridge clears the threshold over several pixels; only its peak is a local max.
```

The magnitude row is the ridge: it climbs 0, 2, 4, peaks at 7, then falls 5, 2, 0. The "≥ thresh" row shows three pixels — indices 2, 3, 4 — clearing the cutoff of 3: that is the thick edge, and pixels 2 and 4 are on it purely because the ridge is wide, not because the edge is at three places. The "local max" row shows a single Y at index 3: only the peak is at least as large as both its neighbors (7 ≥ 4 and 7 ≥ 5), while index 2 loses to index 3 and index 4 loses to index 3. Non-maximum suppression keeps the intersection — above threshold *and* local max — which is index 3 alone.

<svg role="img" aria-label="The magnitude ridge peaks at index 3; three pixels clear the threshold but only index 3 is a local maximum" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">gradient magnitude across the edge (dashed = threshold 3)</text>
  <line x1="20" y1="100" x2="280" y2="100" stroke="var(--grid)" stroke-width="1"/>
  <line x1="20" y1="64" x2="280" y2="64" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 3"/><text x="255" y="62" fill="var(--muted)" font-size="7">thresh</text>
  <rect x="30" y="100" width="20" height="0" fill="var(--grid)"/>
  <rect x="55" y="82" width="20" height="18" fill="var(--grid)"/>
  <rect x="80" y="64" width="20" height="36" fill="var(--s2)"/>
  <rect x="105" y="37" width="20" height="63" fill="var(--s1)"/><text x="108" y="32" fill="var(--s1)" font-size="7">peak</text>
  <rect x="130" y="55" width="20" height="45" fill="var(--s2)"/>
  <rect x="155" y="82" width="20" height="18" fill="var(--grid)"/>
  <rect x="180" y="100" width="20" height="0" fill="var(--grid)"/>
  <text x="30" y="112" fill="var(--muted)" font-size="7">0</text><text x="80" y="112" fill="var(--s2)" font-size="7">2</text><text x="105" y="112" fill="var(--s1)" font-size="7">3</text><text x="130" y="112" fill="var(--s2)" font-size="7">4</text>
  <text x="205" y="60" fill="var(--s2)" font-size="7">shoulders (2,4)</text><text x="205" y="72" fill="var(--muted)" font-size="7">clear thresh but</text><text x="205" y="84" fill="var(--muted)" font-size="7">not local max</text>
</svg>
^ Three bars rise above the dashed threshold, but only the tallest (index 3) is taller than both its neighbors; the two shoulder bars cleared the threshold yet lose to the peak, so suppression drops them.

## Build

Compare the two edges directly. Run `--thin`.

```text filename=--thin
THIN — thresholded edge vs non-maximum-suppressed edge
------------------------------------------------------------
  thresholded (thick):   pixels [2, 3, 4]  (3 wide)
  suppressed  (thin):    pixels [3]  (1 wide)
------------------------------------------------------------
  NMS keeps the peak at index 3 and drops the shoulders -- a one-pixel edge.
```

Thresholding returns a three-pixel-wide edge at indices 2, 3, 4; non-maximum suppression returns one pixel at index 3. Both agree the edge is *around* index 3 — the NMS pixel is a subset of the thresholded ones — but only NMS commits to *where*. That single-pixel answer is what a contour tracer, a length measurement, or a shape matcher needs: a thick edge makes those steps ambiguous (which of the three pixels is the boundary?) and biases any measurement by the ridge width. And note NMS did not lower the threshold or lose the edge — the peak at 7 is still there; it only removed the shoulders that were never the edge to begin with. This is the thinning stage inside the Canny detector, sitting between the gradient and the final hysteresis threshold.

<svg role="img" aria-label="Thresholding marks three pixels 2, 3, 4 as edge; non-maximum suppression marks only pixel 3" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">edge pixels (each cell one pixel)</text>
  <text x="8" y="34" fill="var(--s2)" font-size="8">threshold</text>
  <rect x="70" y="24" width="16" height="16" fill="none" stroke="var(--grid)"/><rect x="86" y="24" width="16" height="16" fill="var(--s2)"/><rect x="102" y="24" width="16" height="16" fill="var(--s2)"/><rect x="118" y="24" width="16" height="16" fill="var(--s2)"/><rect x="134" y="24" width="16" height="16" fill="none" stroke="var(--grid)"/>
  <text x="156" y="36" fill="var(--muted)" font-size="8">3 pixels wide (fuzzy)</text>
  <text x="8" y="66" fill="var(--s1)" font-size="8">NMS</text>
  <rect x="70" y="56" width="16" height="16" fill="none" stroke="var(--grid)"/><rect x="86" y="56" width="16" height="16" fill="none" stroke="var(--grid)"/><rect x="102" y="56" width="16" height="16" fill="var(--s1)"/><rect x="118" y="56" width="16" height="16" fill="none" stroke="var(--grid)"/><rect x="134" y="56" width="16" height="16" fill="none" stroke="var(--grid)"/>
  <text x="156" y="68" fill="var(--muted)" font-size="8">1 pixel (the crest)</text>
  <text x="70" y="92" fill="var(--muted)" font-size="8">same edge, but NMS commits to the single pixel where it actually is</text>
</svg>
^ Thresholding fills three cells; non-maximum suppression fills the one at the crest — the sharp, localized edge every downstream step assumes.

## Definition of done

The self-test pins it: thresholding is thick, NMS is one pixel at the peak, that pixel also cleared the threshold, and NMS is thinner.

```python filename=modules/generative-media/code/nms-inter-01/nms.py:94-107 COMPLETE
    threshold_is_thick = len(th) >= 3
    print("  thresholding gives a thick edge (>= 3 pixels) = %s (%d pixels %s)" % (threshold_is_thick, len(th), th))

    nms_is_one_pixel = len(nms) == 1
    print("  non-maximum suppression gives one pixel = %s (%s)" % (nms_is_one_pixel, nms))

    nms_keeps_the_peak = nms == [peak] and mag[peak] == max(mag)
    print("  the surviving pixel is the ridge's peak = %s (index %d, magnitude %d = max)" % (nms_keeps_the_peak, peak, mag[peak]))

    nms_subset_of_thresholded = set(nms) <= set(th)
    print("  every NMS pixel also cleared the threshold = %s" % nms_subset_of_thresholded)

    nms_thinner = len(nms) < len(th)
    print("  the NMS edge is thinner than the thresholded edge = %s (%d < %d)" % (nms_thinner, len(nms), len(th)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — thresholding gives a multi-pixel band; NMS gives one pixel, at the ridge's peak
--------------------------------------------------------------------------------------------------------
  thresholding gives a thick edge (>= 3 pixels) = True (3 pixels [2, 3, 4])
  non-maximum suppression gives one pixel = True ([3])
  the surviving pixel is the ridge's peak = True (index 3, magnitude 7 = max)
  every NMS pixel also cleared the threshold = True
  the NMS edge is thinner than the thresholded edge = True (1 < 3)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  threshold_is_thick=True  nms_is_one_pixel=True  nms_keeps_the_peak=True  nms_subset_of_thresholded=True  nms_thinner=True
```

**Done means the thinning is proven: thresholding at 3 keeps three pixels [2, 3, 4] while non-maximum suppression keeps only [3], the ridge's peak (magnitude 7, the max), which is a subset of the thresholded pixels — the edge localized without lowering the threshold.**

## Boss fight

The 1D ridge suppressed cleanly. Predict what makes non-maximum suppression harder in a real 2D image, and where the same idea reappears far from edge detection. It is tempting to think the along-the-profile comparison is trivial.

In 2D the hard part is choosing which neighbors to compare against, because a pixel must be a maximum *across* the edge, not along it. The gradient at each pixel has a direction, and NMS compares the pixel to its two neighbors along that direction — but the direction rarely points exactly at a neighboring pixel, so you either round it to the nearest of eight directions (fast, slightly jagged) or interpolate the magnitude between the two straddling neighbors (smoother, the Canny standard). Compare against the wrong neighbors — say the along-edge ones — and you suppress the edge itself, thinning it out of existence. So the correctness of NMS in 2D lives entirely in using the gradient direction to pick the comparison axis; the thinning is easy, getting the axis right is the work.

The same "keep only local maxima" idea reappears wherever a detector fires on a smear around a true location. Object detectors output many overlapping boxes around one object and use non-maximum suppression — keep the highest-confidence box, drop the overlapping lower ones — to collapse them to one detection; peak-finding in a Hough transform, keypoint detection, and audio onset detection all do the same. The pattern is general: a response function peaks at the true location but spreads around it, and thresholding keeps the spread, so you suppress everything that is not a local maximum of the response. Edge thinning is one instance of a detector-wide principle — a raw response tells you *whether*, and non-maximum suppression tells you *where*.

```python filename=modules/generative-media/code/nms-inter-01/nms.py:56-58 COMPLETE
def suppressed(mag, threshold):
    """Non-maximum suppression: keep pixels that are both above threshold and a local maximum."""
    return [i for i, m in enumerate(mag) if m >= threshold and is_local_max(mag, i)]
```

**Thin a thick gradient edge by keeping only pixels that are a local maximum of the magnitude along the gradient direction, not merely above a threshold — thresholding keeps the whole ridge, suppression keeps its crest — and remember the 2D correctness is all in comparing across the edge (via the gradient direction), while the same suppress-non-maxima idea localizes detections far beyond edges.**

## External resources

The Canny edge detector description in any computer-vision text — non-maximum suppression is its thinning stage, between gradient computation and hysteresis thresholding, with the gradient-direction neighbor selection spelled out.

The OpenCV `Canny` documentation and the object-detection literature on non-max suppression (NMS/soft-NMS for bounding boxes) — the same principle applied to edges and to overlapping detections.

The companion "combine both gradient directions" and "sharpen by adding back the detail a blur removed" modules — the gradient module produces the magnitude ridge this one thins, and both are stages of turning raw pixel differences into clean edges.
