---
id: coverage-inter-01
title: Rasterize an edge by pixel coverage, not a center-inside test — a hard in/out raster stair-steps the edge and misestimates the area
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Turning a continuous shape into pixels forces a yes/no decision at every pixel the edge crosses, and the naive decision tests one point — the pixel's center: center inside means the pixel is fully on (1), outside means fully off (0). That throws away the partial information at the edge, where a pixel is neither fully inside nor fully outside. The visible cost is jaggies: a slanted edge forced to be all-or-nothing per pixel renders as a staircase of hard steps. The measurable cost is area: each pixel counts as a whole 0 or 1, so the rendered area jumps a full pixel at a time and the total ink misestimates the true covered area. Coverage-based anti-aliasing asks instead how much of each pixel the shape covers, giving a pixel the edge cuts a fractional value equal to the covered fraction — so the edge becomes a smooth ramp of partial pixels, and (the property that makes it correct, not just prettier) the summed coverage equals the true covered area. The fraction can be computed analytically or estimated by supersampling — testing many sub-points per pixel and taking the fraction inside; a center test is just supersampling with a single sub-point, which is why it only ever returns 0 or 1. On a fixture where a straight edge crosses a 6-by-6 grid, the center test renders every pixel as 0 or 1 with an ink total of 10.0, while the coverage raster has nine fractional edge pixels and totals 9.7969 against a true area of 9.8000.
eli5: Imagine coloring in a shape on graph paper, but the rule is each square must be fully colored or fully blank — you decide by looking only at the tiny dot in the middle of each square. A slanted edge then comes out as an ugly staircase, because each square is all-or-nothing, and you have colored a bit too much or too little compared to the real shape. A better rule: for each square the edge passes through, color it in proportion to how much of that square the shape actually covers — a square that is one-fifth inside gets a light shade, one that is four-fifths inside gets a dark shade. Now the edge looks smooth instead of jagged, and the total amount of color matches the real shape, because you counted the partial squares honestly instead of rounding each one to all or nothing.
---

## Why this module

Every time a shape becomes pixels — a font glyph, a vector icon, the edge of a rendered object — the renderer has to decide, for each pixel, whether it belongs to the shape. In the interior and the exterior the answer is obvious. At the boundary it is not, because the boundary runs through pixels, and a pixel the edge passes through is part shape and part background.

The quick decision is to test the pixel's center: if the center falls inside the shape, the pixel is on; otherwise off. It is one comparison per pixel and it is exact away from the edge. The problem is entirely at the edge, where reducing "partly covered" to a single inside-or-out answer discards the one piece of information that matters there — how much of the pixel the shape actually fills.

Discarding it produces the classic failure two ways. Visually, a slanted or curved edge turns into a staircase of hard steps — jaggies — because each pixel snaps to fully on or fully off with nothing in between. Numerically, the rendered area of the shape is wrong: every boundary pixel is counted as a whole pixel or none, so the total jumps by a full pixel as the edge shifts, over- or under-stating the true area the shape covers.

**A center-inside test reduces every pixel to fully on or fully off, so it discards the partial coverage at the edge — producing a jagged staircase and an area that misestimates the shape by counting each boundary pixel as a whole pixel or none.**

## Concepts

The fix is to answer the question the edge actually poses: not "is this pixel inside" but "how much of this pixel is inside." That fraction — the coverage — is a number between 0 and 1, and using it as the pixel's value turns the hard 0-or-1 step at the boundary into a smooth ramp. A pixel one-fifth covered is drawn at 0.2, four-fifths covered at 0.8, and the eye reads the ramp of partial pixels as a clean straight edge instead of a staircase.

<svg role="img" aria-label="A pixel grid with a diagonal edge. On the left, a binary raster fills whole squares below the edge, producing a jagged staircase boundary. On the right, a coverage raster shades the boundary squares partially, producing a smooth edge." viewBox="0 0 440 160">
<text x="105" y="14" fill="var(--muted)" font-size="9" text-anchor="middle">center test: staircase</text>
<rect x="30" y="24" width="20" height="20" fill="var(--s2)"/><rect x="50" y="24" width="20" height="20" fill="var(--s2)"/><rect x="70" y="24" width="20" height="20" fill="var(--panel)" stroke="var(--line)"/>
<rect x="30" y="44" width="20" height="20" fill="var(--s2)"/><rect x="50" y="44" width="20" height="20" fill="var(--panel)" stroke="var(--line)"/><rect x="70" y="44" width="20" height="20" fill="var(--panel)" stroke="var(--line)"/>
<rect x="30" y="64" width="20" height="20" fill="var(--panel)" stroke="var(--line)"/><rect x="50" y="64" width="20" height="20" fill="var(--panel)" stroke="var(--line)"/><rect x="70" y="64" width="20" height="20" fill="var(--panel)" stroke="var(--line)"/>
<path d="M30 100 L 50 80 L 70 60 L 90 40" fill="none" stroke="var(--ink)"/>
<text x="105" y="120" fill="var(--muted)" font-size="8" text-anchor="middle">hard steps</text>
<text x="335" y="14" fill="var(--muted)" font-size="9" text-anchor="middle">coverage: smooth ramp</text>
<rect x="260" y="24" width="20" height="20" fill="var(--s2)"/><rect x="280" y="24" width="20" height="20" fill="var(--s2)"/><rect x="300" y="24" width="20" height="20" fill="var(--s1)" opacity="0.35"/>
<rect x="260" y="44" width="20" height="20" fill="var(--s2)"/><rect x="280" y="44" width="20" height="20" fill="var(--s1)" opacity="0.5"/><rect x="300" y="44" width="20" height="20" fill="var(--s1)" opacity="0.15"/>
<rect x="260" y="64" width="20" height="20" fill="var(--s1)" opacity="0.5"/><rect x="280" y="64" width="20" height="20" fill="var(--s1)" opacity="0.15"/><rect x="300" y="64" width="20" height="20" fill="var(--panel)" stroke="var(--line)"/>
<path d="M260 100 L 320 40" fill="none" stroke="var(--ink)"/>
<text x="335" y="120" fill="var(--muted)" font-size="8" text-anchor="middle">partial pixels</text>
</svg>
^ The center test fills whole squares and leaves a jagged staircase along the edge; coverage shades the boundary squares by how much the shape fills them, and the partial pixels read as a smooth edge.

The reason coverage is correct and not merely prettier is that it conserves area. Each pixel now contributes exactly the amount of the shape inside it, so summing the pixel values gives the shape's true area — a partial pixel adds its real fraction instead of a rounded whole. The center test cannot conserve area because it only ever adds 0 or 1 per pixel, so its total is the count of pixels whose centers happen to be inside, which drifts from the true area as the edge moves.

<svg role="img" aria-label="One boundary pixel shown two ways. Left: a single center dot, either inside or outside, giving 0 or 1. Right: a grid of sub-sample dots, some inside the shape and some outside, giving the fraction inside as the coverage." viewBox="0 0 440 130">
<text x="105" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">center test: 1 sub-point</text>
<rect x="60" y="30" width="80" height="80" fill="var(--panel)" stroke="var(--line)"/>
<path d="M60 90 L 140 50" fill="none" stroke="var(--ink)"/>
<circle cx="100" cy="70" r="4" fill="var(--s2)"/>
<text x="100" y="124" fill="var(--muted)" font-size="8" text-anchor="middle">one dot -&gt; 0 or 1</text>
<text x="335" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">supersample: many sub-points</text>
<rect x="290" y="30" width="80" height="80" fill="var(--panel)" stroke="var(--line)"/>
<path d="M290 90 L 370 50" fill="none" stroke="var(--ink)"/>
<circle cx="303" cy="43" r="2" fill="var(--muted)"/><circle cx="323" cy="43" r="2" fill="var(--muted)"/><circle cx="343" cy="43" r="2" fill="var(--muted)"/><circle cx="357" cy="43" r="2" fill="var(--muted)"/>
<circle cx="303" cy="63" r="2" fill="var(--muted)"/><circle cx="323" cy="63" r="2" fill="var(--muted)"/><circle cx="343" cy="63" r="2" fill="var(--s1)"/>
<circle cx="303" cy="83" r="2" fill="var(--s1)"/><circle cx="323" cy="83" r="2" fill="var(--s1)"/><circle cx="343" cy="83" r="2" fill="var(--s1)"/>
<circle cx="303" cy="97" r="2" fill="var(--s1)"/><circle cx="323" cy="97" r="2" fill="var(--s1)"/><circle cx="343" cy="97" r="2" fill="var(--s1)"/>
<text x="330" y="124" fill="var(--muted)" font-size="8" text-anchor="middle">fraction inside -&gt; coverage</text>
</svg>
^ A center test samples one point and can only answer 0 or 1; supersampling tests many sub-points and returns the fraction inside — the center test is just supersampling with a single sub-point.

That reframing gives the general way to compute coverage: supersampling. Spread many sub-sample points across the pixel, test each one for inside-ness, and take the fraction that land inside as the coverage. More sub-points give a finer estimate; simple shapes admit an exact analytic coverage, but supersampling works for any shape. And it exposes what the center test really is — supersampling with exactly one sub-point, at the center — which is precisely why it can only return 0 or 1 and can never represent a partial pixel.

**Coverage is the fraction of a pixel the shape fills; using it as the pixel value ramps the edge smoothly and conserves the shape's true area, and it is computed by supersampling — of which the center test is the degenerate one-sample case that can only answer 0 or 1.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/coverage-inter-01. The fixture is a small pixel grid, a straight edge given as a line, and a supersample count.

```json filename=modules/generative-media/code/coverage-inter-01/coverage.json:3-8 COMPLETE
  "grid_w": 6,
  "grid_h": 6,
  "a": 0.9,
  "b": 1.0,
  "c": 4.2,
  "supersample": 8
```

The shape is a half-plane, so a point is inside when it is on one side of the line.

```python filename=modules/generative-media/code/coverage-inter-01/coverage.py:32-34 COMPLETE
def inside(x, y, data):
    """The shape is the half-plane a*x + b*y < c."""
    return data["a"] * x + data["b"] * y < data["c"]
```

The center test asks only about the pixel's center point.

```python filename=modules/generative-media/code/coverage-inter-01/coverage.py:37-39 COMPLETE
def binary_pixel(i, j, data):
    """Center-inside test: 1 if the pixel center is inside, else 0."""
    return 1.0 if inside(i + 0.5, j + 0.5, data) else 0.0
```

Coverage supersamples an n-by-n grid of sub-points inside the pixel and returns the fraction inside.

```python filename=modules/generative-media/code/coverage-inter-01/coverage.py:42-51 COMPLETE
def coverage_pixel(i, j, data, n):
    """Fraction of the pixel covered, estimated by an n-by-n grid of sub-samples."""
    hits = 0
    for sy in range(n):
        for sx in range(n):
            x = i + (sx + 0.5) / n
            y = j + (sy + 0.5) / n
            if inside(x, y, data):
                hits += 1
    return hits / (n * n)
```

Before running it, predict: the center test will produce a grid of pure 0s and 1s with a jagged boundary, and its ink total will be a whole number. Run `--binary`:

```text filename=coverage.py --binary
BINARY — center-inside test (every pixel 0 or 1)
----------------------------------------
  1.00 1.00 1.00 1.00 0.00 0.00
  1.00 1.00 1.00 0.00 0.00 0.00
  1.00 1.00 0.00 0.00 0.00 0.00
  1.00 0.00 0.00 0.00 0.00 0.00
  0.00 0.00 0.00 0.00 0.00 0.00
  0.00 0.00 0.00 0.00 0.00 0.00
```

The prediction holds. Every value is 0.00 or 1.00, and the boundary between them is a staircase — the number of filled pixels per row drops 4, 3, 2, 1 in hard steps. The ink total is exactly 10.00, a whole number, because each pixel contributed a whole 0 or 1. That staircase is the jaggies, and the 10.00 is a rounded area.

Now the coverage raster on the same edge. Run `--coverage`:

```text filename=coverage.py --coverage
COVERAGE — fraction of each pixel covered (supersample 8)
----------------------------------------
  1.00 1.00 1.00 0.91 0.20 0.00
  1.00 1.00 0.84 0.16 0.00 0.00
  1.00 0.80 0.09 0.00 0.00 0.00
  0.73 0.05 0.00 0.00 0.00 0.00
  0.02 0.00 0.00 0.00 0.00 0.00
  0.00 0.00 0.00 0.00 0.00 0.00
```

Now the boundary is a diagonal band of fractional values — 0.91, 0.20, 0.84, 0.16, 0.80, 0.09, 0.73, 0.05 — each the amount of that pixel the shape fills. Where the center test jumped from 1.00 to 0.00 in one step, coverage passes through the in-between values, which is exactly what makes the rendered edge look smooth. And the ink total is 9.7969 against a true area of 9.8000 — the partial pixels summed to the real area, within the supersampling error. The center test's 10.00 was off by 0.2; coverage is off by 0.003.

<svg role="img" aria-label="A bar comparison of rendered area. The true area is 9.80. The center test totals 10.00 (over by 0.20). The coverage total is 9.7969 (off by 0.0032)." viewBox="0 0 440 120">
<text x="20" y="16" fill="var(--muted)" font-size="9">rendered ink total vs true area (9.80)</text>
<line x1="120" y1="30" x2="120" y2="100" stroke="var(--s1)" stroke-dasharray="4 3"/>
<text x="120" y="112" fill="var(--s1)" font-size="8" text-anchor="middle">true 9.80</text>
<text x="60" y="46" fill="var(--ink)" font-size="8" text-anchor="end">center</text>
<rect x="65" y="38" width="70" height="14" fill="var(--s2)"/><text x="145" y="49" fill="var(--s2)" font-size="8">10.00 (+0.20)</text>
<text x="60" y="76" fill="var(--ink)" font-size="8" text-anchor="end">coverage</text>
<rect x="65" y="68" width="55" height="14" fill="var(--s1)"/><text x="145" y="79" fill="var(--s1)" font-size="8">9.7969 (+0.003)</text>
</svg>
^ The center test's whole-pixel counting overshoots the true area by 0.20; the coverage total lands within 0.003 of it, because partial pixels are counted at their real fraction.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the center test makes every pixel 0 or 1, that the coverage raster has partial edge pixels, that the coverage total matches the true area, that the center-test total misestimates the area by more, and that coverage ramps the edge where the center test steps hard.

```python filename=modules/generative-media/code/coverage-inter-01/coverage.py:104-122 COMPLETE
    flat = [v for row in b for v in row]
    binary_all_or_nothing = all(v == 0.0 or v == 1.0 for v in flat)
    print("  the center test makes every pixel 0 or 1 = %s" % binary_all_or_nothing)

    cflat = [v for row in cov for v in row]
    coverage_has_partial = any(0.0 < v < 1.0 for v in cflat)
    print("  the coverage raster has partial (edge) pixels = %s (%d of %d)" % (coverage_has_partial, sum(1 for v in cflat if 0.0 < v < 1.0), len(cflat)))

    coverage_area_err = abs(total(cov) - area)
    binary_area_err = abs(total(b) - area)

    coverage_matches_area = coverage_area_err < 0.05
    print("  the coverage total matches the true area = %s (err %.4f)" % (coverage_matches_area, coverage_area_err))

    binary_misestimates_area = binary_area_err > coverage_area_err
    print("  the center-test total misestimates the area by more = %s (%.4f vs %.4f)" % (binary_misestimates_area, binary_area_err, coverage_area_err))

    # the coverage edge has intermediate values where the center test has only a hard 0->1 step
    edge_is_ramp = coverage_has_partial and not any(0.0 < v < 1.0 for v in flat)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the coverage total ever drifted from the true area or the center test ever produced a partial pixel:

```text filename=coverage.py --check
SELF-TEST — the center test is all-or-nothing and misestimates the area; coverage has partial pixels and matches the true area
----------------------------------------------------------------------------------------------------------------
  the center test makes every pixel 0 or 1 = True
  the coverage raster has partial (edge) pixels = True (9 of 36)
  the coverage total matches the true area = True (err 0.0032)
  the center-test total misestimates the area by more = True (0.2000 vs 0.0032)
  coverage ramps the edge where the center test steps hard = True
```

**The self-test pins area conservation, not just appearance: coverage's total is within 0.05 of the true area while the center test is off by more — so a pass certifies coverage is correct in the measurable sense (it renders the right amount of the shape), not merely that it looks smoother.**

## Definition of done

You can explain why a center-inside test discards the information that matters at a shape's boundary.
You can name the two costs of a hard raster — jaggies and a misestimated area — and why they share a cause.
You can define pixel coverage and explain why using it as the pixel value both smooths the edge and conserves area.
You can describe supersampling as the general way to estimate coverage and explain why the center test is its one-sample degenerate case.
You can predict that a coverage raster's ink total matches the true area while a binary raster's does not.

## Boss fight

Suppose you supersample to get coverage, then composite the anti-aliased shape onto a background. Reason about what the coverage value has to be treated as. A pixel's coverage is exactly its alpha — the fraction of the pixel the shape occupies — so an anti-aliased edge is a partial-alpha edge, and compositing it must obey the alpha rules: blend in linear light and premultiply, or the edge fringes and darkens (the gamma and premultiplied-alpha modules). This is why coverage anti-aliasing and alpha compositing are the same machinery seen twice: the edge pixel at coverage 0.3 is a pixel that is 30% shape and 70% background, and painting it means mixing the shape's color with the background in that ratio, correctly. Get the coverage right but composite it naively and you have traded jaggies for colored halos.

Now the trap that makes supersampled coverage subtly wrong: correlated samples and the gamma of the value itself. First, a regular grid of sub-samples can still alias against regular patterns (a thin line, a fine texture) because the samples are correlated — which is why real anti-aliasing uses rotated or stochastic sample patterns (rotated-grid or jittered supersampling) that decorrelate the sampling, and why hardware MSAA uses carefully chosen non-grid sample positions. Second, coverage is a linear fraction of area, so it must be applied in linear light: if you compute coverage 0.5 and write it directly into a gamma-encoded 8-bit channel, the pixel is too dark, because 0.5 coverage should be 50% of the linear intensity, not 50% of the encoded code value — the same linearize-before-you-average rule the gamma module makes for downsampling applies to blending an edge. So correct anti-aliasing is coverage computed with a good sample pattern and applied in linear light, then composited with premultiplied alpha; coverage is necessary but only one of the three disciplines.

**An edge pixel's coverage is its alpha, so an anti-aliased edge must be composited with the linear-light and premultiplied-alpha rules or it fringes; and supersampled coverage needs a decorrelated (rotated or jittered) sample pattern and must be applied in linear light, or it aliases against fine patterns and comes out too dark.**

## External resources

Any computer-graphics text's treatment of rasterization and anti-aliasing (for example, the coverage and sampling chapters of Foley/van Dam or Pharr's Physically Based Rendering) covers area coverage, supersampling, and sample patterns.
The documentation for MSAA and rotated-grid / stochastic supersampling explains why sample positions are chosen off the regular grid, and font rasterizers (FreeType, and signed-distance-field text) show analytic and distance-based coverage in practice.
The topic's own modules on band-limiting before you decimate (aliasing), premultiplied alpha, and blending in linear light cover the neighboring sampling and compositing disciplines that a correct anti-aliased edge must combine with coverage.
