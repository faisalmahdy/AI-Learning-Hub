---
id: sobel-inter-01
title: Combine both gradient directions — or an edge detector blind to one orientation misses half the edges
topic: generative-media
level: intermediate
status: ready
time: 19 min
summary: An edge is where brightness changes fast. The Sobel operator measures that change with two derivatives — gx (left-to-right) and gy (top-to-bottom). A vertical edge is a big left-to-right change, so gx is large and gy is zero; a horizontal edge is the mirror, gy large and gx zero. Build the detector on gx alone and you catch every vertical edge and miss every horizontal one, because a horizontal edge gives gx = 0 — and nothing about that zero tells you the edge is there. The fix is the gradient magnitude, √(gx²+gy²), the length of the gradient vector, which is large whenever brightness changes fast in any direction. On three 3×3 edges the vertical gives gx 40 / gy 0, the horizontal gx 0 / gy 40, the diagonal gx 30 / gy 30 — a gx-only detector scores the horizontal edge 0 while the magnitude scores all three above 40.
eli5: To notice a line you have to look for changes across it. If you only check for changes going left-to-right, you will spot a fence post standing upright but walk right past a rope lying flat — because along a flat rope nothing changes left-to-right. You have to check up-and-down too, then combine both, so a line in any direction gets noticed.
---

## Why this module

An edge detector that measures change in only one direction is not a weak detector — it is blind to every edge that runs the wrong way.

Edges are where brightness changes sharply, and change has a direction. The Sobel operator estimates it with two derivatives: gx, how fast brightness changes horizontally, and gy, how fast it changes vertically. A vertical edge — dark on the left, bright on the right — is a large horizontal change, so gx is big; but scan top to bottom along that edge and nothing changes, so gy is zero. A horizontal edge is the exact mirror. If you decide an edge is present by looking at gx alone, every horizontal edge in the image reports gx = 0 and vanishes, and the zero looks identical to flat, featureless region.

**A single-direction gradient is orientation-blind: it cannot distinguish an edge it is aligned against from no edge at all.**

The fix is to combine the two derivatives into the gradient magnitude — √(gx² + gy²), the length of the gradient vector. It is large whenever brightness changes fast in any direction, so vertical, horizontal, and diagonal edges all register. This module computes both on three differently-oriented edges and shows the gx-only detector drop the horizontal one.

## Concepts

The **Sobel kernels** are two 3×3 filters. The gx kernel differences the left column against the right (weighting the center row double), estimating the horizontal derivative; the gy kernel differences the top row against the bottom, estimating the vertical derivative.

Applying a kernel is a **convolution**: multiply each image pixel by the aligned kernel weight and sum. Here we evaluate it at the center of each 3×3 image, giving one gx and one gy response per image.

The **gradient vector** is (gx, gy) — it points in the direction of fastest brightness increase, and its length is how fast. A vertical edge produces a gradient pointing horizontally: gx large, gy near zero. A horizontal edge produces one pointing vertically.

The **gradient magnitude** is that vector's length, √(gx² + gy²). It discards the direction and keeps the strength, which is what an edge detector wants: it fires for a strong change regardless of orientation. This is why the magnitude catches a diagonal edge too — the change splits across gx and gy, and the hypotenuse combines them.

The trap is testing an edge detector only on the orientation you happened to draw. A gx-only detector passes every test built from vertical edges and fails silently on horizontal ones — and the failure is a zero, indistinguishable from a blank region, so it never announces itself.

**The gradient magnitude answers "how much does brightness change here," which is orientation-free; a single derivative answers "how much does it change in this one direction," which is not.**

The magnitude is the hypotenuse of the two derivatives — squaring both before adding is what makes it blind to direction and immune to sign cancellation.

<svg role="img" aria-label="A right triangle with legs gx and gy and hypotenuse the gradient magnitude" viewBox="0 0 300 110" width="300" height="110">
  <line x1="60" y1="85" x2="200" y2="85" stroke="var(--s1)" stroke-width="2"/>
  <text x="115" y="100" fill="var(--s1)" font-size="9">gx (horizontal)</text>
  <line x1="200" y1="85" x2="200" y2="25" stroke="var(--s2)" stroke-width="2"/>
  <text x="205" y="58" fill="var(--s2)" font-size="9">gy (vertical)</text>
  <line x1="60" y1="85" x2="200" y2="25" stroke="var(--ink)" stroke-width="2"/>
  <text x="95" y="45" fill="var(--ink)" font-size="9">√(gx²+gy²)</text>
  <rect x="190" y="75" width="10" height="10" fill="none" stroke="var(--muted)" stroke-width="0.8"/>
</svg>
^ The gradient magnitude is the length of the (gx, gy) vector — the hypotenuse — so it grows with change in any direction and never cancels the way gx + gy could.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/sobel-inter-01/sobel.py

The fixture is three 3×3 images, one edge each: vertical, horizontal, diagonal.

```json filename=modules/generative-media/code/sobel-inter-01/edges.json:1-9 COMPLETE
{
  "_meta": "Three tiny 3x3 grayscale images, each a single edge in a different orientation: a vertical edge (dark left, bright right), a horizontal edge (dark top, bright bottom), and a diagonal edge. The Sobel operator estimates the brightness gradient at the center pixel: gx (horizontal derivative) and gy (vertical derivative). The question: which edges does a single-direction gradient catch, and which does it miss?",
  "images": {
    "vertical":   [[0, 0, 10], [0, 0, 10], [0, 0, 10]],
    "horizontal": [[0, 0, 0], [0, 0, 0], [10, 10, 10]],
    "diagonal":   [[0, 0, 10], [0, 10, 10], [10, 10, 10]]
  }
}
```

The two derivatives are the two Sobel kernels convolved at the center; the magnitude is their hypotenuse.

```python filename=modules/generative-media/code/sobel-inter-01/sobel.py:45-60 COMPLETE
def convolve_center(img, kernel):
    """Apply a 3x3 kernel at the center of a 3x3 image (one response)."""
    return sum(img[r][c] * kernel[r][c] for r in range(3) for c in range(3))


def gx(img):
    return convolve_center(img, GX_KERNEL)


def gy(img):
    return convolve_center(img, GY_KERNEL)


def magnitude(img):
    """The gradient magnitude: length of the (gx, gy) vector -- large for an edge in any direction."""
    return math.hypot(gx(img), gy(img))
```

The two kernels are the operator itself: gx differences left against right, gy top against bottom.

```python filename=modules/generative-media/code/sobel-inter-01/sobel.py:37-38 COMPLETE
GX_KERNEL = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
GY_KERNEL = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]
```

Run `--gradients` and read gx, gy, and magnitude for each edge.

```text filename=--gradients
GRADIENTS — Sobel gx, gy, and magnitude at the center of each edge
----------------------------------------------------------
  edge          gx     gy    magnitude
  vertical       40      0      40.00
  horizontal      0     40      40.00
  diagonal       30     30      42.43
----------------------------------------------------------
  a vertical edge lives in gx, a horizontal edge in gy.
```

The vertical edge puts all its change in gx (40) and none in gy; the horizontal edge does the reverse (gy 40, gx 0); the diagonal splits it (30 and 30). The magnitude is 40, 40, and 42.43 — every edge registers strongly, whichever way it runs.

<svg role="img" aria-label="Gradient vectors: vertical edge points along gx, horizontal along gy, diagonal splits both, all with similar magnitude" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="15" fill="var(--muted)" font-size="8">gradient vector (gx, gy) per edge</text>
  <line x1="50" y1="70" x2="50" y2="110" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="90" x2="90" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <line x1="50" y1="90" x2="85" y2="90" stroke="var(--s1)" stroke-width="2"/>
  <text x="35" y="125" fill="var(--muted)" font-size="8">vertical (gx)</text>
  <line x1="150" y1="70" x2="150" y2="110" stroke="var(--grid)" stroke-width="1"/>
  <line x1="130" y1="90" x2="190" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <line x1="150" y1="90" x2="150" y2="55" stroke="var(--s2)" stroke-width="2"/>
  <text x="128" y="125" fill="var(--muted)" font-size="8">horizontal (gy)</text>
  <line x1="250" y1="70" x2="250" y2="110" stroke="var(--grid)" stroke-width="1"/>
  <line x1="230" y1="90" x2="290" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <line x1="250" y1="90" x2="278" y2="62" stroke="var(--ink)" stroke-width="2"/>
  <text x="238" y="125" fill="var(--muted)" font-size="8">diagonal (both)</text>
</svg>
^ Each edge's gradient points a different way — along gx, along gy, or between — but all three vectors have nearly the same length, which is what the magnitude reads.

## Build

Now build a detector two ways and run `--detect`: one thresholds gx alone, one thresholds the magnitude.

```text filename=--detect
DETECT — a gx-only detector vs the magnitude (threshold 20)
----------------------------------------------------------
  edge          gx-only          magnitude
  vertical    EDGE (40)        edge (40.00)
  horizontal  missed (0)       edge (40.00)
  diagonal    EDGE (30)        edge (42.43)
----------------------------------------------------------
  gx-only misses the horizontal edge; the magnitude catches all three.
```

The gx-only detector fires on the vertical and diagonal edges and reports the horizontal edge as a flat 0 — missed. It is not a weak signal below threshold; it is genuinely zero, the same number a blank patch would give. The magnitude detector fires on all three. The bug is not the threshold; it is that gx cannot represent a horizontal edge at all.

<svg role="img" aria-label="Detection table: gx-only catches vertical and diagonal but misses horizontal; magnitude catches all three" viewBox="0 0 300 120" width="300" height="120">
  <text x="95" y="18" fill="var(--muted)" font-size="8">gx-only</text>
  <text x="200" y="18" fill="var(--muted)" font-size="8">magnitude</text>
  <text x="10" y="42" fill="var(--muted)" font-size="8">vertical</text>
  <rect x="90" y="32" width="50" height="12" fill="var(--s2)"/>
  <rect x="195" y="32" width="50" height="12" fill="var(--s2)"/>
  <text x="10" y="67" fill="var(--muted)" font-size="8">horizontal</text>
  <rect x="90" y="57" width="50" height="12" fill="none" stroke="var(--s1)" stroke-width="1" stroke-dasharray="2 2"/>
  <text x="98" y="67" fill="var(--s1)" font-size="7">missed</text>
  <rect x="195" y="57" width="50" height="12" fill="var(--s2)"/>
  <text x="10" y="92" fill="var(--muted)" font-size="8">diagonal</text>
  <rect x="90" y="82" width="50" height="12" fill="var(--s2)"/>
  <rect x="195" y="82" width="50" height="12" fill="var(--s2)"/>
  <text x="10" y="112" fill="var(--muted)" font-size="8">the gx-only gap is a whole orientation, not a weak signal</text>
</svg>
^ The gx-only detector has a hole exactly the shape of horizontal edges; the magnitude detector fills it because it reads change in any direction.

## Definition of done

The self-test pins the blindness and the fix: gx detects vertical, gx misses horizontal, gy detects horizontal, the magnitude detects every orientation, and the magnitude equals √(gx²+gy²).

```python filename=modules/generative-media/code/sobel-inter-01/sobel.py:95-107 COMPLETE
    gx_detects_vertical = abs(gx(imgs["vertical"])) >= thr
    print("  gx detects the vertical edge = %s (gx %.0f)" % (gx_detects_vertical, gx(imgs["vertical"])))

    gx_misses_horizontal = abs(gx(imgs["horizontal"])) < thr
    print("  gx misses the horizontal edge = %s (gx %.0f)" % (gx_misses_horizontal, gx(imgs["horizontal"])))

    gy_detects_horizontal = abs(gy(imgs["horizontal"])) >= thr
    print("  gy detects the horizontal edge = %s (gy %.0f)" % (gy_detects_horizontal, gy(imgs["horizontal"])))

    magnitude_detects_all = all(magnitude(imgs[name]) >= thr for name in imgs)
    print("  the magnitude detects every orientation = %s (min %.2f)" % (magnitude_detects_all, min(magnitude(imgs[name]) for name in imgs)))

    magnitude_is_hypot = all(abs(magnitude(imgs[name]) - math.sqrt(gx(imgs[name]) ** 2 + gy(imgs[name]) ** 2)) < 1e-9 for name in imgs)
    print("  the magnitude equals sqrt(gx^2 + gy^2) = %s" % magnitude_is_hypot)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — gx alone misses the horizontal edge; the magnitude catches every orientation
----------------------------------------------------------------------------------------------------
  gx detects the vertical edge = True (gx 40)
  gx misses the horizontal edge = True (gx 0)
  gy detects the horizontal edge = True (gy 40)
  the magnitude detects every orientation = True (min 40.00)
  the magnitude equals sqrt(gx^2 + gy^2) = True
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  gx_detects_vertical=True  gx_misses_horizontal=True  gy_detects_horizontal=True  magnitude_detects_all=True  magnitude_is_hypot=True
```

**Done means the blindness is exact, not approximate: the horizontal edge gives gx = 0 — a true zero indistinguishable from flat — while its magnitude is 40, so the fix recovers a signal the single derivative could not represent.**

## Boss fight

The magnitude catches every orientation. Predict what you lose by collapsing (gx, gy) into that single number. It is tempting to think the magnitude is strictly better and the derivatives are now redundant.

You lose the direction, and for many tasks the direction is the point. The gradient's angle — atan2(gy, gx) — tells you which way the edge runs, and algorithms built on Sobel need it: Canny edge detection uses the direction for non-maximum suppression (thinning thick edges to one-pixel lines), and orientation histograms (HOG) are literally histograms of these angles. The magnitude answers "is there an edge and how strong"; the angle answers "which way does it run." Keep both — the magnitude to find edges, the angle to describe them.

The mirror-image mistake is summing the two derivatives instead of taking the hypotenuse — using gx + gy as the strength. That is wrong because the derivatives are signed and can cancel: a diagonal edge with gx = 30 and gy = −30 would sum to 0 and vanish, exactly the bug you were fixing. The magnitude squares before adding, so signs cannot cancel; that is why it is √(gx²+gy²) and not gx + gy.

```python filename=modules/generative-media/code/sobel-inter-01/sobel.py:58-60 COMPLETE
def magnitude(img):
    """The gradient magnitude: length of the (gx, gy) vector -- large for an edge in any direction."""
    return math.hypot(gx(img), gy(img))
```

**Detect edges by the gradient magnitude √(gx²+gy²) so no orientation is missed and no signs cancel — and keep the angle atan2(gy, gx) when you need to know which way the edge runs.**

## External resources

Sobel and Feldman's operator, covered in Gonzalez and Woods, "Digital Image Processing", the image-sharpening / gradient chapter — the kernels, the magnitude, and the direction, derived from the image gradient.

Canny, "A Computational Approach to Edge Detection" (1986) — the classic pipeline that consumes both the Sobel magnitude and direction, showing why keeping the angle matters (the boss fight).

The OpenCV tutorials on `Sobel` and `Canny` — the production functions, their `dx`/`dy` arguments, and how the magnitude and direction are combined into a thinned edge map.
