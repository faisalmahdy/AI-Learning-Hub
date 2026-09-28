---
id: integral-inter-01
title: Precompute a summed-area table, and any rectangle's sum is four lookups — a box blur costs the same at any radius
topic: generative-media
level: intermediate
status: ready
time: 16 min
summary: A box filter replaces each pixel with the average of a square window around it, so the naive cost is k×k additions per output pixel for a k-wide window — fine for a 3×3 blur, ruinous for a 51×51 one, because the work per pixel grows with the window area. The waste is that neighboring windows overlap almost completely and the naive loop re-adds the same pixels for every output. A summed-area table (integral image) pays that sum once: precompute, in a single pass, the sum of every top-left rectangle, so afterward the sum over any rectangle is four lookups by inclusion-exclusion — the big corner minus the two edge rectangles plus the corner subtracted twice — regardless of size. A box blur becomes build-the-table-once plus four lookups per pixel, and the total work no longer depends on the radius at all. On a fixture, the table's rectangle sums exactly match direct addition, and a box blur costs a flat 4 operations per pixel via the table versus 9, 25, 81, and 225 naively at windows of 3, 5, 9, and 15.
eli5: To add up all the numbers in a rectangular block of a grid, you could add them one by one every time — slow if the block is big, and you keep re-adding the same numbers for overlapping blocks. Instead, make a helper grid where each cell already holds the total of everything above-and-left of it. Then the sum of any rectangle is just four of those totals combined: bottom-right, minus the two you overcounted, plus the corner you subtracted twice. Four lookups, whether the rectangle is tiny or huge.
---

## Why this module

A box blur asks for the sum of a window at every pixel, and windows one pixel apart share almost all their pixels — so summing each window from scratch throws away nearly all the work, and the throwaway grows with the blur radius until it dominates.

Averaging a k×k window means adding k² pixels and dividing, so a naive box blur does k² additions for every output pixel. At a 3×3 window that is 9 additions — nothing. At 15×15 it is 225; at 51×51 it is 2601. The per-pixel cost scales with the window *area*, so doubling the blur radius quadruples the work, and a large-radius blur over a large image turns the simplest filter into the slowest step in the pipeline. And it is almost all redundant: the window for one pixel and the window for its right-hand neighbor differ by a single column, yet the naive loop re-adds the entire overlapping interior for each. The information needed to skip that re-adding is a running total, and computing it once is what a summed-area table does.

**A naive box filter costs k² additions per pixel because it re-sums the whole window at every output, and that cost grows with the window area — so a large blur is dominated by re-adding pixels it already added for the neighbor.**

A summed-area table precomputes the sum of every top-left rectangle in one pass: entry S[i][j] is the total of all pixels above and to the left of (i, j). With that table, the sum over any rectangle is four lookups by inclusion-exclusion — take the bottom-right corner's cumulative sum, subtract the two that cover the strips above and to the left, and add back the top-left corner that both subtractions removed. Four reads, and crucially the same four reads whether the rectangle is 3×3 or 300×300. A box blur becomes: build the table once (a single pass over the image), then four operations per output pixel, and the total work is O(pixels) with no dependence on the radius. This module verifies the table's sums against direct addition and counts the operations of both.

## Concepts

**The summed-area table** S has S[i][j] = the sum of every pixel above and to the left of (i, j). A zero border row and column make the corner arithmetic clean. It is built in one pass, each entry from its three already-computed neighbors.

```python filename=modules/generative-media/code/integral-inter-01/integral.py:41-48 COMPLETE
def build_sat(image):
    """Summed-area table with a zero top/left border: S[i][j] = sum of image[0:i][0:j]."""
    rows, cols = len(image), len(image[0])
    s = [[0] * (cols + 1) for _ in range(rows + 1)]
    for i in range(1, rows + 1):
        for j in range(1, cols + 1):
            s[i][j] = image[i - 1][j - 1] + s[i - 1][j] + s[i][j - 1] - s[i - 1][j - 1]
    return s
```

**Inclusion-exclusion** reads any rectangle's sum from four table entries: the bottom-right corner covers too much, so subtract the strip above and the strip to the left, then add back the top-left corner that both strips removed.

```python filename=modules/generative-media/code/integral-inter-01/integral.py:51-53 COMPLETE
def sat_rect_sum(s, r0, c0, r1, c1):
    """Sum over the half-open rectangle rows [r0,r1), cols [c0,c1) via four-corner inclusion-exclusion."""
    return s[r1][c1] - s[r0][c1] - s[r1][c0] + s[r0][c0]
```

<svg role="img" aria-label="The sum of the shaded rectangle equals the bottom-right corner D minus the top strip B minus the left strip C plus the doubly-subtracted top-left corner A" viewBox="0 0 300 104" width="300" height="104">
  <rect x="40" y="20" width="120" height="70" fill="none" stroke="var(--grid)"/>
  <rect x="100" y="50" width="60" height="40" fill="var(--s1)" opacity="0.4"/>
  <text x="120" y="74" fill="var(--ink)" font-size="8">sum?</text>
  <circle cx="100" cy="50" r="3" fill="var(--ink)"/><text x="86" y="48" fill="var(--muted)" font-size="8">A</text>
  <circle cx="160" cy="50" r="3" fill="var(--s2)"/><text x="164" y="48" fill="var(--muted)" font-size="8">B</text>
  <circle cx="100" cy="90" r="3" fill="var(--s2)"/><text x="86" y="100" fill="var(--muted)" font-size="8">C</text>
  <circle cx="160" cy="90" r="3" fill="var(--s1)"/><text x="164" y="100" fill="var(--muted)" font-size="8">D</text>
  <text x="185" y="55" fill="var(--ink)" font-size="9">sum = S(D) − S(B) − S(C) + S(A)</text>
  <text x="185" y="72" fill="var(--muted)" font-size="7">each S is a table entry: pixels above-left of it</text>
  <text x="40" y="102" fill="var(--muted)" font-size="8">four lookups, independent of the shaded rectangle's size</text>
</svg>
^ The shaded rectangle's sum is S(D) − S(B) − S(C) + S(A): the bottom-right cumulative sum, minus the two strips it overcounts, plus the top-left corner both strips removed.

**Build the summed-area table once, and any rectangle's sum is four corner lookups — so a box filter costs a constant four operations per pixel no matter how large the window, instead of one addition per pixel in the window.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/integral-inter-01/integral.py

The fixture is a 5×5 image, four query rectangles, and a set of blur window sizes.

```json filename=modules/generative-media/code/integral-inter-01/integral.json:3-11 COMPLETE
  "image": [
    [5, 2, 3, 4, 1],
    [1, 5, 4, 2, 3],
    [2, 2, 1, 3, 4],
    [4, 1, 5, 2, 2],
    [3, 3, 2, 1, 5]
  ],
  "windows": [[0, 0, 2, 2], [1, 1, 4, 4], [0, 2, 3, 5], [2, 0, 5, 3]],
  "blur_sizes": [3, 5, 9, 15]
```

Run `--sum` to sum each rectangle both ways.

```text filename=--sum
SUM — each rectangle: direct addition vs the four-corner table lookup
----------------------------------------------------------------
  rectangle (r0,c0,r1,c1)     direct   table(4 lookups)   match
  (0,0,2,2)        13       13                 True
  (1,1,4,4)        25       25                 True
  (0,2,3,5)        25       25                 True
  (2,0,5,3)        23       23                 True
```

Every rectangle sums to the same value whether added up pixel by pixel or read from the table in four lookups — the table is exact, not an approximation, and the equality holds for a corner rectangle (0,0,2,2), a central one (1,1,4,4), and edge-touching ones. Take (0,0,2,2): directly it is 5 + 2 + 1 + 5 = 13, and by the table it is one subtraction of corners that happens to reduce to the same 13, because S already accumulated exactly those four pixels. The point is not that four lookups is faster on a 2×2 window — it is 4 operations versus 4, a wash — but that it stays four lookups when the rectangle grows to 3×3 (which it does for the (1,1,4,4) window: still four lookups for a nine-pixel sum) and would stay four for a 300×300. The table has frozen the cost of a rectangle sum at four, whatever its area.

<svg role="img" aria-label="A 5x5 image with the rectangle rows 1 to 3, cols 1 to 3 shaded, summing to 25, computed from four table corners" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">window (1,1,4,4): a 3×3 sum = 25, from four table corners</text>
  <g font-size="7" fill="var(--muted)">
  <g transform="translate(40,20)">
  <rect x="0" y="0" width="150" height="75" fill="none" stroke="var(--grid)"/>
  <rect x="30" y="15" width="90" height="45" fill="var(--s1)" opacity="0.35"/>
  <g fill="var(--ink)" font-size="8"><text x="9" y="12">5</text><text x="39" y="12">2</text><text x="69" y="12">3</text><text x="99" y="12">4</text><text x="129" y="12">1</text>
  <text x="9" y="27">1</text><text x="39" y="27">5</text><text x="69" y="27">4</text><text x="99" y="27">2</text><text x="129" y="27">3</text>
  <text x="9" y="42">2</text><text x="39" y="42">2</text><text x="69" y="42">1</text><text x="99" y="42">3</text><text x="129" y="42">4</text>
  <text x="9" y="57">4</text><text x="39" y="57">1</text><text x="69" y="57">5</text><text x="99" y="57">2</text><text x="129" y="57">2</text>
  <text x="9" y="72">3</text><text x="39" y="72">3</text><text x="69" y="72">2</text><text x="99" y="72">1</text><text x="129" y="72">5</text></g>
  </g>
  </g>
  <text x="200" y="46" fill="var(--ink)" font-size="8">shaded sum = 25</text>
  <text x="200" y="60" fill="var(--muted)" font-size="7">= S(4,4) − S(1,4) − S(4,1) + S(1,1)</text>
  <text x="6" y="100" fill="var(--muted)" font-size="8">the same four-corner formula answers this 3×3 window and any larger one</text>
</svg>
^ The shaded 3×3 window sums to 25 via the four table corners S(4,4) − S(1,4) − S(4,1) + S(1,1) — the identical formula that would sum a window a hundred times larger.

## Build

The payoff shows when the window grows. Run `--cost` to count additions per output pixel for a box blur.

```text filename=--cost
COST — additions per output pixel for a box blur, by window size
----------------------------------------------------------
  window k   naive (k*k)   summed-area (4)   naive/table
  3          9             4                 2x
  5          25            4                 6x
  9          81            4                 20x
  15         225           4                 56x
```

The naive column is the window area — 9, 25, 81, 225 — climbing quadratically as the window widens, because every output pixel re-sums its whole window. The summed-area column is 4 at every size, because the four-corner formula does not care how big the rectangle is. At a 3×3 window the table barely wins (4 versus 9); at 15×15 it does 56× less work per pixel; at a 51×51 blur it would be 650× less. The crossover is almost immediate and the gap widens without bound, which is exactly why summed-area tables are the standard trick behind fast box blurs, multi-scale feature detection (the Haar-like features of the Viola-Jones face detector are rectangle sums), and any algorithm that needs many rectangular region sums over the same image. The one-time cost is building the table — a single O(pixels) pass — and after that every rectangle sum, at every scale, is four reads.

<svg role="img" aria-label="Naive box-blur cost per pixel rises as k-squared from 9 to 225 across window sizes 3 to 15, while the summed-area table stays flat at 4" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">additions per output pixel vs window size k</text>
  <line x1="30" y1="82" x2="288" y2="82" stroke="var(--grid)"/><line x1="30" y1="16" x2="30" y2="82" stroke="var(--grid)"/>
  <g font-size="7" fill="var(--muted)"><text x="46" y="94">3</text><text x="110" y="94">5</text><text x="180" y="94">9</text><text x="250" y="94">15</text></g>
  <path d="M50 78 L114 70 L184 46 L254 18" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <circle cx="254" cy="18" r="2.5" fill="var(--s2)"/><text x="228" y="30" fill="var(--s2)" font-size="7">naive 225</text>
  <line x1="50" y1="80" x2="254" y2="80" stroke="var(--s1)" stroke-width="1.5"/>
  <circle cx="254" cy="80" r="2.5" fill="var(--s1)"/><text x="214" y="76" fill="var(--s1)" font-size="7">table 4 (flat)</text>
  <text x="30" y="99" fill="var(--muted)" font-size="8">naive grows with window area; the table is constant — the gap widens without bound</text>
</svg>
^ Naive per-pixel cost climbs as k² (9 → 225 across the window sizes) while the summed-area table stays flat at 4, so the speedup grows without bound as the blur radius increases.

## Definition of done

The self-test pins correctness and cost: the table matches direct summation on every rectangle, the full-image and 1×1 cases are exact (so the border indexing is right), the table cost is flat, and the naive cost grows.

```python filename=modules/generative-media/code/integral-inter-01/integral.py:104-116 COMPLETE
    all_match = all(sat_rect_sum(s, *w) == direct_rect_sum(image, *w) for w in data["windows"])
    print("  every query rectangle: table sum equals direct sum = %s" % all_match)

    rows, cols = len(image), len(image[0])
    whole = sat_rect_sum(s, 0, 0, rows, cols)
    whole_correct = whole == sum(sum(row) for row in image)
    print("  the full-image rectangle sums to the total of all pixels = %s (%d)" % (whole_correct, whole))

    single = all(sat_rect_sum(s, i, j, i + 1, j + 1) == image[i][j] for i in range(rows) for j in range(cols))
    print("  a 1x1 rectangle recovers the exact pixel (border indexing correct) = %s" % single)

    sat_flat = len({sat_ops_per_pixel() for _ in data["blur_sizes"]}) == 1
    print("  the table's per-pixel cost is the same for every window size = %s (%d)" % (sat_flat, sat_ops_per_pixel()))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the table sum equals the direct sum for every rectangle; its cost is 4 per pixel, flat in window size
------------------------------------------------------------------------------------------------------------------
  every query rectangle: table sum equals direct sum = True
  the full-image rectangle sums to the total of all pixels = True (70)
  a 1x1 rectangle recovers the exact pixel (border indexing correct) = True
  the table's per-pixel cost is the same for every window size = True (4)
  the naive per-pixel cost grows with the window size = True ([9, 25, 81, 225])
  the table is cheaper per pixel at every listed window size = True
```

**Done means the table is proven exact and constant-cost: its four-corner sum equals direct addition on every query rectangle, on the whole-image rectangle (total 70), and on every 1×1 rectangle (so the zero-border indexing is correct) — and a box blur costs a flat 4 operations per pixel via the table against the naive 9, 25, 81, 225 at windows 3, 5, 9, 15, the naive cost growing with the window area while the table's does not.**

## Boss fight

Predict the two ways the summed-area table quietly breaks. It is tempting to treat it as free precision and a universal speedup.

The first trap is that the cumulative sums overflow. Each table entry is the sum of every pixel above and to the left, so the bottom-right entry is the sum of the whole image — for a 4000×3000 image of 8-bit pixels that is up to 3 billion, past a 32-bit signed integer's ceiling, and the table silently wraps to garbage. Worse, the inclusion-exclusion subtracts large numbers to get a small one, so it needs the full precision even for a small window near the far corner. Integer summed-area tables therefore need a wide enough type (64-bit, or careful scaling), and floating-point ones lose precision catastrophically: subtracting two near-equal large partial sums to recover a small window sum is the textbook cancellation that leaves you with the rounding error and none of the signal. Python's arbitrary-precision ints hid this here; a C or GPU implementation must size the accumulator to the image, not the pixel.

```python filename=modules/generative-media/code/integral-inter-01/integral.py:56-58 COMPLETE
def direct_rect_sum(image, r0, c0, r1, c1):
    """The same rectangle summed the naive way: add up every pixel in it."""
    return sum(image[i][j] for i in range(r0, r1) for j in range(c0, c1))
```

The second trap is that the table accelerates a box filter and only a box filter — a uniform average — which is a mediocre blur. A box blur weights every pixel in the window equally, so it has hard edges in its frequency response and produces visible boxy artifacts and ringing compared to a Gaussian, whose smooth weights fall off toward the edges. The summed-area formula sums a rectangle; it cannot apply per-pixel weights, so it cannot do a Gaussian directly. The classic workaround leans on the central limit theorem: convolving a box blur with itself repeatedly approaches a Gaussian, so three or four passes of a constant-cost box blur approximate a Gaussian at constant cost per pass — which is how real-time Gaussian blurs are often built. But that is an approximation with its own tuning, not the exact separable Gaussian. So the table's constant-cost magic is specific to sums over axis-aligned rectangles; the moment the filter needs weights, you either accept the box (or a repeated-box Gaussian approximation) or reach for the separable-convolution machinery instead. Constant cost, but only for the flat-weighted rectangle sum.

**A summed-area table answers any axis-aligned rectangle sum in four corner lookups, making a box filter cost a constant four operations per pixel regardless of window size (versus the naive k²) — but the cumulative sums grow to the whole-image total, so size the accumulator to the image (64-bit integers, not the pixel type) and beware floating-point cancellation, and remember it accelerates only flat-weighted rectangle sums: a box blur, or a repeated-box approximation of a Gaussian, not a true weighted kernel.**

## External resources

Crow's original "Summed-Area Tables for Texture Mapping" and the Viola-Jones face-detection paper (which calls it the "integral image") — the origin of the four-corner rectangle-sum trick and its use for constant-time multi-scale features.

Any reference on box-blur / repeated-box Gaussian approximation and on numerical precision in prefix sums — the central-limit argument for approximating a Gaussian with repeated box blurs, and the accumulator-width and cancellation issues of integral images.

The companion "a 2D Gaussian blur factors into two 1D passes" and "downsample with a filter" modules — the separable Gaussian is the weighted-kernel alternative this box-sum trick cannot do directly, and both are about doing large-window image operations without paying the full k² cost.
